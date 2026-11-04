#!/usr/bin/env python3
"""Finite real-async budget reproduction with explicitly simulated metadata rows.

No database connection or signal is made. The copied production manager runs
unchanged; a gate-local observer seam returns four live identity observations,
then absent identity after a fifth 550ms delay. Each call obeys its supplied
timeout. This tests deadline control flow, not PostgreSQL identity refinement.
"""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import time
from types import SimpleNamespace
import uuid


async def exercise():
    """Observe whether a late positive cleanup result escapes the absolute cutoff."""
    from allow_retrieval.sql_context_identity import process_identity
    from allow_retrieval.sql_context_lease import ContextLeases
    from allow_retrieval.sql_context_observer import ObserverUnavailable
    trace = []
    with tempfile.TemporaryDirectory(prefix='allow-observation-deadline-') as directory:
        root = Path(directory)
        server = SimpleNamespace(status=root/'status.json', listen=root/'socket',
                                 backend=root/'backend', cancel_keys=set())
        manager = ContextLeases(server)
        manager.route_enabled = manager.ready = True
        manager.register(str(uuid.uuid4()), process_identity(os.getpid()))
        entry = manager.journal.entry('context')
        entry.update(phase='RETIRING', opened=True, failed=True, backendPid=40001,
                     backendKey=struct.pack('!II', 40001, 123).hex(), backendStart='2026-11-04 00:00:00+00')
        manager.persist('context', entry)
        started = time.monotonic()
        async def delayed(method, *arguments, timeout=2.5):
            """Honor the production timeout while returning declared simulated live/absent rows."""
            event = {'call': len(trace)+1, 'start_seconds': time.monotonic()-started,
                     'timeout_seconds': timeout, 'simulated_metadata': True}
            trace.append(event)
            try:
                await asyncio.wait_for(asyncio.sleep(.55), timeout)
            except asyncio.TimeoutError:
                event.update(outcome='TIMEOUT', end_seconds=time.monotonic()-started)
                raise ObserverUnavailable('observer_unavailable') from None
            live = event['call'] <= 4
            event.update(outcome='LIVE' if live else 'ABSENT', end_seconds=time.monotonic()-started)
            return ((40001, entry['backendStart'], entry['database'], entry['user'], entry['applicationName']),) if live else ()
        manager.observer.call = delayed
        try:
            try:
                clean = await manager.observe_cleanup('context')
            except (RuntimeError, ValueError, asyncio.TimeoutError):
                clean = False
            if clean:
                manager.complete('context')
            else:
                manager.unknown('context')
            elapsed = time.monotonic()-started
            final = manager.journal.entry('context')
            return {'status': 'PASS' if not clean and final['phase'] == 'UNKNOWN' else 'BLOCKED',
                    'elapsed_seconds': elapsed, 'clean_after_budget': clean and elapsed >= 2.5,
                    'final_phase': final['phase'], 'successPermitted': final['successPermitted'],
                    'trace': trace, 'database_or_kernel_absence_proven': False,
                    'boundary': 'Simulated metadata with real asyncio delays and copied production cleanup control flow only.'}
        finally:
            manager.observer.shutdown()


def main():
    """Verify frozen inputs before executing one non-overwritable finite attempt."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--registration', type=Path, required=True)
    args = parser.parse_args()
    registration = json.loads(args.registration.read_text())
    for row in registration['inputs']:
        if hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() != row['sha256']:
            raise RuntimeError('frozen_fixture_input_changed')
    sys.path.insert(0, registration['import_root'])
    value = asyncio.run(exercise())
    value['registration_sha256'] = hashlib.sha256(args.registration.read_bytes()).hexdigest()
    with Path(registration['output']).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: value[k] for k in ('status', 'elapsed_seconds', 'clean_after_budget', 'final_phase')}))
    return 0 if value['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
