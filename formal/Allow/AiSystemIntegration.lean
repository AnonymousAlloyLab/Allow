import Std

/- Abstract guarded pilot policy. Opaque hashes and IDs are equality tokens.
   Host authorization, clock, serialization, validator, journal, SQL gateway,
   browser atomicity, OS/process cleanup and actual provider are trusted. This
   is not an implementation-refinement, privacy, availability or quality proof. -/
namespace Allow.AiSystemIntegration

inductive Mode where
  | off | fixture | remote
  deriving DecidableEq, Repr
inductive Access where
  | privateUser | anonymous
  deriving DecidableEq, Repr

def enabled (m : Mode) (a : Access) : Bool := m != .off && a == .privateUser

theorem off_denied (a : Access) : enabled .off a = false := by simp [enabled]
theorem anonymous_denied (m : Mode) : enabled m .anonymous = false := by cases m <;> decide
theorem private_fixture_positive : enabled .fixture .privateUser = true := by decide
theorem private_remote_positive : enabled .remote .privateUser = true := by decide

structure Binding where
  owner : Nat
  session : Nat
  document : Nat
  acceptedHead : Nat
  draftIdentity : Nat
  candidateHash : Nat
  versions : Nat
  deriving DecidableEq, Repr
structure Consent where
  binding : Binding
  attempt : Nat
  payloadHash : Nat
  terms : Nat
  deriving DecidableEq, Repr
/- attempt is the zero-based consumed-call index (0 or 1); runtime prepared
   attempt labels are one-based (1 or 2). -/
structure Job where
  binding : Binding
  attempt : Nat
  payloadHash : Nat
  terms : Nat
  deadline : Nat
  live : Bool
  consumed : Bool
  deriving DecidableEq, Repr

def mayDispatch (j : Job) (c : Consent) (current : Binding) (now : Nat) : Bool :=
  j.live && !j.consumed && j.binding == current && c.binding == j.binding &&
  c.attempt == j.attempt && c.payloadHash == j.payloadHash && c.terms == j.terms &&
  decide (now < j.deadline ∧ j.attempt < 2)

theorem stale_binding_denied (j : Job) (c : Consent) (current : Binding) (now : Nat)
    (h : j.binding ≠ current) : mayDispatch j c current now = false := by simp [mayDispatch, h]
theorem wrong_payload_denied (j : Job) (c : Consent) (current : Binding) (now : Nat)
    (h : c.payloadHash ≠ j.payloadHash) : mayDispatch j c current now = false := by simp [mayDispatch, h]
theorem wrong_attempt_denied (j : Job) (c : Consent) (current : Binding) (now : Nat)
    (h : c.attempt ≠ j.attempt) : mayDispatch j c current now = false := by simp [mayDispatch, h]
theorem consumed_denied (j : Job) (c : Consent) (current : Binding) (now : Nat)
    (h : j.consumed = true) : mayDispatch j c current now = false := by simp [mayDispatch, h]
theorem third_attempt_denied (j : Job) (c : Consent) (current : Binding) (now : Nat)
    (h : 2 ≤ j.attempt) : mayDispatch j c current now = false := by
  have hn : ¬ j.attempt < 2 := by omega
  simp [mayDispatch, hn]

def repair (j : Job) (newPayload : Nat) : Job :=
  { j with attempt := j.attempt + 1, payloadHash := newPayload, consumed := false }

theorem repair_needs_new_attempt (j : Job) (c : Consent) (current : Binding) (now payload : Nat)
    (h : c.attempt = j.attempt) : mayDispatch (repair j payload) c current now = false := by
  apply wrong_attempt_denied
  simp [repair, h]

structure Receipt where
  binding : Binding
  proposalHash : Nat
  sourceHash : Nat
  deadline : Nat
  deriving DecidableEq, Repr
structure Editor where
  binding : Binding
  draftHash : Nat
  acceptedHistory : Nat
  consumed : Bool
  undoHash : Nat
  undoAvailable : Bool
  deriving DecidableEq, Repr

def applyDraft (s : Editor) (r : Receipt) (proposalHash sourceHash now : Nat)
    (knownInvalid : Bool) : Option Editor :=
  if !knownInvalid && !s.consumed && r.binding == s.binding && r.proposalHash == proposalHash &&
      r.sourceHash == sourceHash && decide (now < r.deadline) then
    some { s with draftHash := sourceHash, consumed := true, undoHash := s.draftHash, undoAvailable := true }
  else none

def undo (s : Editor) (noInterveningChange : Bool) : Option Editor :=
  if s.undoAvailable && noInterveningChange then
    some { s with draftHash := s.undoHash, undoAvailable := false }
  else none

theorem apply_no_save (s t : Editor) (r : Receipt) (p src now : Nat) (invalid : Bool)
    (h : applyDraft s r p src now invalid = some t) : t.acceptedHistory = s.acceptedHistory := by
  unfold applyDraft at h
  split at h
  · cases Option.some.inj h; rfl
  · contradiction

theorem undo_no_save (s t : Editor) (stable : Bool) (h : undo s stable = some t) :
    t.acceptedHistory = s.acceptedHistory := by
  unfold undo at h
  split at h
  · cases Option.some.inj h; rfl
  · contradiction

theorem receipt_stale_denied (s : Editor) (r : Receipt) (p src now : Nat) (invalid : Bool)
    (h : r.binding ≠ s.binding) : applyDraft s r p src now invalid = none := by simp [applyDraft, h]
theorem receipt_consumed_denied (s : Editor) (r : Receipt) (p src now : Nat) (invalid : Bool)
    (h : s.consumed = true) : applyDraft s r p src now invalid = none := by simp [applyDraft, h]
theorem invalidation_denied (s : Editor) (r : Receipt) (p src now : Nat) :
    applyDraft s r p src now true = none := by simp [applyDraft]
theorem intervening_change_denies_undo (s : Editor) : undo s false = none := by simp [undo]

def reserve (used amount ceiling : Nat) : Option Nat :=
  if used + amount ≤ ceiling then some (used + amount) else none

theorem reserve_bound (used amount ceiling next : Nat) (h : reserve used amount ceiling = some next) :
    next ≤ ceiling := by
  unfold reserve at h
  split at h
  · rename_i guard
    cases Option.some.inj h
    exact guard
  · contradiction

theorem over_budget_denied (used amount ceiling : Nat) (h : ceiling < used + amount) :
    reserve used amount ceiling = none := by
  have hn : ¬ used + amount ≤ ceiling := by omega
  simp [reserve, hn]

def packageMode : Mode := .off
theorem packaged_default_off : packageMode = .off := rfl

def binding : Binding := ⟨1, 2, 3, 4, 5, 6, 7⟩
def job : Job := ⟨binding, 0, 8, 9, 100, true, false⟩
def consent : Consent := ⟨binding, 0, 8, 9⟩
def editor : Editor := ⟨binding, 6, 44, false, 0, false⟩
def receipt : Receipt := ⟨binding, 10, 11, 50⟩
theorem dispatch_positive : mayDispatch job consent binding 1 = true := by decide
theorem repair_positive : mayDispatch (repair job 12) ⟨binding, 1, 12, 9⟩ binding 2 = true := by decide
theorem apply_positive : (applyDraft editor receipt 10 11 1 false).isSome = true := by decide
theorem undo_positive : (undo ⟨binding, 11, 44, true, 6, true⟩ true).isSome = true := by decide
theorem reserve_positive : reserve 50000 50000 100000 = some 100000 := by decide

end Allow.AiSystemIntegration
