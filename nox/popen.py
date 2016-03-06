import subprocess
import sys


def popen(args, env=None, silent=False):
    stdout = None

    if silent:
        stdout = subprocess.PIPE

    proc = subprocess.Popen(
        args, env=env, stdout=stdout, stderr=subprocess.STDOUT)

    try:
        out, err = proc.communicate()
        sys.stdout.flush()

    except KeyboardInterrupt:
        proc.terminate()
        proc.wait()
        raise

    return_code = proc.wait()

    return return_code, out.decode('utf-8') if out else ''
