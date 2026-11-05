#!/usr/bin/python3
"""Keep an explicit WSL invocation alive while the preinstalled service is active."""
import sys
if not sys.flags.isolated or not sys.flags.dont_write_bytecode:
    raise SystemExit('Invoke with /usr/bin/python3 -I -B')

import argparse
import subprocess
import time


def selected_unit(slot):
    """Map only the closed installation selector to a read-only service observation."""
    if slot == 'PRIMARY':
        return 'allow.service'
    if slot == 'PUBLIC_REPLACEMENT':
        return 'allow-public.service'
    raise ValueError('Unknown installation slot')


def main():
    """Observe only the fixed service; lifecycle ownership remains with Windows."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installation-slot', choices=['PRIMARY', 'PUBLIC_REPLACEMENT'], default='PRIMARY')
    args = parser.parse_args()
    unit = selected_unit(args.installation_slot)
    while True:
        result = subprocess.run(['/usr/bin/systemctl', 'is-active', '--quiet', unit],
                                stdin=subprocess.DEVNULL, timeout=10, check=False)
        if result.returncode:
            raise SystemExit('Selected service is not active')
        time.sleep(5)


if __name__ == '__main__':
    main()
