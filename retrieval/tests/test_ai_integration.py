"""Actual LangGraph, real durable ledger and sandboxed Java fixture checks."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from allow_ai.demo import FIXTURE, REPAIRED, INTENT, FixtureProvider
from allow_ai.journal import DispatchJournal
from allow_ai.types import Request
from allow_ai.verification import DocumentVerifier
from allow_ai.wire import request_binding
from allow_ai.workflow import Runner

ROOT = Path(__file__).resolve().parents[2]


class SequenceProvider:
    """Return fixed adversarial candidates without any provider access."""

    def __init__(self, sources):
        """Keep the predetermined fixture list and count actual dispatches."""
        self._sources = list(sources)
        self.calls = 0

    async def generate(self, payload, timeout):
        """Supply the next closed proposal to independent source verification."""
        source = self._sources[self.calls]
        self.calls += 1
        return json.dumps({'kind': 'SOURCE_EDIT', 'source': source, 'explanation': 'Fixture.'})


class GraphIntegrationTests(unittest.IsolatedAsyncioTestCase):
    """Do not skip a missing real worker; the fixture acceptance must actually run."""

    async def asyncSetUp(self):
        """Create a fresh private non-project ledger and independent worker wrapper."""
        self.directory = tempfile.TemporaryDirectory(prefix='allow-ai-integration-')
        self.ledger = Path(self.directory.name) / 'dispatch.json'
        self.verifier = DocumentVerifier(ROOT / 'backend/target')
        self.request = Request('owned-fixture', FIXTURE, INTENT)
        self.consents = []

    async def asyncTearDown(self):
        """Remove only the owned non-billed fixture accounting directory."""
        self.directory.cleanup()

    async def consent(self, prepared):
        """Record exact consent identities without recording any credentials."""
        self.consents.append((prepared.attempt, prepared.payload_hash))
        return True

    async def authorize(self, binding):
        """Bind the fixture to exactly the known input request."""
        return binding == request_binding(self.request)

    async def run_graph(self, provider):
        """Hold the ledger lock over the entire real graph and verifier lifetime."""
        with DispatchJournal(self.ledger, root=ROOT) as journal:
            return await Runner(provider, journal, self.verifier).run(
                self.request, self.consent, self.authorize)

    async def test_real_invalid_then_valid_loopback(self):
        """A real parse failure receives one fresh-consent repair and passes."""
        result = await self.run_graph(FixtureProvider())
        self.assertEqual((result.status, result.attempts), ('REVIEW_READY', 2))
        self.assertEqual(result.source, REPAIRED)
        self.assertEqual(result.verification.source_hash, hashlib.sha256(REPAIRED.encode()).hexdigest())
        self.assertEqual([item[0] for item in self.consents], [1, 2])
        self.assertNotEqual(self.consents[0][1], self.consents[1][1])
        ledger = json.loads(self.ledger.read_text())
        self.assertEqual(sum(a['reserved'] for a in ledger['operations']['owned-fixture']), 100000)

    async def test_real_repeated_type_invalid_terminates(self):
        """Independent Alloy rejection twice cannot produce a ready proposal."""
        source = 'sig S0 {}\npred p0 { S0 and S0 }\n'
        provider = SequenceProvider([source, source])
        result = await self.run_graph(provider)
        self.assertEqual((result.status, result.attempts, provider.calls), ('INVALID_PROPOSAL', 2, 2))
        self.assertEqual(result.source, '')
        self.assertIsNone(result.verification)

    async def test_one_valid_source_then_restart_replay_denied(self):
        """A restarted run with the same operation cannot send even its first call."""
        first = await self.run_graph(SequenceProvider([REPAIRED]))
        self.assertEqual((first.status, first.attempts), ('REVIEW_READY', 1))
        second_provider = SequenceProvider([REPAIRED])
        second = await self.run_graph(second_provider)
        self.assertEqual((second.status, second_provider.calls), ('FAILED', 0))
        self.assertEqual(second.code, 'DISPATCH_REPLAY')


if __name__ == '__main__':
    unittest.main()
