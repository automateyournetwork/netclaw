import shlex
import tempfile
import unittest
from pathlib import Path

from r10_processes import owned_command


class OwnedProcesses(unittest.TestCase):
    def test_other_runs_and_existing_border_member_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve() / 'r10-run-fresh'
            member = root / 'member-one'
            def command(base):
                return shlex.join(['/usr/bin/python3', '-I', '-B', str(base / 'source/scripts/protected-role.py'),
                                   '--contract', str(base / 'contract.json'), 'run'])
            self.assertTrue(owned_command(command(member), root))
            for other in [root.parent / 'r10-run-old/member-one', root.parent / 'genie/member-one',
                          root / 'not-a-member', root / 'member-one/nested']:
                self.assertFalse(owned_command(command(other), root))
            self.assertFalse(owned_command(command(member).replace('source/scripts/protected-role.py', 'other.py'), root))
            self.assertFalse(owned_command(command(member) + ' --extra', root))


if __name__ == '__main__': unittest.main()
