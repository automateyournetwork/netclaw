import importlib.util
from datetime import datetime
import os
from pathlib import Path
import tempfile
import signal
import subprocess
import sys
import time
import unittest

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('collector', root / 'scripts/genie-worlds/collector.py')
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class CollectorTests(unittest.TestCase):
    def setUp(self):
        private_tests = root / '.spec200-local/tests'
        private_tests.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=private_tests)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.adapter = self.directory / 'adapter.py'
        self.calls = self.directory / 'calls'

    def run_capture(self, body, devices=('r1',), **limits):
        self.adapter.write_text('from pathlib import Path\nimport os,time,signal,subprocess,sys\n'
            'qualified_read_only_capture = True\n'
            'def record(device,command):\n'
            f'    with open({str(self.calls)!r}, "a") as f: f.write(device+":"+command+"\\n")\n' + body)
        return collector.collect(devices, self.adapter, 'fixture', evidence_root=self.directory, **limits)

    def test_missing_read_policy_is_not_bypassed(self):
        result = self.run_capture('qualified_read_only_capture=False\n'
            'def capture_once(*a,**k): raise AssertionError("must not execute")\n')
        self.assertFalse(self.calls.exists())
        self.assertTrue(all(o['outcome'] == 'unavailable' for o in result['observations']))

    def test_child_deadline_survives_parent_loss(self):
        sentinel = self.directory/'late-effect'
        started = self.directory/'child-started'
        self.adapter.write_text('import time\nfrom pathlib import Path\n'
            'qualified_read_only_capture=True\n'
            'def capture_once(*a,**k):\n'
            f'    Path({str(started)!r}).write_text("started")\n'
            '    time.sleep(1.5)\n'
            f'    Path({str(sentinel)!r}).write_text("late")\n'
            '    return "raw"\n')
        code = ('import importlib.util\n'
            f's=importlib.util.spec_from_file_location("collector",{str(root/"scripts/genie-worlds/collector.py")!r})\n'
            'm=importlib.util.module_from_spec(s);s.loader.exec_module(m)\n'
            f'm.collect(["r1"],{str(self.adapter)!r},"fixture",evidence_root={str(self.directory)!r},read_timeout=.8)\n')
        parent = subprocess.Popen([sys.executable, '-B', '-c', code],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic()+3
            while not started.exists() and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue(started.exists())
            parent.kill()
            parent.wait(timeout=2)
            time.sleep(1.7)
            self.assertFalse(sentinel.exists())
            self.assertEqual(len(list(self.directory.glob('capture-*/capture-started'))), 1)
            self.assertFalse(list(self.directory.glob('capture-*/result')))
        finally:
            if parent.poll() is None:
                parent.kill()
                parent.wait(timeout=2)

    def test_parse_failure_never_reexecutes_and_facts_stay_private(self):
        result = self.run_capture('def capture_once(device,command,timeout):\n'
            '    record(device,command); return "captured bytes"\n'
            'def parse_captured(device,command,output):\n'
            '    assert output == "captured bytes"\n'
            '    raise ValueError("parser unavailable")\n', devices=('r1','r2'))
        self.assertEqual(len(self.calls.read_text().splitlines()), 6)
        self.assertTrue(all(o['outcome'] == 'parse_failed' for o in result['observations']))
        self.assertFalse(result['facts']['hosted_eligible'])
        self.assertEqual(result['facts']['links'], [])

    def test_partial_neighbors_do_not_invent_an_adjacency(self):
        result = self.run_capture('def capture_once(*a,**k): return "raw"\n'
            'def parse_captured(device,command,output):\n'
            '    if command == "show lldp neighbors detail":\n'
            '        return {"interfaces":{"Eth1":{"port_id":{"Eth2":{"neighbors":{"unmatched":{}}}}}}}\n'
            '    return {}\n')
        self.assertEqual(result['facts']['neighbor_observations'], [])
        self.assertEqual(result['facts']['facts'][-1]['reason'], 'normalization_unqualified')
        self.assertEqual(result['facts']['links'], [])

    def test_hung_capture_is_killed_without_retry_and_other_device_finishes(self):
        began = time.monotonic()
        result = self.run_capture('def capture_once(device,command,timeout):\n'
            '    record(device,command)\n'
            '    if device == "r1":\n'
            '        signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
            f'        Path({str(self.directory / "pid")!r}).write_text(str(os.getpid()))\n'
            '        time.sleep(60)\n'
            '    return "raw"\n'
            'def parse_captured(*a,**k): return {}\n', devices=('r1','r2'), read_timeout=.4)
        self.assertLess(time.monotonic()-began, 2)
        self.assertEqual(sum(x.startswith('r1:') for x in self.calls.read_text().splitlines()), 1)
        self.assertEqual(sum(x.startswith('r2:') for x in self.calls.read_text().splitlines()), 3)
        timed = next(o for o in result['observations'] if o['device_ref'] == 'r1')
        self.assertEqual(timed['outcome'], 'timeout')
        self.assertTrue(timed['capture_outcome_unknown'])
        self.assertFalse(result['complete'])
        with self.assertRaises(ProcessLookupError): os.kill(int((self.directory/'pid').read_text()),0)

    def test_parser_hang_preserves_raw_and_overall_deadline(self):
        began = time.monotonic()
        result = self.run_capture('def capture_once(device,command,timeout):\n'
            '    record(device,command); return "retained evidence"\n'
            'def parse_captured(*a,**k): time.sleep(60)\n', devices=('r1','r2','r3','r4'),
            read_timeout=1, overall_timeout=.4)
        self.assertLess(time.monotonic()-began, 2)
        self.assertEqual(len(self.calls.read_text().splitlines()), 2)
        self.assertTrue(all(o['outcome']=='timeout' and o['raw']=='retained evidence'
                            and not o['capture_outcome_unknown'] for o in result['observations']))

    def test_raw_budget_and_private_artifacts(self):
        result = self.run_capture('def capture_once(*a,**k): return "abcdefgh"\n'
            'def parse_captured(*a,**k): return {}\n', devices=('r1','r2'), byte_limit=10)
        self.assertLessEqual(sum(len(o['raw'].encode()) for o in result['observations']),10)
        self.assertTrue(any(o['failure_reason']=='evidence_limit' for o in result['observations']))
        self.assertLessEqual(sum(p.stat().st_size for p in self.directory.glob('capture-*/raw')),10)
        for path in self.directory.glob('capture-*/*'):
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_parser_process_loss_is_raw_only_not_empty_or_recaptured(self):
        result = self.run_capture('def capture_once(device,command,timeout):\n'
            '    record(device,command); return "retained evidence"\n'
            'def parse_captured(*a,**k): os._exit(7)\n')
        self.assertEqual(len(self.calls.read_text().splitlines()),3)
        self.assertTrue(all(o['outcome']=='raw_only' and o['parsed'] is None
                            and o['raw']=='retained evidence' for o in result['observations']))

    def test_context_preserves_raw_before_cleanup_and_parses_after_disconnect(self):
        result = self.run_capture('from contextlib import contextmanager\n'
            '@contextmanager\n'
            'def capture_context(device,command,timeout,evidence_directory):\n'
            '    record(device,"capture"); yield "retained evidence"\n'
            '    assert (Path(evidence_directory)/"raw").read_text()=="retained evidence"\n'
            '    record(device,"disconnect")\n'
            'def capture_once(*a,**k): raise AssertionError("legacy fallback forbidden")\n'
            'def parse_captured(device,command,output):\n'
            '    record(device,"parse"); return {}\n')
        self.assertEqual(self.calls.read_text().splitlines(),
                         ['r1:capture','r1:disconnect','r1:parse']*3)
        self.assertTrue(result['complete'])
        self.assertTrue(all(o['outcome']=='empty' and not o['cleanup_outcome_unknown']
                            for o in result['observations']))

    def test_context_cleanup_failure_or_loss_retires_device_and_preserves_raw(self):
        for ending in ['raise RuntimeError("private native error")', 'os._exit(7)', 'time.sleep(60)']:
            with self.subTest(ending=ending):
                self.calls.unlink(missing_ok=True)
                result = self.run_capture('from contextlib import contextmanager\n'
                    '@contextmanager\n'
                    'def capture_context(device,command,timeout,evidence_directory):\n'
                    '    record(device,command); yield "retained evidence"\n'
                    f'    if device=="r1": {ending}\n'
                    'def parse_captured(*a,**k): return {}\n',
                    devices=('r1','r2'), read_timeout=.5)
                failed = [o for o in result['observations'] if o['device_ref']=='r1']
                self.assertEqual(len(failed),1)
                self.assertEqual(failed[0]['raw'],'retained evidence')
                self.assertIsNone(failed[0]['parsed'])
                self.assertFalse(failed[0]['capture_outcome_unknown'])
                self.assertTrue(failed[0]['cleanup_outcome_unknown'])
                self.assertIn(failed[0]['outcome'],('raw_only','timeout'))
                self.assertEqual(sum(o['device_ref']=='r2' for o in result['observations']),3)
                self.assertFalse(result['complete'])

    def test_context_budget_refusal_still_cleans_up_without_parsing(self):
        result = self.run_capture('from contextlib import contextmanager\n'
            '@contextmanager\n'
            'def capture_context(device,command,timeout,evidence_directory):\n'
            '    try: yield "too much raw"\n'
            '    finally: record(device,"disconnect")\n'
            'def parse_captured(*a,**k): raise AssertionError("no admitted raw")\n',byte_limit=2)
        self.assertEqual(self.calls.read_text().splitlines(),['r1:disconnect'])
        self.assertEqual(result['observations'][0]['failure_reason'],'evidence_limit')
        self.assertFalse(result['observations'][0]['cleanup_outcome_unknown'])

    def test_context_entry_failure_never_uses_legacy_fallback(self):
        result = self.run_capture('from contextlib import contextmanager\n'
            '@contextmanager\n'
            'def capture_context(device,command,timeout,evidence_directory):\n'
            '    record(device,"connect"); raise RuntimeError("private connection failure")\n'
            '    yield "unreachable"\n'
            'def capture_once(*a,**k): raise AssertionError("fallback forbidden")\n'
            'def parse_captured(*a,**k): raise AssertionError("parse forbidden")\n')
        self.assertEqual(self.calls.read_text().splitlines(),['r1:connect'])
        self.assertTrue(result['observations'][0]['capture_outcome_unknown'])
        self.assertTrue(result['observations'][0]['cleanup_outcome_unknown'])

    def test_context_parser_loss_keeps_completed_cleanup_distinct(self):
        result = self.run_capture('from contextlib import contextmanager\n'
            '@contextmanager\n'
            'def capture_context(device,command,timeout,evidence_directory):\n'
            '    record(device,command); yield "retained evidence"\n'
            'def parse_captured(*a,**k): os._exit(7)\n')
        self.assertEqual(len(self.calls.read_text().splitlines()),3)
        self.assertTrue(all(o['outcome']=='raw_only' and not o['cleanup_outcome_unknown']
                            and not o['capture_outcome_unknown'] for o in result['observations']))

    def test_capture_process_loss_is_unknown_and_not_retried(self):
        result = self.run_capture('def capture_once(device,command,timeout):\n'
            '    record(device,command); os._exit(9)\n')
        self.assertEqual(len(self.calls.read_text().splitlines()),1)
        self.assertEqual(result['observations'][0]['outcome'],'unavailable')
        self.assertTrue(result['observations'][0]['capture_outcome_unknown'])
        self.assertFalse(result['complete'])

    def test_owned_descendants_cannot_continue_after_timeout(self):
        sentinel = self.directory / 'late-effect'
        child_code = f'import time; from pathlib import Path; time.sleep(.7); Path({str(sentinel)!r}).write_text("late")'
        self.run_capture('def capture_once(device,command,timeout):\n'
            '    record(device,command)\n'
            f'    subprocess.Popen([sys.executable,"-c",{child_code!r}])\n'
            '    time.sleep(60)\n', read_timeout=.3)
        time.sleep(.8)
        self.assertFalse(sentinel.exists())
        self.assertEqual(len(self.calls.read_text().splitlines()),1)

    def test_parallel_worker_bound_and_serial_device_reads(self):
        result = self.run_capture('def capture_once(device,command,timeout):\n'
            '    record(device,"start"); time.sleep(.08); record(device,"end"); return "raw"\n'
            'def parse_captured(*a,**k): return {}\n', devices=('r1','r2','r3','r4'))
        active, maximum = set(), 0
        for line in self.calls.read_text().splitlines():
            device, action = line.split(':')
            if action == 'start':
                self.assertNotIn(device, active)
                active.add(device)
                maximum = max(maximum,len(active))
            else:
                active.remove(device)
        self.assertEqual(maximum,2)
        self.assertFalse(active)
        self.assertTrue(result['complete'])

    def test_limits_cannot_be_expanded(self):
        for limits in ({'read_timeout':31},{'overall_timeout':181},{'read_timeout':float('nan')},
                       {'byte_limit':collector.LIMIT+1}):
            with self.assertRaisesRegex(ValueError,'collection_limit'):
                collector.collect(['r1'],self.adapter,'fixture',evidence_root=self.directory,**limits)

    def test_nonprivate_or_symlink_root_refused_before_capture(self):
        self.adapter.write_text('raise AssertionError("must not import")')
        os.chmod(self.directory,0o755)
        with self.assertRaisesRegex(ValueError,'private_evidence_root'):
            collector.collect(['r1'],self.adapter,'fixture',evidence_root=self.directory)
        os.chmod(self.directory,0o700)
        alias = self.directory/'alias'
        alias.symlink_to(self.directory, target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'private_evidence_root'):
            collector.collect(['r1'],self.adapter,'fixture',evidence_root=alias)

    def test_detailed_profile_exact_reads_spacing_and_parse_failure_no_retry(self):
        result = self.run_capture('def capture_once(device,command,timeout):\n'
            '    record(device,command+":"+str(time.monotonic())); return "captured"\n'
            'def parse_captured(device,command,output):\n'
            '    assert output == "captured"\n'
            '    if command == "show interfaces": raise ValueError("unavailable parser")\n'
            '    return {}\n', devices=('r1','r2','r3','r4'), profile='detailed')
        self.assertTrue(result['complete'])
        self.assertEqual(len(result['observations']),24)
        lines = [line.split(':') for line in self.calls.read_text().splitlines()]
        for device in ('r1','r2','r3','r4'):
            calls = [(c,float(t)) for d,c,t in lines if d == device]
            self.assertEqual([c for c,t in calls], list(collector.facts.DETAILED_COMMANDS))
            self.assertGreaterEqual(calls[-1][1]-calls[-2][1],10)
            samples = [o for o in result['observations'] if o['device_ref']==device and o['command']=='show interfaces']
            self.assertEqual([o['sample_index'] for o in samples],[1,2])
            self.assertTrue(all(o['outcome']=='parse_failed' for o in samples))
            gap = datetime.fromisoformat(samples[1]['started_at']) - datetime.fromisoformat(samples[0]['finished_at'])
            self.assertGreaterEqual(gap.total_seconds(),10)
        self.assertFalse(result['facts']['hosted_eligible'])
        self.assertEqual(result['facts']['links'],[])

    def test_detailed_deadline_expires_during_sample_wait_without_extra_read(self):
        began = time.monotonic()
        result = self.run_capture('def capture_once(device,command,timeout):\n'
            '    record(device,command); return "raw"\n'
            'def parse_captured(*a,**k): return {}\n',profile='detailed',overall_timeout=1)
        self.assertLess(time.monotonic()-began,2)
        self.assertFalse(result['complete'])
        self.assertEqual(self.calls.read_text().splitlines().count('r1:show interfaces'),1)
        self.assertEqual(len(result['observations']),5)

    def test_detailed_bounds_and_profile_are_closed(self):
        for limits in ({'profile':'other'}, {'profile':'detailed','overall_timeout':241}):
            with self.assertRaises(ValueError):
                collector.collect(['r1'],self.adapter,'fixture',evidence_root=self.directory,**limits)

    def test_detailed_parsed_payload_is_not_guessed_into_neighbors_or_counters(self):
        observations = [dict(id=str(i),device_ref='r1',classification='private',
            command=command,finished_at='2026-11-22T00:00:00Z',sha256='a'*64,
            parser_version='fixture',outcome='observed',parsed={
                'interfaces':{'Eth1':{'port_id':{'Eth2':{'neighbors':{'unproven':{}}}}}},
                'in_octets':123})
            for i,command in enumerate(('show cdp neighbors detail','show interfaces'))]
        result = collector.facts.normalize(observations,profile='detailed')
        self.assertEqual(result['neighbor_observations'],[])
        self.assertEqual(result['links'],[])
        self.assertEqual([f['reason'] for f in result['facts']],['normalization_unqualified']*2)
        self.assertTrue(all(f['value'] is None for f in result['facts']))
        with self.assertRaisesRegex(ValueError,'private_observation_required'):
            collector.facts.normalize(observations)

if __name__ == '__main__': unittest.main()
