namespace Allow.SavedAnalysisUpgrade

/-- Abstract identities of the validation policy and the installed worker. -/
structure Build where
  policy : Nat
  dependency : Nat
  deriving DecidableEq

structure Selection where
  owned : Bool
  bound : Bool
  saved : Build
  running : Build
  rechecked : Bool
  sameOccurrence : Bool

def admit (s : Selection) : Bool :=
  decide (s.owned = true ∧ s.bound = true ∧
    (s.saved = s.running ∨ (s.rechecked = true ∧ s.sameOccurrence = true)))

theorem old_requires_recheck (s : Selection) (h : s.saved ≠ s.running) :
    admit s = true ↔ s.owned = true ∧ s.bound = true ∧ s.rechecked = true ∧ s.sameOccurrence = true := by
  simp [admit, h]

theorem current_admission (s : Selection) (h : s.saved = s.running) :
    admit s = true ↔ s.owned = true ∧ s.bound = true := by simp [admit, h]

theorem no_foreign_submission (s : Selection) (h : s.owned = false) : admit s = false := by simp [admit, h]
theorem no_unbound_submission (s : Selection) (h : s.bound = false) : admit s = false := by simp [admit, h]

structure Receipt where
  saved : Build
  execution : Build
  document : Nat
  job : Nat

def register (saved execution : Build) (document job : Nat) : Receipt :=
  ⟨saved, execution, document, job⟩

def poll (owned : Bool) (r : Receipt) (running : Build) (document job : Nat) : Bool :=
  decide (owned = true ∧ r.document = document ∧ r.job = job ∧ r.execution = running)

/-- Polling binds all execution fields, including both components of the build. -/
theorem poll_iff (owned : Bool) (r : Receipt) (running : Build) (document job : Nat) :
    poll owned r running document job = true ↔
      owned = true ∧ r.document = document ∧ r.job = job ∧
      r.execution.policy = running.policy ∧ r.execution.dependency = running.dependency := by
  cases r with
  | mk _ execution _ _ => cases execution; cases running; simp [poll]

theorem saved_binding_preserved (saved exec : Build) (document job : Nat) :
    (register saved exec document job).saved = saved := rfl

end Allow.SavedAnalysisUpgrade
