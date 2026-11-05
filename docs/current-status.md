# Current status and evidence

This index describes the installed validation-context implementation and the
checks completed through 5 November 2026. Implementation of the reviewed
[performance remediation plan](performance-remediation-plan.md) is underway.
The source tree contains the new cleanup path, a disabled JVM optimization
profile and a disabled prestarted-worker pool. Full acceptance is still in progress. The application remains a local development system,
with commercial release **NO_GO**.

## Private AI integration — 5 November 2026

The [private assistant](ai-system-integration.md) now integrates Spring authority,
anonymous slot payloads, explicit per-attempt consent, real LangGraph generation
and shared-lane Java validation with React review, draft-only Apply and one-step
Undo. The integration supplement received the required six reviews and two
matching clean Lean builds covering 24 finite policy theorems before production
edits. AI remains OFF by default; ANONYMOUS cannot enable it. No RAG or private
corpus disclosure is added.

The [integration report](../gates/ai-system-v1/report.json) records current tests,
actual local HTTP/browser evidence and the generated distribution. This is an
opt-in private pilot, not completion of the broader quality, commercial, native
deployment or public-assistance gates. Historical counts and limits below remain
scoped to their original runs.

## Anonymous Windows/WSL deployment candidate — 4 November 2026

The selected target is `https://allow.alloy4.fun`, Windows 10 21H2 IoT Enterprise,
WSL2 Ubuntu 24.04, for anyone using separate temporary workspaces. The operator
reported `Ubuntu-24.04` Running on WSL2, WSL 3.0.1.0 and Windows build
10.0.19044.7807. Subsequent operator output reports PID 1 systemd, x86-64,
Python 3.12.3, Java/Bubblewrap/prlimit command paths and the `allow` service account.
`allow.service` is loaded, active and enabled, running as `allow:allow` from
`/opt/allow`. The reported manifest matches original private R1 exactly; Java is
17.0.20.1 and the root is `allow:allow` mode0700. IIS site `Allow` at
`C:\inetpub\allow` has HTTPS SNI binding `*:443:allow.alloy4.fun`. The selected
[separate public cutover](staged-public-cutover.md) leaves that private store
in place and initializes a fresh `/opt/allow-public` under `allow-public`.
It supplies no in-place migration. Its six-seat-reviewed contract and separate
50-theorem Lean policy check preceded implementation. The local two-store
rehearsal preserved the stopped old runtime and all four private fixture
readbacks; it used one workstation UID and reused test dependencies. See the
[operator inventory](../gates/deployment/anonymous-v1/target-linux-inventory.json).
The six required
reviewers approved the exact [contract](../spec/anonymous-workspaces.json), then
the [56 finite policy theorems](../gates/deployment/anonymous-v1/formal-report.json)
passed two matching clean Lean builds before production changes. This is a policy
model result, not proof of implementation correspondence or commercial readiness.

Source now implements closed PRIVATE/ANONYMOUS modes, scoped document and solver
ownership, four capacity-consuming reservations, a 30-minute absolute lifetime,
expiry publication checks and parser-routed lifecycle cleanup. Unknown cleanup
retains its reservation. Public mode has no corpus access. The frontend offers
explicit enrollment, reload/resume and draft export after ending a workspace.
The [WSL transfer procedure](wsl-anonymous-deployment.md) stages loopback-only
routing and a foreground supervisor without changing other WSL distributions.

The [R5 transfer archive](../dist/allow-iis-wsl-anonymous-20261104-r5.zip) passes
its 310-file manifest/extraction audit. It changes nine deployment/documentation
files and adds seven cutover inputs relative to R4; 294 existing files match
exactly, including all224 compiled/dependency/frontend/solver artifacts and all
retrieval/database inputs. New checks pass35 Linux tests, eight renderer tests,
12 cutover PowerShell mock checks and four legacy supervisor mock checks.
Fresh PRIMARY package preflight passes, and all three replacement entrypoints
reject a wrong root before runtime/SQL effects. The guard now verifies the
cgroup2 mount before accepting an absent group and reserves the public numeric
UID despite account aliases. Failed service-stop cleanup releases the Windows
mutex. Independent reviews found those defects and verified the fixes. See the
[cutover report](../gates/deployment/cutover-v1/report.json).

The unchanged application's earlier local evidence
records 334 Java tests, 172 frontend tests, 65 selected SQL/context tests (six
real anonymous SQL cases), 52 actual HTTP checks, 45 deployment/probe/renderer
tests and four portable WSL supervisor mock checks. The frontend's final expiry
wording was rebuilt after its test run. Browser checks passed separate enrollment,
scoped model lists, saving, reload/resume, ending one session while the other
remained usable, retained unsaved source and exact-file export. Native clipboard
verification and a full wall-clock expiry/browser matrix remain open. See the
[candidate report](../gates/deployment/anonymous-v1/report.json) for exact evidence
and the local proxy adapter's limits. Anonymous R1/R2/R3 archives are superseded
as transfer packages; R4 is also superseded by R5's separate-install tooling.
Their evidence remains preserved.

Native Windows/WSL/IIS, effective resource limits, TLS, reboot/outage recovery and
external anonymous acceptance remain **OPEN**. Remote desktop control is not
available in this session; no remote deployment or ingress changes were made.
The [read-only existing-domain probe](../gates/deployment/anonymous-v1/existing-public-boundary-probe.json)
failed: `/api;ignored/config` returned configuration without a bearer in the
tested request, and several denial responses missed expected security headers.
Do not treat the already-running public site as the tested candidate.

Historical baselines below keep their original counts and scope. The R7 package
is a private staging baseline; it is not an anonymous deployment artifact.

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
acceptance on the actual intended server remains open. AppCDS remains
unimplemented and needs its own reviewed contract and Lean supplement.

The [warm-pool candidate](warm-pool.md) now has a separate
[reviewed contract](../spec/warm-pool.json), all six requested council reviews,
and [36 checked model propositions](../gates/performance/warm-pool-candidate/formal-runs/final-v1/report.json)
in two matching clean builds before its production edits. The implementation
prestarts at most one unassigned, single-use advisory JVM within a shared
two-tree limit. It uses sealed images, an exact READY protocol, fresh context
permits, owned cgroups, conservative recovery and a final identity fence.
The active 309-proposition aggregate is unchanged.

The [repaired-source nine-case ownership probe](../gates/performance/warm-pool-candidate/runtime-experiments/runs/ownership-r5/report.json)
passed cold/ready validation, fresh revalidation, replay rejection, startup
failure and shutdown cases, including an attached STARTING worker. Both injected uncertainty cases retained capacity
while their actual processes were cleaned up. The enclosing group was observed
empty and its launcher reaped; peak group memory was 317,820,928 bytes. This
diagnostic assumes a synthetic CLEAN context and does not establish SQL cleanup,
full runtime refinement, latency or production acceptance. It includes the
deadline and containment-creation repairs. The latest source's
[complete isolated build](../gates/performance/warm-pool-candidate/implementation/development-full-r7-report.json)
passes 307 Java tests and style checks, and its
[helper tests](../gates/performance/warm-pool-candidate/implementation/helper-boundaries-r3-report.json)
pass 13 cases, including the actual configured image inventory boundaries.
The [expanded eleven-case run](../gates/performance/warm-pool-candidate/runtime-experiments/runs/pooling-lifecycle-r1/report.json)
also passes. Its added same-pool A→B→A case binds each later request to the prior
automatic replacement and checks complete repeat-A output. Its idle case waits
for the actual 30-second expiry, observes two seconds without demand or durable
generation advance, and validates a new request. All consumed, expired and spare
workers were reaped, all groups were observed empty, and the isolated scope is
gone. Peak group memory was 363,286,528 bytes. That historical r5 build's 208 production
artifacts were byte-identical to r4; only five Java test files changed. The
[offline checks](../gates/performance/warm-pool-candidate/implementation/pooling-offline-r1-report.json)
pass 13 helper tests and 133 harness tests. These finite lifecycle diagnostics
assume CLEAN and do not close full cold/history/SQL/performance/soak acceptance.

The later [semantic run](../gates/performance/warm-pool-candidate/runtime-experiments/runs/semantic-r2/report.json)
stopped after 121 matching cases when shutdown retained an uncertain replacement
worker after correctly rejecting oversized input. Actual processes were cleaned
up. An [orderly-shutdown repair](../gates/performance/warm-pool-candidate/implementation/shutdown-development-report-r11.json)
passes real-journal regressions; restoring the old interrupting shutdown calls
makes both regressions fail with `ClosedByInterruptException`. The exact lost
exception from the original run is not retrospectively asserted.

The repaired [complete finite comparison](../gates/performance/warm-pool-candidate/runtime-experiments/runs/semantic-r3/report.json)
has **187 equal complete responses and two matching input-limit rejections**.
Both variants completed all 190 expected cases with cleanup and unchanged inputs.
The remaining blank-policy case is explicitly **NOT_COMPARABLE**: the fresh
worker returns UNAVAILABLE, while the pool rejects the invalid binding before
handoff. Thus finite expected checks pass, but the whole 190-case equivalence
gate remains **BLOCKED**. Advisory fixtures await READY in separate per-fixture
pool incarnations; complete cold/refill/history sequences remain open. CLEAN is
test-assumed, and fresh revalidation uses the direct helper/ledger path rather
than the selected Spring `OwnedWorkerRun` route. These limits do not authorize
pool activation, SQL acceptance or a speedup claim.
The [warm-pool implementation status](../gates/performance/warm-pool-candidate/implementation/status.json)
records the latest build, finite checks and remaining gates. Pooling stays
disabled, with no claimed speedup.

The subsequent [component latency diagnostic](warm-pool-latency.md) completed
860 attempts (140 warmups, 720 measured), with zero errors and clean teardown
of all eight scopes. Under four CPU quota, serial pool p95 was **307.6–309.3 ms**
across three independent pairs, versus **275.0–278.2 ms** fresh: **11.2–11.9%
slower**, with **33.2–34.0% more measurement-plus-teardown CPU**. All 300 measured
serial pool admissions observed STARTING replacements. READY-conditioned p95
was 197.3 ms excluding its preparation wait, or 303.2 ms for the complete cycle.
Empty-pool first-demand p95 was 484.7 ms, or 524.7 ms including initialization
and shutdown. Peak whole-scope memory across profiles was 508.0 MiB.

This is instrumented worker-component evidence with test-assumed CLEAN,
different isolation policies and no HTTP/SQL. It does not close selected-runtime,
sustained-load, actual target-host or promotion acceptance. The frozen diagnostic
contract had two Terra, two Sol and two Astra approvals before code; its separate
[14-proposition Lean supplement](../gates/performance/warm-pool-candidate/latency-diagnostic/policy-proof-report-r2.json)
passed two clean builds. The earlier model defect and corrected revision are
preserved. The diagnostic's r7 Java build passes all 307 tests and style checks;
208 production artifacts remain byte-identical. Six new gate-only Java classes
add timing and lifecycle observations; production telemetry remains an open gate.

The later [IIS + Linux deployment package](iis-deployment.md) implements the
user-requested private deployment path. IIS terminates HTTPS and forwards over
a Windows loopback SSH tunnel to the Linux loopback listener. Exact configured
Host/Origin checks preserve bearer authority; no forwarded header grants access.
The navigation's “Local workspace” badge is removed. The package selects fresh
Tier-1 only for document advisory validation; local launch, durable revalidation
and solver profiles retain DEFAULT, and warm pooling remains disabled. This is
an explicit opt-in selection under a new contract, not a revision of KEEP_F0 or
the failed strict latency gate.

The initial IIS archive's 310 Java, 164 frontend and 14 Python checks remain
[historical deployment evidence](../gates/deployment/iis-v1/report.json).
The current **R6 private archive** supersedes it after the
[security and visual-drag contract](../spec/security-drag.json). All six requested
reviewers approved the refined contract; its 47 finite Lean policy theorems
passed two clean builds before the corresponding production corrections. These
prove the encoded policies, not implementation refinement or production security.

The security patch closes encoded/matrix-path authentication bypasses, defaults
nonpublic routes to bearer authentication, and narrowly preserves the existing
literal/encoded `server:UUID` document routes. Deployment entrypoints now require
isolated Python, verify source before loading helpers, reject stray application
bytecode/imports and preexisting generated tools, check ownership and permissions,
and hold a shared exclusive lock through startup and cleanup. JVM preflight
also receives the sanitized environment. Every SQL operation still uses SQLeanParser.

The current build passes **314 Java tests**, **169 frontend tests**, **22 deployment
Python tests**, and code-style checks. The R6 archive passed fresh Linux setup
with an explicitly captured zero exit, authenticated and encoded document
operations, supervisor contention, SAT4J execution, restart persistence, token
rotation and owned-stack shutdown. The
[current report](../gates/security-drag-v1/report.json) binds sources, archive and
receipts. Prior benchmark numbers remain scoped to their original binaries.
No production service was upgraded by these isolated tests.

The editor has a grouped, scrollable palette beside a connected block canvas,
explicit reference names, typed dashed holes and fixed-size drag feedback.
Owned gesture nonces and current-content checks prevent foreign/stale drops;
hover and final mutation use the same type/scope preparation. Actual browser
checks confirmed native compatible reference insertion, rejection of a
relation-to-formula move without a content change, click-based construction,
explicit copy/paste, source projection and saving/reopening. The remaining
Boolean-gate and modified move/copy pointer matrix is **OPEN**: some automation
attempts cancelled or reported a missing hit-test node. That result is not a
complete browser acceptance pass. Narrow viewport, full keyboard shortcuts,
Firefox ESR/Orca and touchscreen drag acceptance are also open.

Real Windows/IIS/SSH, target-host performance, cold-browser measurements,
dataset/dependency redistribution rights, a consenting customer pilot and
support economics remain **OPEN**. Private packaging is not commercial release.
Two earlier R4 setup shell sessions exited143 for an unresolved reason; those
logs and roots are preserved. A separate fresh R4 run and the final R6 setup
and smoke captured child and parent exit0. The failed initial document-path
candidate and earlier archives are also retained and explicitly superseded.

## Architecture and work in progress

The [R7 Windows/IIS staging report](../gates/deployment/public-iis-v1/report.json)
adds a stopped-by-default installer and bounded unauthenticated HTTPS probe.
The exact [public staging contract](../spec/public-iis-staging.json) received all
six required council reviews, and 37 finite Lean policy theorems passed two clean
builds before production edits. This is a policy model, not implementation
refinement or a Windows security certificate.

R7 contains the same 213 compiled application artifacts as R6. Its archive audit
and Linux package preflight passed; full R6 database/bootstrap smoke results
remain historical evidence and were not rerun as R7. Deployment tests comprise
17 probe tests (including real local TLS, full subprocess CLI and deadline
termination), 18 Linux tests, 4 renderer tests and 11 portable PowerShell helper
checks. The helper checks do not execute native Windows IIS/HTTP.sys.

The site installer validates a closed rendered configuration and certificate
policy, stages SNI with auto-start disabled, and sets restricted W3C fields.
Uncertain commit failures retain artifacts for operator inspection. NTFS ACLs,
ancestor reparse points, effective logging, actual stopped state and all native
acceptance remain open. The probe uses no real token and its PASS cannot establish
authenticated flows or public readiness. At the R7 milestone, domain, target
access and audience were pending; the anonymous candidate section above records
their later selection. No remote deployment, DNS, firewall or public exposure was
performed by this work. Public artifact redistribution remains a separate decision.

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
- [Warm JVM pool candidate](warm-pool.md): implemented ownership and protocol,
  disabled selection, evidence and remaining promotion requirements.

The installed system still uses fresh isolated validator JVMs. The earlier
[persistent-validator proposal](../gates/document/validator-session-candidate/council-disposition.json)
was not approved for implementation. Its rejection remains part of the design
history. The new reviewed candidate uses each JVM once; it does not authorize
reuse of a process after private model data has entered it.

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

The [warm-pool documentation receipt](../gates/documentation/warm-pool-20261104/receipt.json)
preserves the prior README, status and plan, checks the refreshed local links,
and binds that documentation revision to its cited evidence. Historical
reports remain unchanged; documentation refresh is not a new correctness proof.

The [pooling-test documentation receipt](../gates/documentation/pooling-test-20261104/receipt.json)
archives the preceding status documents and binds the eleven-case lifecycle
results, current build and offline checks to this revision. Historical failed
runs and the blocked full semantic gate remain unchanged.
