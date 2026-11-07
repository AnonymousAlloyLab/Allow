# Oracle parity mode

Parity mode treats a predicate from an uploaded Alloy model as a reference for
one predicate being edited in the workbench. Choose the local oracle file and
its parsed predicate, choose the current predicate and scope, then enable parity.
The file remains in memory; it is not saved with the document or sent to an AI
provider. A reference is user-designated, not certified correct.

The selected predicate's entire block body has a frame and a text label:

- **Green — bounded match:** neither directional difference has an instance,
  and at least one admissible shared instance exists.
- **Red — bounded difference:** a shared instance and assignment demonstrate
  opposing truth values. The result panel exposes the distinguishing example.
- **Neutral:** incomplete or source-authoritative draft, waiting or stale check,
  failure, unsupported context, disabled/offline mode, or no admissible instances.

SAT for a single matching example does not establish parity. The comparison
searches for differences; UNSAT in both directions is required for green. Four
UNSAT categories mean that the context is empty or inconsistent, so the frame
stays neutral. All conclusions are limited to the displayed facts, assignments,
scope, bitwidth and sequence bounds.

Complete edits trigger debounced checks, with one active parity request and only
the latest pending input retained. Dirty drafts wait for their current advisory
validation before automatic parity. The manual check can request independent
validation. Failures do not create an automatic retry loop. Changes invalidate
the previous frame immediately; an older response cannot recolor a newer draft.

The oracle and current model must share the supported normalized background:
signatures, fields, facts, assertions and nonselected helpers. Parameters pair by
position and ordered schema. Background dependencies on the selected predicate
are rejected. The whole current module must be complete and block-supported.
Files are limited to 32 KiB of strict UTF-8 and the existing supported grammar.

The backend validates the actual current block candidate inside its sandbox,
resolves the selected predicate by its remapped declaration identity, reparses
the oracle, and uses the existing four-category SAT4J comparison and assignment
replay. Requests inherit existing authority, capacity, ten-second aggregate
deadline, cleanup and freshness checks. No operation automatically saves a model.

The [contract](../spec/oracle-parity.json) and
[finite Lean policy report](../gates/oracle-parity-v1/formal-report.json) preceded
implementation. They do not prove production-code refinement, unrestricted
equivalence, oracle correctness or commercial readiness. Native deployment and
public acceptance gates remain unchanged.
