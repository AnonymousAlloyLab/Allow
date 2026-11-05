"""Actual graph callbacks, strict IPC and durable budget integration checks."""
import asyncio
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'retrieval'), str(ROOT / 'services/ai')]
from bridge import run
from journal import IntegrationJournal
from protocol import Channel, ProtocolFailure, decode
from allow_ai.provider import ProviderFailure

SOURCE = 'sig Slot0 {}\npred Slot1 { some Slot0 }\nrun Slot1 for 3\n'


def frame(nonce, seq, kind, data):
    """Encode authored parent/child test frames, without a live credential."""
    return (json.dumps({'protocol': 1, 'nonce': nonce, 'seq': seq, 'kind': kind, 'data': data}) + '\n').encode()


class FixtureHost:
    """Respond to real serialized callbacks while recording consent attempts."""

    def __init__(self, reader, nonce, *, deny_repair=False):
        """Own a pipe-like byte sink with explicit server authorization decisions."""
        self.reader, self.nonce, self.deny_repair = reader, nonce, deny_repair
        self.frames, self.consents, self.result = [], [], None

    def write(self, raw):
        """Check requests and queue one matching reply; no implicit repair approval."""
        value = decode(raw)
        self.frames.append(value)
        kind, data = value['kind'], value['data']
        if kind == 'RESULT':
            self.result = data
            return len(raw)
        if kind in ('AUTH', 'PREPARED'):
            approved = not (kind == 'PREPARED' and data['attempt'] == 2 and self.deny_repair)
            reply = {'approved': approved}
            if kind == 'PREPARED':
                self.consents.append((data['attempt'], data['payloadHash']))
                assert hashlib.sha256(data['payload'].encode()).hexdigest() == data['payloadHash']
        elif kind == 'VERIFY':
            valid = data['source'] == SOURCE
            reply = {'status': 'VALIDATED' if valid else 'INVALID',
                     'code': None if valid else 'SOURCE_PARSE_INVALID',
                     'projection': 'BLOCK_SUPPORTED' if valid else None,
                     'source_hash': hashlib.sha256(data['source'].encode()).hexdigest() if valid else None,
                     'evidence': None}
        else:
            raise AssertionError('Unexpected frame')
        self.reader.feed_data(frame(self.nonce, value['seq'], 'REPLY', reply))
        return len(raw)

    def flush(self):
        """The in-memory transport has no pending buffered bytes."""


class BridgeTests(unittest.IsolatedAsyncioTestCase):
    """Exercise the installed real graph across serialized host exchanges."""

    async def perform(self, directory, *, deny=False, ceiling=100000):
        """Run a fixed anonymous request through the production bridge callbacks."""
        nonce = str(uuid.uuid4())
        reader = asyncio.StreamReader(limit=262144)
        writer = FixtureHost(reader, nonce, deny_repair=deny)
        data = {'operationId': str(uuid.uuid4()), 'source': SOURCE, 'intent': 'Keep the declaration names.',
                'feature': 'SOURCE_EDIT', 'binding': 'owned-draft', 'provider': 'FIXTURE',
                'credential': '', 'ledger': str(Path(directory) / 'ledger.json'), 'ceiling': ceiling}
        reader.feed_data(frame(nonce, 0, 'START', data))
        await asyncio.wait_for(run(Channel(reader, writer), ROOT), 3)
        return writer

    async def test_loopback_requires_two_exact_consents(self):
        """Deterministic verification failure creates a distinct second preview."""
        with tempfile.TemporaryDirectory() as directory:
            host = await self.perform(directory)
            self.assertEqual((host.result['status'], host.result['attempts']), ('REVIEW_READY', 2))
            self.assertEqual([a for a, _ in host.consents], [1, 2])
            self.assertNotEqual(host.consents[0][1], host.consents[1][1])
            self.assertEqual(host.result['binding'], 'owned-draft')
            self.assertNotIn('credential', json.dumps(host.frames))

    async def test_repair_denial_prevents_second_dispatch(self):
        """Explicitly declined repair cannot reuse initial disclosure consent."""
        with tempfile.TemporaryDirectory() as directory:
            host = await self.perform(directory, deny=True)
            self.assertEqual((host.result['status'], host.result['attempts']), ('FAILED', 1))
            self.assertEqual(host.result['code'], 'CONSENT_REQUIRED')

    async def test_insufficient_remaining_budget_prevents_repair(self):
        """Consent cannot override the durable remaining installation budget."""
        with tempfile.TemporaryDirectory() as directory:
            host = await self.perform(directory, ceiling=50000)
            self.assertEqual((host.result['code'], host.result['attempts']), ('BUDGET_EXHAUSTED', 1))

    async def test_wrong_response_nonce_and_sequence(self):
        """An unrelated or replayed response cannot unblock a capability callback."""
        for nonce_wrong, seq_wrong in [(True, False), (False, True)]:
            nonce = str(uuid.uuid4())
            reader = asyncio.StreamReader()
            reader.feed_data(frame(nonce, 0, 'START', {}))
            channel = Channel(reader, io.BytesIO())
            await channel.start()
            reader.feed_data(frame(str(uuid.uuid4()) if nonce_wrong else nonce, 0 if seq_wrong else 1, 'REPLY', {'approved': True}))
            with self.assertRaises(ProtocolFailure):
                await channel.exchange('AUTH', {})


class JournalTests(unittest.TestCase):
    """Exercise lifetime ceiling binding independently of graph state."""

    def test_ceiling_and_profile_immutable_on_restart(self):
        """Changing configuration cannot reopen the journal with a larger budget."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ledger.json'
            with IntegrationJournal(path, ceiling=200000, profile='FIXTURE') as journal:
                journal.claim('first', 1)
            for ceiling, profile in [(300000, 'FIXTURE'), (200000, 'REMOTE_ASSISTED')]:
                with self.assertRaises(ProviderFailure):
                    with IntegrationJournal(path, ceiling=ceiling, profile=profile):
                        pass

    def test_custom_ceiling_preserves_completed_and_unknown_cost(self):
        """More than the old demo ceiling is possible only within a pinned new bound."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ledger.json'
            for i in range(3):
                with IntegrationJournal(path, ceiling=150000) as journal:
                    journal.claim('op' + str(i), 1)
                    if i == 0:
                        journal.finish('op0', 1, 'COMPLETED')
            with IntegrationJournal(path, ceiling=150000) as journal:
                with self.assertRaises(ProviderFailure) as failure:
                    journal.claim('another', 1)
                self.assertEqual(failure.exception.code, 'BUDGET_EXHAUSTED')
            saved = json.loads(path.read_text())
            self.assertEqual(saved['ceiling'], 150000)
            self.assertEqual(sum(a['reserved'] for values in saved['operations'].values() for a in values), 150000)

    def test_corruption_missing_and_ceiling_type(self):
        """Ambiguous persisted state and boolean numeric coercion fail closed."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ledger.json'
            with IntegrationJournal(path):
                pass
            path.unlink()
            with self.assertRaises(ProviderFailure):
                with IntegrationJournal(path):
                    pass
            with self.assertRaises(ProviderFailure):
                IntegrationJournal(path, ceiling=True)

    def test_frame_limits_and_duplicate_fields(self):
        """Reject malformed, excessive and ambiguous protocol frames before callbacks."""
        for raw in [b'{}', b'{}\n{}\n', b'{"x":1,"x":2}\n', b'[' + b'0' * 262144 + b']\n', b'{"x":NaN}\n']:
            with self.assertRaises(ProtocolFailure):
                decode(raw)


if __name__ == '__main__':
    unittest.main()
