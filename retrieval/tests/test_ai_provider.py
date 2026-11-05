"""Finite mock transport checks; these tests never send credentials or network data."""
import asyncio
import json
import unittest
from unittest.mock import patch

import httpx

from allow_ai.provider import ENDPOINT, MODEL, OpenAiSolProvider, ProviderFailure
from allow_ai.types import Request
from allow_ai.wire import build_payload


class BytesStream(httpx.AsyncByteStream):
    """Track closure of bounded or interrupted response bodies."""
    def __init__(self, body, delay=0):
        self.body, self.delay, self.closed = body, delay, False

    async def __aiter__(self):
        """Optionally wait long enough to exercise overall cancellation."""
        if self.delay:
            await asyncio.sleep(self.delay)
        yield self.body

    async def aclose(self):
        """Record transport body cleanup."""
        self.closed = True


def envelope(**changes):
    """Create a synthetic envelope without any real model data."""
    value = {'status': 'completed', 'model': MODEL, 'service_tier': 'default',
             'output': [{'type': 'message', 'role': 'assistant', 'status': 'completed',
                         'content': [{'type': 'output_text', 'text': '{"fixture":true}'}]}],
             'usage': {'input_tokens': 10, 'output_tokens': 5}}
    return {**value, **changes}


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    """Exercise one-shot requests and inert strict envelope admission."""
    def setUp(self):
        """Prepare only an authored anonymous fixture."""
        self.payload = build_payload(Request('test', 'sig A {}', 'Explain fixture.'), 1)
        self.calls = []
        self.streams = []

    def provider(self, body=None, status=200, headers=None, delay=0):
        """Build an in-memory mock transport and record its fixed outbound request."""
        async def handle(request):
            self.calls.append(request)
            raw = json.dumps(envelope()).encode() if body is None else body
            stream = BytesStream(raw, delay)
            self.streams.append(stream)
            return httpx.Response(status, stream=stream, headers=headers)
        return OpenAiSolProvider('synthetic-secret', transport=httpx.MockTransport(handle))

    async def rejected(self, data, code='PROVIDER_ENVELOPE_INVALID'):
        """Require one terminal denial and no retry for a synthetic response."""
        provider = self.provider(json.dumps(data).encode())
        with self.assertRaises(ProviderFailure) as caught:
            await provider.generate(self.payload, 1)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(len(self.calls), 1)
        provider.close()

    async def test_exact_request_and_no_ambient_transport(self):
        """Pin endpoint, request choices and proxy/redirect/TLS controls."""
        provider = self.provider()
        original = httpx.AsyncClient
        with patch('allow_ai.provider.httpx.AsyncClient', wraps=original) as client:
            self.assertEqual(await provider.generate(self.payload, 1), '{"fixture":true}')
        request = self.calls[0]
        self.assertEqual(str(request.url), ENDPOINT)
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.content, self.payload)
        self.assertEqual(request.headers['authorization'], 'Bearer synthetic-secret')
        self.assertIs(client.call_args.kwargs['trust_env'], False)
        self.assertIs(client.call_args.kwargs['follow_redirects'], False)
        self.assertIs(client.call_args.kwargs['verify'], True)
        self.assertTrue(self.streams[0].closed)
        self.assertNotIn('synthetic-secret', repr(provider))
        provider.close()
        with self.assertRaises(ProviderFailure):
            await provider.generate(self.payload, 1)

    async def test_request_admission_before_network(self):
        """Deny tools, remote media input, bad model and excess request bytes."""
        provider = self.provider()
        data = json.loads(self.payload)
        values = [{**data, 'tools': []}, {**data, 'model': 'other'},
                  {**data, 'store': True}, {**data, 'input': [{'type': 'input_image'}]},
                  {**data, 'max_output_tokens': True}]
        for value in values:
            with self.assertRaises(ProviderFailure):
                await provider.generate(json.dumps(value).encode(), 1)
        with self.assertRaises(ProviderFailure):
            await provider.generate(b' ' * 4097, 1)
        self.assertEqual(self.calls, [])

    async def test_bad_identity_status_and_tier(self):
        """Refuse unknown aliases, processing status or premium tier."""
        for changes in ({'model': 'gpt-6.1-sol-other'}, {'status': 'incomplete'},
                        {'service_tier': 'priority'}, {'service_tier': None},
                        {'error': {'message': 'private'}}):
            self.calls.clear()
            await self.rejected(envelope(**changes))

    async def test_tools_refusal_multiple_text_and_reasoning(self):
        """Never execute action items or choose among multiple answers."""
        await self.rejected(envelope(output=[{'type': 'function_call'}]))
        self.calls.clear()
        good = envelope()['output'][0]
        await self.rejected(envelope(output=[good, good]))
        self.calls.clear()
        refused = {**good, 'content': [{'type': 'refusal', 'refusal': 'private'}]}
        await self.rejected(envelope(output=[refused]), 'PROVIDER_REFUSED')
        self.calls.clear()
        provider = self.provider(json.dumps(envelope(output=[{'type': 'reasoning', 'summary': []}, good])).encode())
        self.assertEqual(await provider.generate(self.payload, 1), '{"fixture":true}')

    async def test_http_error_sanitized_and_no_retry(self):
        """Discard error bodies and preserve only fixed code and HTTP status."""
        provider = self.provider(b'private-body-and-secret', status=429)
        with self.assertRaises(ProviderFailure) as caught:
            await provider.generate(self.payload, 1)
        self.assertEqual(caught.exception.http_status, 429)
        self.assertEqual(str(caught.exception), 'PROVIDER_HTTP_ERROR')
        self.assertNotIn('private', repr(caught.exception))
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(self.streams[0].closed)

    async def test_raw_body_bound_and_no_compression(self):
        """Bound raw response allocation and disallow compressed expansion."""
        for body, headers in ((b'X' * 65537, {}), (b'private', {'content-encoding': 'gzip'})):
            provider = self.provider(body, headers=headers)
            with self.assertRaises(ProviderFailure):
                await provider.generate(self.payload, 1)
            self.assertTrue(self.streams[-1].closed)

    async def test_timeout_closes_body_and_does_not_retry(self):
        """A hard overall timeout cancels reading and releases the response."""
        provider = self.provider(delay=1)
        with self.assertRaises(ProviderFailure) as caught:
            await provider.generate(self.payload, 0.01)
        self.assertEqual(caught.exception.code, 'OUTCOME_UNKNOWN')
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(self.streams[0].closed)

    async def test_duplicate_deep_invalid_and_oversized_text(self):
        """Strict decoding rejects ambiguity, excess nesting and oversized text."""
        for raw in (b'{"status":"completed","status":"other"}', b'{"x":' + b'[' * 30 + b'0' + b']' * 30 + b'}', b'\xff'):
            with self.assertRaises(ProviderFailure):
                await self.provider(raw).generate(self.payload, 1)
        good = envelope()['output'][0]
        good['content'][0]['text'] = 'X' * 32769
        self.calls.clear()
        await self.rejected(envelope(output=[good]))

    async def test_usage_caps_and_missing_usage_keep_conservative_path(self):
        """Reject reported over-cap usage; missing usage never grants refunds."""
        await self.rejected(envelope(usage={'input_tokens': 8193, 'output_tokens': 1}), 'PROVIDER_USAGE_INVALID')
        provider = self.provider(json.dumps(envelope(usage=None)).encode())
        self.assertEqual(await provider.generate(self.payload, 1), '{"fixture":true}')

    async def test_same_provider_rejects_overlapping_dispatch(self):
        """The adapter does not create an additional provider concurrency lane."""
        provider = self.provider(delay=0.03)
        task = asyncio.create_task(provider.generate(self.payload, 1))
        await asyncio.sleep(0)
        with self.assertRaises(ProviderFailure) as caught:
            await provider.generate(self.payload, 1)
        self.assertEqual(caught.exception.code, 'PROVIDER_BUSY')
        self.assertEqual(await task, '{"fixture":true}')
        self.assertEqual(len(self.calls), 1)
