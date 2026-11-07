# Reusable blocks and bounded comparison

The visual workbench offers a document-local shelf of reusable subformulas,
context-sensitive block choices, and two comparison modes. These features do not
need an AI provider or API key. The governing contract is
[block-workbench.json](../spec/block-workbench.json); its finite Lean supplement
and implementation evidence live under `gates/block-workbench-v1/`.

## Reuse and substitutions

Select a formula or relation subtree, give it a name and save it to the reusable
shelf. Insert a saved block into the selected slot, or drag it to a slot. Each
insertion creates independent expression and internal binder identities. External
references retain their declaration identities and are checked at the new
location. A predicate reference uses the current definition of that predicate.

The shelf remains in memory for the current document and authority. It is not
saved with the model, sent to a corpus, or persisted in browser storage. Switching
documents or closing the workbench clears it. The shelf is limited to 24 entries,
128 nodes per entry, 1,536 nodes in total and 512 KiB of serialized content.
Changes to declaration shapes can make a saved entry unavailable; matching a name
does not make a different declaration interchangeable.

Select an edit location to filter constructors, references and saved entries.
Incompatible substitutions are hidden by default. Unresolved choices still need
their child slots completed, and unavailable checks do not authorize insertion.
The all-choices view explains rejected choices. Click, keyboard and drag actions
use the same candidate preparation and recheck current content before editing.

An unaccepted source draft takes precedence over the previously parsed block
tree. Block mutations and comparisons remain unavailable until a current typed
model is available; the older tree cannot silently replace newer source text.

## Compare current blocks

Compose two alternatives in the forest, select a formula block for A and another
for B, choose a common scope, and explicitly compare them. Both selections must
belong to the same complete supported module. Relation-valued expressions and
unresolved holes cannot be used as Boolean comparison arms.

The solver searches for one instance in each of four categories:

- Both formulas are true.
- A is true and B is false.
- A is false and B is true.
- Both formulas are false.

All four searches use the same declarations, facts, bounds and variable-assignment
rules. A free variable with the same declaration identity receives one shared
assignment. Distinct binder identities remain distinct. The existing supported
source grammar still rejects duplicate binder spellings within a model; this
feature does not broaden that grammar. Separate uploaded files may use the same
parameter spelling.
All original facts remain assumptions, including a fact containing a selected
block. Run and check commands do not contribute extra assumptions.

A returned instance includes bounded model data and the free-variable assignment.
Both arms are evaluated again on that exact solution before a truth pair is
published. Display truncation is labeled. Editing a model, changing either arm or
changing bounds invalidates the displayed comparison.

## Compare predicates from local files

The model-file mode has a separate local `.als` file picker and predicate selector
for each side. Each file must be valid UTF-8, no more than 32 KiB, and supported by
Allow's existing block grammar. The isolated parser supplies predicate choices;
the comparison reparses the exact selected sources. Files remain in memory and
do not replace or save the current workbench model.

The two files must have the same background declarations and constraints after
validated normalization: signatures, fields, multiplicities, ordered schemas,
facts, assertions and nonselected predicate definitions. Comments and commands
are ignored for this match. The selected predicates may have different names,
parameter names and bodies. Their parameters pair by position and identical
ordered schema, with one shared set-valued relation assignment per pair.

Background declarations that depend on a selected predicate are rejected. This
restriction prevents the changed predicate body from silently changing the facts
under which it is compared. Differences in background facts or helper semantics
produce an explanation; the system does not silently conjoin incompatible files.
The resulting declaration and parameter correspondence is shown with the result.

## Read results accurately

A difference instance demonstrates a difference under the reported assumptions
and bounds. When both difference searches complete with UNSAT, the predicates
agree only in that bounded context. Four UNSAT categories mean there are no
admissible bounded instances, possibly because the facts are inconsistent or a
required singleton domain is empty. Neither result proves unrestricted model
equivalence. Timeouts, errors, unsupported input and unavailable capacity are
separate outcomes and never count as UNSAT.

Each request uses the existing scoped authority, SQL parser gateway, public
expensive-operation admission and global worker capacity. One isolated worker
runs the four searches sequentially under one ten-second deadline, including
context resolution and validation. Capacity remains owned through cleanup.
Comparison has no automatic Save, persistent result cache or corpus side effect.

## Layout and release limits

The block forest is the primary workbench surface, with a compact palette/shelf
and collapsible supporting declarations and source panels. Formula, relation,
reference, quantifier and hole colors supplement labels and icons; color alone
does not convey compatibility or truth. Every drag action has a native control
alternative.

The Lean supplement proves a finite policy model. It does not prove the Java or
React implementation, parser/solver refinement, operating-system cleanup,
accessibility, unbounded equivalence or commercial readiness. Existing commercial
and native Windows/IIS deployment gates remain unchanged.
