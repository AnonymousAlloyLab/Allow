"""Isolated authored-fixture CLI; it cannot open production workspaces or corpus."""
import argparse
import asyncio
import getpass
import json
import os
from pathlib import Path
import resource
import sys
import time
import uuid

from .journal import DispatchJournal
from .provider import ENDPOINT, MODEL, OpenAiSolProvider, ProviderFailure
from .types import Request
from .verification import DocumentVerifier
from .wire import FAILURES, build_payload, digest, request_binding
from .workflow import Runner

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = 'sig S0 {}\npred p0 { some S0 }\nrun p0 for 3\n'
REPAIRED = 'sig S0 {}\npred p0 { no S0 }\nrun p0 for 3\n'
INTENT = 'Keep sig S0, make predicate p0 require no S0, and retain the bounded run command.'


class FixtureProvider:
    """Deterministically exercise an invalid first source and a valid repair."""

    def __init__(self):
        """Start a fresh private fixture sequence with no credential."""
        self._calls = 0

    async def generate(self, payload, timeout):
        """Return inert JSON; the actual Java worker independently checks source."""
        self._calls += 1
        source = 'sig S0 {\n' if self._calls == 1 else REPAIRED
        return json.dumps({'kind': 'SOURCE_EDIT', 'source': source,
                           'explanation': 'Authored fixture repair.'})


def _secret(fd):
    """Read only from a private inherited descriptor or non-echo terminal."""
    if fd is None:
        if not sys.stdin.isatty():
            raise ProviderFailure('CREDENTIAL_UNAVAILABLE')
        return getpass.getpass('OpenAI key (hidden; memory only): ')
    try:
        raw = os.read(fd, 4097)
        if not raw or len(raw) > 4096:
            raise ProviderFailure('CREDENTIAL_INVALID')
        return raw.decode('ascii').rstrip('\r\n')
    finally:
        os.close(fd)


async def _run(args, provider):
    """Authorize only the finite authored fixture payloads, never arbitrary files."""
    request = Request(args.operation_id, FIXTURE, INTENT, binding='isolated-authored-fixture-v1')
    binding = request_binding(request)
    allowed = {(1, digest(build_payload(request, 1, None)))}
    allowed.update((2, digest(build_payload(request, 2, code))) for code in FAILURES)

    async def consent(prepared):
        """Apply this run's explicit synthetic grant to exact finite payload hashes."""
        return (prepared.binding == binding and prepared.operation_id == request.operation_id
                and prepared.model == MODEL and (prepared.attempt, prepared.payload_hash) in allowed
                and digest(prepared.payload) == prepared.payload_hash)

    async def authorize(observed):
        """Recognize only this authored run; this is not production authorization."""
        return observed == binding

    verifier = DocumentVerifier(args.backend_target)
    with DispatchJournal(args.ledger, root=ROOT) as journal:
        return await Runner(provider, journal, verifier).run(request, consent, authorize)


def main():
    """Run offline repair by default; explicit flags gate the one-off live fixture."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--backend-target', type=Path, default=ROOT / 'backend/target')
    parser.add_argument('--operation-id', default=str(uuid.uuid4()))
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--synthetic-test-grant', action='store_true')
    parser.add_argument('--standard-tariff-reviewed', action='store_true')
    parser.add_argument('--key-fd', type=int)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.umask(0o077)
    provider = None
    started = time.monotonic()
    try:
        if args.live and not (args.synthetic_test_grant and args.standard_tariff_reviewed):
            raise ProviderFailure('TEST_AUTHORIZATION_REQUIRED')
        if not args.live and args.key_fd is not None:
            raise ProviderFailure('CREDENTIAL_NOT_NEEDED')
        provider = OpenAiSolProvider(_secret(args.key_fd)) if args.live else FixtureProvider()
        started = time.monotonic()
        result = asyncio.run(_run(args, provider))
        report = {'mode': 'LIVE_SYNTHETIC' if args.live else 'OFFLINE_FIXTURE',
                  'model': MODEL, 'endpoint': ENDPOINT if args.live else None,
                  'status': result.status, 'attempts': result.attempts, 'code': result.code,
                  'http_status': result.http_status,
                  'verification': result.verification.status if result.verification else None,
                  'projection': result.verification.projection if result.verification else None,
                  'elapsed_ms': round((time.monotonic() - started) * 1000, 3),
                  'reserved_micro_usd': result.attempts * 50000,
                  'accounting': 'conservative reservation, not observed billed amount',
                  'production_workspace_or_corpus_access': False}
        print(json.dumps(report, indent=2))
        return 0 if result.status == 'REVIEW_READY' else 1
    except (Exception, KeyboardInterrupt) as error:
        allowed = {'TEST_AUTHORIZATION_REQUIRED', 'CREDENTIAL_NOT_NEEDED', 'CREDENTIAL_INVALID',
                   'CREDENTIAL_UNAVAILABLE', 'LEDGER_UNAVAILABLE'}
        code = error.code if isinstance(error, ProviderFailure) and error.code in allowed else 'HARNESS_UNAVAILABLE'
        print(json.dumps({'status': 'FAILED', 'code': code, 'credential_persisted': False}))
        return 1
    finally:
        if isinstance(provider, OpenAiSolProvider):
            provider.close()


if __name__ == '__main__':
    raise SystemExit(main())
