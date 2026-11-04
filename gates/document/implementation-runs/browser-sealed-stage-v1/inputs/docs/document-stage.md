# Typed document stage

Allow's document editor connects the React declaration and block workbench to
Spring, an isolated Alloy validator, and a separate PostgreSQL `documents`
schema. It retains exact accepted source, typed syntax, source occurrences,
comment inventory and parser-derived command descriptors. Draft previews are
advisory; only a successful durable commit becomes accepted content.

## Contract and proof boundary

The reviewed document contract consists of `spec/document-stage-draft.json`,
`spec/document-wire-draft.json`, `spec/document-ui-draft.json` and
`spec/document-adapter-draft.json`. The filenames retain their historical draft
names; the frozen r5 manifest and external implementation release identify the
approved bytes. The six seats comprise two GPT-6.1 Terra, two GPT-6.1 Sol and two
GPT-6 Astra reviewers. Their findings were reconciled before implementation.

The r5 formal run checks 112 inherited plus 125 document propositions. The
field-order amendment adds 14, for 251 exact model propositions with two clean,
matching builds. These statements model typing, scope, transaction outcomes,
identity, projection and history invariants. They do not prove that Java,
TypeScript, the Alloy parser, SQL transactions or browser behavior refine the
model. Actual implementation checks are recorded separately.

The [associativity amendment](../spec/document-associativity.json) adds 16 more
propositions, bringing the checked formal surface to 267. A real 500-node
balanced block tree exposed a parser-adapter regression: left-folding Alloy's
flattened conjunction produced a depth-168 intermediate. The amendment proves
ordered Boolean regrouping in its abstract model and retains public limits.
Source elaboration now groups AND/OR operands by balanced halves. Round-trip
comparison may inspect a bounded transient tree, which is discarded and cannot
become an accepted artifact. The original block shape, source and history retain
their separate identity rules. Six independent exact-hash reviews and two clean
builds preceded this production change.

The partial-types amendment adds 13 abstract propositions, bringing the surface
to 280. The active SQL sealed-image amendment adds seven, for 287 propositions
with two clean builds; see the [formal report](../gates/sql/immutable-image-candidate/formal-runs/final-287-v2/report.json).
These propositions do not prove the browser, SQL runtime, or their correspondence
to the models. The final full build reports 171 Java and 164 frontend tests, with
style checks covering 96 files and 988 callables. Separate checks report 164
Python tests, 52 SQL runtime tests, and 107 sealed-image stage tests. HTTP,
restart and recovery checks passed on their recorded finite fixtures. Active SQL
routing is revision 7: it serves its initialized pinned sealed image and checks
the disk image again at restart, rather than checking the live path on each admission.

## Local operation

For this provisioned workspace:

```bash
python3 scripts/build.py
python3 scripts/bootstrap_corpus.py start
python3 scripts/bootstrap_corpus.py migrate
.tools/retrieval-venv/bin/python scripts/bootstrap_documents.py
python3 scripts/run_local.py --show-url
```

Fresh machines also need the pinned PostgreSQL, SQLeanParser and Python runtime
described in [retrieval setup](retrieval-stage.md#run-and-check-locally).
All SQL, including bootstrap, migrations, transaction control and backup/restore,
passes through the pinned SQLeanParser proxy. There is no direct connection
fallback. An unavailable grammar gate or database denies document operations.

Keep `.runtime/documents/identity.json` private and retain it with backups. It
binds the durable principal, workspace and logical launch independently of the
per-launch bearer. The directory is mode 0700; metadata is mode 0600. Missing
identity for a nonempty store is an error, not an invitation to generate a new
identity. An exclusive lock admits one local document server incarnation.
Restart the server after a rebuild; current-policy validation binds the installed
worker bytes. Historical artifacts remain immutable and can be revalidated by
copying history into a new revision.

## Editing and evidence

The block profile supports signatures, owner-grouped fields, set-valued predicate
parameters, facts, assertions and bounded run/check commands. Expressions include
references, predicate calls, Boolean gates, relation tests, set operations,
transpose, join, product and unary-signature quantifiers. Nominal column schemas
are exact and ordered; equal arity alone does not make relations compatible.

Draft analysis distinguishes a known formula or relation sort and partial schema
constraints from a complete inferred type. Holes remain incomplete even when a
slot constrains them. Explicit slot obligations are retained in a draft-only
sidecar, including in-tab known-revision history; this is not a persistence or
restart-recovery guarantee for that sidecar.

The browser maintains accepted state separately from drafts and pending requests.
It debounces advisory validation, rejects stale replies by exact request identity,
and never saves automatically. Mutations retain their exact original bytes and
idempotency key. Retry sends those same bytes. Reformatting a body or changing the
raw route under an existing key is a conflict. A lost acknowledgement never means
that a transaction rolled back.

Source mode preserves exact UTF-8 bytes, including CRLF and non-BMP characters.
Parser-valid syntax outside the bounded block profile is explicitly `TEXT_ONLY`;
it has no invented block graph. Verified source positions use scalar-aligned
UTF-16 offsets. Unavailable or ambiguous locations are reported rather than
guessed. Comments retain exact token bytes and have explicit anchors, copy
provenance and orphan handling.

Analysis uses a stored artifact's opaque command key. The server resolves its
source and command index, and returns a key binding document, accepted revision,
draft epoch, artifact, source, policy, dependency, command and options. Results
from an older accepted revision are historical. SAT examples and counterexamples
remain bounded solver evidence, not proofs of arbitrary correctness.

Document presentation names and IDs are not embedding inputs. The separate
[retrieval pipeline](retrieval-stage.md) admits anonymized context/predicate
records, checked e-graph representatives and complete positive/negative pools.

## Bounds and recovery

Public bodies are at most 256 KiB; source is at most 32,768 UTF-8 bytes. Accepted
block modules have at most 512 expression nodes and depth 32. Complete artifacts
and HTTP outcomes are limited to 1 MiB. Validation shares the local principal's
single solver/validator permit and has no queue. The existing Bubblewrap worker
uses a 512 MiB Java heap, 2 GiB address-space limit, CPU limit and external deadline;
the heap limit is not a claim about total RSS.

Workspace quotas include pending admissions: 64 documents, 4,096 revisions,
16,384 receipts and 256 MiB of accounted logical payload. Revisions and receipts
are immutable. Recovery requires the current nonce and verified process evidence;
elapsed time does not transfer ownership. A worker whose start ticks could not be
read is recoverable only after the supervisor has reaped its exact owned process
and the store independently confirms that PID is absent. A live or reused PID
does not satisfy this narrow recovery branch.

`scripts/smoke_documents.py` exercises the actual HTTP path with authored models.
`scripts/document_recovery_test.py` uses an isolated temporary database to verify
full native backup/restore, history, exact receipts, RLS, ownership and ACLs.
The fixture test never restarts or restores over the live database.

## Acceptance still required

A connected in-app browser has exercised part of the workbench. The previously
observed insertion of `not HOLE` into a relation slot has been retested after the
partial-types fix; the browser evidence records rejection. The earlier pointer
drag attempt produced no observable drop, so pointer acceptance remains open.
Full keyboard scenarios and the named Firefox ESR with Orca manual run also
remain open; component tests and partial browser observations do not replace
them.

The historical pre-fix 500-node warm browser series reported p95 12.3 ms.
The completed final sealed-image run reported p95 12.4 ms over 1,000 measured
edits after 100 warmups and passed its warm preview target. It uses real
controller edits and frame opportunities, not proof of physical pixel
presentation. A separate cold-start series remains required.

The completed 1,000-event authoritative diagnostic run reported p95 468.35 ms,
improved from the earlier 1,258.91 ms baseline but still failing the unchanged
strict <300 ms target. The prior run interrupted by static asset mutation remains
preserved as blocked. Browser preview timing is not server latency evidence.
A reusable validator JVM is a design proposal only: its council review requested
changes, and it has not been implemented.

Dependency and dataset redistribution rights, customer task pilots and support
economics remain unresolved. The commercial release decision is **NO_GO**.
Local proof and test results do not authorize public deployment or distribution.
