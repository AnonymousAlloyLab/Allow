# Warm JVM pool candidate

Allow implements a **disabled prestarted, single-use worker pool** for advisory
document validation. A JVM accepts one private request and is then retired.
The live preview continues to use fresh `DEFAULT` workers. There is no request
field or environment variable that enables the candidate.

The authoritative [contract](../spec/warm-pool.json) and
[experiment](../gates/performance/warm-pool-candidate/experiment.json) were
frozen before production changes. The requested council of two Terra, two Sol
and two Astra reviewers approved that contract. The separate
[Lean run](../gates/performance/warm-pool-candidate/formal-runs/final-v1/report.json)
checks 36 finite model propositions in two matching clean builds, with three
witnesses. It does not prove Java/Python/kernel refinement or performance.

## Implemented behavior

- Demand starts at most one unassigned worker. At most two process trees exist
  in the shared ledger, including fresh revalidation and solver workers when
  the candidate is selected. Retirement and uncertain cleanup retain capacity.
- Bootstrap loads the approved classes and checks an empty JSON round-trip.
  It parses no synthetic or private Alloy model. The helper captures a bounded
  sealed application image before the exact nonce/image READY handshake.
- A fresh validation context must permit success and report CLEAN before any
  private handoff. The one-use permit binds the exact request, document/base,
  policy, build and pool incarnation. Existing PostgreSQL routing still goes
  through SQLeanParser.
- The success budget starts before admission and includes context resolution,
  a cold miss, validation, cleanup and the final identity fence. Startup has
  a five-second budget; an unassigned READY worker expires after 30 seconds.
  Expiry alone never requests another refill.
- Output is staged until the direct child is reaped, its exact cgroup is
  positively empty, and owned streams/tasks are closed. Publication requires
  a fresh complete build/image check and an unexpired, uncancelled operation.
- Failed ownership observations retain UNKNOWN and disable the incarnation.
  Failed group creation also disables admission, preventing repeated creation
  of untracked empty groups. Failed pool shutdown retains the workspace lock.

Coordinator shutdown uses orderly executor termination and retires workers
through their owned cleanup paths. It avoids injecting interrupts into threads
that own journal or cgroup channels: Java's
[interruptible-channel contract](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/nio/channels/InterruptibleChannel.html)
closes a channel when an interrupt affects its blocking I/O.
[Orderly executor shutdown](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/util/concurrent/ExecutorService.html#shutdown())
stops new submissions while allowing existing tasks to finish; cleanup and
termination must still be observed before ownership is released.

## Runtime requirements and selection

The candidate needs Linux cgroup v2 with a privately delegated, process-free
root, a control leaf for the server, and descriptor-owned worker groups.
The helper retains Bubblewrap namespace/capability isolation and the existing
JVM limits. Image setup has a bounded 64-MiB file limit; the in-sandbox launcher
lowers both hard and soft limits to 8 MiB before Java starts. CPU limits remain
per process and are not described as aggregate tree CPU accounting.

The workstation screening profile uses four CPU quota, a 5-GiB peak-memory
objective, 6-GiB maximum, no swap and 512 tasks for the complete isolated stack.
This screens the selected **4 vCPU / 8 GiB** baseline; it does not emulate the
production server's CPU generation, storage or contention.

`WarmRuntime.ENABLED` remains a fixed false policy in production source.
Do not delete a retained journal or recycle an uncertain reservation to make
startup succeed. A missing delegated root or incomplete recovery is an
unavailable candidate, not permission for an uncontained fallback.

## Evidence and open gates

The machine-readable [implementation status](../gates/performance/warm-pool-candidate/implementation/status.json)
links the exact build receipts and runtime input roots. Development tests,
actual ownership probes, synthetic output comparisons and real SQL integration
have distinct scopes; a successful diagnostic does not merge those scopes.
Historical failed runs and superseded source receipts remain preserved.

The latency diagnostic's [isolated build](../gates/performance/warm-pool-candidate/implementation/development-full-r7-report.json)
passes 307 Java tests and style checks. The 13 helper tests remain passing,
and the [eleven-case actual ownership/lifecycle probe](../gates/performance/warm-pool-candidate/runtime-experiments/runs/latency-ownership-r1/report.json)
was repeated on the timing harness's exact inputs. The production executable remains
byte-identical to the prior build. The latest finite corpus comparison
matches 187 complete responses and two explicit size-limit rejections. Its
blank-policy fixture remains non-comparable, so the full 190-case equivalence
gate is BLOCKED despite passing finite expected checks. The run uses READY
advisory workers in fresh per-fixture pools, assumed CLEAN contexts and direct
helper/ledger revalidation; it does not test the full selected Spring runtime.
The current [offline harness suite](../gates/performance/warm-pool-candidate/latency-diagnostic/offline-runtime-suite-final-r1-report.json)
passes all 156 checks, including complete-output and timing-verifier negatives.
These receipts bind the diagnostic's original source. The subsequent
[IIS deployment changes](iis-deployment.md) add explicit routing and advisory
profile configuration; the old warm-pool receipts do not certify those new bytes.
Warm pooling remains disabled in both deployment and local modes.

The two new lifecycle cases pass with one pool per case: A→B→A consumes three
separate worker generations and checks that automatic refills serve later
requests; actual 30-second idle expiry is followed by two seconds without demand,
unchanged durable generation counters, and a successful new request. Every
consumed, expired and spare worker has exact reap and empty-group evidence.
The isolated scope was removed after cleanup. Phase samples bracket expiry;
they do not measure its exact transition time. These two finite cases do not
close the full cold/idle profiles, history coverage, selected SQL route or soak.

The [500-node component latency diagnostic](warm-pool-latency.md) completed
860 attempts without errors, including 140 warmups and 720 measured requests.
Across three independent pairs, automatic-refill pool p95 was 307.6–309.3 ms
versus 275.0–278.2 ms for fresh DEFAULT workers: the pool was 11.2–11.9% slower
and used 33.2–34.0% more measurement-plus-teardown CPU. All 300 measured serial
pool admissions found the replacement STARTING. A separate READY-conditioned
profile had 197.3-ms request p95, but 303.2-ms full-cycle p95 including the
preparation wait. This instrumented component comparison assumes CLEAN and
excludes HTTP/SQL; it does not establish the isolated causal effect of prewarming
or close the strict HTTP gate. The diagnostic contract received six council
approvals and its separate 14-proposition Lean model was checked before harness
implementation; it does not prove clocks, implementation refinement or performance.

Promotion still requires the frozen fault matrix, selected-runtime SQL/durable/
solver checks, and three independently started paired HTTP comparisons. Each
candidate run must complete all 1,000 measured requests without error and have
p95 strictly below 300 ms and its paired fresh baseline. Ready hits, cold misses
and refill costs must all be represented; exact per-operation observations are
required before this benchmark can run.

Cold/idle-expiry, sustained-load, one-hour resource-soak and 10,000-request gates
also remain mandatory for activation. No warm-pool speedup is currently claimed.
Actual target-host acceptance, browser/accessibility acceptance and commercial
release remain separate open gates; commercialization remains **NO_GO**.
