# Local predicate corpus and retrieval

This page describes the installed retrieval profile and its bounded pilot. Use
[current status](current-status.md) for the latest application evidence and
[the remediation plan](performance-remediation-plan.md) for proposed work.

Allow now stores anonymous Alloy predicate records in local PostgreSQL 16.15
with pgvector 0.8.7. A record joins the exact anonymous model context, selected
predicate body and checked e-graph representative, and two complete witness
pools. Human names, original source, paths and dataset labels remain in separate
private provenance. The encoder receives only the four structural components.

## Admission and pools

`N` means examples **per polarity**, configurable from 3 through 5. A FULL record
contains exactly N distinct validated satisfying instances of facts AND P and
N distinct instances of facts AND NOT P. All six to ten instances are complete,
jointly canonicalized structures, including empty field relations. An incomplete
pool remains a diagnostic and cannot acquire a published retrieval vector.

The admitted slice is static, self-contained modules with nullary predicates and
supported declarations. It uses the existing **32,768-byte** source limit, which
is stricter than the supplement's outer 262,144-byte ceiling. Imports, temporal
syntax and unsupported attributes are rejected explicitly. Original run/check
commands do not select predicates or alter corpus bounds. Both queries use scope
3, bitwidth 4, maximum sequence length 3 and no-overflow mode.

The isolated Java worker evaluates facts and predicate truth in every returned
solution. It stops after N distinct canonical structures, 64 enumerated solutions
per polarity, or a resource limit. The complete-instance canonicalizer permits
at most eight ordinary atoms; integer atom meanings stay fixed. SAT existence
and enumeration termination are separate fields. Collecting N instances does
not imply exhaustive enumeration or unbounded validity.

Worker classes, dependencies, solver and rule resources are hashed before and
after a job. The installed JDK is identified by its runtime version; the JDK and
native library bytes, filesystem and operating system remain trusted. This is
not an immutable execution-environment attestation.

## Embeddings and ranking

Pinned `intfloat/e5-base-v2` weights execute locally through ONNX Runtime. Four
768-dimensional vectors represent context, predicate, positive pool and negative
pool. The backbone stays frozen; a local CPU-trained positive diagonal adapter
learns 3,072 parameters. Each block is normalized, adapted and normalized again;
concatenating the blocks and dividing by two produces a unit 3,072-dimensional
float32 vector. No repetition, padding or hash expansion supplies dimensions.

Every token is processed within the declared budgets, or the record is rejected.
Members have equal weight within each pool. Model identity binds weights,
tokenizer, adapter and the serialization/chunking/normalization recipe.

The descending score is

```
w_d * (1 + cosine(full_hierarchy_q, full_hierarchy_r)) / 2
  + w_p * |positive intersection| / max(positive sizes)
  + w_c * |negative intersection| / max(negative sizes)
```

Overlaps require exact canonical context/bounds and complete instance bytes.
Incompatible contexts receive zero overlap. The baseline weights are
0.55/0.225/0.225; adapter weights are selected from the frozen validation grid.
Distances never receive a positive contribution to a descending similarity rank.
Predicate-only cosine is returned as a diagnostic. Exact filtered search is the
default, bounded to 1,000 eligible candidates and 32 MiB before allocation. No ANN
recall or large-scale performance result is claimed.

## Corpus and evaluation evidence

The bounded pilot draws from Alloy4Fun, Alloy5 and Alloy6. A deterministic
selector scans the inventory and lexically preflights up to 64 files per origin
family. The expanded pilot admitted 240 worker candidates; this is not a count
of every source file read during selection. The final corrected-worker replay
contains 35 source files, 69 targets, 65 FULL outcomes and four PARTIAL outcomes,
deduplicating to **46 active FULL records** with N=3 per polarity.

Alloy4Fun contributes two records, Alloy5 23 and Alloy6 35. These counts overlap
because identical records retain multiple origins. All 46 records are partitioned
into 13 family components: nine training, two validation and two test. Exact
source, anonymous record and family aliases prevent duplicates crossing splits.
This is a small accepted subset of the supplied datasets, not full-corpus coverage.

The adapter uses 32 checked structural-variant training pairs and a fixed
20-epoch recipe. Original, intermediate and repaired evaluation artifacts remain
separate. The first evaluation lacked one checked test query variant and had
only one eligible test family. The repair replaces unnecessary saturation with
an independently replayed one-step AND/TRUE derivation, retaining the original
checkpoint, weights, data and split. Reusing an observed holdout is disclosed;
it is not a new blind test. Current measured results and promotion status are
recorded in [the pilot summary](../retrieval/pilot-summary.json).

These metrics measure retrieval of known checked structural rewrites. They do
not establish semantic relevance for arbitrary Alloy predicates. The GPT-6 Luna
fixture tests found that exact pool overlap separated an equivalent predicate
from its opposite while their pretrained cosine scores were both near one.
Independent pools can share no sampled witnesses even for equivalent predicates.
No learned-quality improvement or broad semantic generalization is claimed.

## Persistence and framework integration

Record, both pool memberships and durable embedding intent commit together.
Model jobs use owner tokens and leases. Publication rechecks the current record,
rights and model lineage; registering a model does not make it servable.
Promotion requires an immutable checked evaluation artifact. PostgreSQL enforces
tenant/project row policies under a non-superuser, non-BYPASSRLS application role.

An independently retained, fsynced hash-chained revocation journal is verified
and replayed before repository access. Revoking training consent disables the
affected adapter and all its derived vectors. The actual backup/restore test
restores a stale PostgreSQL dump while retaining the newer journal and confirms
that revoked data cannot reappear. Missing or truncated journals deny service.
Rolling back both the database and its independent journal is outside this model.

The Spring API resolves an authorized stored record identity; it rejects supplied
vectors, pools and validation flags. The React panel displays score components
and context compatibility. The Python LangGraph node has been executed against
the installed framework and emits actual LangChain `Document` objects containing
all four anonymous components. It performs no generation or external tracing.

Every Allow PostgreSQL client now uses a private Unix-socket proxy that admits
SQL through the local SQLeanParser before forwarding it. This includes driver
transaction commands, bootstrap/migrations and PostgreSQL backup/restore tools.
Parameter values and COPY row data retain their original protocol representation.
Direct DSN overrides and the old backend TCP listener are disabled. The grammar
gate rejects malformed or inconclusive input; it has no direct-execution fallback.

SQLeanParser checks a context-free derivation and exact source preservation for
PostgreSQL 16.15. It does not certify SQL types, privileges or execution semantics.
Opaque application DO/function bodies are forbidden; migrations use explicit
statements and catalog checks. PostgreSQL and the pinned pgvector implementation
remain trusted for engine-internal behavior. See [SQL routing](sql-stage.md).

## Run and check locally

The existing workspace already contains the private pilot database and pinned
model runtime. To start the installed database and workbench:

```bash
python3 scripts/bootstrap_corpus.py start
python3 scripts/bootstrap_corpus.py migrate
python3 scripts/run_local.py --show-url
```

For a fresh local installation, build the workbench and provision the database
and pinned model dependencies first:

```bash
python3 scripts/build.py
python3 scripts/bootstrap_corpus.py build
python3 scripts/bootstrap_sqlean.py
/usr/bin/python3 retrieval/bootstrap_ml.py --provision-runtime .tools/retrieval/models
python3 scripts/bootstrap_corpus.py start
python3 scripts/bootstrap_corpus.py migrate
PYTHONPATH=retrieval .tools/retrieval-venv/bin/python -m allow_retrieval.manage initialize
.tools/retrieval-venv/bin/python scripts/bootstrap_documents.py
```

Corpus import/export and model publication are documented in
[retrieval/README.md](../retrieval/README.md); the training recipe and pinned
runtime are in [retrieval/ML.md](../retrieval/ML.md). Initialize the journal only
for an empty database. Keep database credentials, launch links, private exports
and the independent journal out of logs and version control.

```bash
PYTHONPATH=retrieval .tools/retrieval-venv/bin/python scripts/verify_corpus_runtime.py
.tools/retrieval-venv/bin/python scripts/retrieval_recovery_test.py
python3 scripts/bootstrap_corpus.py stop
```

## Acceptance boundary

The historical retrieval/SQL milestone checked 112 model propositions, including
31 retrieval and 28 SQL-routing additions, in two matching clean builds. Later
document amendments bring the tested active surface to 309; exact reports are
linked from [current status](current-status.md). Runtime tests establish finite
implementation behavior; they do not prove Java/Python/SQL refinement, parser or
solver correctness. The 34-rule e-graph supports checked bounded representatives,
not complete canonical forms for arbitrary Alloy.

The six requested council seats and GPT-6 Luna fixture reviews are recorded in
`reviews/`. Connected browser checks now include a passing warm preview series,
saving, SAT analysis and typed-slot rejection. Cold-start, pointer, complete
keyboard and named screen-reader acceptance remain open. Typed document
transactions and source occurrence mapping are implemented and separately tested;
see [document operations](document-stage.md) for their limits.
Local corpus use and training were authorized by the user; third-party dataset
redistribution, dependency-license reconciliation, commercial rights and a
customer pilot remain unresolved. No production or commercial release is claimed.
