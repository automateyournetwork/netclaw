import os, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(__file__))
import r10_group as g
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
NODES = 'nne1 20.1.1.1 10.198.1.4\new1 20.1.1.2 10.198.2.4\nase1 20.1.1.3 10.198.3.4\n'


class Group(unittest.TestCase):
    def setUp(self):
        self.nodes = g.read_nodes(NODES)

    def test_azure_names_and_two_remote_voters(self):
        s = g.node_spec('azure', 'nne1', self.nodes, '20261115')
        self.assertEqual(s['etcd'], ['azus.r10-20261115.azure.internal:12379', 'azse.r10-20261115.azure.internal:12379'])
        self.assertEqual(s['resolve']['azus.r10-20261115.azure.internal'], '10.198.2.4')
        self.assertNotIn('azca', str(s))                      # never the node's own host

    def test_gcp_names_are_gce_zonal_internal(self):
        s = g.node_spec('gcp', 'ew1', self.nodes, project='p-1', vm_prefix='nc198-gc')
        self.assertIn('nc198-gc-nne1.northamerica-northeast1-b.c.p-1.internal:12379', s['etcd'])
        self.assertEqual(len(s['peers']), 2)

    def test_prepare_args_carry_internal_name_third_field(self):
        a = g.prepare_args('azure', self.nodes, '20261115')
        self.assertEqual(a[1], 'nne1=10.198.1.4,20.1.1.1,azca.r10-20261115.azure.internal')
        self.assertEqual(a.count('--node'), 3)

    def test_refusals(self):
        for bad in ('nne1 1.1.1.1 10.0.0.1\n', NODES + 'nne1 1.1.1.1 10.0.0.1\n', 'xx 1.1.1.1 10.0.0.1\n' + NODES,
                    'nne1 a.b.c.d 10.0.0.1\new1 1.1.1.1 10.0.0.2\nase1 1.1.1.2 10.0.0.3\n'):
            with self.assertRaises(ValueError): g.read_nodes(bad)
        with self.assertRaises(ValueError): g.internal_host('azure', 'nne1', 'bad')
        with self.assertRaises(ValueError): g.internal_host('gcp', 'nne1', None)
        with self.assertRaises(ValueError): g.internal_host('aws', 'nne1', '20261115')

    def test_specs_pass_the_real_policy_builder(self):
        try:
            import r09a_policy as p
        except Exception:
            self.skipTest('r09a_policy deps (yaml) unavailable')
        for prov, kw in (('azure', {'run_date': '20261115'}), ('gcp', {'project': 'netclaw-1', 'vm_prefix': 'nc198-gc'})):
            for c in g.CODES:
                p.build_policy(g.node_spec(prov, c, self.nodes, **kw))

    def test_cli(self):
        with tempfile.NamedTemporaryFile('w', suffix='.txt') as f:
            f.write(NODES); f.flush()
            r = subprocess.run([sys.executable, os.path.join(ROOT, 'labs/ha/r10_group.py'), 'node-spec', '--provider', 'azure',
                                '--run-date', '20261115', '--nodes', f.name, '--code', 'ew1'], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0); self.assertIn('azca.r10-20261115', r.stdout)




class Federation(unittest.TestCase):
    def roots(self, tmp):
        import json
        out = []
        for tag, cluster in (('a', 'aaaaaaaa-0000-4000-8000-000000000001'), ('b', 'bbbbbbbb-0000-4000-8000-000000000002')):
            root = os.path.join(tmp, tag)
            for sub in ('identity', 'transport'):
                os.makedirs(os.path.join(root, sub))
            open(os.path.join(root, 'identity/manifest.json'), 'w').write('{"m":"%s"}' % tag)
            open(os.path.join(root, 'identity/root.crt'), 'w').write('ROOT-' + tag)
            open(os.path.join(root, 'transport/transport-ca.crt'), 'w').write('CA-' + tag + '\n')
            json.dump({'cluster_id': cluster, 'generation': cluster.replace('0001', '1111').replace('0002', '2222'),
                       'anchor_key_id': tag * 64,
                       'nodes': [{'code': c, 'dns': '%s-%s.automateyournetwork.com' % (c, tag * 6 if tag == 'a' else 'b0be28'),
                                  'public': '34.0.0.%d' % i} for i, c in enumerate(g.CODES, 1)]},
                      open(os.path.join(root, 'summary.json'), 'w'))
            out.append(root)
        return out

    def test_peer_config_pins_the_peer_and_defaults_to_its_own_ports(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = self.roots(tmp)
            config, files = g.peer_config(a, b, 'gcp', members=['m1'], tools=['t1'])
            peer = config['peers'][0]
            self.assertEqual(config['listen'], {'host': '127.0.0.1', 'port': 7445})
            self.assertEqual(peer['cluster_id'], 'bbbbbbbb-0000-4000-8000-000000000002')
            self.assertEqual(peer['grant'], {'actions': g.FULL_ACTIONS, 'members': ['m1'], 'tools': ['t1']})
            self.assertEqual(files['peer/gcp/root.crt'], b'ROOT-b')
            self.assertNotIn(b'root.key', b''.join(files.values()))
            self.assertEqual(config['transport_certificate_file'], '/sandbox/nc182/transport/node.crt')

    def test_peer_config_refuses_itself_and_bad_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = self.roots(tmp)
            with self.assertRaises(ValueError): g.peer_config(a, a, 'self')
            with self.assertRaises(ValueError): g.peer_config(a, b, 'Bad Label')

    def test_merged_configs_bundle_every_peer_ca(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = self.roots(tmp)
            c = os.path.join(tmp, 'c'); os.makedirs(c); import shutil
            shutil.copytree(os.path.join(b, 'identity'), os.path.join(c, 'identity')); shutil.copytree(os.path.join(b, 'transport'), os.path.join(c, 'transport'))
            import json
            summary = json.load(open(os.path.join(b, 'summary.json'))); summary['cluster_id'] = 'cccccccc-0000-4000-8000-000000000003'
            json.dump(summary, open(os.path.join(c, 'summary.json'), 'w'))
            config, files = g.merge_peer_configs([g.peer_config(a, b, 'one'), g.peer_config(a, c, 'two')])
            self.assertEqual([p['label'] for p in config['peers']], ['one', 'two'])
            self.assertEqual(files['peer/peer-ca-bundle.pem'].count(b'CA-b'), 2)

    def test_node_spec_adds_exact_federation_egress_that_passes_the_real_policy_builder(self):
        try:
            import r09a_policy as p
        except Exception:
            self.skipTest('r09a_policy deps (yaml) unavailable')
        with tempfile.TemporaryDirectory() as tmp:
            a, b = self.roots(tmp)
            import json
            peer = json.load(open(os.path.join(b, 'summary.json')))
            spec = g.node_spec('azure', 'nne1', self.nodes, '20261115', peer_summaries=[peer])
            self.assertEqual(len(spec['federation_peers']), 3)
            self.assertTrue(all(x.endswith(':7445') for x in spec['federation_peers']))
            self.assertEqual(spec['resolve']['nne1-b0be28.automateyournetwork.com'], '34.0.0.1')
            self.assertGreater(p.validate_policy(p.render_yaml(p.build_policy(spec)))['endpoints'], 0)
            self.assertNotIn('federation_peers', g.node_spec('azure', 'nne1', self.nodes, '20261115'))

    def setUp(self):
        self.nodes = g.read_nodes(NODES)


if __name__ == '__main__':
    unittest.main()
