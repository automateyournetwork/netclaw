"""Member discovery must preserve runtime and platform qualification boundaries."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/lib'))
from setup_plan import PlanValidator
from test_setup_plan import sample_plan


class ConvergenceProfileTests(unittest.TestCase):
    def setUp(self):
        self.validator = PlanValidator(ROOT)
        self.plan = sample_plan()
        border = self.plan['claws'][0]
        border['role'] = 'border'
        border['capabilities'].update(components=['n2n', 'protocol'], skills=[])
        member = copy.deepcopy(border)
        member.update(id='evidence', role='member', runtimeHome='/private/tmp/netclaw-fixture/evidence',
                      workspace='/private/tmp/netclaw-fixture/evidence/workspace')
        member['capabilities'].update(profile='convergence', components=['n2n', 'convergence-read'],
                                      skills=['convergence-observations'])
        member['settings']['ANTHROPIC_API_KEY']['owner'] = 'evidence'
        member['endpoints'] = {k: v + 100 for k, v in border['endpoints'].items()}
        member['service']['name'] = 'netclaw-evidence'
        self.plan.update(shape='risk', claws=[border, member])
        self.plan['verification']['risk'] = True
        self.member = member

    def codes(self):
        return {e['code'] for e in self.validator.inspect(self.plan)['errors']}

    def test_profile_requires_reader_and_rejects_hermes(self):
        self.assertNotIn('unsupported_member_profile', self.codes())
        self.member['capabilities']['components'].remove('convergence-read')
        self.assertIn('member_profile_components_missing', self.codes())
        self.member['capabilities']['components'].append('convergence-read')
        self.member['harness'] = 'hermes'
        self.assertIn('unsupported_member_profile', self.codes())

    def test_profile_does_not_expand_component_platform_qualification(self):
        for platform in ('macos', 'wsl2'):
            self.plan['host'].update(platform=platform, remote='local' if platform == 'macos' else 'wsl',
                                     osVersion='26.0' if platform == 'macos' else '24.04')
            self.assertIn('unsupported_component_platform', self.codes())
            self.assertFalse(self.validator.inspect(self.plan)['applyReady'])


if __name__ == '__main__':
    unittest.main()
