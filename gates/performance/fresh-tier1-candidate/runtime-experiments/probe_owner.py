#!/usr/bin/env python3
"""Tiny frozen containment witness: one supervisor and one idle inherited child."""
import os
from pathlib import Path
import subprocess
import sys
import time

from harness_common import process_identity, write_private


def main():
    """Publish two exact owned incarnations and then remain idle until service cleanup."""
    os.umask(0o077)
    root = Path(__file__).resolve().parent.parent
    child = subprocess.Popen([sys.executable, '-I', '-c', 'import time; time.sleep(25)'],
                             env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'})
    write_private(root/'.gate/probe-owner.json', {'supervisor': process_identity(os.getpid()),
                  'child': process_identity(child.pid)})
    time.sleep(25)


if __name__ == '__main__':
    main()
