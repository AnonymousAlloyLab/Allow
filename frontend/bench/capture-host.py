#!/usr/bin/env python3
"""Capture server-host metadata without querying the application or claiming browser affinity."""
import json
import os
from pathlib import Path
import platform
import subprocess
from datetime import datetime, timezone


def main():
    """Print an independently timestamped, nonsecret host inventory."""
    cpu = 'unavailable'
    for line in Path('/proc/cpuinfo').read_text().splitlines():
        if line.startswith('model name'):
            cpu = line.split(':', 1)[1].strip()
            break
    memory = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
    java = subprocess.run(['java', '-version'], capture_output=True, text=True, check=False)
    print(json.dumps({'timestamp_utc':datetime.now(timezone.utc).isoformat(), 'scope':'server host; browser CPU affinity not attested',
                      'platform':platform.platform(), 'cpu_model':cpu, 'logical_cpus':os.cpu_count(), 'ram_bytes':memory,
                      'java_version':java.stderr.strip(), 'java_exit_code':java.returncode}, indent=2))


if __name__ == '__main__':
    main()
