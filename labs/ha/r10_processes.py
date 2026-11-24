"""Stop only member processes belonging to an explicit R10 evidence root."""
import argparse
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess


def owned_command(command, root):
    try:
        args = shlex.split(command)
        index = args.index('--contract')
        contract = Path(args[index + 1])
        member = contract.parent
        return (contract.is_absolute() and contract.name == 'contract.json'
                and member.parent == root and re.fullmatch(r'member-[A-Za-z0-9_-]+', member.name)
                and member.resolve() == member
                and str(member / 'source/scripts/protected-role.py') in args[:index]
                and args[index + 2:] == ['run'])
    except (ValueError, IndexError):
        return False


def stop(root):
    root = Path(root).absolute()
    if root.resolve() != root or not root.name.startswith('r10-run-'):
        raise ValueError('exact_r10_root_required')
    output = subprocess.run(['ps', '-U', str(os.getuid()), '-o', 'pid=,command='],
                            capture_output=True, text=True, check=True).stdout
    stopped = []
    for line in output.splitlines():
        pid, _, command = line.strip().partition(' ')
        if not pid.isdigit() or not owned_command(command.strip(), root):
            continue
        # Recheck immediately before the signal; a stale PID is never enough.
        check = subprocess.run(['ps', '-p', pid, '-o', 'command='], capture_output=True, text=True, check=True)
        if check.stdout.strip() != command.strip():
            raise ValueError('member_process_changed')
        os.kill(int(pid), signal.SIGTERM)
        stopped.append(int(pid))
    return stopped


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    print({'stopped_owned_pids': stop(parser.parse_args().root)})
