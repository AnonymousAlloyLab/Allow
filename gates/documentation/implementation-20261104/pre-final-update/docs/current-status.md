# Current status and evidence

This index describes the installed validation-context implementation and the
checks completed on 3 November 2026. Implementation of the reviewed
[performance remediation plan](performance-remediation-plan.md) is underway.
The source tree contains the new cleanup path; its isolated runtime acceptance
and live-service promotion are still in progress. The application remains a local development system,
with commercial release **NO_GO**.

## Tested baseline

The [formal report](../gates/document/validation-context-candidate/formal-runs/final-309-v1/report.json)
checks 309 exact model propositions in two isolated clean builds. Its guarantee
is limited to the frozen model, claim inventory and declared trusted components;
it does not establish universal implementation refinement.

The [recorded implementation evidence](../gates/document/implementation-report.json)
contains 189 Java tests, 164 frontend tests and 186 Python tests. The separate
[SQL runtime report](../gates/sql/runtime-tests.json) records 52 tests. The build,
HTTP smoke, restart and database recovery checks passed their finite fixtures.
The required six-seat council reviewed the validation-context gameplan before
implementation.

The [warm browser run](../gates/document/browser-benchmark-runs/validation-context-v1/report.json)
passed: 500 nodes, 100 warmups, 1,000 measured edits and p95 **12.5 ms**, against
an unchanged strict 50 ms target. Connected browser checks also exercised saving,
SAT analysis and typed-slot rejection. This measures controller edits through
frame opportunities; it is not a physical-paint or cold-start guarantee.

The [server run](../gates/document/server-benchmark-runs/validation-context-v1/server-performance.json)
completed 100 warmups and 1,000 measured requests with no failed requests or
changed inputs. Its p95 **392.298835 ms** fails the unchanged strict **300 ms**
target. The previous sealed-image run measured 468.348787 ms. These are local
shared-workstation observations, not evidence for a smaller production server.

## Open acceptance work

The historical [23/26 runtime audit](../gates/document/validation-context-candidate/runtime-closure/runs/final-v2/report.json)
remains preserved. The new [P0 binding](../gates/document/performance-remediation/p0/binder-runs/final-v1/report.json)
is **VERIFIED: 26/26 finite obligations** after actual frame-size, JSON-depth
and parser-shutdown probes. This closes those evidence gaps, not the latency
or automatic database-cleanup gates.

The [cleanup contract](../spec/document-context-cleanup.json) received all six
required reviews, and its separate [28-proposition model](../gates/document/context-cleanup-candidate/formal-runs/final-v2/report.json)
passed two matching clean builds before production edits. The inherited
309-proposition aggregate is unchanged. The new proxy lease, strict SQL
sequence, deadlines and cleanup-receipt bridge are implemented in source.
Their [33-case runtime plan](../gates/document/context-cleanup-candidate/runtime-test-plan.json)
is not yet closed; the model does not prove implementation refinement.

The first [isolated runtime run](../gates/document/context-cleanup-candidate/runtime-experiments/runs/r3/report.json)
passed three real context cases, including 4,096 requested IDs, with backend
absence and unchanged durable-table hashes. It is **BLOCKED** overall: the
lock-timeout result lost its SQLSTATE, and graceful proxy shutdown required
emergency cleanup. Those failures are being repaired; they are not waived.

A [timeout probe](../gates/document/validation-context-candidate/runtime-checks/python/lifecycle-limitation-r1.json)
found that a deliberately sleeping PostgreSQL query survived killing and reaping
its private CLI at the 20-second deadline. The probe explicitly cancelled its
owned backend and verified unchanged durable state. Automatic backend execution
termination is unresolved; a Python process limit is not a database query limit.

Cold-browser measurements, positive pointer-drag acceptance, complete keyboard
scenarios and the named Firefox ESR/Orca accessibility run remain open. Dataset
and dependency redistribution rights, a consenting customer task pilot and
support economics also remain open. The warm browser result does not close
these separate gates.

## Architecture and work in progress

- [Document operations](document-stage.md): typed blocks and exact source,
  immutable revisions, advisory validation and recovery boundaries.
- [SQL routing](sql-stage.md): every PostgreSQL client uses SQLeanParser through
  the pinned sealed-image proxy; no direct-query fallback.
- [Retrieval](retrieval-stage.md): anonymous context and canonical predicate,
  complete positive/negative pools, 3072-dimensional embeddings and LangGraph
  retrieval integration.
- [Finite e-graph profile](egraph-stage.md): supported rewrites and certificate
  checks, with historical milestone evidence clearly identified.
- [Original G1 milestone](implementation-g1.md): historical foundation notes.
- [Performance remediation plan](performance-remediation-plan.md): constrained
  hardware measurements, lifecycle repair and proposed JVM optimization work.

The installed system still uses fresh isolated validator JVMs. The earlier
[persistent-validator proposal](../gates/document/validator-session-candidate/council-disposition.json)
was not approved for implementation. Its rejection remains part of the design
history; a new warm-JVM plan must address the recorded isolation and resource
objections explicitly.

## Documentation provenance

The [pre-cleanup archive](../gates/documentation/cleanup-20261103/pre-cleanup/manifest.json)
preserves the exact earlier README, stage documents, implementation report and
implementation manifest. The earlier whole-source manifest includes those old
document bytes and is therefore historical after this documentation cleanup.
Original proof, test and benchmark reports remain unmodified.

The [cleanup receipt](../gates/documentation/cleanup-20261103/cleanup-receipt.json)
records changed documentation hashes and checks the unchanged non-document
files listed in that earlier manifest. That projection is a byte comparison,
not a new test run or a new full-source correctness claim.
