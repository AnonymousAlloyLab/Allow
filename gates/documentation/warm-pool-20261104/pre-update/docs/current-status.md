# Current status and evidence

This index describes the installed validation-context implementation and the
checks completed through 4 November 2026. Implementation of the reviewed
[performance remediation plan](performance-remediation-plan.md) is underway.
The source tree contains the new cleanup path and a disabled JVM optimization
profile. Full acceptance is still in progress. The application remains a local development system,
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

The initial [isolated run](../gates/document/context-cleanup-candidate/runtime-experiments/runs/r3/report.json)
exposed lost lock-timeout SQLSTATE and a graceful-shutdown hang. Both were repaired;
the failed evidence remains unchanged. The later
[eight-subcase run](../gates/document/context-cleanup-candidate/runtime-experiments/runs/r6/report.json)
passed normal contexts, lock timeout, deadline retirement and CLI-death checks,
with observed backend absence and normal service cleanup.

The [maximum-history run](../gates/document/context-cleanup-candidate/runtime-experiments/runs/r9-quota-memory/report.json)
passed all eight subcases, including 4,096 revisions accounting for 268,434,782
bytes. Full instrumented scans took 660–728 ms; measured post-startup peak RSS
was approximately 260 MiB. This fixture represents stored history, not 4,096
independently Alloy-admitted edits. Three samples do not establish a production
p95. The [full regression run](../gates/document/context-cleanup-candidate/runtime-experiments/runs/r11-regressions/report.json)
passed 250 Python tests and 52 SQL checks without skips, retrieval/document
backup recovery, eight HTTP smoke checks and six JVM crash/restart checks.
The [33-case evidence map](../gates/document/context-cleanup-candidate/runtime-experiments/case-readiness-r2.json)
still records missing fault cases and final binding obligations; these finite
successes do not close the entire cleanup or automatic-restart availability gate.

An additional [deadline regression](../gates/document/context-cleanup-candidate/runtime-experiments/observation-deadline-r1/report.json)
found that cleanup accepted a delayed observation at 2.85 seconds. The repair
clamps each observation to the remaining budget and rejects late results. The
same delayed-observation fixture now retains UNKNOWN; it uses simulated metadata
and real asynchronous delays, not a database or kernel-absence proof. The
[fully bound regression run](../gates/document/context-cleanup-candidate/runtime-experiments/runs/r15-regressions/report.json)
passes 258 Python tests, 52 SQL checks, backup recovery, HTTP smoke and restart
recovery, with unchanged runtime files and manifest. The
[repair readiness record](../gates/document/context-cleanup-candidate/runtime-experiments/deadline-repair-readiness-r1.json)
keeps the complete fault matrix open.

The [local preview restoration](../gates/document/context-cleanup-candidate/runtime-experiments/local-preview-restoration-r3/post-launch-survival.json)
installed the tested default JVM build and v8 SQL proxy. The preview survives
its launcher exiting; the original PostgreSQL process, documents, revisions and
receipts were preserved. A separate browser tab opened the saved test model and
completed **Check model** after the deadline repair without saving a new revision.
Its [browser observation](../gates/documentation/implementation-20261104/browser/repaired-observation.json)
and screenshot are retained. The original tab's
unsaved draft was left untouched. This development restart does not certify the
remaining fault matrix or change the active compilation profile.

A [timeout probe](../gates/document/validation-context-candidate/runtime-checks/python/lifecycle-limitation-r1.json)
found that a deliberately sleeping PostgreSQL query survived killing and reaping
its private CLI at the 20-second deadline. The probe explicitly cancelled its
owned backend and verified unchanged durable state. Automatic backend execution
termination in that historical implementation was unresolved; a Python process
limit is not a database query limit. The new cleanup tests above address a finite
set of failure paths. Pre-key crash recovery can still retain UNKNOWN and deny
new contexts instead of guessing that backend work stopped.

The [JVM profile contract](../spec/fresh-tier1.json) received the requested six
reviews and a separate [22-proposition Lean check](../gates/performance/fresh-tier1-candidate/formal-runs/final-v1/report.json)
in two clean builds before its Java changes. The implementation preserves fresh
isolated processes, full build checks, default solver/mutation behavior and
the existing time/output limits. Only a fixed advisory profile can add
`-XX:TieredStopAtLevel=1`; the active profile remains `DEFAULT`.

The [190-case output comparison](../gates/performance/fresh-tier1-candidate/runtime-experiments/semantic-comparison-r2/report.json)
passed for both profiles, comparing complete responses with tightly scoped
generated-ID correspondence. The [registered safety run](../gates/performance/fresh-tier1-candidate/implementation/registered-safety-r1/report.json)
verified 12 finite claims across 36 methods, including actual 10-second deadlines
and process reaping. The isolated Java build passed 204 tests; later focused
tests are separately recorded rather than combined into an invented full-suite
count. All 164 frontend tests and the authored JavaScript/TypeScript style scan
also passed.

The [whole-stack harness](../gates/performance/fresh-tier1-candidate/runtime-experiments/README.md)
has passed cold readiness and containment checks with four CPU quota, 5 GiB
memory high, 6 GiB memory maximum, no swap and 512 tasks. The
[first comparative attempt](../gates/performance/fresh-tier1-candidate/runtime-experiments/runs/paired-http-r1/selection.json)
stopped during initial fixture commit with HTTP 503, before any warmup or measured
requests. The group was cleaned up. Generated Python bytecode inventory and
the outside observer's user-bus environment also exposed harness defects;
the failed inputs and reports remain preserved. An isolated diagnostic is
now [recorded](../gates/performance/fresh-tier1-candidate/runtime-experiments/runs/bootstrap-diagnostic-r3/report.json):
the user service inherited a security context that denied Bubblewrap's isolated
loopback setup before the worker read its request. The diagnostic's PASS means
successful evidence collection and cleanup, not successful model validation.
The later [scope preflight](../gates/performance/fresh-tier1-candidate/runtime-experiments/runs/scope-preflight-r5/report.json)
passes actual unchanged worker validation, resource checks and explicit empty-group
cleanup. It preserves the caller's existing security context without delegation
or host policy changes. Its terminal group peak was 175,779,840 bytes; this is a
small launch probe, not full-stack memory acceptance.

The [frozen paired HTTP experiment](../gates/performance/fresh-tier1-candidate/runtime-experiments/runs/comparison-r2-experiment-binding.json)
then completed its first pair. Both profiles ran 100 warmups and 1,000 measured
requests with zero HTTP/protocol errors, unchanged inputs and verified cleanup.
[F0 default](../gates/performance/fresh-tier1-candidate/runtime-experiments/runs/comparison-r2-pair1-f0/pair-verification.json)
measured p95 **399.671788 ms**, with group peak **669,532,160 bytes**.
[F1 Tier-1](../gates/performance/fresh-tier1-candidate/runtime-experiments/runs/comparison-r2-pair1-f1/pair-verification.json)
measured p95 **348.699540 ms**, with group peak **646,619,136 bytes**. Both peaks
are below the 5-GiB objective; F1 still fails strict p95 **<300 ms**. The F1
report's `valid_measurement=false` represents selection ineligibility despite
its complete verified raw series; its recorded threshold failure is preserved.

The [terminal decision is KEEP_F0](../gates/performance/fresh-tier1-candidate/runtime-experiments/runs/comparison-r2-history/selection.json).
The remaining four trials were **NOT_EXECUTED**, as required by the frozen stop
rule. There was no retry, threshold change or profile activation. Independent
read-only replay confirmed the two verdicts, raw percentiles and history hashes.
This is a workstation screen for the selected **4 vCPU / 8 GiB** baseline;
acceptance on the actual intended server remains open. Warm/prestarted JVMs and
AppCDS remain unimplemented and need their own reviewed contracts and Lean
supplements before production changes.

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

The later [implementation documentation receipt](../gates/documentation/implementation-20261104/receipt.json)
binds the refreshed README, status, plan and SQL/document guides to their archived
preimages and cited evidence. It also checks the named current source/build
projection. Original proof, regression and failed-attempt reports remain intact.
Duplicate model files in four completed temporary regression copies were
[archived reversibly](../gates/document/context-cleanup-candidate/runtime-experiments/model-retention-r1/completion.json)
with verified byte hashes and a tested restore procedure. Their original reports
and manifests remain unchanged; the latest r15 copy and active model remain intact.
