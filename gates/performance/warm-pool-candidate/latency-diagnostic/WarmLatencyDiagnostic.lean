import Lean

/- Policy supplement only. Receipt truth, clock behavior, Java/OS refinement and actual
measurement values are not established. Existing WarmPoolCandidate is unchanged. -/
namespace Allow.WarmLatencyDiagnostic

inductive Profile where
  | fresh | serial | readyConditioned | emptyPool
  deriving DecidableEq, Repr

structure Attempt where
  succeeded : Bool
  clean : Bool
  durationNs : Nat
  deriving DecidableEq, Repr

structure State where
  authorized : Bool := false
  productionSelected : Bool := false
  promoted : Bool := false
  diagnosticPassed : Bool := false
  attempts : List Attempt := []
  deriving DecidableEq, Repr

inductive Event where
  | explicitComponentAuthorization
  | attempt (record : Attempt)
  | diagnosticPass
  deriving DecidableEq, Repr

def advance (s : State) : Event → State
  | .explicitComponentAuthorization => { s with authorized := true }
  | .attempt a => { s with attempts := s.attempts ++ [a] }
  | .diagnosticPass => { s with diagnosticPassed := true }

def Interpretable (records : List Attempt) : Prop :=
  ∀ a ∈ records, a.succeeded = true ∧ a.clean = true

inductive Step : State → Event → State → Prop where
  | authorize (s) : Step s .explicitComponentAuthorization
      (advance s .explicitComponentAuthorization)
  | attempt (s a) (authorized : s.authorized = true) :
      Step s (.attempt a) (advance s (.attempt a))
  | pass (s) (authorized : s.authorized = true)
      (complete : s.attempts.length = 860) (valid : Interpretable s.attempts) :
      Step s .diagnosticPass (advance s .diagnosticPass)

inductive Reachable : State → Prop where
  | initial : Reachable {}
  | next {s t e} : Reachable s → Step s e t → Reachable t

theorem selection_unchanged {s t e} (h : Step s e t) :
    t.productionSelected = s.productionSelected ∧ t.promoted = s.promoted := by
  cases h <;> exact ⟨rfl, rfl⟩

theorem production_selection_disabled {s} (h : Reachable s) :
    s.productionSelected = false ∧ s.promoted = false := by
  induction h with
  | initial => exact ⟨rfl, rfl⟩
  | next _ step ih =>
    have unchanged := selection_unchanged step
    exact ⟨unchanged.1.trans ih.1, unchanged.2.trans ih.2⟩

theorem diagnostic_pass_cannot_promote {s t} (h : Step s .diagnosticPass t) :
    t.promoted = s.promoted := (selection_unchanged h).2

theorem attempt_requires_authorization {s t a} (h : Step s (.attempt a) t) :
    s.authorized = true := by cases h; assumption

theorem no_attempt_before_explicit_authorization {s t a}
    (noAuth : s.authorized = false) : ¬ Step s (.attempt a) t := by
  intro step
  have := attempt_requires_authorization step
  simp_all

theorem all_attempt_accounting {s t a} (h : Step s (.attempt a) t) :
    t.attempts = s.attempts ++ [a] ∧ t.attempts.length = s.attempts.length + 1 := by
  cases h
  simp [advance]

theorem failure_blocks_interpretation {records : List Attempt} {a : Attempt}
    (included : a ∈ records) (failure : a.succeeded = false ∨ a.clean = false) :
    ¬ Interpretable records := by
  intro valid
  have both := valid a included
  cases failure <;> simp_all

def primarySerial (p : Profile) : Bool := p == .serial

theorem ready_conditioned_never_serial : primarySerial .readyConditioned = false := by decide

def rank50 (n : Nat) : Nat := (50 * n + 99) / 100
def rank95 (n : Nat) : Nat := (95 * n + 99) / 100
def rank99 (n : Nat) : Nat := (99 * n + 99) / 100

theorem nearest_rank_bounded (n : Nat) (positive : 0 < n) :
    (1 ≤ rank50 n ∧ rank50 n ≤ n) ∧
    (1 ≤ rank95 n ∧ rank95 n ≤ n) ∧
    (1 ≤ rank99 n ∧ rank99 n ≤ n) := by
  unfold rank50 rank95 rank99
  omega

theorem measured100_exact_ranks :
    rank50 100 = 50 ∧ rank95 100 = 95 ∧ rank99 100 = 99 := by decide

theorem empty20_exact_ranks :
    rank50 20 = 10 ∧ rank95 20 = 19 ∧ rank99 20 = 20 := by decide

theorem planned_request_count : 3 * 2 * (20 + 100) + (20 + 100) + 20 = 860 := by decide

theorem diagnosticpass_requires_complete_valid_accounting {s t}
    (h : Step s .diagnosticPass t) :
    s.attempts.length = 860 ∧ Interpretable s.attempts := by
  cases h
  exact ⟨by assumption, by assumption⟩

private def success : Attempt := ⟨true, true, 0⟩
private def completed (n : Nat) : State :=
  { authorized := true, attempts := List.replicate n success }

private theorem completed_reachable (n : Nat) : Reachable (completed n) := by
  induction n with
  | zero => exact Reachable.next Reachable.initial (Step.authorize {})
  | succ n ih =>
    have step := Step.attempt (completed n) success rfl
    have eq : advance (completed n) (.attempt success) = completed (n + 1) := by
      simp only [advance, completed, List.replicate_succ']
    rw [eq] at step
    exact Reachable.next ih step

theorem authorized_success_witness :
    ∃ s : State, Reachable s ∧ s.diagnosticPassed = true ∧
      s.attempts.length = 860 ∧ Interpretable s.attempts ∧
      s.productionSelected = false ∧ s.promoted = false := by
  let s := completed 860
  have complete : s.attempts.length = 860 := by simp only [s, completed, List.length_replicate]
  have valid : Interpretable s.attempts := by
    intro a member
    have eq : a = success := (List.mem_replicate.mp member).2
    subst a
    exact ⟨rfl, rfl⟩
  refine ⟨advance s .diagnosticPass, ?_, rfl, complete, valid, rfl, rfl⟩
  exact Reachable.next (completed_reachable 860) (Step.pass s rfl complete valid)

end Allow.WarmLatencyDiagnostic
