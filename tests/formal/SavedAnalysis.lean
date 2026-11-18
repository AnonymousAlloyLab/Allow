import Allow.SavedAnalysisUpgrade
import Lean.Util.CollectAxioms
import Lean.Elab.Command

open Allow.SavedAnalysisUpgrade

-- Keep the contract's types and both directions of admission in the CI interface.
example (s : Selection) (h : s.saved ≠ s.running) :
    admit s = true ↔ s.owned = true ∧ s.bound = true ∧ s.rechecked = true ∧ s.sameOccurrence = true :=
  old_requires_recheck s h

example (s : Selection) (h : s.saved = s.running) :
    admit s = true ↔ s.owned = true ∧ s.bound = true := current_admission s h

example (owned : Bool) (r : Receipt) (running : Build) (document job : Nat) :
    poll owned r running document job = true ↔ owned = true ∧ r.document = document ∧ r.job = job ∧
      r.execution.policy = running.policy ∧ r.execution.dependency = running.dependency :=
  poll_iff owned r running document job

example (saved exec : Build) (document job : Nat) : (register saved exec document job).saved = saved :=
  saved_binding_preserved saved exec document job

-- Only the standard axioms already accepted by the repository may enter these proofs.
run_cmd do
  let allowed := #[``propext, ``Quot.sound, ``Classical.choice]
  for theoremName in #[``old_requires_recheck, ``current_admission, ``no_foreign_submission,
      ``no_unbound_submission, ``poll_iff, ``saved_binding_preserved] do
    for dependency in ← Lean.collectAxioms theoremName do
      unless allowed.contains dependency do
        throwError "{theoremName} depends on unapproved axiom {dependency}"
