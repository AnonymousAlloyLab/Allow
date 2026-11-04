# Local predicate retrieval

The corpus, witness pools, cached features, training checkpoints, database credentials and revocation journal live under private `.runtime/corpus/` paths. They are excluded from tracked source. The supplied datasets have local engineering authorization; third-party redistribution and commercial clearance remain unresolved.

Apply `db/migrations/004_retrieval.sql` through the workspace database bootstrap. The HTTP bridge reads the private `.runtime/corpus/database.json` configuration and connects as `allow_app`, a non-superuser without `BYPASSRLS`. Never pass this file or its contents through an API response.

The local tools use `PYTHONPATH=retrieval` and `.tools/retrieval-venv/bin/python`:

- `python -m allow_retrieval.manage initialize` initializes the independent journal only for an empty database.
- `python -m allow_retrieval.importer --families 60 --files 2 --targets 3` selects a deterministic bounded pilot. This initial anonymous profile has a stricter **32,768-byte** source ceiling than the contract's outer ceiling. It rejects unsupported imports, temporal syntax, signature attributes and parametric predicates.
- `python -m allow_retrieval.manage export` freezes an immutable private export for local feature caching and evaluation.
- `python -m allow_retrieval.manage embed` registers the pinned pretrained encoder and processes only that model's durable outbox jobs. Adapter registration additionally requires `--adapter` and `--training-manifest`.

Ingestion stores artifact origins, target records, both polarity runs, complete canonical witnesses, their memberships and a durable embedding intent in one transaction. A newly registered model turns eligible intents into concrete outbox jobs. A claim has an owner token and a 120-second lease; expired claims can be retried, and their former owners cannot publish. Publication rechecks record identity, model lineage and rights.

Model registration does not enable serving. Promotion reads an immutable hash-verified local evaluation artifact that binds the model, adapter, training lineage and selected weights. A learned model also needs the frozen family/split/source and non-regression gates. Default retrieval considers only active, explicitly servable models. Exact search checks its 1,000-candidate and 32 MiB serialized-content/vector bounds before allocating candidate payloads.

The Java subprocess receives only the JDK, required runtime libraries, compiled worker classes/dependencies and pinned solver. It has isolated namespaces, no network, a private `/tmp`, no inherited environment and no host/home/project mount. Sources are read without following any path-component symlinks. Both selected-body and nontrivial training-variant certificates are produced and replayed in the trusted worker; Python never admits client-provided certificate flags.

`allow_retrieval.cli` accepts one bounded JSON request on stdin, with protocol 1, a canonical UUID `requestId`, and `operation` equal to `status`, `list` or `search`. Search requires an existing stored `recordId`; clients cannot submit vectors, pools or admission flags. Listing returns only searchable records. Search returns score components and authorized anonymous structural content, with explicit content-budget omissions. The LangGraph node returns that structural content in real LangChain `Document` objects and performs no generation or remote tracing.

Every repository operation locks and verifies the independent hash-chained journal before using the database. A revoke is fsynced before its database application. Revoking a training record disables every affected checkpoint and removes every vector derived from it. A restored database replays later journal entries; missing, truncated, mismatched or rolled-back journals deny service. The journal must be retained independently of database backups.

Run the checks with:

```bash
PYTHONPATH=retrieval .tools/retrieval-venv/bin/python -m unittest discover -s retrieval/tests -v
.tools/retrieval-venv/bin/python scripts/retrieval_recovery_test.py
```

The recovery check creates and drops a temporary database. It performs a real `pg_dump`/`pg_restore` around training-consent revocation, retains the independent journal, and checks model-wide vector invalidation, outbox cancellation and missing/corrupt-journal denial.
