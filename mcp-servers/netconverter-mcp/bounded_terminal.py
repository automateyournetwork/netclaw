"""Byte-only stdio size supervisor around the operator's official Terminal.

The official SDK still owns MCP framing/parsing/session behavior. This process
only bounds newline-delimited bytes before the SDK can accumulate an unbounded
line. It does not inspect or alter messages, credentials, arguments or outputs.
"""
import os
import signal
import subprocess
import sys
import threading

LIMIT=2*1024*1024

def main():
    if len(sys.argv)<2:return 2
    child=subprocess.Popen(sys.argv[1:],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                           stderr=sys.stderr,start_new_session=os.name!='nt')
    def stop(signum,frame):raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    def stdin_pump():
        try:
            while data:=os.read(sys.stdin.fileno(),65536):
                child.stdin.write(data);child.stdin.flush()
            child.stdin.close()
        except (OSError,ValueError):pass
    threading.Thread(target=stdin_pump,daemon=True).start()
    size=0
    try:
        while chunk:=os.read(child.stdout.fileno(),65536):
            parts=chunk.split(b'\n')
            for index,part in enumerate(parts):
                size+=len(part)
                if size>LIMIT:
                    print('Terminal response exceeds the private transport limit.',file=sys.stderr);return 2
                if index<len(parts)-1:size=0
            sys.stdout.buffer.write(chunk);sys.stdout.buffer.flush()
        return child.wait(timeout=5)
    finally:
        if child.poll() is None:
            if os.name=='nt':child.terminate()
            else:os.killpg(child.pid,signal.SIGTERM)
            try:child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                if os.name=='nt':child.kill()
                else:os.killpg(child.pid,signal.SIGKILL)
                child.wait(timeout=3)
        child.stdout.close()

if __name__=='__main__':raise SystemExit(main())
