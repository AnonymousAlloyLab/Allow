"""Tests for bounded verifier supervisor ownership and input handling."""
import asyncio
import os
import sys
import unittest
from unittest.mock import patch

from allow_ai.verification import DocumentVerifier


class VerifierTests(unittest.IsolatedAsyncioTestCase):
    """Exercise real subprocess timeout and repeated cancellation cleanup."""

    async def test_source_limit_without_launch(self):
        """Oversized source cannot reach the supervisor."""
        verifier = DocumentVerifier('/tmp/unused')
        result = await verifier('x' * 32769, 1)
        self.assertEqual((result.status, result.code), ('INVALID', 'SOURCE_PROFILE_INVALID'))

    async def test_timeout_kills_and_reaps_supervisor(self):
        """A slow owned subprocess is killed before timeout is returned."""
        real = asyncio.create_subprocess_exec
        processes = []

        async def launch(*args, **kwargs):
            process = await real(sys.executable, '-c', 'import time; time.sleep(30)', **kwargs)
            processes.append(process)
            return process

        with patch('allow_ai.verification.asyncio.create_subprocess_exec', side_effect=launch):
            result = await DocumentVerifier('/tmp/unused')('sig A {}', 0.1)
        self.assertEqual((result.status, result.code), ('UNAVAILABLE', 'WORKER_TIMEOUT'))
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].returncode)

    async def test_repeated_cancel_reaps_supervisor(self):
        """A second cancellation cannot interrupt unfinished shielded cleanup."""
        real = asyncio.create_subprocess_exec
        processes = []
        ready, cleaning, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
        verifier = DocumentVerifier('/tmp/unused')
        actual_cleanup = verifier._cleanup

        async def launch(*args, **kwargs):
            process = await real(sys.executable, '-c', 'import time; time.sleep(30)', **kwargs)
            processes.append(process)
            ready.set()
            return process

        async def gated_cleanup(launch_task):
            cleaning.set()
            await release.wait()
            await actual_cleanup(launch_task)

        with patch('allow_ai.verification.asyncio.create_subprocess_exec', side_effect=launch), \
                patch.object(verifier, '_cleanup', side_effect=gated_cleanup):
            task = asyncio.create_task(verifier('sig A {}', 5))
            await ready.wait()
            task.cancel()
            await asyncio.wait_for(cleaning.wait(), 1)
            self.assertFalse(task.done())
            task.cancel()
            try:
                await asyncio.sleep(0)
                await asyncio.sleep(0)
                self.assertFalse(task.done())
                self.assertIsNone(processes[0].returncode)
            finally:
                release.set()
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(task, 2)
        self.assertIsNotNone(processes[0].returncode)

    async def test_build_change_fails_closed(self):
        """A new supervisor identity cannot replace an established pin."""
        verifier = DocumentVerifier('/tmp/unused')
        verifier._build = 'original'
        async def response(*_):
            return b'{"status":"VALIDATED","build":"changed","projection":"TEXT_ONLY","source_hash":"x"}\n'
        with patch.object(verifier, '_exchange', side_effect=response):
            result = await verifier('sig A {}', 1)
        self.assertEqual((result.status, result.code), ('UNAVAILABLE', 'WORKER_BUILD_CHANGED'))


class CgroupTests(unittest.TestCase):
    """Check canonical kernel metadata and bounded ancestor traversal."""

    def test_mount_mapping_and_ancestor_limit(self):
        """A finite mounted-root ceiling applies to a descendant membership."""
        import tempfile
        from pathlib import Path
        from allow_ai.verifier_worker import _membership, _cgroup_limit
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'pids.max').write_text('512\n')
            (root / 'child').mkdir()
            (root / 'child/pids.max').write_text('max\n')
            info = f'30 20 0:2 /slice {root} rw - cgroup2 cgroup rw\n'
            mount, relative = _membership('0::/slice/child\n', info)
            self.assertTrue(_cgroup_limit(mount, relative))
            (root / 'pids.max').write_text('max\n')
            self.assertFalse(_cgroup_limit(mount, relative))

    def test_invalid_and_symlinked_metadata_rejected(self):
        """Noncanonical membership and symlinked pids.max fail closed."""
        import tempfile
        from pathlib import Path
        from allow_ai.verifier_worker import _membership, _cgroup_limit
        with self.assertRaises(ValueError):
            _membership('0::/a/../b\n', '30 20 0:2 / /sys/fs/cgroup rw - cgroup2 cgroup rw\n')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'limit').write_text('512\n')
            (root / 'pids.max').symlink_to(root / 'limit')
            with self.assertRaises(OSError):
                _cgroup_limit(root, Path('.'))
