# Allow

Allow now has a local Spring Boot / React workbench backed by the existing Java 17
installation and sandboxed Alloy/Kodkod/SAT4J. This implements the G1 development
foundation, a typed document editor with durable revisions, the bounded e-graph
stage, and local predicate-pool retrieval. It is not a
completed production platform.

Start with the [current status and evidence index](docs/current-status.md),
[document operations](docs/document-stage.md), and
[performance remediation plan](docs/performance-remediation-plan.md).
Older milestone reports below retain their original scope and source hashes.

The [implementation supplement](spec/implementation-g1.json) and
[anonymous slot grammar](spec/slot-profile.json) were frozen and checked in Lean
before production source was created. They extend the original
[development contract](spec/allow-contract.json). The supplement takes precedence
where the original contract describes a specification-only phase.
The [e-graph supplement](spec/egraph-stage.json) and
[34-rule catalog](spec/egraph-rules.json) were also checked before their
production implementation.
The [retrieval supplement](spec/retrieval-stage.json) adds the anonymous paired
corpus, local learned 3072-dimensional embeddings and retrieval policy. Its Lean
obligations and six-member council were completed before implementation.
The [SQL-routing supplement](spec/sql-stage.json) requires every client SQL
statement to pass through the pinned local SQLeanParser grammar gate, including
driver transaction commands, migrations and backup/restore tooling.
See [SQL routing operations and proof boundaries](docs/sql-stage.md) for the
exact local gateway, prepared-statement policy and recovery checks.
The [document contract](spec/document-stage-draft.json), its wire/UI/parser
supplements and the [field-order amendment](spec/document-field-order.json)
were reviewed by the six requested council seats and checked before their
production changes. See [document operations](docs/document-stage.md).
The [associativity amendment](spec/document-associativity.json) repairs parser
reconstruction of large balanced Boolean trees while retaining the public
depth-32 and 512-node limits. That historical 267-proposition surface passed two
clean builds after an independent six-seat review. Later partial-type, sealed
SQL-image and validation-context amendments bring the tested model surface to
309; the current status index links their exact evidence. The new database
cleanup implementation has a separate reviewed 28-proposition supplement;
its runtime acceptance remains in progress and does not enlarge the inherited
aggregate proof claim.

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
python3 scripts/bootstrap_corpus.py start
python3 scripts/bootstrap_corpus.py migrate
.tools/retrieval-venv/bin/python scripts/bootstrap_documents.py
python3 scripts/run_local.py --show-url
```

Open the printed launch link. It contains private, per-launch authority in its
fragment; the UI consumes and removes the fragment immediately. The default port
is 8080; pass `--port 8081` to choose another. Without `--show-url`, the link is
written only to `.runtime/launch.url` with private file permissions. Stop with
Ctrl+C. Restart after rebuilding: the worker checks the compiled build identity.

## Available now

- Create documents and edit signatures, fields, predicate parameters, facts,
  assertions and bounded commands using 23 expression types. Typed slots reject
  incompatible relations, formulas and out-of-scope variables. Holes prevent
  submission. Keyboard operations and pointer dragging have implementation tests;
  manual browser and screen-reader acceptance remains open.
- Preview generated Alloy alongside blocks, or edit exact source text. Save a
  supported model as blocks; retain valid unsupported syntax explicitly as text.
  Accepted revisions and draft previews remain separate. Select an accepted
  command for bounded analysis, with historical results labeled separately.
- Keep immutable revisions and byte-exact commit receipts in PostgreSQL through
  SQLeanParser. Copy historical content into a fresh checked revision, including
  revision zero. A restarted local server retains workspace identity and issues
  a fresh bearer capability.
- Keep visible names separate from the backend's `allow-slot-ast-v1` payload.
  Hierarchical retrieval encodes anonymous context, predicate and witness pools
  into 3072 dimensions. The older 128-dimensional feature encoder is a separate
  diagnostic. Unsupported canonical syntax produces no payload or features.
- Run Alloy validation and solver jobs in a bounded, isolated JVM using the pinned Alloy 6.2.0 Maven
  artifact and SAT4J. HTTP authority, revision/epoch identities, queue limits,
  protocol framing, cancellation and sandbox denial have implementation tests.
- Enforce Javadoc/JSDoc, private class state and the 30-line callable cap with
  Checkstyle and a TypeScript-AST checker, including authored tests.
- Explore typed e-classes with hash-consing, union-find, congruence rebuilding,
  pattern matching, bounded saturation, finite extraction and independent
  certificate replay. Inspect directed graph links, costs, anonymous terms and
  downloadable proof data for each supported root.
- Store anonymized predicate/context records with checked e-graph representatives
  and **3–5 complete distinct examples per polarity**. Both pools satisfy the
  same model facts: positives satisfy P and negatives satisfy not P.
- Encode context, predicate, positive pool and negative pool into four learned
  768-dimensional blocks, stored as one 3072-dimensional pgvector. Search combines
  pretrained/local-adapter similarity with context-compatible pool overlap.
- Retrieve stored candidates through the authenticated Spring/React workbench
  or a tested LangGraph node returning structured LangChain documents.

The anonymous representation is a structural profile, not a complete semantic
normal form. Identifier pseudonymization does not prevent identification through
model structure. The old 128-dimensional deterministic features remain a separate
diagnostic; retrieval uses the new pretrained hierarchical encoder. The e-graph uses 21 Boolean rules and
13 rules over relations with identical full nominal schemas. Other operators
remain opaque. Retrieval returns candidate evidence; LLM generation is disabled.
See [retrieval operations and limits](docs/retrieval-stage.md) for setup, the
bounded real-corpus pilot, learned-adapter evaluation and remaining gates.

## Evidence and boundaries

The [e-graph formal report](gates/egraph/formal-report.json) records 53 model
propositions, 34 exact catalog-to-Lean mappings and 272 finite rule evaluations,
with two matching clean builds before e-graph production edits. Twenty model
obligations were added for Boolean, relational and mixed derivations, guarded
merges, extraction and concrete witnesses. These proofs do not establish
Java/TypeScript refinement, parser correspondence, solver correctness or OS
isolation. The abstract graph model assumes justified class membership; the
runtime separately checks concrete derivations before merging and publishing.

The [implementation report](gates/egraph/implementation-report.json) records the
historical e-graph build, tests, source hashes and acceptance work. The
[retrieval formal report](gates/retrieval/formal-report.json) records 84 model
propositions, including 31 added retrieval obligations, with two matching clean
builds. The [retrieval implementation report](gates/retrieval/implementation-report.json)
binds that historical stage's sources and executed checks. The
[current status index](docs/current-status.md) identifies the later document
build, the passing warm browser series, and the remaining cold, pointer and
accessibility acceptance work. The
[e-graph notes](docs/egraph-stage.md) explain the supported rules, proof boundaries
and an example to try. The [foundation notes](docs/implementation-g1.md) describe
the underlying local service.

The [six-member e-graph council record](reviews/egraph-council.json) binds the
supplement reviewed by two GPT-6.1 Terra, two GPT-6.1 Sol and two GPT-6 Astra seats.
The [runtime review](reviews/egraph-runtime-astra-1.json) preserves subsequent
certificate-checker findings and fixes. Earlier foundation reviews are retained.
Reviews are advisory evidence; requested dispatch models are recorded without
claiming independent attestation of provider internals.

The three supplied datasets have an [aggregate inventory](docs/dataset-inventory.json).
The user subsequently authorized local ingestion and training. A bounded pilot
now contains 46 distinct FULL records from 35 source files across 13 family
components. Private source snapshots, pools, features and checkpoints stay in
ignored `.runtime/corpus/`; no corpus was uploaded or added to tracked source. The
[dependency inventory](gates/g1/dependencies.json) records exact runtime bytes
and embedded notices. Dataset rights and conflicting component license metadata
remain open commercialization gates. No commercial distribution is cleared.

To replay the historical retrieval slice's 84-proposition inventory with a fresh
run name (this is not the current 309-proposition closure):

```bash
python3 scripts/verify_retrieval.py --run-id independent-retrieval-replay
```

The original specification-only evidence is preserved under
`closure/archives/r4-c2`. The completed foundation snapshot is preserved under
`gates/egraph/baseline-g1`. Historical reports do not certify later source edits.
The completed e-graph source snapshot is preserved under
`gates/retrieval/baseline-egraph`.
