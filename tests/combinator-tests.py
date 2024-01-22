
import sys
from plumbum.cmd import echo, cat, pv, head, tee

# cmd = (cat['/dev/zero'] | pv['-ptr', '-L', '10M'] >= sys.stdout)

# cmd = (cat['/dev/zero'] | head['-c', '10M'])

# cmd = cat['/dev/zero'] | pv['-ptr', '-L', '10M']
# cmd = cmd >= sys.stdout

# cmd = cat['/dev/zero'] | pv['-ptr', '-L', '10M'] | tee['/dev/null']

# cmd = cat['/dev/zero'] | (pv['-ptr', '-L', '10M'] >= sys.stdout) | tee['/dev/null']

cmd = cat['/dev/zero'] | head['-c', '10'] | (pv['-ptr', '-L', '10M'] >= sys.stdout) | tee['/dev/null']

# cmd = cat['/dev/zero'] | head['-c', '10'] | (pv['-ptr', '-L', '10M'] >= sys.stdout) | tee['tee-out.txt']

# cmd = echo['hello'] | head['-c', '1M'] | tee['test_file.txt']

# cmd = cat['test_input.txt'] | head['-c', '1M'] | tee['test_output.txt']

# not OK
# cmd = cat['test_input.txt'] | tee['test_output.txt']


res = cmd.run(retcode = None)

print(f"return code: {res[0]}, len(stdout)={len(res[1])}, len(stderr)={len(res[2])}")
