# SQLeanParser query routing

All Allow-issued PostgreSQL SQL crosses a workspace-owned Unix-socket proxy.
The proxy checks each Simple Query and extended-protocol Parse message using the
pinned `sqlean_pg_grammar` executable built from `/home/augustus/SQLeanParser`.
Policy `sql-routing-v8-context-leases` requires successful grammar acceptance, the
expected profile and upstream commit, and exact source preservation before
forwarding the original bytes. Admissions use the initialized pinned sealed
executable and immutable configuration. The disk image is checked at
initialization/restart; a later disk replacement does not alter the running
sealed image. A bounded cache retains only acceptance for identical SQL under
that image, policy and generation. SQL, credentials and parameter values are
not logged by the proxy.

The [contract](../spec/sql-stage.json) and [28 Lean propositions](../spec/sql-types.json)
were reviewed by two GPT-6.1 Terra, two GPT-6.1 Sol and two GPT-6 Astra agents before
production changes. The [formal report](../gates/sql/formal-report.json) records
the historical 112-proposition SQL milestone and two matching clean builds. The
[sealed-image amendment](../spec/sql-immutable-image.json) adds seven abstract
obligations to the later document surface. The [current status index](current-status.md)
links the complete tested 309-proposition surface. The original SQL model proves an
abstract admission policy, reachable prepared-statement/portal provenance and
cycle-barrier properties. PostgreSQL message classification is a tested adapter
obligation, not a conclusion of the abstract model.
It does not establish Python protocol refinement or PostgreSQL correctness.
The separate [context-cleanup contract](../spec/document-context-cleanup.json)
adds 28 checked model propositions and six reviews before the v8 production
changes. Its complete runtime fault matrix remains open; these propositions
are not added to the inherited 309-proposition aggregate.

## Execution boundary

The proxy sees SQL produced by psycopg, including its numbered placeholders and
implicit transaction commands. Bind parameter values and COPY row bytes are
data, and are preserved. Parse and Bind establish connection-local provenance;
Execute can only use a known admitted portal. Backend errors may still reject
an admitted statement. Native SQL PREPARE and EXECUTE also require exact-source
parser acceptance. Their names share connection-local accepted provenance with
protocol statements. The native form is limited to one top-level statement and
simple ASCII names; all protocol statement and portal names are bounded to 63
bytes to avoid PostgreSQL name truncation aliases. The proxy never retries mutations.

It fixes UTF-8 and `standard_conforming_strings=on`, checks startup and backend
session state, and rejects new SQL while any earlier effect-capable protocol
step awaits its ordered ReadyForQuery. This covers Parse and Bind planning as
well as execution and transaction completion. Bind, Execute, Sync, COPY and
cancellation can still finish an admitted sequence. Consecutive pipelined Parse
messages require synchronization; pipeline throughput is not promised.
Opaque DO blocks, new function/procedure definitions, nested native EXECUTE,
DEALLOCATE, prepared transactions, legacy function-call messages and unreviewed
extensions are rejected. Forbidden grammar productions are checked throughout the parse tree,
including nested statements. The utility policy admits only the specific
additional forms needed by the pinned backup/restore tools.

The protocol rules follow the [PostgreSQL 16 message flow](https://www.postgresql.org/docs/16/protocol-flow.html)
and [message format](https://www.postgresql.org/docs/16/protocol-message-formats.html)
specifications. A single 15-second deadline covers startup through first
readiness. After readiness, frame-progress deadlines apply to partial messages;
ordinary idle sessions and long-running queries do not time out merely because
no new message has arrived. Ordinary live handlers are limited to 15, with one
exclusive validation-context lease and one persistent same-role observer.
Four bounded startup/cancel handlers remain available. Parser concurrency is two, with five-second
wall deadlines and a 1 GiB address-space limit per process.

Ordinary handler limits do not bound all PostgreSQL backend lifetimes: disconnected
ordinary clients can leave backend work running and exhaust database capacity.
The special validation-context path accepts only its fixed read-only sequence,
with a 1.5-second statement timeout, 250-ms lock timeout, 1-second idle-transaction
timeout and a 3-second work deadline from registration. All settings and observer
queries pass through SQLeanParser. The observer has a 500-ms statement timeout;
cleanup observation has a separate 2.5-second budget.

The proxy durably records lease ownership before work, binds the peer and backend
generation, and uses the secret-bound PostgreSQL CancelRequest when available.
It does not use PID-only cancellation SQL. Context results remain staged until
the connection closes and the observer confirms cleanup. Failed or uncertain
cleanup cannot publish success or release the reservation. Pre-key crashes or
observer loss can retain UNKNOWN/DEGRADED and deny new contexts; automatic
availability after those faults is not established.

In the historical implementation, a deliberate sleeping-query
probe observed a live backend after the private document CLI was killed and
reaped at its 20-second deadline; the probe explicitly cancelled its owned
backend. Closing transports does not establish immediate database query
cancellation. That [limitation record](../gates/document/validation-context-candidate/runtime-checks/python/lifecycle-limitation-r1.json)
remains preserved. The new implementation has passed selected real deadline,
lock-timeout, CLI-death and maximum-history cases. A late-observation regression
was repaired by clamping the remaining budget and checking completion time;
the later bound run passes 258 Python tests and
52 SQL checks. The [current status index](current-status.md) distinguishes those
finite successes from the unclosed 33-case cleanup matrix.

PostgreSQL bootstrap internals, built-in routines and reviewed pgvector engine
behavior are explicitly trusted server internals. They are not additional
client SQL packets. This design does not claim to intercept every SQL-like
operation inside PostgreSQL or prevent a host administrator from bypassing an
owned local service. PostgreSQL continues to enforce authentication and RLS.

## Local operation

The proxy socket lives in `.runtime/corpus/sql-proxy/socket`; the actual database
socket remains private under `.runtime/corpus/postgres/socket`. There is no
PostgreSQL TCP listener. Both application and admin DSNs point to the proxy.
Connection helpers reject alternate hosts, service files, hostaddr, multi-host
and environment routing overrides. Original source snapshots and credentials
remain private and unchanged by the routing migration.

```bash
/usr/bin/python3 scripts/bootstrap_sqlean.py
/usr/bin/python3 scripts/bootstrap_corpus.py start
/usr/bin/python3 scripts/bootstrap_corpus.py migrate
/usr/bin/python3 scripts/run_local.py --show-url
```

The parser build copies only the grammar source closure and required notice
metadata into ignored `.tools/sqlean`. It uses Lean 4.34.0 and records source,
compiler and binary hashes in [the parser lock](../config/sqlean-parser-lock.json).
A small pinned C initializer reduces Lean worker stack reservation so the parser
can run inside the declared memory cap; its grammar sources remain unchanged.
No root SQLean LICENSE/NOTICE was found in the supplied checkout. Local use is
user-authorized; redistribution and commercial rights remain unresolved.

Schema migration now runs through one explicit transaction helper. It no longer
executes the historical `004_retrieval.sql` DO/EXECUTE bodies. Database backup,
restore, revocation replay and repository operations use the same query gate.
Managed psycopg connections disable automatic preparation to prevent the driver's
implicit `DEALLOCATE ALL` maintenance from violating the conservative policy;
extended parameter binding remains supported.

```bash
.tools/retrieval-venv/bin/python scripts/verify_sql_runtime.py --status .runtime/corpus/sql-proxy/status.json
PYTHONPATH=retrieval .tools/retrieval-venv/bin/python scripts/verify_corpus_runtime.py
.tools/retrieval-venv/bin/python scripts/retrieval_recovery_test.py
/usr/bin/python3 scripts/bootstrap_corpus.py stop
```

The runtime report distinguishes an independent synthetic wire peer from actual
PostgreSQL checks. Per-client counters establish which paths traversed the
proxy; a global readiness count alone is insufficient. Historical failures and
their fixes remain in the review/evidence records. Grammar acceptance, passing
fixtures and the abstract Lean model do not close manual accessibility, dataset
rights or commercial-pilot gates.
