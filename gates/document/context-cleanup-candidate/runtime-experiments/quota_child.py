#!/usr/bin/env python3
"""Observe real history iteration/resource usage around the unchanged copied CLI/Store."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import time

from probe_child import save


def memory_status():
    """Read current executable memory high-water fields separately from lifetime getrusage RSS."""
    result = {}
    for line in Path('/proc/self/status').read_text().splitlines():
        name, separator, value = line.partition(':')
        if separator and name in ('VmPeak', 'VmSize', 'VmHWM', 'VmRSS'):
            result[name+'_bytes'] = int(value.strip().split()[0])*1024
    return result


class HistoryRows:
    """Delegate every real row while counting bytes and binding the complete observed multiset."""
    def __init__(self, cursor, stats, focus):
        """Retain one actual cursor, private numeric telemetry and optional synthetic focus ID."""
        self.cursor, self.stats, self.focus = cursor, stats, focus

    def __iter__(self):
        """Yield unchanged rows; hash exact byte content before the production decoder receives it."""
        for row in self.cursor:
            raw = bytes(row['content'])
            self.stats['rows_iterated'] += 1
            self.stats['decoded_content_bytes'] += len(raw)
            self.stats['row_sha256'].append(hashlib.sha256(raw).hexdigest())
            if self.focus and self.focus.encode() in raw:
                self.stats['focus_row_indexes'].append(self.stats['rows_iterated']-1)
            yield row


class HistoryConnection:
    """Change only observation of the exact already-admitted full-history SELECT."""
    def __init__(self, connection, stats, focus):
        """Retain the original canonical connection and fixed observer state."""
        self.connection, self.stats, self.focus = connection, stats, focus

    def execute(self, statement, *args, **kwargs):
        """Execute original SQL/parameters, then observe the actual libpq result and cursor."""
        started = time.monotonic_ns()
        cursor = self.connection.execute(statement, *args, **kwargs)
        if statement != 'SELECT content FROM documents.artifact WHERE document_id=%s':
            raise RuntimeError('unexpected_history_observation_statement')
        self.stats['history_select_count'] += 1
        self.stats['history_execute_ns'] = time.monotonic_ns()-started
        result = cursor.pgresult
        self.stats['raw_rows_buffered'] = result.ntuples
        self.stats['raw_column_format'] = result.fformat(0)
        self.stats['raw_column_bytes'] = sum(len(result.get_value(index, 0)) for index in range(result.ntuples))
        return HistoryRows(cursor, self.stats, self.focus)


def main():
    """Run the real private CLI and report only finite resource/iteration observations."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True, type=Path)
    arguments = parser.parse_args()
    from allow_documents import cli
    from allow_documents.store import Store
    control = arguments.directory/'quota-control.json'
    focus = json.loads(control.read_text()).get('focus_id') if control.exists() else None
    original = Store._history_inventory
    stats = {'history_select_count': 0, 'raw_rows_buffered': 0, 'raw_column_bytes': 0,
             'rows_iterated': 0, 'decoded_content_bytes': 0, 'row_sha256': [], 'focus_row_indexes': [],
             'started_ns': time.monotonic_ns(), 'rlimit_as': list(resource.getrlimit(resource.RLIMIT_AS)),
             'rlimit_cpu': list(resource.getrlimit(resource.RLIMIT_CPU)), 'entry_memory': memory_status()}

    def observed(instance, connection, document, wanted):
        """Delegate the unchanged production method using a read-only observation adapter."""
        try:
            return original(instance, HistoryConnection(connection, stats, focus), document, wanted)
        finally:
            stats['history_finished_ns'] = time.monotonic_ns()

    Store._history_inventory = observed
    try:
        cli.main()
    finally:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        stats.update(finished_ns=time.monotonic_ns(), kernel_peak_rss_bytes=usage.ru_maxrss*1024,
                     cpu_seconds=usage.ru_utime+usage.ru_stime, final_memory=memory_status(),
                     lifetime_rss_interpretation='getrusage includes pre-exec process lifetime; do not equate with post-exec VmHWM or physical group memory')
        stats['row_multiset_sha256'] = hashlib.sha256('\n'.join(sorted(stats['row_sha256'])).encode()).hexdigest()
        save(arguments.directory/'quota-telemetry.json', stats)


if __name__ == '__main__':
    main()
