"""Real LangGraph host callbacks over a private pipe; no direct SQL or validator."""
from dataclasses import asdict
import json

from allow_ai.provider import OpenAiSolProvider
from allow_ai.types import Request, Verification
from allow_ai.wire import request_binding
from allow_ai.workflow import Runner
from journal import IntegrationJournal
from protocol import ProtocolFailure


def request(data):
    """Validate the closed trusted launch object without accepting provider controls."""
    keys = {'operationId', 'source', 'intent', 'feature', 'binding', 'provider', 'credential', 'ledger', 'ceiling'}
    if set(data) != keys or any(type(data[k]) is not str for k in keys - {'ceiling'}):
        raise ProtocolFailure()
    if data['provider'] not in {'FIXTURE', 'REMOTE_ASSISTED'}:
        raise ProtocolFailure()
    if len(data['credential']) > 4096 or data['provider'] == 'FIXTURE' and data['credential']:
        raise ProtocolFailure()
    value = Request(data['operationId'], data['source'], data['intent'], data['feature'], data['binding'])
    request_binding(value)
    return value


class FixtureProvider:
    """Exercise fresh repair consent without a credential or network request."""

    def __init__(self, source, kind):
        """Store only the anonymous prepared source and requested operation."""
        self._source, self._kind, self._calls = source, kind, 0

    async def generate(self, payload, timeout):
        """Return invalid then unchanged valid source; fixture behavior is explicit."""
        self._calls += 1
        source = '' if self._kind == 'EXPLANATION' else ('sig Slot0 {\n' if self._calls == 1 else self._source)
        return json.dumps({'kind': self._kind, 'source': source,
                           'explanation': 'Deterministic fixture suggestion; no remote model was called.'})


class Host:
    """Translate capability callbacks without putting authority or keys in graph state."""

    def __init__(self, channel, value):
        """Bind callbacks to exactly the original request and private channel."""
        self._channel, self._request = channel, value
        self._runner_binding = request_binding(value)

    async def authorize(self, binding):
        """Recheck the graph binding locally and host authority on every edge."""
        if binding != self._runner_binding:
            return False
        reply = await self._channel.exchange('AUTH', {'binding': self._request.binding})
        if set(reply) != {'approved'} or type(reply['approved']) is not bool:
            raise ProtocolFailure()
        return reply['approved']

    async def consent(self, prepared):
        """Present exact payload bytes and require a fresh explicit host approval."""
        reply = await self._channel.exchange('PREPARED', {
            'binding': self._request.binding, 'attempt': prepared.attempt,
            'payload': prepared.payload.decode('ascii'), 'payloadHash': prepared.payload_hash,
            'model': prepared.model})
        if set(reply) != {'approved'} or type(reply['approved']) is not bool:
            raise ProtocolFailure()
        return reply['approved']

    async def verify(self, source, timeout):
        """Delegate to Spring's existing scoped shared worker lane."""
        reply = await self._channel.exchange('VERIFY', {'source': source, 'timeout': timeout})
        if set(reply) != {'status', 'code', 'projection', 'source_hash', 'evidence'}:
            raise ProtocolFailure()
        if reply['status'] not in {'VALIDATED', 'INVALID', 'UNAVAILABLE'}:
            raise ProtocolFailure()
        return Verification(**reply)


async def run(channel, root):
    """Run one job with exclusive durable accounting and release key references."""
    data = await channel.start()
    value = request(data)
    secret = data.pop('credential')
    provider = None
    try:
        provider = OpenAiSolProvider(secret) if data['provider'] == 'REMOTE_ASSISTED' else FixtureProvider(value.source, value.kind)
        secret = None
        host = Host(channel, value)
        with IntegrationJournal(data['ledger'], ceiling=data['ceiling'], profile=data['provider'], root=root) as journal:
            result = await Runner(provider, journal, host.verify).run(value, host.consent, host.authorize)
        output = asdict(result)
        output['binding'] = value.binding
        channel.send('RESULT', output)
    finally:
        secret = None
        if isinstance(provider, OpenAiSolProvider):
            provider.close()
