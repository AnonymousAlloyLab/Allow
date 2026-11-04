# Allow

Allow now has a local Spring Boot / React workbench backed by the existing Java 17
installation and sandboxed Alloy/Kodkod/SAT4J. This implements the G1 development
foundation and an initial subset of G2. It is not a completed production platform.

The [implementation supplement](spec/implementation-g1.json) and
[anonymous slot grammar](spec/slot-profile.json) were frozen and checked in Lean
before production source was created. They extend the original
[development contract](spec/allow-contract.json). The supplement takes precedence
where the original contract describes a specification-only phase.

## Run locally

Prerequisites: Linux, Java/Javac 17, Node/npm, Python 3, `bwrap` and `prlimit`.
The build bootstraps a SHA-512-pinned Maven 3.9.11 archive, a SHA-256-pinned
Checkstyle CLI and the locked/pinned dependencies. Worker namespaces must be
permitted by the host. The current launcher targets this Debian/Ubuntu-style layout: `/usr/bin/bwrap`,
`/usr/bin/prlimit`, `/lib64` and `/etc/java-17-openjdk`; other layouts need an
explicit sandbox-path adaptation before use.

```bash
cd /home/augustus/Allow
python3 scripts/build.py
python3 scripts/run_local.py --show-url
```

Open the printed launch link. It contains private, per-launch authority in its
fragment; the UI consumes and removes the fragment immediately. The default port
is 8080; pass `--port 8081` to choose another. Without `--show-url`, the link is
written only to `.runtime/launch.url` with private file permissions. Stop with
Ctrl+C. Restart after rebuilding: the worker checks the compiled build identity.

## Available now

- Drag blocks or use keyboard-accessible slot and palette buttons to compose
  `and`, `or`, `implies`, `not`, `some`, `no`, and relation union. Declare unary
  signatures with readable names. Incompatible formula/relation slots reject a
  move; holes prevent applying a candidate.
- Validate a composer candidate before applying its Alloy source. Edit source
  directly in text-only mode, validate it, run bounded analysis, inspect instances
  or counterexamples, and cancel jobs. This slice selects the first command.
- Keep visible names separate from the backend's `allow-slot-ast-v1` payload.
  Only anonymous structural bytes enter the local 128-dimensional feature
  encoder. Unsupported canonical syntax produces no payload or features.
- Run each request in a bounded, isolated JVM using the pinned Alloy 6.2.0 Maven
  artifact and SAT4J. HTTP authority, revision/epoch identities, queue limits,
  protocol framing, cancellation and sandbox denial have implementation tests.
- Enforce Javadoc/JSDoc, private class state and the 30-line callable cap with
  Checkstyle and a TypeScript-AST checker, including authored tests.

The anonymous representation is a structural profile, not a complete semantic
normal form. Identifier pseudonymization does not prevent identification through
model structure. The deterministic local features are a baseline for a future
retrieval adapter, not learned embeddings. No vector database, pooled-witness
ingestion, e-graph saturation or LLM integration has been implemented yet.

## Evidence and boundaries

The [formal report](gates/g1/formal-report.json) records 33 checked propositions
(27 model obligations and six concrete witnesses), two clean Lean builds, and
zero production sources at the contract freeze. The eight new obligations cover
anonymous projections, slot separation, admission bounds, terminal cancellation
and the abstract coding policy. These proofs do not establish Java/TypeScript
refinement, parser correspondence, solver correctness or OS isolation.

The [implementation report](gates/g1/implementation-report.json) records the
final build, tests, source hashes and remaining acceptance work. Browser-based
keyboard/drag/drop QA could not run because no browser surface was available;
the G2 browser acceptance gate remains open. The
[implementation notes](docs/implementation-g1.md) explain the supported subset,
security boundaries and validation procedures.

The [six-member council record](reviews/g1-council-summary.json) binds the
supplement reviewed by two GPT-6.1 Terra, two GPT-6.1 Sol and two GPT-6 Astra seats.
The [implementation review record](reviews/g1-implementation-council.json)
preserves the subsequent findings and fixes from the same six requested seats.
Reviews are advisory evidence; requested dispatch models are recorded without
claiming independent attestation of provider internals.

The three supplied datasets have a read-only
[aggregate inventory](docs/dataset-inventory.json). No corpus source was copied
into this repository, embedded, trained on or uploaded. The
[dependency inventory](gates/g1/dependencies.json) records exact runtime bytes
and embedded notices. Dataset rights and conflicting component license metadata
remain open commercialization gates. No commercial distribution is cleared.

To replay the supplemented formal check with a fresh run name:

```bash
python3 scripts/verify_formal.py --run-id independent-replay
```

The original specification-only evidence is preserved under
`closure/archives/r4-c2`; it does not certify the new implementation.
