import Std

/- Finite protocol abstraction. IDs and hashes are opaque equality tokens; clock,
   owner, rights and validation observations are trusted inputs. This does not
   prove cryptography, runtime correspondence, race freedom, LLM quality, Alloy
   validity, provider billing or confidentiality. -/
namespace Allow.AiNativeDevelopment

structure Binding where
  owner : Nat
  workspace : Nat
  incarnation : Nat
  document : Nat
  acceptedRevision : Nat
  acceptedHash : Nat
  draftEpoch : Nat
  draftHash : Nat
  target : Nat
  proposalHash : Nat
  versions : Nat
  deriving DecidableEq, Repr

inductive Kind where
  | explanation | typedEdit | sourceEdit
  deriving DecidableEq, Repr

inductive Validation where
  | unverified | invalid | complete | incomplete
  deriving DecidableEq, Repr

inductive Projection where
  | typed | textOnly
  deriving DecidableEq, Repr

structure Proposal where
  binding : Binding
  kind : Kind
  validation : Validation
  projection : Projection
  resultHash : Nat
  obligationsPreserved : Bool
  contradictionFree : Bool
  deriving DecidableEq, Repr

structure Authority where
  owner : Nat
  workspace : Nat
  incarnation : Nat
  deadline : Nat
  active : Bool
  rights : Bool
  policy : Bool
  deriving DecidableEq, Repr

def live (a : Authority) (b : Binding) (now : Nat) : Bool :=
  a.active && a.rights && a.policy && decide (now < a.deadline) &&
  a.owner == b.owner && a.workspace == b.workspace && a.incarnation == b.incarnation

def eligible (p : Proposal) : Bool :=
  (p.kind == .sourceEdit || (p.kind == .typedEdit && p.projection == .typed)) &&
  (p.validation == .complete ||
   (p.validation == .incomplete && p.obligationsPreserved && p.contradictionFree))

structure Receipt where
  binding : Binding
  kind : Kind
  resultHash : Nat
  deadline : Nat
  deriving DecidableEq, Repr

def approve (a : Authority) (p : Proposal) (current : Binding) (now deadline : Nat) : Option Receipt :=
  if live a p.binding now && p.binding == current && eligible p &&
      decide (now < deadline ∧ deadline ≤ a.deadline) then
    some ⟨p.binding, p.kind, p.resultHash, deadline⟩
  else none

structure State where
  current : Binding
  acceptedHistory : Nat
  draftContents : Nat
  consumed : Bool
  deriving DecidableEq, Repr

structure LocalObservation where
  invalidated : Bool
  deriving DecidableEq, Repr

def applyDraft (obs : LocalObservation) (p : Proposal) (r : Receipt) (s : State) (now newDraft : Nat) : Option State :=
  if !obs.invalidated && p.binding == s.current && r.binding == p.binding &&
     r.kind == p.kind && r.resultHash == p.resultHash && eligible p && newDraft == p.resultHash && decide (now < r.deadline) && !s.consumed then
    some { s with current := { s.current with draftEpoch := s.current.draftEpoch + 1, draftHash := newDraft }, draftContents := newDraft, consumed := true }
  else none

theorem apply_preserves_history (obs : LocalObservation) (p : Proposal) (r : Receipt)
    (s t : State) (now draft : Nat) (h : applyDraft obs p r s now draft = some t) :
    t.acceptedHistory = s.acceptedHistory := by
  unfold applyDraft at h
  split at h
  · cases Option.some.inj h; rfl
  · contradiction

theorem apply_consumes_identity (obs : LocalObservation) (p : Proposal) (r : Receipt)
    (s t : State) (now draft : Nat) (h : applyDraft obs p r s now draft = some t) :
    t.consumed = true := by
  unfold applyDraft at h
  split at h
  · cases Option.some.inj h; rfl
  · contradiction

theorem altered_receipt_result_denied (obs : LocalObservation) (p : Proposal) (r : Receipt)
    (s : State) (now draft : Nat) (h : r.resultHash ≠ p.resultHash) :
    applyDraft obs p r s now draft = none := by simp [applyDraft, h]

theorem wrong_result_denied (obs : LocalObservation) (p : Proposal) (r : Receipt)
    (s : State) (now draft : Nat) (h : draft ≠ p.resultHash) :
    applyDraft obs p r s now draft = none := by simp [applyDraft, h]

theorem applied_result_matches (obs : LocalObservation) (p : Proposal) (r : Receipt)
    (s t : State) (now draft : Nat) (h : applyDraft obs p r s now draft = some t) :
    t.draftContents = p.resultHash := by
  unfold applyDraft at h
  split at h
  · rename_i guard
    simp only [Bool.and_eq_true, beq_iff_eq] at guard
    cases Option.some.inj h
    simp only
    exact guard.1.1.2
  · contradiction

theorem expired_authority (a : Authority) (b : Binding) (now : Nat)
    (h : a.deadline ≤ now) : live a b now = false := by
  have hn : ¬ now < a.deadline := by omega
  simp [live, hn]

theorem revoked_server_approval_denied (a : Authority) (p : Proposal) (current : Binding)
    (now deadline : Nat) (h : a.rights = false) : approve a p current now deadline = none := by
  simp [approve, live, h]

theorem observed_revocation_denied (obs : LocalObservation) (p : Proposal) (r : Receipt)
    (s : State) (now draft : Nat) (h : obs.invalidated = true) :
    applyDraft obs p r s now draft = none := by simp [applyDraft, h]

theorem wrong_owner (a : Authority) (b : Binding) (now : Nat)
    (h : a.owner ≠ b.owner) : live a b now = false := by simp [live, h]
theorem wrong_workspace (a : Authority) (b : Binding) (now : Nat)
    (h : a.workspace ≠ b.workspace) : live a b now = false := by simp [live, h]
theorem wrong_incarnation (a : Authority) (b : Binding) (now : Nat)
    (h : a.incarnation ≠ b.incarnation) : live a b now = false := by simp [live, h]
theorem stale_approval (a : Authority) (p : Proposal) (current : Binding) (now deadline : Nat)
    (h : p.binding ≠ current) : approve a p current now deadline = none := by simp [approve, h]
theorem stale_apply (obs : LocalObservation) (p : Proposal) (r : Receipt) (s : State) (now draft : Nat)
    (h : p.binding ≠ s.current) : applyDraft obs p r s now draft = none := by simp [applyDraft, h]
theorem wrong_receipt (obs : LocalObservation) (p : Proposal) (r : Receipt) (s : State) (now draft : Nat)
    (h : r.binding ≠ p.binding) : applyDraft obs p r s now draft = none := by simp [applyDraft, h]
theorem expired_receipt (obs : LocalObservation) (p : Proposal) (r : Receipt) (s : State) (now draft : Nat)
    (h : r.deadline ≤ now) : applyDraft obs p r s now draft = none := by
  have hn : ¬ now < r.deadline := by omega
  simp [applyDraft, hn]
theorem consumed_replay (obs : LocalObservation) (p : Proposal) (r : Receipt) (s : State) (now draft : Nat)
    (h : s.consumed = true) : applyDraft obs p r s now draft = none := by simp [applyDraft, h]
theorem ineligible_rejected (obs : LocalObservation) (p : Proposal) (r : Receipt) (s : State) (now draft : Nat)
    (h : eligible p = false) : applyDraft obs p r s now draft = none := by simp [applyDraft, h]

structure Disclosure where
  owner : Nat
  workspace : Nat
  incarnation : Nat
  payloadHash : Nat
  providerModelConfig : Nat
  purpose : Nat
  rightsTermsPolicy : Nat
  attempt : Nat
  deadline : Nat
  deriving DecidableEq, Repr

def maySend (a : Authority) (b : Binding) (consent requested : Disclosure) (now : Nat) : Bool :=
  live a b now && consent == requested && consent.owner == b.owner &&
  consent.workspace == b.workspace && consent.incarnation == b.incarnation &&
  decide (now < consent.deadline ∧ consent.deadline ≤ a.deadline)

theorem changed_disclosure_denied (a : Authority) (b : Binding) (c request : Disclosure) (now : Nat)
    (h : c ≠ request) : maySend a b c request now = false := by simp [maySend, h]
theorem expired_disclosure_denied (a : Authority) (b : Binding) (c request : Disclosure) (now : Nat)
    (h : c.deadline ≤ now) : maySend a b c request now = false := by
  have hn : ¬ now < c.deadline := by omega
  simp [maySend, hn]
theorem revoked_rights_deny_send (a : Authority) (b : Binding) (c request : Disclosure) (now : Nat)
    (h : a.rights = false) : maySend a b c request now = false := by simp [maySend, live, h]

inductive EvidenceKind where
  | suggestion | schemaChecked | typeComplete | incompleteChecked | boundedSat
  | boundedCounterexample | noCounterexampleWithinBounds | checkedRewrite | leanPolicy
  deriving DecidableEq, Repr
inductive Issuer where
  | model | deterministicVerifier
  deriving DecidableEq, Repr

def mayIssue (issuer : Issuer) (kind : EvidenceKind) : Bool :=
  kind == .suggestion || issuer == .deterministicVerifier

theorem model_cannot_issue_checked (kind : EvidenceKind) (h : kind ≠ .suggestion) :
    mayIssue .model kind = false := by simp [mayIssue, h]

structure Budget where
  used : Nat
  outstanding : Nat
  principalLimit : Nat
  installationUsed : Nat
  installationOutstanding : Nat
  installationLimit : Nat
  tariffKnown : Bool
  deriving DecidableEq, Repr

def reserve (b : Budget) (amount : Nat) : Option Budget :=
  if b.tariffKnown && decide (b.used + b.outstanding + amount ≤ b.principalLimit ∧
      b.installationUsed + b.installationOutstanding + amount ≤ b.installationLimit) then
    some { b with outstanding := b.outstanding + amount, installationOutstanding := b.installationOutstanding + amount }
  else none

theorem reserve_preserves_limits (b next : Budget) (amount : Nat)
    (h : reserve b amount = some next) :
    next.used + next.outstanding ≤ next.principalLimit ∧
    next.installationUsed + next.installationOutstanding ≤ next.installationLimit := by
  unfold reserve at h
  split at h
  · rename_i guard
    simp only [Bool.and_eq_true, decide_eq_true_eq] at guard
    cases Option.some.inj h
    simp only
    omega
  · contradiction

theorem unknown_tariff_denied (b : Budget) (amount : Nat) (h : b.tariffKnown = false) :
    reserve b amount = none := by simp [reserve, h]
theorem principal_over_budget (b : Budget) (amount : Nat)
    (h : b.principalLimit < b.used + b.outstanding + amount) : reserve b amount = none := by
  have hn : ¬ b.used + b.outstanding + amount ≤ b.principalLimit := by omega
  simp [reserve, hn]
theorem installation_over_budget (b : Budget) (amount : Nat)
    (h : b.installationLimit < b.installationUsed + b.installationOutstanding + amount) :
    reserve b amount = none := by
  have hn : ¬ b.installationUsed + b.installationOutstanding + amount ≤ b.installationLimit := by omega
  simp [reserve, hn]
/-- An uncertain dispatch does not release its reservation. -/
def uncertain (b : Budget) : Budget := b
theorem uncertain_retains_reservation (b : Budget) : (uncertain b).outstanding = b.outstanding := rfl

def binding : Binding := ⟨1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11⟩
def authority : Authority := ⟨1, 2, 3, 100, true, true, true⟩
def complete : Proposal := ⟨binding, .typedEdit, .complete, .typed, 12, true, true⟩
def incomplete : Proposal := ⟨binding, .sourceEdit, .incomplete, .typed, 12, true, true⟩
def receipt : Receipt := ⟨binding, .typedEdit, 12, 50⟩
def state : State := ⟨binding, 42, 8, false⟩
theorem complete_approval_positive : approve authority complete binding 1 50 = some receipt := by decide
theorem incomplete_approval_positive : approve authority incomplete binding 1 50 = some ⟨binding, .sourceEdit, 12, 50⟩ := by decide
theorem draft_apply_positive : (applyDraft ⟨false⟩ complete receipt state 1 12).isSome = true := by decide
/-- A server revocation unknown to the client cannot retract delivered content.
    Local draft application remains possible and leaves accepted history intact. -/
theorem unobserved_revocation_local_draft_only :
    (approve { authority with rights := false } complete binding 1 50 = none) ∧
    (∃ t, applyDraft ⟨false⟩ complete receipt state 1 12 = some t ∧
      t.acceptedHistory = state.acceptedHistory) := by
  refine ⟨by decide, ?_⟩
  refine ⟨{ state with current := { binding with draftEpoch := 8, draftHash := 12 }, draftContents := 12, consumed := true }, by decide, by decide⟩
theorem incomplete_contradiction_rejected : eligible { incomplete with contradictionFree := false } = false := by decide
theorem typed_text_only_rejected : eligible { complete with projection := .textOnly } = false := by decide
theorem source_text_only_eligible : eligible { complete with kind := .sourceEdit, projection := .textOnly } = true := by decide
theorem source_text_only_apply_positive :
    (applyDraft ⟨false⟩ { complete with kind := .sourceEdit, projection := .textOnly }
      ⟨binding, .sourceEdit, 12, 50⟩ state 1 12).isSome = true := by decide
theorem explanation_rejected : eligible { complete with kind := .explanation } = false := by decide
theorem budget_positive : (reserve ⟨1, 2, 10, 3, 2, 20, true⟩ 4).isSome = true := by decide

def consent : Disclosure := ⟨1, 2, 3, 21, 22, 23, 24, 1, 50⟩
theorem send_positive : maySend authority binding consent consent 1 = true := by decide

end Allow.AiNativeDevelopment
