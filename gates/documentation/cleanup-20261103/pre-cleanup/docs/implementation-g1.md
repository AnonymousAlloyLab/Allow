# First implementation gates

The authoritative requirements are `spec/implementation-g1.json` revision 4
and `spec/slot-profile.json`. The first development slice is local and ephemeral:
Spring serves the React assets and authenticated API; memory holds jobs; a fresh
sandboxed JVM parses, checks and optionally solves each selected Alloy command.
There is no database or persistent project store in this slice.

## Model and implementation evidence

The supplement was proved before production source creation. Its immutable
snapshot, exact expected proposition types and two-build evidence are in
`gates/g1/formal-runs/supplement-r4/`. The model's anonymity theorems assume an
already resolved, fixed anonymous structure. They do not prove that the Java
parser adapter assigns that structure correctly for arbitrary source programs.
The style theorem concerns accepted method metadata, not the completeness of
the source checkers. Worker lifecycle theorems concern abstract transitions,
not Java memory-model or operating-system behavior.

Java integration tests separately exercise actual parsing and SAT4J solving,
anonymous structure generation, worker protocol failures, queue/cancellation
behavior, HTTP boundaries and real filesystem/network denial. Frontend tests
exercise the typed tree and response policies. The HTTP smoke checks the built
React shell and Spring API together. These are finite implementation tests.
No available browser meant real keyboard/drag/drop and visual acceptance could
not be completed. G2 is therefore explicitly partial.

## Presentation and anonymous structure

The UI keeps original source and user names. The canonical package receives a
resolved Alloy AST, assigns slots by declaration and lexical binder position,
and emits only the closed JSON-array grammar. It never sorts or hashes display
names to allocate slots. Separate namespaces represent signatures, fields,
functions and lexical variables. Binder scope is restored on exit, while each
allocated binder ordinal stays globally distinct within the traversal.

The payload includes supported declarations, function bodies, facts, operand
order, multiplicity and the selected command bounds. It excludes comments,
paths, labels, diagnostics, source hashes and witness presentation names.
Renaming a display label without changing resolved structure is expected to
leave the payload and local feature vector identical. Reordering declarations
is not normalized. A digest is an integrity key, not proof of equivalence.

Only `AnonymizedArtifact` can enter `EmbeddingEncoder`. Its exact compact UTF-8
JSON is divided into successive four-byte chunks, including a final short
chunk. SHA-256's first two bytes, interpreted big-endian, choose one of 128
count buckets; the vector is L2 normalized. The fixed algorithm is specified in
the slot profile. No remote model is contacted. Witnesses retain readable names
in a separate authenticated result and never enter this encoder.

The adapter conservatively rejects unrepresented signature/declaration flags,
inheritance, strings, temporal expressions and unknown AST constructors. A
solver result can still be available while canonicalization reports
`UNSUPPORTED_CANONICAL`. There is no source-text fallback. Full relational or
temporal normalization, proved e-graph merges and vector persistence remain
later implementation gates.

Alloy 6.2.0 introduces an implicit `util/integer` open even for import-free
source, and represents inline `run` blocks as synthetic private functions. The
adapter recognizes only the parser's exact built-in/synthetic markers. Explicit
source imports and source-private declarations are not admitted through those
exceptions. This compatibility handling is tied to the pinned parser artifact.

## Workbench transactions

The initial palette supports Boolean formulas and unary relation references,
union, and `some`/`no` tests. A candidate can differ from the current source.
Applying it requires server validation; editing raw source switches the composer
to text-only mode so old blocks cannot claim to represent new text. Unsupported
reverse projection is not attempted. The UI currently uses command index zero.

Each request binds exact source SHA-256, accepted revision and presentation
epoch. Editing clears visible results immediately. Job identities and freshness
checks prevent old requests from becoming results for a new edit. `SAT` on a
`run` means an instance; `SAT` on a `check` means a counterexample. `UNSAT`
reports absence only within the selected finite bounds. Errors, cancellation,
timeouts and unknown outcomes are separate statuses.

## Local authority and worker boundaries

The launcher binds Spring to literal `127.0.0.1`, generates new bearer authority
and stores a private launch link. The fragment is consumed into browser memory
and removed from history; no localStorage or query-token persistence is used.
Private endpoints require the token, the exact Host and, when supplied, the
exact local Origin. A static shell contains no private model data. This is a
single-user local capability service, not a deployed multi-tenant service.

Only one worker runs at a time; four jobs may queue and 128 results may be
retained. Cancellation marks the logical result immediately, but admission is
held until the sandbox exits and is reaped. Each worker uses bubblewrap
namespaces, private temporary storage, read-only runtime dependencies and a
cleared environment. The host supplies resource limits and an external wall
deadline. There is no unsandboxed fallback.

Source is capped at 32 KiB; AST traversal is capped at 10,000 nodes and depth
128. Stdout must be exactly one bounded newline-terminated compact JSON frame;
stderr is drained separately with its own cap. Frame schema, identity and clean
exit are checked before accepting results. The analysis identity binds compiled
classes, dependencies, the solver and the JDK version string; changing build
bytes requires restart. Exact JDK binary/library hashing is not implemented.
See `backend/README.md` for classpath details and API limits.

## Reproduce the checks

`python3 scripts/build.py` runs dependency installation from the lockfile,
JS/TS style inventory and checker fixtures, frontend tests, TypeScript/build,
Maven Checkstyle and Java tests, then copies the React assets into Spring's
classpath. Generated outputs and vendor code are excluded narrowly; authored
test code is checked. Maven's ordinary Checkstyle check always runs. The default
build obtains a SHA-256-verified Checkstyle 10.21.2 all-in-one JAR to run the Java
checker-negative fixtures as well. `ALLOW_CHECKSTYLE_JAR` can point to an existing
copy of those exact bytes. Running only the standalone Node self-test without
that variable skips its Java cases and is not the complete build check.

The mechanical checks cover callable inventory, physical length, documentation
presence/tags and private field visibility. They cannot establish that prose is
meaningful, methods have a single responsibility or mutable objects never
escape through getters. Private-final-by-default and defensive-copy policies
also require review; mutable internal state is necessary in lifecycle services.

After starting the local server, `python3 scripts/smoke_local.py` reads the
private launch link without printing its token and exercises synthetic models.
`python3 scripts/dependency_inventory.py` records exact runtime JAR identities,
hashes, embedded notices and the frontend lock. `npm audit --json` in `frontend`
is separate advisory dependency evidence, not a security proof or Java audit.

## Datasets and commercialization

The supplied roots contain 70,737, 3,582 and 66,080 Alloy files respectively.
There is substantial duplicate content within and across roots; these are not
three independent training populations. Counts differ from some source README
claims. Some individual models exceed the workbench's bounded input policy.
The inventory's oversized-file count used the earlier 256 KiB inventory
threshold, not the current 32 KiB API limit; it is only a lower bound on current
size-based rejections. No current-limit dataset acceptance rate was measured.
The inventory records aggregate counts, overlaps, notice evidence and hashes;
no dataset-wide parser/solver validity claim follows from it.

Before ingestion or commercialization, resolve per-artifact corpus rights,
dependency redistribution and notice requirements, retention/access policy,
tenant isolation, operational support and measured customer value. The pinned
Alloy binary's manifest, Maven POM and upstream license history need a specific
resolution; a reference repository's MIT label is insufficient. Local technical
feasibility has been demonstrated, while commercial clearance remains open.
