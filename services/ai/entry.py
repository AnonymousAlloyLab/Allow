#!/usr/bin/python3
"""Isolated stdlib-first launcher; dependencies are verified before any imports."""
import sys

if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
    raise SystemExit('Invoke with /usr/bin/python3 -I -S -B')

import asyncio
import hashlib
import json
import os
from pathlib import Path
import resource
import types

ROOT = Path(__file__).absolute().parents[2]


def sources():
    """Check shipped AI sources against the deployment manifest when installed."""
    manifest = ROOT / 'MANIFEST.json'
    if not manifest.exists():
        return
    raw = manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != (ROOT / 'MANIFEST.sha256').read_text().split()[0]:
        raise ValueError('manifest')
    files = json.loads(raw)['files']
    for name, expected in files.items():
        if name.startswith(('services/ai/', 'retrieval/allow_ai/')):
            path = ROOT / name
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError('source')
    for name in ['entry.py', 'runtime.py', 'bridge.py', 'protocol.py', 'journal.py']:
        if 'services/ai/' + name not in files:
            raise ValueError('missing_source')


def runtime():
    """Load the stdlib verifier by exact path, before adding dependency imports."""
    sources()
    path = ROOT / 'services/ai/runtime.py'
    module = types.ModuleType('allow_ai_runtime')
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    site = module.verify(ROOT)
    sys.path.extend([str(site), str(ROOT / 'retrieval'), str(ROOT / 'services/ai')])


async def main():
    """Run only the fixed IPC bridge and emit no secret-bearing exception text."""
    from protocol import Channel
    from bridge import run
    channel = await Channel.stdio()
    try:
        async with asyncio.timeout(60):
            await run(channel, ROOT)
    except (Exception, asyncio.CancelledError):
        try:
            channel.send('RESULT', {'status': 'FAILED', 'attempts': 0, 'binding': '',
                                   'source': '', 'explanation': '', 'verification': None,
                                   'code': 'BRIDGE_UNAVAILABLE', 'http_status': None})
        except Exception:
            pass
        return 1
    return 0


if __name__ == '__main__':
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        os.umask(0o077)
        runtime()
        raise SystemExit(asyncio.run(main()))
    except Exception:
        raise SystemExit(1) from None
