# Local backend foundation

This is the authorized G1 development foundation, with a restricted initial
workbench adapter. Lean proves scoped model properties; these Java integrations
have separate finite tests. No commercial packaging or redistribution clearance
is asserted.

Build and test from this directory:

```sh
../.tools/apache-maven-3.9.11/bin/mvn test
```

The build uses Java 17 and Spring Boot 3.5.16. It places ordinary parent runtime
dependencies in `target/dependency` and the official Maven Central Alloy 6.2.0
distribution in `target/solver/alloy.jar`. The latter has SHA-256
`6037cbeee0e8423c1c468447ed10f5fcf2f2743a2ffc39cb1c81f2905c0fdb9d`.
It contains SAT4J 2.3.1. The artifact stays on compiler/test and isolated worker
classpaths; its bundled SLF4J must stay off the Spring parent runtime classpath.

The root launcher supplies a fresh `ALLOW_TOKEN` and writes its fragment-bearing
local URL; `--show-url` prints the link for you to open. For direct development, a missing token is generated in
`.runtime/token` with private directory/file permissions. Tokens are never
returned by the API. Run only from this backend directory:

```sh
java -cp 'target/classes:target/dependency/*' dev.allow.backend.AllowApplication --debug=false --trace=false --logging.level.root=WARN --logging.level.org.springframework=WARN
```

The listener is pinned to literal `127.0.0.1`; `ALLOW_PORT` defaults to 8080.
Every `/api/` request needs launch bearer authority. Host must exactly match
the literal address and actual port. A supplied Origin must exactly match the
local HTTP origin, including when bearer authorization is correct. No remote
model or embedding calls occur.

`POST /api/jobs` accepts exactly `source`, `commandIndex`, `revision`, `epoch`,
and `operation` (`ANALYZE` or `VALIDATE`). Poll `GET /api/jobs/{jobId}`; cancel
with `DELETE` on the same path. `GET /api/config` reports local capabilities.
Statuses retain exact UTF-8 source hash, revision, presentation epoch and an
analysis identity containing compiled build/dependency/runtime identity.
Rebuilds require restarting the parent: changed class or dependency bytes cause
new worker launches to fail closed.

One sandbox runs at a time, with four queued jobs and 128 retained results.
Source is limited to 32 KiB, ASTs to 10,000 occurrences and depth 128. Scope,
bitwidth and sequence bounds are at most eight; temporal trace bounds at most
ten, with integer overflow excluded. Explicit `open` rejects before parsing;
only Alloy's implicit bundled integer library is admitted by resolved policy.
Arbitrary project or ambient filesystem imports are excluded.

The Linux worker requires bubblewrap and prlimit. It unshares namespaces,
mounts dependencies read-only, clears the environment and uses private
temporary storage. No unsandboxed fallback exists. Heap, address-space, CPU and
file-output limits complement the external ten-second wall deadline. Stdout is
one strict compact JSON frame capped at 2 MiB; stderr is concurrently drained
and capped at 64 KiB. Cancellation/timeout retain admission until sandbox exit
and reaping. Late responses cannot overwrite terminal status or become UNSAT.

Alloy licensing metadata differs between its manifest, Maven POM and upstream
root notice; component licenses include SAT4J LGPL text. Exact artifacts and
notices require review before redistribution. Local feasibility does not clear
these obligations.

Tests execute actual SAT/UNSAT run/check cases in the sandbox, invalid types,
imports, validation, hostile frames/stream overflow, timeout, cancellation,
crash, denied launch, cleanup, queue bounds, HTTP authority/Host/Origin/body
guards and real private-file/network denial probes. Compiled test entry points
are available only through package-private test seams, never client input or
forced-status environment variables.
