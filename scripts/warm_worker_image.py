#!/usr/bin/python3
"""Trusted public-only image capture and cgroup join for fixed one-use JVM modes.

Run with the isolated installed interpreter and exactly these trusted arguments:
MODE OWNER_PID OWNER_START_TICKS BOOT_ID CGROUP_ROOT ROOT_DEVICE ROOT_INODE.
The one bounded bootstrap JSON line is operational metadata, never a model frame.
"""

import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import select
import signal
import stat
import sys
import time
import uuid


ALLOY_SHA = "6037cbeee0e8423c1c468447ed10f5fcf2f2743a2ffc39cb1c81f2905c0fdb9d"
IMAGE_BYTES = 67108864
IMAGE_FILES = 512
SEALS = fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL
MODES = {
    "warm-document": "dev.allow.worker.WarmDocumentWorkerMain",
    "fresh-document": "dev.allow.worker.DocumentWorkerMain",
    "fresh-solver": "dev.allow.worker.WorkerMain",
}
FIELDS = frozenset({
    "protocol", "ownerPid", "ownerStartTicks", "bootId", "childPid", "childStartTicks",
    "poolNonce", "slot", "generation", "workerNonce", "cgroupRoot", "cgroupRelative",
    "cgroupDevice", "cgroupInode", "target", "buildSha256", "javaHome", "javaRuntimeVersion",
})


def require(condition):
    """Reject unavailable or malformed operational state without exposing its values."""
    if not condition:
        raise ValueError("Warm worker startup rejected")


def decimal(value, positive=True):
    """Accept only canonical bounded decimal strings used by process identities."""
    require(type(value) is str and re.fullmatch(r"[1-9][0-9]*|0", value) is not None)
    result = int(value)
    require((result > 0 if positive else result >= 0) and result <= 9223372036854775807)
    return result


def integer(value, positive=True):
    """Reject booleans and numeric coercions in the closed bootstrap schema."""
    require(type(value) is int)
    require((value > 0 if positive else value >= 0) and value <= 9223372036854775807)
    return value


def canonical_uuid(value):
    """Require canonical lowercase UUID spelling rather than permissive UUID parsing."""
    require(type(value) is str and str(uuid.UUID(value)) == value)
    return value


def canonical_directory(value):
    """Reject relative, noncanonical, symlinked, or missing directory roots."""
    require(type(value) is str and "\0" not in value)
    path = Path(value)
    require(path.is_absolute() and str(path) == value and path.resolve(strict=True) == path)
    require(path.is_dir())
    return path


def start_ticks(pid):
    """Read Linux process incarnation without confusing spaces in the command name."""
    contents = Path("/proc", str(pid), "stat").read_text(encoding="ascii")
    return contents[contents.rfind(")") + 2:].split()[19]


def owner_check(expected):
    """Bind the direct parent to its PID, start ticks and current boot incarnation."""
    require(os.getppid() == expected["ownerPid"])
    require(start_ticks(expected["ownerPid"]) == expected["ownerStartTicks"])
    require(Path("/proc/sys/kernel/random/boot_id").read_text().strip() == expected["bootId"])


def arm_parent_death(expected):
    """Kill this direct child on parent death and reject the prctl installation race."""
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    libc.prctl.restype = ctypes.c_int
    require(libc.prctl(1, signal.SIGKILL, 0, 0, 0) == 0)
    owner_check(expected)


def limits():
    """Bound trusted setup before capture; the inner fixed prlimit lowers final FS to 8 MiB."""
    for kind, value in ((resource.RLIMIT_AS, 2147483648), (resource.RLIMIT_CPU, 12),
                        (resource.RLIMIT_FSIZE, IMAGE_BYTES), (resource.RLIMIT_NOFILE, 1024)):
        resource.setrlimit(kind, (value, value))
        require(resource.getrlimit(kind) == (value, value))


def close_unintended(keep=()):
    """Close inherited or setup descriptors except stdio and the enumerated sealed image."""
    retained = {0, 1, 2, *keep}
    for name in os.listdir("/proc/self/fd"):
        descriptor = int(name)
        if descriptor not in retained:
            try:
                os.close(descriptor)
            except OSError as error:
                if error.errno != 9:
                    raise


def arguments(argv):
    """Validate fixed trusted argv independently from the subsequent public JSON frame."""
    require(len(argv) == 7 and argv[0] in MODES)
    root = canonical_directory(argv[4])
    require(root.is_relative_to(Path("/sys/fs/cgroup")) and root != Path("/sys/fs/cgroup"))
    return {"mode": argv[0], "ownerPid": decimal(argv[1]), "ownerStartTicks": str(decimal(argv[2])),
            "bootId": canonical_uuid(argv[3]), "cgroupRoot": str(root),
            "rootDevice": decimal(argv[5], False), "rootInode": decimal(argv[6])}


def closed_object(pairs):
    """Refuse duplicate JSON keys at every object level before schema validation."""
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def read_bootstrap(descriptor, deadline):
    """Read exactly one bounded UTF-8 line without consuming later private pipe bytes."""
    line = bytearray()
    while len(line) < 4096:
        remaining = deadline - time.monotonic()
        require(remaining > 0 and select.select([descriptor], [], [], remaining)[0])
        byte = os.read(descriptor, 1)
        require(byte and byte != b"\0" and time.monotonic() < deadline)
        line.extend(byte)
        if byte == b"\n":
            value = json.loads(line.decode("utf-8", errors="strict"), object_pairs_hook=closed_object)
            require(type(value) is dict)
            return value
    raise ValueError("Warm worker bootstrap exceeds limit")


def validate_bootstrap(value, expected):
    """Require the exact reviewed schema and independently supplied owner/root identity."""
    require(set(value) == FIELDS)
    for item in value.values():
        require(type(item) in (str, int) and (type(item) is not str or "\0" not in item))
    require(integer(value["protocol"]) == 1 and integer(value["slot"], False) in (0, 1))
    for key in ("ownerPid", "childPid", "generation", "cgroupInode"):
        integer(value[key])
    integer(value["cgroupDevice"], False)
    for key in ("ownerStartTicks", "childStartTicks"):
        decimal(value[key])
    for key in ("bootId", "poolNonce", "workerNonce"):
        canonical_uuid(value[key])
    for key in ("ownerPid", "ownerStartTicks", "bootId", "cgroupRoot"):
        require(value[key] == expected[key])
    require(value["childPid"] == os.getpid() and value["childStartTicks"] == start_ticks(os.getpid()))
    relative = "pool-" + value["poolNonce"] + "/slot-" + str(value["slot"]) + "-g" + str(value["generation"])
    require(value["cgroupRelative"] == relative)
    require(type(value["buildSha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", value["buildSha256"]))
    require(type(value["javaRuntimeVersion"]) is str and 0 < len(value["javaRuntimeVersion"]) <= 256)
    canonical_directory(value["target"])
    canonical_directory(value["javaHome"])
    owner_check(expected)
    return value


def directory_at(parent, name):
    """Open one generated directory component without following any symlink."""
    require(name not in ("", ".", "..") and "/" not in name and "\0" not in name)
    return os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)


def control_read(directory, name):
    """Read bounded kernel cgroup metadata through the captured directory descriptor."""
    descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
    try:
        value = os.read(descriptor, 4097)
        require(len(value) <= 4096)
        return value.decode("ascii").strip()
    finally:
        os.close(descriptor)


def join_group(value, expected):
    """Join the exact empty generation-owned cgroup before image capture or executable startup."""
    descriptors = []
    try:
        root = os.open(value["cgroupRoot"], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        descriptors.append(root)
        metadata = os.fstat(root)
        require((metadata.st_dev, metadata.st_ino, metadata.st_uid) ==
                (expected["rootDevice"], expected["rootInode"], os.getuid()))
        for component in value["cgroupRelative"].split("/"):
            descriptors.append(directory_at(descriptors[-1], component))
        group = descriptors[-1]
        metadata = os.fstat(group)
        require((metadata.st_dev, metadata.st_ino, metadata.st_uid) ==
                (value["cgroupDevice"], value["cgroupInode"], os.getuid()))
        for key, fixed in (("pids.max", "32"), ("memory.max", "1073741824"), ("memory.swap.max", "0")):
            require(control_read(group, key) == fixed)
        require(control_read(group, "cgroup.procs") == "")
        require("populated 0" in control_read(group, "cgroup.events").splitlines())
        owner_check(expected)
        descriptor = os.open("cgroup.procs", os.O_WRONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=group)
        descriptors.append(descriptor)
        data = (str(os.getpid()) + "\n").encode("ascii")
        require(os.write(descriptor, data) == len(data))
        relative = str(Path(value["cgroupRoot"]).relative_to("/sys/fs/cgroup")) + "/" + value["cgroupRelative"]
        require(Path("/proc/self/cgroup").read_text().strip() == "0::/" + relative)
        require(str(os.getpid()) in control_read(group, "cgroup.procs").splitlines())
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def inventory(target):
    """Match BuildIdentity ordering while rejecting unexpected members and nonregular sources."""
    rows = []
    for group in ("classes", "dependency", "solver"):
        directory = target / group
        require(not directory.is_symlink() and directory.is_dir())
        members = []
        for parent, directories, files in os.walk(directory, followlinks=False):
            for name in directories + files:
                path = Path(parent, name)
                metadata = path.lstat()
                require(stat.S_ISDIR(metadata.st_mode) or stat.S_ISREG(metadata.st_mode))
                if stat.S_ISREG(metadata.st_mode):
                    require(group == "classes" or (group == "dependency" and path.suffix == ".jar")
                            or path == target / "solver/alloy.jar")
                    members.append(path)
        require(members and (group != "solver" or members == [target / "solver/alloy.jar"]))
        for path in sorted(members, key=str):
            relative = str(path.relative_to(target))
            require("\0" not in relative and "\n" not in relative)
            rows.append((relative, path.stat().st_size))
    require(len(rows) <= IMAGE_FILES and sum(size for _, size in rows) <= IMAGE_BYTES)
    require(len({path for path, _ in rows}) == len(rows))
    return rows


def source_open(target, relative):
    """Open every image path component relative to captured nonsymlink directory descriptors."""
    descriptors = []
    try:
        descriptors.append(os.open(target, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC))
        components = relative.split("/")
        for component in components[:-1]:
            descriptors.append(directory_at(descriptors[-1], component))
        return os.open(components[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=descriptors[-1])
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def capture_file(target, relative, size):
    """Copy and seal one bounded ordinary file, refusing size changes during capture."""
    source = source_open(target, relative)
    image = None
    try:
        metadata = os.fstat(source)
        require(stat.S_ISREG(metadata.st_mode) and metadata.st_size == size)
        image = os.memfd_create("allow-worker-image", os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING)
        os.fchmod(image, 0o444)
        remaining = size
        while remaining:
            chunk = os.read(source, min(65536, remaining))
            require(chunk)
            remaining -= len(chunk)
            view = memoryview(chunk)
            while view:
                written = os.write(image, view)
                require(written > 0)
                view = view[written:]
        require(not os.read(source, 1) and os.fstat(source).st_size == size)
        fcntl.fcntl(image, fcntl.F_ADD_SEALS, SEALS)
        require(fcntl.fcntl(image, fcntl.F_GET_SEALS) == SEALS)
        result, image = image, None
        return result
    finally:
        os.close(source)
        if image is not None:
            os.close(image)


def digest_image(rows, images, version):
    """Hash sealed destination bytes using the existing exact logical BuildIdentity algorithm."""
    digest = hashlib.sha256()
    alloy = None
    for (relative, size), descriptor in zip(rows, images):
        digest.update(relative.encode("utf-8") + b"\0")
        file_digest = hashlib.sha256()
        offset = 0
        while offset < size:
            chunk = os.pread(descriptor, min(65536, size - offset), offset)
            require(chunk)
            digest.update(chunk)
            file_digest.update(chunk)
            offset += len(chunk)
        digest.update(b"\0")
        if relative == "solver/alloy.jar":
            alloy = file_digest.hexdigest()
    digest.update(version.encode("utf-8"))
    require(alloy == ALLOY_SHA)
    return digest.hexdigest()


def image_mount(relative):
    """Keep solver and directory classpath paths identical to the fresh launcher."""
    return "/app/solver.jar" if relative == "solver/alloy.jar" else "/app/" + relative


def command(value, mode, rows, images):
    """Construct only fixed runtime mounts, sealed data mounts and trusted JVM entrypoints."""
    java_home = value["javaHome"]
    argv = ["/usr/bin/bwrap", "--unshare-all", "--new-session", "--die-with-parent", "--cap-drop", "ALL", "--clearenv"]
    for path in (java_home, "/lib", "/lib64", "/etc/java-17-openjdk", "/usr/bin/prlimit"):
        require(Path(path).exists())
        argv.extend(("--ro-bind", path, path))
    directories = set()
    for relative, _ in rows:
        directories.update(str(parent) for parent in Path(image_mount(relative)).parents if str(parent) != "/")
    for directory in sorted(directories, key=directory_order):
        argv.extend(("--dir", directory))
    for (relative, _), descriptor in zip(rows, images):
        os.lseek(descriptor, 0, os.SEEK_SET)
        argv.extend(("--perms", "0444", "--ro-bind-data", str(descriptor), image_mount(relative)))
    argv.extend(("--tmpfs", "/tmp", "--proc", "/proc", "--dev", "/dev", "--chdir", "/tmp",
                 "/usr/bin/prlimit", "--fsize=8388608", "--", java_home + "/bin/java",
                 "-Xmx512m", "-Xss512k", "-XX:+UseSerialGC", "-XX:ActiveProcessorCount=2",
                 "-XX:MaxMetaspaceSize=128m", "-XX:CompressedClassSpaceSize=64m", "-XX:ReservedCodeCacheSize=48m",
                 "-Djava.awt.headless=true", "-Dfile.encoding=UTF-8", "-Djava.io.tmpdir=/tmp", "-cp",
                 "/app/classes:/app/solver.jar:/app/dependency/*", MODES[mode]))
    if mode == "warm-document":
        argv.extend((value["workerNonce"], value["buildSha256"]))
    return argv


def directory_order(value):
    """Create mount parents before their nested directories, deterministically."""
    return value.count("/"), value


def run(argv):
    """Join, capture, seal and exec one reviewed mode without reading any private frame."""
    deadline = time.monotonic() + 5
    expected = arguments(argv)
    arm_parent_death(expected)
    close_unintended()
    limits()
    value = validate_bootstrap(read_bootstrap(0, deadline), expected)
    join_group(value, expected)
    images = []
    try:
        target = Path(value["target"])
        rows = inventory(target)
        for relative, size in rows:
            require(time.monotonic() < deadline)
            images.append(capture_file(target, relative, size))
        require(digest_image(rows, images, value["javaRuntimeVersion"]) == value["buildSha256"])
        require(inventory(target) == rows and time.monotonic() < deadline)
        owner_check(expected)
        executable = command(value, expected["mode"], rows, images)
        close_unintended(images)
        for descriptor in images:
            os.set_inheritable(descriptor, True)
        os.execve("/usr/bin/bwrap", executable, {})
    finally:
        for descriptor in images:
            os.close(descriptor)


def main():
    """Return one bounded sanitized startup failure; only the fixed Java main emits READY."""
    try:
        run(sys.argv[1:])
    except Exception:
        os.write(2, b"Warm worker startup unavailable\n")
        return 70
    return 70


if __name__ == "__main__":
    raise SystemExit(main())
