"""Single-endpoint, non-retrying OpenAI transport with bounded inert output.

Tariff and provider behavior remain external trust assumptions. This adapter grants
neither document authority nor budget admission; the host must reserve first.
"""
import asyncio
import json
import math
from typing import Any

import httpx

ENDPOINT = 'https://api.openai.com/v1/responses'
MODEL = 'gpt-6.1-sol'


class ProviderFailure(Exception):
    """Expose only a fixed code and optional HTTP status, never provider bodies."""

    def __init__(self, code: str, http_status: int | None = None):
        """Initialize safe public failure metadata."""
        self.code = code
        self.http_status = http_status
        super().__init__(code)


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON keys before a dictionary loses that information."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate key')
        result[key] = value
    return result


def _decode(raw: bytes) -> dict[str, Any]:
    """Decode bounded strict JSON without exposing decoder exceptions."""
    try:
        value = json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=_object,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if not isinstance(value, dict):
            raise ValueError()
        _depth(value)
        return value
    except (ValueError, UnicodeError, RecursionError, TypeError):
        raise ProviderFailure('PROVIDER_ENVELOPE_INVALID') from None


def _depth(value: Any, depth: int = 0) -> None:
    """Reject adversarial JSON nesting beyond the fixed envelope allowance."""
    if depth > 24:
        raise ValueError()
    if isinstance(value, dict):
        for child in value.values():
            _depth(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _depth(child, depth + 1)


def _validate_payload(payload: bytes) -> None:
    """Require the pinned non-agent request profile before opening a socket."""
    if not isinstance(payload, bytes) or len(payload) > 4096 or not payload.isascii():
        raise ProviderFailure('PROVIDER_REQUEST_INVALID')
    data = _decode(payload)
    allowed = {'model', 'input', 'store', 'stream', 'service_tier', 'reasoning',
               'max_output_tokens', 'text', 'instructions'}
    expected = {'model': MODEL, 'store': False, 'stream': False,
                'service_tier': 'default', 'reasoning': {'effort': 'low'}}
    if set(data) - allowed or any(data.get(k) != v for k, v in expected.items()):
        raise ProviderFailure('PROVIDER_REQUEST_INVALID')
    limit = data.get('max_output_tokens')
    if type(limit) is not int or not 1 <= limit <= 2048 or not isinstance(data.get('input'), str):
        raise ProviderFailure('PROVIDER_REQUEST_INVALID')
    if 'instructions' in data and not isinstance(data['instructions'], str):
        raise ProviderFailure('PROVIDER_REQUEST_INVALID')


def _text_answer(data: dict[str, Any]) -> str:
    """Extract exactly one completed assistant text, ignoring inert reasoning."""
    if data.get('status') != 'completed' or data.get('model') != MODEL:
        raise ProviderFailure('PROVIDER_ENVELOPE_INVALID')
    if data.get('service_tier') != 'default' or data.get('error') is not None:
        raise ProviderFailure('PROVIDER_ENVELOPE_INVALID')
    _usage(data.get('usage'))
    output = data.get('output')
    if not isinstance(output, list):
        raise ProviderFailure('PROVIDER_ENVELOPE_INVALID')
    texts = []
    for item in output:
        if not isinstance(item, dict):
            raise ProviderFailure('PROVIDER_ENVELOPE_INVALID')
        if item.get('type') == 'reasoning':
            continue
        texts.append(_message(item))
    if len(texts) != 1 or len(texts[0].encode('utf-8')) > 32768:
        raise ProviderFailure('PROVIDER_ENVELOPE_INVALID')
    return texts[0]


def _usage(usage: Any) -> None:
    """Inspect reported categories without refunds; absence keeps full reservation."""
    if usage is None:
        return
    if not isinstance(usage, dict):
        raise ProviderFailure('PROVIDER_USAGE_INVALID')
    for field, bound in (('input_tokens', 8192), ('output_tokens', 2048)):
        count = usage.get(field)
        if type(count) is not int or not 0 <= count <= bound:
            raise ProviderFailure('PROVIDER_USAGE_INVALID')


def _message(item: dict[str, Any]) -> str:
    """Reject refusals, actions and multiple text items rather than selecting one."""
    if item.get('type') != 'message' or item.get('role') != 'assistant':
        raise ProviderFailure('PROVIDER_ENVELOPE_INVALID')
    if item.get('status') != 'completed':
        raise ProviderFailure('PROVIDER_INCOMPLETE')
    content = item.get('content')
    if not isinstance(content, list) or len(content) != 1:
        raise ProviderFailure('PROVIDER_ENVELOPE_INVALID')
    part = content[0]
    if not isinstance(part, dict) or part.get('type') != 'output_text':
        raise ProviderFailure('PROVIDER_REFUSED')
    text = part.get('text')
    if not isinstance(text, str) or not text:
        raise ProviderFailure('PROVIDER_ENVELOPE_INVALID')
    return text


class OpenAiSolProvider:
    """Keep the credential outside graph state and release it explicitly on close."""

    def __init__(self, secret: str, *, transport: httpx.AsyncBaseTransport | None = None):
        """Accept an in-memory secret and optional isolated test transport."""
        if not isinstance(secret, str) or not secret or any(c.isspace() for c in secret):
            raise ProviderFailure('CREDENTIAL_INVALID')
        self._secret = secret
        self._transport = transport
        self._active = False

    def __repr__(self) -> str:
        """Avoid revealing secret state through ordinary diagnostic formatting."""
        return 'OpenAiSolProvider(<redacted>)'

    def close(self) -> None:
        """Drop our secret reference; Python strings do not promise secure erasure."""
        self._secret = None

    async def generate(self, payload: bytes, timeout: float) -> str:
        """Perform one bounded dispatch, with no redirects, proxy inheritance or retry."""
        _validate_payload(payload)
        if not self._secret:
            raise ProviderFailure('CREDENTIAL_UNAVAILABLE')
        if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ProviderFailure('PROVIDER_TIMEOUT')
        if self._active:
            raise ProviderFailure('PROVIDER_BUSY')
        self._active = True
        try:
            async with asyncio.timeout(min(float(timeout), 20.0)):
                return await self._request(payload, min(float(timeout), 20.0))
        except TimeoutError:
            raise ProviderFailure('OUTCOME_UNKNOWN') from None
        except httpx.HTTPError:
            raise ProviderFailure('OUTCOME_UNKNOWN') from None
        except (UnicodeError, ValueError, TypeError):
            raise ProviderFailure('PROVIDER_ENVELOPE_INVALID') from None
        finally:
            self._active = False

    async def _request(self, payload: bytes, timeout: float) -> str:
        """Stream raw bytes with a hard cap and close all network resources on exit."""
        options = {'verify': True, 'trust_env': False, 'follow_redirects': False,
                   'timeout': httpx.Timeout(timeout, connect=min(timeout, 5.0)),
                   'transport': self._transport}
        headers = {'Authorization': 'Bearer ' + self._secret, 'Content-Type': 'application/json',
                   'Accept-Encoding': 'identity'}
        async with httpx.AsyncClient(**options) as client:
            async with client.stream('POST', ENDPOINT, content=payload, headers=headers) as response:
                if response.status_code != 200:
                    raise ProviderFailure('PROVIDER_HTTP_ERROR', response.status_code)
                if response.headers.get('content-encoding', 'identity') != 'identity':
                    raise ProviderFailure('PROVIDER_ENVELOPE_INVALID')
                raw = bytearray()
                async for chunk in response.aiter_raw():
                    if len(raw) + len(chunk) > 65536:
                        raise ProviderFailure('PROVIDER_RESPONSE_TOO_LARGE')
                    raw.extend(chunk)
                return _text_answer(_decode(bytes(raw)))
