"""Bounded, sequenced private pipe protocol; never logs received frame content."""
import asyncio
import json
import math
import sys
import uuid

MAX_FRAME = 262144


class ProtocolFailure(Exception):
    """Represent a content-free private protocol failure."""


def unique(pairs):
    """Reject duplicate object keys at every decoded depth."""
    value = {}
    for name, child in pairs:
        if name in value:
            raise ProtocolFailure()
        value[name] = child
    return value


def depth(value, level=0):
    """Reject excessive nesting and non-finite numbers in a bounded frame."""
    if level > 24 or isinstance(value, float) and not math.isfinite(value):
        raise ProtocolFailure()
    if isinstance(value, dict):
        for child in value.values():
            depth(child, level + 1)
    elif isinstance(value, list):
        for child in value:
            depth(child, level + 1)


def decode(raw):
    """Decode exactly one small newline-terminated strict UTF-8 object."""
    if len(raw) > MAX_FRAME or not raw.endswith(b'\n') or raw.count(b'\n') != 1:
        raise ProtocolFailure()
    try:
        value = json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=unique)
        depth(value)
        if not isinstance(value, dict):
            raise ProtocolFailure()
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise ProtocolFailure() from None


class Channel:
    """Own one stdin/stdout conversation with no network listener or retries."""

    def __init__(self, reader, writer):
        """Store private streams and an initially unbound sequence."""
        self._reader, self._writer = reader, writer
        self._nonce, self._sequence = None, 0

    @classmethod
    async def stdio(cls):
        """Attach cancellable async reads to the owned parent pipe."""
        reader = asyncio.StreamReader(limit=MAX_FRAME)
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_running_loop().connect_read_pipe(lambda: protocol, sys.stdin.buffer)
        return cls(reader, sys.stdout.buffer)

    async def _read(self):
        """Read one bounded frame without retaining parser exception text."""
        try:
            return decode(await self._reader.readline())
        except (ValueError, OSError):
            raise ProtocolFailure() from None

    def _check(self, frame, kind, sequence):
        """Bind every response to its exact schema, nonce, sequence and kind."""
        if set(frame) != {'protocol', 'nonce', 'seq', 'kind', 'data'}:
            raise ProtocolFailure()
        if type(frame['protocol']) is not int or frame['protocol'] != 1:
            raise ProtocolFailure()
        if type(frame['seq']) is not int or frame['seq'] != sequence or frame['kind'] != kind:
            raise ProtocolFailure()
        if not isinstance(frame['data'], dict) or frame['nonce'] != self._nonce:
            raise ProtocolFailure()

    async def start(self):
        """Accept one server-owned launch frame, establishing the private nonce."""
        frame = await self._read()
        nonce = frame.get('nonce')
        try:
            if not isinstance(nonce, str) or str(uuid.UUID(nonce)) != nonce:
                raise ProtocolFailure()
        except ValueError:
            raise ProtocolFailure() from None
        self._nonce = nonce
        self._check(frame, 'START', 0)
        return frame['data']

    def send(self, kind, data):
        """Emit one bounded server-visible event; never write diagnostics to stdout."""
        if self._nonce is None or kind not in {'AUTH', 'PREPARED', 'VERIFY', 'RESULT'}:
            raise ProtocolFailure()
        self._sequence += 1
        frame = {'protocol': 1, 'nonce': self._nonce, 'seq': self._sequence, 'kind': kind, 'data': data}
        raw = (json.dumps(frame, ensure_ascii=True, separators=(',', ':'), allow_nan=False) + '\n').encode('ascii')
        if len(raw) > MAX_FRAME:
            raise ProtocolFailure()
        self._writer.write(raw)
        self._writer.flush()

    async def exchange(self, kind, data):
        """Send one request and accept only its matching parent reply."""
        self.send(kind, data)
        frame = await self._read()
        self._check(frame, 'REPLY', self._sequence)
        return frame['data']
