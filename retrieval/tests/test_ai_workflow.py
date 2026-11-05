"""Finite fake-provider tests for the actual bounded LangGraph execution."""
import asyncio
import json
import unittest
from allow_ai import Request, Runner, Verification
from allow_ai.wire import digest, parse_proposal, request_binding
from allow_ai.types import WorkflowFailure
from allow_ai.provider import ProviderFailure
from dataclasses import FrozenInstanceError

SOURCE = 'sig Person {}\npred populated { some Person }\nrun populated for 3\n'


def answer(source=SOURCE, kind='SOURCE_EDIT'):
    """Produce one closed fake model answer."""
    return json.dumps({'kind': kind, 'source': source, 'explanation': 'A suggestion.'})


class Provider:
    """Record bounded payloads and return queued deterministic answers."""
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    async def generate(self, payload, timeout):
        self.calls.append(payload)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


class Journal:
    """Minimal durable-boundary double; real journal has independent tests."""
    def __init__(self):
        self.claims, self.finishes = [], []

    def claim(self, operation_id, attempt):
        if (operation_id, attempt) in self.claims:
            raise ValueError('replay')
        self.claims.append((operation_id, attempt))

    def finish(self, operation_id, attempt, status):
        self.finishes.append((operation_id, attempt, status))


async def verifier(source, timeout):
    """Treat one fixture string as valid; report no solver evidence."""
    if source == SOURCE:
        return Verification('VALIDATED', projection='BLOCK_SUPPORTED', source_hash=digest(source.encode()))
    return Verification('INVALID', code='SOURCE_PARSE_INVALID')


async def approved(argument):
    """An explicit asynchronous affirmative host callback."""
    return True


async def denied(argument):
    """An explicit asynchronous negative host callback."""
    return False


class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    """Exercise real conditional edges with controlled host capabilities."""
    async def execute(self, replies, *, consent=approved, authorize=approved, verify=verifier, kind='SOURCE_EDIT'):
        provider, journal = Provider(replies), Journal()
        runner = Runner(provider, journal, verify)
        result = await runner.run(Request('operation', SOURCE, 'Explain or repair fixture', kind), consent, authorize)
        return result, provider, journal

    async def test_valid_first(self):
        result, provider, journal = await self.execute([answer()])
        self.assertEqual((result.status, result.attempts), ('REVIEW_READY', 1))
        self.assertEqual(len(journal.claims), 1)
        payload = json.loads(provider.calls[0])
        self.assertEqual((payload['model'], payload['store'], payload['stream']), ('gpt-6.1-sol', False, False))
        self.assertNotIn('tools', payload)

    async def test_invalid_then_valid_fresh_consent(self):
        approvals = []
        async def consent(prepared):
            approvals.append(prepared)
            return True
        result, provider, _ = await self.execute([answer('sig Person {'), answer()], consent=consent)
        self.assertEqual((result.status, result.attempts), ('REVIEW_READY', 2))
        self.assertEqual([p.attempt for p in approvals], [1, 2])
        self.assertNotEqual(approvals[0].payload_hash, approvals[1].payload_hash)
        self.assertNotIn('sig Person {"', provider.calls[1].decode())

    async def test_twice_invalid_stops(self):
        result, provider, _ = await self.execute([answer('broken'), answer('still broken')])
        self.assertEqual((result.status, result.attempts, len(provider.calls)), ('INVALID_PROPOSAL', 2, 2))
        self.assertEqual(result.source, '')

    async def test_invalid_schema_repairs(self):
        result, _, _ = await self.execute(['{"kind":"SOURCE_EDIT","kind":"SOURCE_EDIT"}', answer()])
        self.assertEqual((result.status, result.attempts), ('REVIEW_READY', 2))

    async def test_infrastructure_never_repairs(self):
        async def unavailable(source, timeout):
            return Verification('UNAVAILABLE')
        result, provider, _ = await self.execute([answer(), answer()], verify=unavailable)
        self.assertEqual((result.status, len(provider.calls)), ('FAILED', 1))

    async def test_provider_failure_never_repairs(self):
        result, provider, journal = await self.execute([RuntimeError('sensitive text')])
        self.assertEqual((result.status, result.code, len(provider.calls)), ('FAILED', 'UNAVAILABLE', 1))
        self.assertEqual(journal.finishes[-1][-1], 'OUTCOME_UNKNOWN')
        self.assertNotIn('sensitive', repr(result))

    async def test_consent_denial_zero_calls(self):
        result, provider, journal = await self.execute([answer()], consent=denied)
        self.assertEqual((result.code, len(provider.calls), len(journal.claims)), ('CONSENT_REQUIRED', 0, 0))

    async def test_second_consent_denial(self):
        async def first_only(prepared):
            return prepared.attempt == 1
        result, provider, _ = await self.execute([answer('broken'), answer()], consent=first_only)
        self.assertEqual((result.code, len(provider.calls)), ('CONSENT_REQUIRED', 1))

    async def test_stale_after_provider_denies(self):
        checks = 0
        async def authorize(binding):
            nonlocal checks
            checks += 1
            return checks < 6
        result, provider, _ = await self.execute([answer()], authorize=authorize)
        self.assertEqual(result.status, 'FAILED')
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(result.source, '')

    async def test_explanation_is_suggestion(self):
        async def forbidden(source, timeout):
            raise AssertionError('must not validate explanation')
        result, _, _ = await self.execute([answer('', 'EXPLANATION')], kind='EXPLANATION', verify=forbidden)
        self.assertEqual(result.status, 'SUGGESTION')
        self.assertIsNone(result.verification)

    async def test_wrong_verifier_hash_denies(self):
        async def wrong(source, timeout):
            return Verification('VALIDATED', projection='BLOCK_SUPPORTED', source_hash='wrong')
        result, provider, _ = await self.execute([answer()], verify=wrong)
        self.assertEqual((result.code, len(provider.calls)), ('VERIFIER_IDENTITY', 1))

    async def test_unknown_callback_code_is_inert(self):
        async def denied(binding):
            raise WorkflowFailure('secret callback text')
        result, provider, _ = await self.execute([answer()], authorize=denied)
        self.assertEqual((result.code, len(provider.calls)), ('UNAVAILABLE', 0))
        self.assertNotIn('secret callback', repr(result))

    async def test_expected_provider_quota_codes(self):
        for code in ('BUDGET_EXHAUSTED', 'DISPATCH_REPLAY', 'PROVIDER_USAGE_INVALID', 'PROVIDER_BUSY'):
            with self.subTest(code=code):
                result, provider, _ = await self.execute([ProviderFailure(code)])
                self.assertEqual((result.code, len(provider.calls)), (code, 1))

    async def test_consent_preparation_is_frozen(self):
        async def consent(prepared):
            with self.assertRaises(FrozenInstanceError):
                prepared.payload = b'changed'
            return True
        result, _, _ = await self.execute([answer()], consent=consent)
        self.assertEqual(result.status, 'REVIEW_READY')

    async def test_payload_budget_denies(self):
        provider, journal = Provider([answer()]), Journal()
        result = await Runner(provider, journal, verifier).run(Request('op', 'x' * 8000, 'intent'), approved, approved)
        self.assertEqual((result.code, len(provider.calls)), ('PAYLOAD_LIMIT', 0))

    async def test_deadline(self):
        ticks = iter([0, 61])
        runner = Runner(Provider([answer()]), Journal(), verifier, clock=lambda: next(ticks))
        result = await runner.run(Request('op', SOURCE, 'intent'), approved, approved)
        self.assertEqual(result.status, 'EXPIRED')

    async def test_sync_callback_never_invoked(self):
        invoked = []
        def blocking(argument):
            invoked.append(True)
            raise AssertionError('would block')
        for callbacks in ((blocking, approved), (approved, blocking)):
            provider = Provider([answer()])
            result = await Runner(provider, Journal(), verifier).run(Request('op', SOURCE, 'intent'), *callbacks)
            self.assertEqual((result.code, len(provider.calls)), ('CALLBACK_INVALID', 0))
        self.assertEqual(invoked, [])

    async def test_async_callable_object(self):
        class Approval:
            async def __call__(self, argument):
                return True
        result, _, _ = await self.execute([answer()], consent=Approval(), authorize=Approval())
        self.assertEqual(result.status, 'REVIEW_READY')

    async def test_cooperative_callback_crossing_deadline(self):
        now = [0.0]
        async def slow_authority(binding):
            await asyncio.sleep(0)
            now[0] = 61.0
            return True
        provider = Provider([answer()])
        runner = Runner(provider, Journal(), verifier, clock=lambda: now[0])
        result = await runner.run(Request('op', SOURCE, 'intent'), approved, slow_authority)
        self.assertEqual((result.status, len(provider.calls)), ('EXPIRED', 0))
        self.assertEqual(result.source, '')

    async def test_expiry_after_verified_source_never_publishes(self):
        now = [0.0]
        async def expiring_verifier(source, timeout):
            observation = await verifier(source, timeout)
            now[0] = 61.0
            return observation
        provider = Provider([answer()])
        runner = Runner(provider, Journal(), expiring_verifier, clock=lambda: now[0])
        result = await runner.run(Request('op', SOURCE, 'intent'), approved, approved)
        self.assertEqual((result.status, len(provider.calls)), ('EXPIRED', 1))
        self.assertEqual(result.source, '')
        self.assertIsNone(result.verification)

    def test_binding_changes_and_duplicate_json(self):
        self.assertNotEqual(request_binding(Request('op', SOURCE, 'one')), request_binding(Request('op', SOURCE, 'two')))
        with self.assertRaises(WorkflowFailure):
            parse_proposal('{"kind":"EXPLANATION","source":"","explanation":"a","explanation":"b"}', 'EXPLANATION')


if __name__ == '__main__':
    unittest.main()
