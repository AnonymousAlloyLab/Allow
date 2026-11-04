"""Own sealed image and bounded execution reservations under one lifecycle lock."""
from contextlib import contextmanager
from dataclasses import dataclass
import array
import fcntl
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time

from .sql_image_config import ImageError, duplicates
from .sql_image_init import REQUIRED_SEALS

ENVIRONMENT = {'LEAN_NUM_THREADS':'1', 'PATH':'/usr/bin:/bin'}
PRLIMIT = '/usr/bin/prlimit'
MAX_OUTPUT = 16777216


class ParserFailure(ImageError):
    category = 'parserFailure'


@dataclass(eq=False)
class Reservation:
    descriptor: int
    process: object = None


def receive_image(channel, config):
    """Own and close every ancillary fd unless exactly one valid image is returned."""
    descriptors = []
    try:
        payload, ancillary, flags, _ = channel.recvmsg(1024, socket.CMSG_SPACE(16*array.array('i').itemsize), socket.MSG_CMSG_CLOEXEC)
        valid_ancillary = True
        for level, kind, data in ancillary:
            if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS:
                values = array.array('i')
                # Close all complete installed descriptors even for a malformed tail.
                values.frombytes(data[:len(data)-len(data)%values.itemsize])
                descriptors.extend(values)
                valid_ancillary &= len(data)%values.itemsize == 0
            else:
                valid_ancillary = False
        if flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC) or not valid_ancillary or len(descriptors) != 1:
            raise ImageError('initializer descriptor framing')
        metadata = json.loads(payload.decode('ascii'), object_pairs_hook=duplicates)
        descriptor = descriptors[0]
        actual = os.fstat(descriptor)
        expected = {'sha256':config.binary_sha256, 'size':config.expected_size,
                    'device':actual.st_dev, 'inode':actual.st_ino}
        if metadata != expected or actual.st_size != config.expected_size:
            raise ImageError('initializer evidence mismatch')
        if fcntl.fcntl(descriptor, fcntl.F_GET_SEALS) & REQUIRED_SEALS != REQUIRED_SEALS:
            raise ImageError('initializer seals missing')
        descriptors.clear()
        return descriptor
    except (OSError, ValueError, TypeError, UnicodeError) as error:
        raise ImageError('initializer transfer failed') from error
    finally:
        cleanup_failed = False
        for descriptor in descriptors:
            try:
                os.close(descriptor)
            except OSError:
                cleanup_failed = True
        if cleanup_failed:
            raise ImageError('initializer descriptor cleanup incomplete')


def initialize_image(source, config):
    """Supervise full initialization; close every owned resource before publication."""
    descriptor = None
    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    process = None
    failure = None
    cleanup_failed = False
    deadline = time.monotonic()+5
    try:
        command = [PRLIMIT, '--as=268435456', '--cpu=6', '--core=0', '--',
            sys.executable, '-I', str(Path(__file__).with_name('sql_image_init.py')),
            '--socket-fd', str(child.fileno()), '--source', str(source),
            '--size', str(config.expected_size), '--sha256', config.binary_sha256]
        process = subprocess.Popen(command, pass_fds=(child.fileno(),),
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=ENVIRONMENT)
        child.close()
        parent.settimeout(max(0.001, deadline-time.monotonic()))
        descriptor = receive_image(parent, config)
        code = process.wait(timeout=max(0.001, deadline-time.monotonic()))
        if code != 0 or time.monotonic() > deadline:
            raise ImageError('initializer failed')
    except BaseException as error:
        failure = error
    finally:
        if process is not None and process.poll() is None:
            try:
                process.kill()
                process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                cleanup_failed = True
        for channel in (parent, child):
            try:
                channel.close()
            except OSError:
                cleanup_failed = True
        if (failure is not None or cleanup_failed) and descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                cleanup_failed = True
    if isinstance(failure, (KeyboardInterrupt, SystemExit)):
        raise failure
    if failure is not None or cleanup_failed:
        raise ImageError('initializer cleanup incomplete' if cleanup_failed else 'parser image unavailable') from failure
    return descriptor


class SealedImage:
    """Gate-local object ownership; only reservation owners close their duplicate."""
    def __init__(self, source, config):
        self.config = config
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        self._descriptor = initialize_image(source, config)
        try:
            metadata = os.fstat(self._descriptor)
        except OSError as error:
            os.close(self._descriptor)
            self._descriptor = None
            raise ImageError('parser image unavailable') from error
        self._object = (metadata.st_dev, metadata.st_ino)
        self._state = 'ready'
        self._owners = set()
        self._waiters = 0
        self._slots_free = 2
        self._cleanup_failed = False

    def ensure_live(self, config):
        """Caller holds lifecycle lock; every generation has one snapshot object."""
        if self._state != 'ready' or config is not self.config:
            raise ImageError('parser image stopped')

    def _checked_duplicate(self, config):
        self.ensure_live(config)
        descriptor = None
        try:
            descriptor = os.dup(self._descriptor)
            metadata = os.fstat(descriptor)
            if ((metadata.st_dev, metadata.st_ino) != self._object or
                    metadata.st_size != config.expected_size or
                    fcntl.fcntl(descriptor, fcntl.F_GET_SEALS) & REQUIRED_SEALS != REQUIRED_SEALS):
                raise ImageError('parser image identity mismatch')
            return descriptor
        except (OSError, ValueError) as error:
            self._state = 'failed'
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    self._cleanup_failed = True
            self.changed.notify_all()
            raise ImageError('parser image identity unavailable') from error

    def check_locked(self, config):
        """At most one transient check duplicate; never retained outside the lock."""
        descriptor = self._checked_duplicate(config)
        try:
            os.close(descriptor)
        except OSError as error:
            self._cleanup_failed = True
            self._state = 'failed'
            self.changed.notify_all()
            raise ImageError('parser cleanup incomplete') from error

    @staticmethod
    def check_cancel(cancel):
        if cancel is not None and cancel.is_set():
            raise ParserFailure('parser cancelled')

    @contextmanager
    def reserve(self, config, cancel=None):
        """Waiters hold no fd. Acquire slot before duplicating under lifetime lock."""
        owner = None
        deadline = time.monotonic()+30
        with self.changed:
            self.ensure_live(config)
            if self._waiters >= 24:
                raise ImageError('parser wait capacity')
            self._waiters += 1
            try:
                while not self._slots_free:
                    self.ensure_live(config)
                    self.check_cancel(cancel)
                    remaining = deadline-time.monotonic()
                    if remaining <= 0:
                        raise ParserFailure('parser wait timeout')
                    self.changed.wait(min(remaining, 0.05))
                self.ensure_live(config)
                self.check_cancel(cancel)
                descriptor = self._checked_duplicate(config)
                owner = Reservation(descriptor)
                self._slots_free -= 1
                self._owners.add(owner)
            finally:
                self._waiters -= 1
        try:
            yield owner
        finally:
            cleanup_error = None
            try:
                if owner.process is not None and owner.process.poll() is None:
                    owner.process.kill()
                    owner.process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired) as error:
                cleanup_error = error
            if owner.process is not None:
                for stream in (getattr(owner.process, 'stdin', None),
                               getattr(owner.process, 'stdout', None),
                               getattr(owner.process, 'stderr', None)):
                    if stream is not None:
                        try:
                            stream.close()
                        except OSError as error:
                            cleanup_error = error
            try:
                os.close(owner.descriptor)
            except OSError as error:
                cleanup_error = error
            with self.changed:
                self._owners.discard(owner)
                self._slots_free += 1
                if cleanup_error:
                    self._cleanup_failed = True
                    self._state = 'failed'
                self.changed.notify_all()
            if cleanup_error:
                raise ImageError('parser cleanup incomplete') from cleanup_error

    def run(self, owner, sql, config, cancel=None):
        """Execute the reserved sealed fd through the unchanged child resource limits."""
        self.check_cancel(cancel)
        try:
            temporary = tempfile.TemporaryFile(mode='w+b', dir='/dev/shm')
        except OSError as error:
            raise ImageError('parser output unavailable') from error
        with temporary as output:
            with self.lock:
                self.ensure_live(config)
                # The lock excludes shutdown between launch and process registration.
                try:
                    owner.process = subprocess.Popen([PRLIMIT, '--as=1073741824', '--cpu=6',
                        '--core=0', '--fsize=16777216', '--', f'/proc/self/fd/{owner.descriptor}',
                        '--max-transitions', '1000000'], pass_fds=(owner.descriptor,),
                        stdin=subprocess.PIPE, stdout=output, stderr=subprocess.DEVNULL,
                        env=ENVIRONMENT)
                except OSError as error:
                    raise ImageError('parser unavailable') from error
            deadline = time.monotonic()+5
            first = True
            while True:
                self.check_cancel(cancel)
                with self.lock:
                    self.ensure_live(config)
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    raise ParserFailure('parser unavailable')
                try:
                    owner.process.communicate(sql if first else None, timeout=min(remaining, 0.05))
                    break
                except subprocess.TimeoutExpired:
                    first = False
            if owner.process.returncode != 0:
                raise ParserFailure('parser rejected')
            if output.tell() > MAX_OUTPUT:
                raise ParserFailure('parser output too large')
            output.seek(0)
            return output.read(MAX_OUTPUT+1)

    def status_locked(self, config):
        return {'identity_mode':'sealed-image', 'policy':config.policy,
            'profile':config.profile, 'postgresql_commit':config.commit,
            'binary_sha256':config.binary_sha256, 'sealed_bytes':config.expected_size,
            'mapping_sha256':config.mapping_sha256, 'snapshot_sha256':config.digest,
            'generation':config.generation, 'configuration_sha256':config.source_sha256,
            'required_seals':REQUIRED_SEALS,
            'lifecycle':self._state, 'reserved_execution_descriptors':len(self._owners),
            'waiting':self._waiters, 'disk_policy':'restart-check-only',
            'config_policy':'frozen-until-new-generation',
            'shutdown_complete':self._state == 'stopped' and not self._owners and not self._waiters}

    def close_locked(self):
        """Mark stopped and close only the private fd; reservation owners retain theirs."""
        if self._state == 'ready':
            self._state = 'stopped'
        if self._descriptor is not None:
            try:
                os.close(self._descriptor)
            except OSError:
                self._cleanup_failed = True
                self._state = 'failed'
            self._descriptor = None
        self.changed.notify_all()

    def finish_close(self):
        """Never hold lifetime lock while waiting for child or owner cleanup."""
        with self.lock:
            processes = [owner.process for owner in self._owners if owner.process is not None]
        for process in processes:
            try:
                if process.poll() is None:
                    process.kill()
            except ProcessLookupError:
                pass
            except OSError:
                with self.lock:
                    self._cleanup_failed = True
                    self._state = 'failed'
        deadline = time.monotonic()+6
        with self.changed:
            while self._owners or self._waiters:
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    self._state = 'failed'
                    raise ImageError('parser shutdown incomplete')
                self.changed.wait(min(remaining, 0.05))
            if self._cleanup_failed:
                raise ImageError('parser shutdown incomplete')
