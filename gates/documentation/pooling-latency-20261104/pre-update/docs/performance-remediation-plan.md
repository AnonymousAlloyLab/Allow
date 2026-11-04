# Performance and acceptance remediation plan

This is a gameplan for the **4 vCPU / 8 GiB production baseline selected by the
user on 2026-11-03**. It does not enable a warm worker or change the running
application. The machine-readable [planning contract](../gates/planning/performance-remediation-20261103/contract.json)
is authoritative for the proposed work. The [council disposition](../gates/planning/performance-remediation-20261103/council-disposition.json)
records review of the exact candidate; approval of this plan is not acceptance
of an unmeasured architecture.

The recorded server baseline p95 is **392.30 ms**, above the strict **300 ms** gate. Warm
browser preview passed at **12.5 ms**, but cold, pointer and accessibility
acceptance remain open. The original runtime audit had **23 checked obligations
and three missing cases**. P0 now closes all 26 finite obligations; the old
blocked report remains preserved. A deliberately stalled SQL query also survived its
private bridge's termination until the test cancelled it explicitly. See the
[current evidence index](current-status.md).

## Implementation progress

P0 is complete under its [new evidence binding](../gates/document/performance-remediation/p0/binder-runs/final-v1/report.json).
P1 has a [reviewed contract](../spec/document-context-cleanup.json), a separate
28-proposition Lean supplement, and implemented context leases, deadlines and
cleanup receipts. The maximum-history checks and complete Python/SQL/backup/HTTP
regressions pass. A strict cleanup observation-deadline repair is installed and
passes the bound 258-test Python and 52-check SQL regression run; its complete
33-case fault matrix remains open.

The bounded [fresh-JVM Tier-1 experiment](../spec/fresh-tier1.json) now has its
own six reviews and 22-proposition Lean supplement. The fixed profile is
implemented with `DEFAULT` still active. Its 190-case output comparison and
registered 12-claim safety run pass. Initial setup failures were preserved and
the harness repaired before a new frozen experiment. Its first complete pair
measured F0 p95 **399.671788 ms** and F1 p95 **348.699540 ms**, with zero request
errors and verified cleanup. F1 misses the strict **300 ms** target, so the
[registered stop decision](../gates/performance/fresh-tier1-candidate/runtime-experiments/runs/comparison-r2-history/selection.json)
keeps F0 and leaves the other four trials unexecuted. No optimized profile or
smaller-server production acceptance has been promoted.

The next design is now the implemented, disabled [warm-pool candidate](warm-pool.md).
Its own contract, six requested reviews and 36-proposition Lean check preceded
production changes. The current-source actual ownership probe passes, but full fault,
output-equivalence, SQL integration and performance evidence remain separate
requirements. The implementation status links the latest exact-source results;
none of these finite checks activates pooling or changes the strict latency gate.
The options below retain the original reviewed planning basis.

The sequence below is the original reviewed gameplan. Completed work is tracked
in the status index rather than retroactively changing its frozen contracts.

## Recommended sequence

1. **Close the three missing runtime cases.** Exercise the private 3-MiB frame
   boundaries, JSON depth 96/97, and actual shutdown of an owned isolated parser
   service/subprocess. Keep the shared development proxy running. Require
   fail-closed results, no SQL bypass and no validator launch on failure. Preserve
   the old blocked reports and generate a new binding from actual execution.
2. **Fix ownership of database work.** Add a separate reviewed SQL deadline and
   cancellation amendment for read-only validation contexts. Start with fixed
   experiment limits of 1.5 seconds per statement, 250 ms lock wait, 1 second
   idle in transaction, a 3-second context deadline and a 2.5-second cleanup
   observation budget. These are proposed constants that must pass the permitted
   maximum-history workload before promotion. Install exact transaction-local
   settings through SQLeanParser; leave migration, backup and durable-mutator
   policies separately defined. Observe the exact owned backend's termination;
   neither a cancellation acknowledgement nor a closed pipe proves it stopped.
   Retain its admission reservation while cleanup is uncertain.
3. **Profile the entire stack on the target budget.** Separate context startup,
   SQL, decoding, build checks, JVM bootstrap, class loading, validation,
   serialization and reaping. Measure elapsed time, CPU, allocation and group
   memory. Bound Spring, PostgreSQL, proxy, helpers and workers together. Keep
   offline ingestion/training outside the interactive service budget.
4. **Compare the worker candidates below in isolation.** Freeze a prototype's
   exact assumptions and failure checks before measuring it. Select a candidate
   only after correctness, cleanup and resource evidence are satisfactory.
5. **Formalize and implement the selected design.** Each production increment
   needs its exact contract, Lean supplement, six council reviews and two clean
   formal builds first. Then run regression, recovery, SQL-routing and actual
   target-host performance acceptance, with an explicit rollback to fresh workers.
6. **Finish browser and commercial acceptance.** Complete cold-browser,
   positive/negative pointer, keyboard and Firefox ESR/Orca task cases. Resolve
   redistribution rights, then run a consenting customer pilot with frozen
   task-completion, support-cost and stop criteria. Commercial release remains
   **NO_GO** until those independent gates close.

Database cleanup and profiling can proceed as separate workstreams after the
missing baseline checks. Warm-worker promotion depends on both.

## Warm JVM choices

**Prestarted single-use JVMs are the first pool experiment.** Keep at most one
ready advisory worker, with at most two live worker slots overall. Starting,
idle, busy and retiring workers all count. Each process handles at most one user
request, then exits and is reaped. A ready process can shorten the critical path,
but replacement still consumes CPU and memory. Include empty-pool requests,
refill contention and startup in the measured workload. Start with bootstrap and
audited class loading; parsing synthetic models for warmup requires a separate
differential experiment. Never preload private user models.

**True reusable JVMs remain a serious but conditional experiment.** They could
reduce repeated startup and preserve JIT work, but the earlier design was
rejected by all six reviewers. A fresh classloader resets some application
statics while losing much application-class JIT reuse; it does not isolate
JDK-global state. Closing a loader does not invalidate classes already loaded,
and unloading is optional. A same-loader design therefore needs a concrete
audit of Alloy state, JDK registries, threads, native state, loader escapes and
every reset path. See the [URLClassLoader API](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/net/URLClassLoader.html#close())
and [JLS unloading rules](https://docs.oracle.com/javase/specs/jls/se17/html/jls-12.html#jls-12.7).

The reusable experiment is advisory-only and single-flight, with a fresh
authorized database context on every request. Initial lifetime ceilings are
64 requests, 120 seconds age, 30 seconds idle and the existing cumulative JVM
CPU cap. Any timeout, cancellation, OOM, unexpected exception, failed reset or
ambiguous output retires the process. These ceilings do not establish that 64
requests are safe or affordable. Freeze the actual process tree, immutable image,
generation/nonce protocol and cleanup owner; use A/B/A histories and full-output
comparison against fresh workers. Commit, history validation and solving retain
one-shot recovery semantics initially. Reject reuse if its isolation obligations
remain unresolved.

**Fresh JVM optimization is the comparison baseline.** Test Tier-1 compilation,
AppCDS and a smaller private advisory reply independently before combining them.
Retain full validation, diagnostic/source identity, size rejection and build
checks. AppCDS needs pinned archive, JDK, classpath and flags; default CDS may
already be active. Use a tested compatibility policy and report fallback rather
than assuming sharing. Oracle's [CDS guide](https://docs.oracle.com/en/java/javase/17/vm/class-data-sharing.html)
explicitly discourages `-Xshare:on` as a production setting.

If context-process startup remains material after these measurements, evaluate
a bounded read-only context service or Java adapter through SQLeanParser as a
separate contract. Do not add an authorization or result cache to make the
benchmark faster.

## Production performance contract

Use the actual intended server or a pinned VM matching its CPU generation,
storage, OS and JDK. Screening on this workstation will constrain the complete
stack to four CPUs and a 6-GiB memory ceiling, with a 5-GiB peak-memory acceptance
objective and no swap. That leaves nominal headroom on an 8-GiB server; it does
not emulate slower cores or storage. Explicitly budget Spring and PostgreSQL as
well as workers. Linux [cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)
provides whole-group CPU, memory and process accounting; JVM processor-count
flags alone do not enforce the server budget. Missing delegated containment
blocks pool deployment rather than enabling an uncontained fallback.

Retain the original 500-node, 100-warmup, 1,000-measurement HTTP protocol and
strict p95 below 300 ms. Require **three independent target-host runs**, each
passing with no failed requests. The engineering selection objective is **p95
at or below 240 ms**, providing 20% headroom; this is not an observed result or a
replacement threshold. Do not average away a failed run.

Add separate cold and sustained profiles: 30 process-start and 30 empty-pool or
idle-expiry cycles, plus an open-loop 2-request/second, 30-minute workload with
distinct edits. Proposed cold first-operation p95 is below 1 second after READY,
with every request below 3 seconds; startup-to-READY is separately limited to
10 seconds. Sustained p95 stays below 300 ms, p99 below 600 ms, with no capacity
rejections at that offered load. Sweep higher offered loads and bursts separately
to identify saturation and explicit overload behavior. All refill, retirement,
failures and rejected requests remain visible. A one-hour resource soak and
10,000-request sequence check finite resource stability. Freeze these additional
procedures in the selected implementation contract before execution.

The SQL deadlines required an exact policy amendment because the earlier guard
only admitted timeout-setting forms needed by existing tools. That amendment is
now implemented in [v8 context leases](../spec/document-context-cleanup.json).
PostgreSQL 16's
statement timeout and idle-transaction timeout address different states; a
blanket global change would affect unrelated operations. PostgreSQL 16 also
lacks the later transaction-timeout setting. The
[PostgreSQL 16 documentation](https://www.postgresql.org/docs/16/runtime-config-client.html)
is the version-specific reference. Audit server logging as part of this work so
timeout errors do not expose private source or parameters.

## Proof and documentation boundaries

The inactive [Lean supplement](../gates/planning/performance-remediation-20261103/PerformancePlan.lean)
models guarded single-use worker transitions, capacity ownership, cleanup
evidence and benchmark decision conditions. It is separate from the active 309
propositions. It does not prove a real JVM reset, PostgreSQL termination,
wall-clock performance, universal semantic equivalence or commercial readiness.
The [authoring check](../gates/planning/performance-remediation-20261103/development-check.json)
records the initial development check. The later
[registered closure](../gates/planning/performance-remediation-20261103/formal-runs/final-v1/report.json)
verifies 32 exact model propositions in two matching isolated clean builds after
all six exact-input approvals. These artifacts concern only
the inactive model; implementation acceptance requires the concrete evidence
specified above.

Stale documentation has been reconciled around [current-status.md](current-status.md).
The [cleanup receipt](../gates/documentation/cleanup-20261103/cleanup-receipt.json)
binds the archived originals and new document bytes. Old whole-source reports
remain historical after documentation changes; their test results are not
rewritten as fresh runs. Rejected designs, failures, proofs and runtime evidence
are retained for traceability.
