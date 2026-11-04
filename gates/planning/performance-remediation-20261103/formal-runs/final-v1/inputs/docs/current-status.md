# Current status and evidence

This index describes the installed validation-context implementation and the
checks completed on 3 November 2026. The [performance remediation plan](performance-remediation-plan.md)
is proposed work; it does not change the installed worker lifecycle or convert
an open gate into a pass. The application remains a local development system,
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

The [strict runtime audit](../gates/document/validation-context-candidate/runtime-closure/runs/final-v2/report.json)
is **BLOCKED**: 23 of 26 obligations have checked evidence. Missing cases remain
for private full-frame limits (VC01), decoded JSON nesting boundaries (VC13),
and literal parser shutdown during the new context operation (VC14).

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

## Installed architecture and proposed work

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
