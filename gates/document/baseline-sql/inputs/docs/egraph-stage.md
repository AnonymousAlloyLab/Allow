# Bounded typed e-graphs

The engine now performs structural hash-consing, deterministic union-find,
congruence rebuilding to a fixed point, generic e-matching, bounded equality
saturation and positive-cost extraction. It retains concrete derivations rather
than treating e-class membership as proof. The supported rewrite profile is
defined by `spec/egraph-stage.json` revision 2 and `spec/egraph-rules.json`.

This is complete e-graph machinery for that finite rule profile. It is not a
decision procedure for equivalence of arbitrary Alloy programs. A saturated
result means a complete pass over the enabled forward rules added no new nodes
or equalities and rebuilding finished. Reaching a node, match, iteration, proof,
time or output limit remains explicitly incomplete. Different extracted terms
do not demonstrate inequivalence.

## Try a nontrivial example

Start the application using the root README, paste this into the source editor,
and choose **Run analysis** or **Validate**:

```alloy
sig Person {}
pred demo {
  some Person and (some Person or no Person)
}
run demo for 3
```

The predicate-body island can extract the anonymous equivalent of `some Person`
by absorption. Its tree cost decreases while the original Alloy source stays
unchanged. The selected command may be a separate opaque call island. Use the
root selector to inspect the islands, directed parent/child links, input and
extracted terms, proof steps and certificate download. Function bodies have
paths `[3, functionSlot, 5]`, facts `[4, factIndex]`, and the selected command
formula `[5, 6]`, corresponding to positions in the anonymous module array.

For a relation example, use `some (Person & Person)`. Relation idempotence and
nonemptiness congruence allow the same cheaper extraction. Solver results still
describe the original source and declared bounds. Validation produces no SAT
witness. An equivalence certificate and a solver outcome are distinct evidence.

## Anonymous identity and supported rules

The existing structural payload, hash and 128-dimensional local features retain
their original v1 bytes. E-graph results are a separate member of that result;
extracted terms are not substituted into existing embedding input.

Each graph binds the complete anonymous module, an exact numeric root occurrence
and a sorted, unique inventory of typed opaque atoms. Inventory remains fixed
even when a rewrite removes an atom. Capture happens during the original
canonical traversal, so repeated AST objects cannot silently reuse binder slots
from a different occurrence. Display names, source hashes, diagnostics and paths
do not enter this anonymous context. The authenticated outer job still carries
normal source/revision/epoch provenance.

Boolean operators include constants, negation, conjunction and disjunction.
Implication and equivalence lower through specified Boolean identities. The
21 Boolean rules include commutativity, associativity, idempotence, identities,
absorption, distribution, complements, double negation and De Morgan laws.

Relations carry the complete set of ordered nominal signature-product
alternatives, using anonymous slots and fixed builtin tokens. The 13 relation
rules cover union/intersection commutativity, associativity, idempotence,
empty identities, absorption, intersection distribution and safe difference
identities. Every relation rule requires identical operand/result schemas.
Equal arity alone is insufficient. Integer arithmetic, relation override, joins,
quantifiers, lets, calls, ITE and other unsupported constructs are not rewritten.
Unsupported subtrees stay whole opaque leaves; no traversal through their
binders or semantic boundaries occurs.

## Proof checking and limits

Every semantic merge has a locally checked ground derivation before union-find
mutation. Congruence collisions use proofs of ordered child equalities. The
checker accepts only reflexivity, symmetry, transitivity, congruence and exact
instances of the pinned rule catalog. It does not read the engine's union-find
or trust a matcher flag. It rejects foreign atoms, wrong schemas or contexts,
unknown rules, altered substitutions, invalid endpoints, cyclic/forward
premises, excessive depth and conclusions unrelated to the original root.
Export retains only the conclusion's required proof steps, preserving their
order and remapping premise indices before checking the compacted artifact.
The downloaded certificate covers the selected input-to-extraction equality;
the graph preview may contain additional explored members. Internal proof
history, budgets and termination reasons are unchanged by export compaction.

The catalog's exact approved SHA-256 is checked before parsing. Updating its
bytes requires a new contract/proof gate and pin update. Build identity also
covers classpath resources so a registry or configuration change requires a
server restart. The strict worker JSON codec uses deterministic property/map
ordering, including after generic preview values have crossed the process
boundary.

Each island permits at most 512 e-nodes, 12 rounds, 4,096 matching visits,
1,024 unions and 4,096 proof steps. Input terms are capped at 2,048 occurrences;
term and proof dependency depth are capped at 128. The shared e-graph deadline
is one second per job, within the existing worker's external ten-second deadline.
Certificates are capped at 256 KiB, all e-graph output at 512 KiB, and at most
16 root islands are analyzed. Size checks use capped output sinks. Graph
previews retain at most 24 classes and 48 nodes and label truncation explicitly.

Extraction counts each operator/atom occurrence with unit cost, uses anonymous
lexicographic tie-breaking, and returns a finite tree even when the e-graph has
cycles. A checked result never costs more than the original. A limited run may
return a checked original-term fallback; this does not imply successful
optimization or complete search. No global minimum across every equivalent
Alloy expression is claimed.

## What the evidence establishes

The model has 20 new exact-proposition obligations, including four concrete
witnesses. Together with the foundation, 53 model propositions and 34 generated
rule-to-constructor mappings passed two clean Lean builds. The verifier also
evaluated 272 pointwise Boolean/relational rule assignments. It captured no
e-graph production changes at the initial proof freeze.

Lean establishes the abstract rewrite and mixed Boolean/relational calculi.
The graph soundness and extraction theorems assume justified membership; they
do not prove the Java union-find, matcher, parser adapter or operating system.
Runtime checker and adapter correspondence remain explicitly trusted and tested.
Implementation tests cover cycles, multi-level rebuild, matching modulo class
equality, proof forgeries, resource limits, exact prior-profile preservation,
alpha-renaming and bounded Alloy counterexample checks.

The final implementation report records the actual assembled build and HTTP
results. Browser QA remains open: tool inventory stayed empty and explicitly
opening Chrome returned `Browser is not available`. Server-rendered UI tests
and HTTP asset checks do not replace manual keyboard, drag/drop, screen-reader
or visual testing.

Reproduce the current checks from the repository root:

```bash
python3 scripts/build.py
python3 scripts/verify_egraph.py --run-id independent-egraph-replay
python3 scripts/run_local.py --show-url
# In a separate terminal, while that server is running:
python3 scripts/smoke_egraph.py
```

The original Java implementation borrows design ideas from the local ACGN
repository and the established separation between search, application, rebuilding
and extraction described in the [egg tutorial](https://egraphs-good.github.io/egg/egg/tutorials/_01_background/index.html)
and [egg paper](https://arxiv.org/abs/2004.03082). No e-graph library, reference
JAR or dataset source was copied into the runtime. Existing dependency and
corpus-rights questions remain open; this stage does not clear commercial
distribution, introduce vector storage or enable LLM/RAG calls.
