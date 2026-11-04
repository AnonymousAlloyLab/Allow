#!/usr/bin/env python3
"""Gate-only observation/barrier adapter around the copied actual CLI and Store bodies."""
import argparse
import json
import os
from pathlib import Path
import time


class PausedConnection:
    """Delay only after four completed legal SELECTs, leaving all SQL and return values intact."""
    statements = ("SELECT set_config('allow.tenant',%s,true)",
                  "SELECT set_config('allow.project',%s,true)",
                  "SELECT set_config('allow.purpose',%s,true)",
                  'SELECT head_revision FROM documents.document WHERE document_id=%s')

    def __init__(self, connection, events):
        """Retain the real canonical connection and private timing-only trace."""
        self.connection, self.events = connection, events

    def __enter__(self):
        """Preserve the real driver's transaction lifecycle."""
        self.connection.__enter__()
        return self

    def __exit__(self, *arguments):
        """Commit or roll back and close through the real driver."""
        return self.connection.__exit__(*arguments)

    def __getattr__(self, name):
        """Forward capabilities without changing transport or session identity."""
        return getattr(self.connection, name)

    def execute(self, statement, *arguments, **keywords):
        """Pause800ms after a real matching query response, recording exact pause intervals."""
        result = self.connection.execute(statement, *arguments, **keywords)
        if statement in self.statements:
            event = {'template': self.statements.index(statement), 'started_ns': time.monotonic_ns()}
            self.events.append(event)
            time.sleep(.8)
            event['finished_ns'] = time.monotonic_ns()
        return result


def save(path, value):
    """Write a new private, content-free telemetry event without overwriting evidence."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(value, stream)


def main():
    """Run the unchanged CLI; optionally pause only after actual history decoding completes."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--barrier', action='store_true')
    parser.add_argument('--registration-stall', action='store_true')
    parser.add_argument('--paced-selects', action='store_true')
    arguments = parser.parse_args()
    from allow_documents import cli, context_lease
    from allow_documents.store import Store
    original = Store.validation_context
    inventory = Store._history_inventory
    registration = context_lease.register
    connector = context_lease.sql_connections.connect
    telemetry = {'sqlstates': [], 'failure_classes': [], 'pauses': [], 'started_ns': time.monotonic_ns()}

    def observed_context(instance, *args, **kwargs):
        """Capture exception classes/SQLSTATE only while preserving the original exception chain."""
        try:
            return original(instance, *args, **kwargs)
        except BaseException as error:
            current = error
            seen = set()
            while current is not None and id(current) not in seen:
                seen.add(id(current))
                telemetry['failure_classes'].append(type(current).__name__)
                state = getattr(current, 'sqlstate', None)
                if state:
                    telemetry['sqlstates'].append(state)
                current = current.__cause__ or current.__context__
            raise

    def after_decode(instance, *args, **kwargs):
        """Expose a gate-only barrier after complete real inventory collection, without SQL replacement."""
        value = inventory(instance, *args, **kwargs)
        if arguments.barrier:
            save(arguments.directory/'barrier.json', {'phase': 'history_decoded', 'monotonic_ns': time.monotonic_ns()})
            deadline = time.monotonic()+10
            while not (arguments.directory/'release').exists():
                if time.monotonic() >= deadline:
                    raise TimeoutError('gate_barrier_deadline')
                time.sleep(.01)
        return value

    def after_registration(nonce):
        """Pause after the real lease reservation and before any backend-open attempt."""
        value = registration(nonce)
        save(arguments.directory/'barrier.json', {'phase': 'registered_before_connect', 'monotonic_ns': time.monotonic_ns()})
        deadline = time.monotonic()+10
        while not (arguments.directory/'release').exists():
            if time.monotonic() >= deadline:
                raise TimeoutError('gate_barrier_deadline')
            time.sleep(.01)
        return value

    def paced_connect(*args, **kwargs):
        """Wrap only the actual reserved-context connection; preserve all canonical routing checks."""
        current = connector(*args, **kwargs)
        if kwargs.get('client', '').startswith('allow-document-context:'):
            return PausedConnection(current, telemetry['pauses'])
        return current

    Store.validation_context = observed_context
    Store._history_inventory = after_decode
    if arguments.registration_stall:
        context_lease.register = after_registration
    if arguments.paced_selects:
        context_lease.sql_connections.connect = paced_connect
    try:
        cli.main()
    finally:
        telemetry['finished_ns'] = time.monotonic_ns()
        save(arguments.directory/'telemetry.json', telemetry)


if __name__ == '__main__':
    main()
