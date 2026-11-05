"""Owned, deadline-bounded synthetic document verification supervisor."""
import asyncio
import json
import os
from pathlib import Path
import signal
import tempfile
import time

from .types import Verification

MAX_SOURCE = 32768
MAX_FRAME = 1048576
POLICY = 'allow-ai-synthetic-source-v1'


async def _drain(task):
    """Hold ownership through repeated cancellation until a cleanup task finishes."""
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    result = task.result()
    if cancelled:
        raise asyncio.CancelledError
    return result


class DocumentVerifier:
    """Run a disposable private supervisor without passing credentials to children."""

    def __init__(self, target):
        """Capture only the trusted build path; hashing happens in the supervisor."""
        self._target = Path(target).absolute()
        self._build = ''

    @property
    def build_identity(self):
        """Return the pinned successful worker build identity, if established."""
        return self._build

    async def _cleanup(self, launch):
        """Wait for an owned launch, then kill and reap its entire process group."""
        try:
            process = await launch
        except Exception:
            return
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        await process.wait()

    async def _exchange(self, request, timeout):
        """Bound launch and computation, while always draining owned cleanup."""
        with tempfile.TemporaryFile() as output:
            worker = Path(__file__).with_name('verifier_worker.py')
            launch = asyncio.create_task(asyncio.create_subprocess_exec(
                '/usr/bin/python3', '-I', '-B', str(worker), stdin=asyncio.subprocess.PIPE,
                stdout=output, stderr=asyncio.subprocess.DEVNULL, env={}, close_fds=True,
                start_new_session=True))
            try:
                async with asyncio.timeout(timeout):
                    process = await asyncio.shield(launch)
                    await process.communicate(request)
                    if process.returncode != 0:
                        raise ValueError('worker_failed')
                    output.seek(0)
                    return output.read(MAX_FRAME + 1)
            finally:
                await _drain(asyncio.create_task(self._cleanup(launch)))

    async def __call__(self, source, timeout):
        """Return a bounded observation; expiry and uncertain cleanup fail closed."""
        started = time.monotonic()
        try:
            if not isinstance(source, str) or len(source.encode('utf-8')) > MAX_SOURCE:
                return Verification('INVALID', code='SOURCE_PROFILE_INVALID')
            limit = min(10.0, float(timeout))
            if limit <= 0:
                return Verification('UNAVAILABLE', code='WORKER_TIMEOUT')
            request = json.dumps({'target': str(self._target), 'source': source, 'expected': self._build},
                                 ensure_ascii=True).encode()
            remaining = limit - (time.monotonic() - started)
            if remaining <= 0:
                return Verification('UNAVAILABLE', code='WORKER_TIMEOUT')
            raw = await self._exchange(request, remaining)
            if time.monotonic() - started >= limit:
                return Verification('UNAVAILABLE', code='WORKER_TIMEOUT')
            return self._observation(raw)
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            return Verification('UNAVAILABLE', code='WORKER_TIMEOUT')
        except Exception:
            return Verification('UNAVAILABLE', code='WORKER_UNAVAILABLE')

    def _observation(self, raw):
        """Check the supervisor result and preserve the established build pin."""
        if len(raw) > MAX_FRAME or raw.count(b'\n') != 1 or not raw.endswith(b'\n'):
            raise ValueError('worker_frame')
        value = json.loads(raw)
        if not isinstance(value, dict) or value.get('status') not in ('VALIDATED', 'INVALID', 'UNAVAILABLE'):
            raise ValueError('worker_protocol')
        build = value.get('build')
        if build:
            if self._build and self._build != build:
                return Verification('UNAVAILABLE', code='WORKER_BUILD_CHANGED')
            self._build = build
        if value['status'] == 'VALIDATED':
            return Verification('VALIDATED', projection=value['projection'], source_hash=value['source_hash'],
                                evidence={'worker_build': build, 'policy': POLICY,
                                          'scope': 'synthetic_source_validation_only'})
        return Verification(value['status'], code=value.get('code'))
