"""Bounded short-lived sealed-image initializer. Linux only; no pathname fallback.

The explicit MFD_EXEC binding0x0010 is from Linux uapi linux/memfd.h. A kernel
rejecting that flag fails closed; no retry weakens execution/noexec policy.
"""
import argparse
import array
import fcntl
import hashlib
import json
import os
import socket
import stat

MFD_EXEC = 0x0010
REQUIRED_SEALS = fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL
CHUNK = 1048576


def copy_exact(source, image, expected_size):
    """Total source bytes are bounded by trusted size plus one excess byte."""
    remaining = expected_size
    while remaining:
        chunk = os.read(source, min(CHUNK, remaining))
        if not chunk:
            raise ValueError('early EOF')
        remaining -= len(chunk)
        view = memoryview(chunk)
        while view:
            count = os.write(image, view)
            if count <= 0:
                raise ValueError('zero write')
            view = view[count:]
    if os.read(source, 1):
        raise ValueError('excess source')


def build_image(source_path, expected_size, expected_sha):
    """Return an owned sealed fd only after final destination hash acceptance."""
    if type(expected_size) is not int or not 0 < expected_size <= 136492600:
        raise ValueError('invalid trusted size')
    source = image = None
    try:
        source = os.open(source_path, os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK | os.O_NOFOLLOW)
        metadata = os.fstat(source)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != expected_size:
            raise ValueError('source type/size')
        image = os.memfd_create('allow-sqlean-image', os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING | MFD_EXEC)
        copy_exact(source, image, expected_size)
        closing, source = source, None
        os.close(closing)
        fcntl.fcntl(image, fcntl.F_ADD_SEALS, REQUIRED_SEALS)
        if (os.fstat(image).st_size != expected_size or
                fcntl.fcntl(image, fcntl.F_GET_SEALS) & REQUIRED_SEALS != REQUIRED_SEALS):
            raise ValueError('image seals/size')
        digest = hashlib.sha256()
        offset = 0
        while offset < expected_size:
            chunk = os.pread(image, min(CHUNK, expected_size-offset), offset)
            if not chunk:
                raise ValueError('sealed EOF')
            digest.update(chunk)
            offset += len(chunk)
        if digest.hexdigest() != expected_sha:
            raise ValueError('image digest')
        result, image = image, None
        return result
    finally:
        cleanup_error = None
        for descriptor in (source, image):
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError as error:
                    cleanup_error = error
        if cleanup_error is not None:
            raise cleanup_error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--socket-fd', type=int, required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--size', type=int, required=True)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    descriptor = None
    channel = socket.socket(fileno=args.socket_fd)
    try:
        descriptor = build_image(args.source, args.size, args.sha256)
        metadata = os.fstat(descriptor)
        payload = json.dumps({'sha256':args.sha256, 'size':metadata.st_size,
            'device':metadata.st_dev, 'inode':metadata.st_ino}, separators=(',', ':')).encode('ascii')
        channel.sendmsg([payload], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', [descriptor]))])
        return 0
    except (OSError, ValueError, TypeError, AttributeError):
        return 1
    finally:
        try:
            if descriptor is not None:
                os.close(descriptor)
        finally:
            channel.close()


if __name__ == '__main__':
    raise SystemExit(main())
