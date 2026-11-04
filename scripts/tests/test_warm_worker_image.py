"""Focused public helper checks; these do not claim full cgroup/JVM correspondence."""
import errno
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "warm_worker_image.py"
SPEC = importlib.util.spec_from_file_location("warm_worker_image", SOURCE)
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)


class WarmImageTest(unittest.TestCase):
    """Exercise strict framing, finite inventory and real kernel seal behavior."""

    def setUp(self):
        """Create a uniquely owned ordinary-file image fixture."""
        self.temporary = tempfile.TemporaryDirectory(prefix="allow-warm-helper-test-")
        self.target = Path(self.temporary.name)
        for group in ("classes", "dependency", "solver"):
            (self.target / group).mkdir()
        (self.target / "classes/A.class").write_bytes(b"class-bytes")
        (self.target / "dependency/a.jar").write_bytes(b"dependency-bytes")
        (self.target / "solver/alloy.jar").write_bytes(b"alloy-fixture-bytes")

    def tearDown(self):
        """Remove only this test's generated fixture after descriptors are closed."""
        self.temporary.cleanup()

    def read(self, payload):
        """Write a small pipe frame and call the actual bytewise bootstrap reader."""
        read, write = os.pipe()
        try:
            os.write(write, payload)
            os.close(write)
            write = None
            return HELPER.read_bootstrap(read, time.monotonic() + 1)
        finally:
            os.close(read)
            if write is not None:
                os.close(write)

    def test_bootstrap_no_read_ahead(self):
        """The later private bytes remain unread after the exact first line."""
        read, write = os.pipe()
        try:
            os.write(write, b'{"protocol":1}\nPRIVATE')
            self.assertEqual(HELPER.read_bootstrap(read, time.monotonic() + 1), {"protocol": 1})
            self.assertEqual(os.read(read, 7), b"PRIVATE")
        finally:
            os.close(read)
            os.close(write)

    def test_malformed_lines(self):
        """Duplicate, incomplete, nonobject, NUL, malformed UTF-8 and oversized lines fail."""
        for payload in (b'{"a":1,"a":2}\n', b'{}', b'[]\n', b'{"a":"\x00"}\n', b'\xff\n', b' ' * 4096):
            with self.subTest(payload_length=len(payload)), self.assertRaises((ValueError, UnicodeError)):
                self.read(payload)

    def test_deadline(self):
        """An expired startup budget never attempts a blocking read."""
        read, write = os.pipe()
        try:
            with self.assertRaises(ValueError):
                HELPER.read_bootstrap(read, time.monotonic() - 1)
        finally:
            os.close(read)
            os.close(write)

    def test_schema_and_identity_rejection(self):
        """Closed metadata refuses coercions, nonce/path substitutions and child mismatches."""
        expected, value = self.bootstrap()
        self.assertEqual(HELPER.validate_bootstrap(value, expected), value)
        changes = {"protocol": True, "slot": 2, "generation": 0, "childPid": os.getpid() + 1,
                   "childStartTicks": "00", "poolNonce": value["poolNonce"].upper(),
                   "cgroupRelative": "../escape", "buildSha256": "F" * 64,
                   "ownerStartTicks": "1", "javaRuntimeVersion": "bad\0version", "extra": 1}
        for key, replacement in changes.items():
            changed = dict(value, **{key: replacement})
            with self.subTest(field=key), self.assertRaises((ValueError, FileNotFoundError)):
                HELPER.validate_bootstrap(changed, expected)
        changed = dict(value)
        del changed["workerNonce"]
        with self.assertRaises(ValueError):
            HELPER.validate_bootstrap(changed, expected)

    def bootstrap(self):
        """Build valid public-only identities from this test's actual parent and process."""
        owner = os.getppid()
        expected = {"ownerPid": owner, "ownerStartTicks": HELPER.start_ticks(owner),
                    "bootId": Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                    "cgroupRoot": "/sys/fs/cgroup"}
        nonce = "a3fd8aa2-9632-417b-944f-9029e725d92e"
        value = dict(expected, protocol=1, childPid=os.getpid(), childStartTicks=HELPER.start_ticks(os.getpid()),
                     poolNonce=nonce, slot=0, generation=1, workerNonce=nonce,
                     cgroupRelative="pool-" + nonce + "/slot-0-g1", cgroupDevice=0, cgroupInode=1,
                     target=str(self.target), javaHome=str(self.target), javaRuntimeVersion="17-test", buildSha256="a" * 64)
        return expected, value

    def test_inventory_order_and_unexpected_files(self):
        """Inventory matches logical group order and rejects unbound dependency members."""
        rows = HELPER.inventory(self.target)
        self.assertEqual([row[0] for row in rows], ["classes/A.class", "dependency/a.jar", "solver/alloy.jar"])
        (self.target / "dependency/unbound.txt").write_text("unexpected")
        with self.assertRaises(ValueError):
            HELPER.inventory(self.target)

    def test_symlinks_and_special_members(self):
        """Symlinks and FIFOs cannot enter executable/resource inventory."""
        path = self.target / "classes/escape"
        path.symlink_to(self.target / "dependency/a.jar")
        with self.assertRaises(ValueError):
            HELPER.inventory(self.target)
        path.unlink()
        os.mkfifo(path)
        with self.assertRaises(ValueError):
            HELPER.inventory(self.target)

    def test_image_caps(self):
        """Both file count and aggregate byte ceilings fail before image allocation."""
        with patch.object(HELPER, "IMAGE_FILES", 2), self.assertRaises(ValueError):
            HELPER.inventory(self.target)
        with patch.object(HELPER, "IMAGE_BYTES", 1), self.assertRaises(ValueError):
            HELPER.inventory(self.target)

    def test_actual_configured_file_boundary(self):
        """The unchanged 512-file setting accepts its boundary and rejects file 513."""
        self.assertEqual(HELPER.IMAGE_FILES, 512)
        for index in range(509):
            (self.target / "classes" / f"Boundary{index:03}.class").write_bytes(b"x")
        self.assertEqual(len(HELPER.inventory(self.target)), 512)
        (self.target / "classes/BoundaryOverflow.class").write_bytes(b"x")
        with self.assertRaises(ValueError):
            HELPER.inventory(self.target)

    def test_actual_configured_byte_boundary(self):
        """Real file lengths exercise 64 MiB and 64 MiB plus one without patched caps."""
        self.assertEqual(HELPER.IMAGE_BYTES, 64 * 1024 * 1024)
        existing = sum(size for _, size in HELPER.inventory(self.target))
        padding = self.target / "classes/boundary.resource"
        with padding.open("wb") as stream:
            stream.truncate(HELPER.IMAGE_BYTES - existing)
        self.assertEqual(sum(size for _, size in HELPER.inventory(self.target)), HELPER.IMAGE_BYTES)
        with padding.open("r+b") as stream:
            stream.truncate(HELPER.IMAGE_BYTES - existing + 1)
        with self.assertRaises(ValueError):
            HELPER.inventory(self.target)

    def test_source_component_symlink_rejected(self):
        """Descriptor-relative capture rejects a parent symlink even after inventory."""
        (self.target / "classes/nested").symlink_to(self.target / "dependency", target_is_directory=True)
        with self.assertRaises(OSError):
            HELPER.source_open(self.target, "classes/nested/a.jar")

    def test_actual_seals_and_logical_identity(self):
        """Actual memfds reject mutation and reproduce path-NUL/content-NUL/version hashing."""
        rows = HELPER.inventory(self.target)
        images = []
        try:
            digest = hashlib.sha256()
            for relative, size in rows:
                image = HELPER.capture_file(self.target, relative, size)
                images.append(image)
                self.assertEqual(fcntl.fcntl(image, fcntl.F_GET_SEALS), HELPER.SEALS)
                for operation in (os.pwrite, os.ftruncate):
                    with self.assertRaises(OSError) as error:
                        operation(image, b"!", 0) if operation is os.pwrite else operation(image, size + 1)
                    self.assertEqual(error.exception.errno, errno.EPERM)
                digest.update(relative.encode() + b"\0" + (self.target / relative).read_bytes() + b"\0")
            digest.update(b"17-test")
            alloy = hashlib.sha256((self.target / "solver/alloy.jar").read_bytes()).hexdigest()
            with patch.object(HELPER, "ALLOY_SHA", alloy):
                self.assertEqual(HELPER.digest_image(rows, images, "17-test"), digest.hexdigest())
            with self.assertRaises(ValueError):
                HELPER.digest_image(rows, images, "17-test")
        finally:
            for image in images:
                os.close(image)

    def test_size_mutation_rejected_without_fd_leak(self):
        """Capture refuses changed input length and closes its owned descriptors on failure."""
        before = set(os.listdir("/proc/self/fd"))
        with self.assertRaises(ValueError):
            HELPER.capture_file(self.target, "classes/A.class", 999)
        self.assertEqual(set(os.listdir("/proc/self/fd")), before)

    def test_fixed_modes_and_final_limit(self):
        """All fixed modes share immutable mounts and lower FS before JVM entry."""
        _, value = self.bootstrap()
        rows = HELPER.inventory(self.target)
        images = [HELPER.capture_file(self.target, path, size) for path, size in rows]
        try:
            for mode, main in HELPER.MODES.items():
                command = HELPER.command(value, mode, rows, images)
                self.assertEqual(command[0], "/usr/bin/bwrap")
                self.assertIn("--clearenv", command)
                self.assertIn("--fsize=8388608", command)
                self.assertEqual(command.count("--ro-bind-data"), len(rows))
                self.assertIn(main, command)
                self.assertNotIn("-XX:TieredStopAtLevel=1", command)
                self.assertEqual(command[-2:], [value['workerNonce'], value['buildSha256']] if mode == 'warm-document'
                                 else ["/app/classes:/app/solver.jar:/app/dependency/*", main])
        finally:
            for image in images:
                os.close(image)


if __name__ == "__main__":
    unittest.main()
