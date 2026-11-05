"""A bounded actual LangGraph pipeline with host-owned capabilities outside state."""
import asyncio
import inspect
import time
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langsmith import tracing_context
from .types import PreparedAttempt, Request, Result, Verification, WorkflowFailure
from .provider import ProviderFailure
from .wire import MODEL, FAILURES, build_payload, digest, parse_proposal, request_binding


class State(TypedDict, total=False):
    """Only bounded content and observations; capabilities live in node closures."""
    attempt: int
    status: str
    code: str | None
    proposal: dict
    verification: Verification


def _is_async(callback):
    """Recognize coroutine functions and async callable objects without invoking them."""
    return inspect.iscoroutinefunction(callback) or inspect.iscoroutinefunction(getattr(callback, '__call__', None))


async def _call(callback, argument):
    """Invoke only a previously checked cooperative asynchronous capability."""
    return await callback(argument)


class Runner:
    """Runs sequential isolated requests; the ledger independently prevents replay."""
    def __init__(self, provider, journal, verifier, *, clock=time.monotonic):
        """Keep nonserializable provider/ledger/verifier capabilities outside graph state."""
        self._provider, self._journal, self._verifier, self._clock = provider, journal, verifier, clock
        self._running = False

    async def run(self, request: Request, consent, authorize) -> Result:
        """Run one bounded request; callbacks receive PreparedAttempt and binding string."""
        if not all(_is_async(callback) for callback in (consent, authorize, self._verifier, self._provider.generate)):
            return Result('FAILED', 0, '', code='CALLBACK_INVALID')
        if self._running:
            return Result('FAILED', 0, '', code='BUSY')
        self._running = True
        try:
            return await self._run(request, consent, authorize)
        finally:
            self._running = False

    async def _run(self, request, consent, authorize):
        """Build one uncheckpointed graph whose closure owns authoritative counters."""
        try:
            binding = request_binding(request)
        except WorkflowFailure as failure:
            return Result('FAILED', 0, '', code='INVALID_REQUEST')
        deadline, attempts = self._clock() + 60, 0
        prepared = None

        def remaining():
            left = deadline - self._clock()
            if left <= 0:
                raise WorkflowFailure('EXPIRED')
            return left

        async def authority():
            remaining()
            timeout = remaining()
            if await asyncio.wait_for(_call(authorize, binding), timeout) is not True:
                raise WorkflowFailure('STALE_INPUT')
            remaining()

        async def prepare(state):
            nonlocal prepared
            await authority()
            number = attempts + 1
            payload = build_payload(request, number, state.get('code') if number == 2 else None)
            prepared = PreparedAttempt(request.operation_id, number, payload, digest(payload), MODEL, binding)
            return {'attempt': number, 'status': 'AWAITING_DISCLOSURE'}

        async def approve(state):
            await authority()
            timeout = remaining()
            if await asyncio.wait_for(_call(consent, prepared), timeout) is not True:
                raise WorkflowFailure('CONSENT_REQUIRED')
            await authority()
            return {'status': 'RESERVED'}

        async def dispatch(state):
            nonlocal attempts
            await authority()
            if prepared is None or attempts >= 2 or prepared.attempt != attempts + 1:
                raise WorkflowFailure('INVALID_STATE')
            self._journal.claim(request.operation_id, prepared.attempt)
            attempts += 1
            try:
                timeout = min(20, remaining())
                text = await asyncio.wait_for(self._provider.generate(prepared.payload, timeout), timeout)
                await authority()
            except BaseException:
                self._journal.finish(request.operation_id, attempts, 'OUTCOME_UNKNOWN')
                raise
            self._journal.finish(request.operation_id, attempts, 'COMPLETED')
            try:
                proposal = parse_proposal(text, request.kind)
            except WorkflowFailure:
                return {'status': 'INVALID', 'code': 'SCHEMA_INVALID'}
            return {'proposal': proposal, 'status': 'VERIFYING', 'code': None}

        async def verify(state):
            await authority()
            if state['status'] == 'INVALID':
                return state
            proposal = state['proposal']
            if request.kind == 'EXPLANATION':
                return {'status': 'SUGGESTION', 'code': None}
            timeout = min(10, remaining())
            observation = await asyncio.wait_for(self._verifier(proposal['source'], timeout), timeout)
            await authority()
            if type(observation) is not Verification:
                raise WorkflowFailure('VERIFIER_UNAVAILABLE')
            if observation.status == 'INVALID' and observation.code in FAILURES:
                return {'status': 'INVALID', 'code': observation.code}
            if observation.status != 'VALIDATED' or observation.projection not in ('BLOCK_SUPPORTED', 'TEXT_ONLY'):
                raise WorkflowFailure('VERIFIER_UNAVAILABLE')
            if observation.source_hash != digest(proposal['source'].encode('utf-8')):
                raise WorkflowFailure('VERIFIER_IDENTITY')
            return {'status': 'REVIEW_READY', 'verification': observation, 'code': None}

        def route(state):
            return 'repair' if state['status'] == 'INVALID' and attempts < 2 else 'done'

        graph = StateGraph(State)
        for name, node in [('prepare', prepare), ('consent', approve), ('dispatch', dispatch), ('verify', verify)]:
            graph.add_node(name, node)
        graph.add_edge(START, 'prepare')
        graph.add_edge('prepare', 'consent')
        graph.add_edge('consent', 'dispatch')
        graph.add_edge('dispatch', 'verify')
        graph.add_conditional_edges('verify', route, {'repair': 'prepare', 'done': END})
        compiled = graph.compile(checkpointer=None, store=None, cache=None)
        try:
            with tracing_context(enabled=False):
                timeout = remaining()
                state = await asyncio.wait_for(compiled.ainvoke({'attempt': 0}, config={'recursion_limit': 16, 'callbacks': []}), timeout)
            await authority()
            status = 'INVALID_PROPOSAL' if state['status'] == 'INVALID' else state['status']
            proposal = state.get('proposal', {}) if status in ('REVIEW_READY', 'SUGGESTION') else {}
            return Result(status, attempts, binding, proposal.get('source', ''), proposal.get('explanation', ''), state.get('verification'), state.get('code'))
        except asyncio.CancelledError:
            raise
        except Exception as failure:
            safe_provider = {'PROVIDER_ENVELOPE_INVALID', 'PROVIDER_REQUEST_INVALID', 'CREDENTIAL_INVALID', 'CREDENTIAL_UNAVAILABLE', 'PROVIDER_TIMEOUT', 'OUTCOME_UNKNOWN', 'PROVIDER_HTTP_ERROR', 'PROVIDER_RESPONSE_TOO_LARGE', 'PROVIDER_INCOMPLETE', 'PROVIDER_REFUSED', 'LEDGER_UNAVAILABLE', 'BUDGET_EXHAUSTED', 'DISPATCH_REPLAY', 'PROVIDER_USAGE_INVALID', 'PROVIDER_BUSY'}
            safe_workflow = {'INVALID_REQUEST', 'EXPIRED', 'STALE_INPUT', 'CONSENT_REQUIRED', 'INVALID_STATE', 'PAYLOAD_LIMIT', 'SCHEMA_INVALID', 'VERIFIER_UNAVAILABLE', 'VERIFIER_IDENTITY'}
            code = failure.code if isinstance(failure, WorkflowFailure) and failure.code in safe_workflow else 'UNAVAILABLE'
            if isinstance(failure, ProviderFailure) and failure.code in safe_provider:
                code = failure.code
            http_status = failure.http_status if isinstance(failure, ProviderFailure) and type(failure.http_status) is int and 100 <= failure.http_status <= 599 else None
            return Result('EXPIRED' if isinstance(failure, TimeoutError) or code == 'EXPIRED' else 'FAILED', attempts, binding, code=code, http_status=http_status)
