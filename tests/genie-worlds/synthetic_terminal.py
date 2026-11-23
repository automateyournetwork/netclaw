"""Independent PTY peer for installed Unicon qualification; never opens a socket.

Every received line is durably recorded before replying, including unexpected
setup commands. This file must never be used as a production device adapter.
"""
import json
import os
from pathlib import Path
import sys

transcript = Path(sys.argv[1])
expected = sys.argv[2]
prompt = 'Router#' if sys.argv[3] == 'enable' else 'Router>'
print(prompt, end='', flush=True)
for line in sys.stdin:
    command = line.rstrip('\r\n')
    with transcript.open('a') as output:
        output.write(json.dumps(command) + '\n')
        output.flush()
        os.fsync(output.fileno())
    if command == expected:
        response = (Path(sys.argv[4]).read_text() if len(sys.argv) == 5
                    else 'SPEC200 independent synthetic raw response')
        print('\r\n' + response + '\r\n', end='')
    elif command:
        print('\r\n% Invalid input detected at marker.\r\n', end='')
    print(prompt, end='', flush=True)
