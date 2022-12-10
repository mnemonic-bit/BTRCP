
import pytest
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import runcmdutils
import prelude


def _mk_disk_image(path):
    #dd if=/dev/zero of=sparse_file bs=1 count=0 seek=512M
    cmd_args = ['dd', 'if=/dev/zero', 'of=' + str(path), 'bs=1', 'count=0', 'seek=512M']
    res = run_cmd (cmd_args, machine = path.get_context())
    if (res.returncode == 0):
        return fst (res.stdout.rstrip().split())
    return None

