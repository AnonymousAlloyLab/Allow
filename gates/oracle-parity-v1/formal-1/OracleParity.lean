import Std
namespace Allow.OracleParity
inductive Outcome where | sat | unsat | unknown | failure deriving DecidableEq, Repr
inductive Verdict where | green | red | neutral deriving DecidableEq, Repr
structure Categories where
  candidateOnly : Outcome
  oracleOnly : Outcome
  bothTrue : Outcome
  bothFalse : Outcome
  deriving DecidableEq, Repr

def category (c o : Bool) : Nat := if c then (if o then 2 else 0) else (if o then 1 else 3)
def difference (c o : Bool) : Bool := c != o
theorem xor_categories (c o : Bool) : difference c o = true ↔ category c o = 0 ∨ category c o = 1 := by
  cases c <;> cases o <;> decide

def resolved (x : Outcome) : Bool := x == .sat || x == .unsat
def complete (q : Categories) : Bool := resolved q.candidateOnly && resolved q.oracleOnly && resolved q.bothTrue && resolved q.bothFalse
def greenCondition (q : Categories) : Bool := q.candidateOnly == .unsat && q.oracleOnly == .unsat && (q.bothTrue == .sat || q.bothFalse == .sat)
def redCondition (q : Categories) : Bool := q.candidateOnly == .sat || q.oracleOnly == .sat
def classify (validated : Bool) (q : Categories) : Verdict :=
  if validated && complete q then if redCondition q then .red else if greenCondition q then .green else .neutral else .neutral

theorem green_requirements (v : Bool) (q : Categories) (h : classify v q = .green) :
    v = true ∧ complete q = true ∧ q.candidateOnly = .unsat ∧ q.oracleOnly = .unsat ∧ (q.bothTrue = .sat ∨ q.bothFalse = .sat) := by
  cases q with
  | mk a b c d => cases v <;> cases a <;> cases b <;> cases c <;> cases d <;> simp_all [classify, complete, resolved, greenCondition, redCondition]
theorem red_requirements (v : Bool) (q : Categories) (h : classify v q = .red) :
    v = true ∧ complete q = true ∧ (q.candidateOnly = .sat ∨ q.oracleOnly = .sat) := by
  cases q with
  | mk a b c d => cases v <;> cases a <;> cases b <;> cases c <;> cases d <;> simp_all [classify, complete, resolved, greenCondition, redCondition]
theorem unresolved_neutral (v : Bool) (q : Categories) (h : complete q = false) : classify v q = .neutral := by simp [classify, h]
theorem invalid_neutral (q : Categories) : classify false q = .neutral := by simp [classify]
theorem vacuous_neutral (v : Bool) : classify v ⟨.unsat, .unsat, .unsat, .unsat⟩ = .neutral := by cases v <;> decide

/- Identity equality and lifecycle flags are trusted abstractions of concrete inputs. -/
structure Binding where
  authority : String
  documentId : String
  draftId : String
  draftEpoch : Nat
  contentGeneration : Nat
  contentSnapshot : String
  baseRevision : Nat
  artifact : String
  policy : String
  dependency : String
  targetId : String
  oracleHash : String
  oraclePredicate : String
  scope : Nat
  deriving DecidableEq, Repr
structure State where
  binding : Binding
  enabled : Bool
  online : Bool
  complete : Bool
  supported : Bool
  blockAuthoritative : Bool
  deriving DecidableEq, Repr
def publish (s : State) (b : Binding) (r : Verdict) : Verdict :=
  if s.enabled && s.online && s.complete && s.supported && s.blockAuthoritative && decide (s.binding = b) then r else .neutral
theorem binding_required (s : State) (b : Binding) (r : Verdict) (h : publish s b r ≠ .neutral) : s.binding = b := by
  by_cases he : s.binding = b
  · exact he
  · simp [publish, he] at h
theorem stale_neutral (s : State) (b : Binding) (r : Verdict) (h : s.binding ≠ b) : publish s b r = .neutral := by simp [publish, h]
theorem disabled_neutral (s : State) (b : Binding) (r : Verdict) (h : s.enabled = false) : publish s b r = .neutral := by simp [publish, h]
theorem offline_neutral (s : State) (b : Binding) (r : Verdict) (h : s.online = false) : publish s b r = .neutral := by simp [publish, h]
theorem incomplete_neutral (s : State) (b : Binding) (r : Verdict) (h : s.complete = false) : publish s b r = .neutral := by simp [publish, h]
theorem unsupported_neutral (s : State) (b : Binding) (r : Verdict) (h : s.supported = false) : publish s b r = .neutral := by simp [publish, h]
theorem source_draft_neutral (s : State) (b : Binding) (r : Verdict) (h : s.blockAuthoritative = false) : publish s b r = .neutral := by simp [publish, h]
def advisoryCheck (revision : Nat) (result : Verdict) : Nat × Verdict := (revision, result)
theorem advisory_preserves_revision (revision : Nat) (result : Verdict) : (advisoryCheck revision result).1 = revision := rfl
#print axioms xor_categories
#print axioms green_requirements
#print axioms red_requirements
#print axioms unresolved_neutral
#print axioms invalid_neutral
#print axioms vacuous_neutral
#print axioms binding_required
#print axioms stale_neutral
#print axioms disabled_neutral
#print axioms offline_neutral
#print axioms incomplete_neutral
#print axioms unsupported_neutral
#print axioms source_draft_neutral
#print axioms advisory_preserves_revision
end Allow.OracleParity
