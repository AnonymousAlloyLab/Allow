import Std

/- Finite workflow policy. Identity, payload hashes, grants, clock, verifier,
   durable journal and host authority are trusted observations, not proved
   implementations. No proof of LangGraph/Python refinement, exactly-once
   billing, network behavior, sandbox isolation, or real provider pricing. -/
namespace Allow.AiLangGraphImplementation

inductive Phase where
  | awaitingConsent | dispatched | reviewReady | suggestion | invalid | terminal
  deriving DecidableEq, Repr
inductive Verification where
  | validSource | explanation | deterministicInvalid | unavailable | authDenied
  | budgetDenied | uncertain | malformedEnvelope
  deriving DecidableEq, Repr
structure Consent where
  payload : Nat
  attempt : Nat
  owner : Nat
  deadline : Nat
  deriving DecidableEq, Repr
structure State where
  phase : Phase
  owner : Nat
  calls : Nat
  usedAttempts : List Nat
  reserved : Nat
  history : Nat
  deriving DecidableEq, Repr

/-- A synthetic fixture grant and a user grant both arrive as trusted exact
    consent. The host alone establishes the special fixture grant's scope. -/
def dispatch (s : State) (consent : Consent) (payload attempt now cost limit : Nat)
    (authorized durable : Bool) : Option State :=
  if s.phase == .awaitingConsent && authorized && durable && consent.owner == s.owner &&
      consent.payload == payload && consent.attempt == attempt && decide (now < consent.deadline) &&
      decide (s.calls < 2) && !s.usedAttempts.contains attempt &&
      decide (s.reserved + cost ≤ limit) then
    some { s with phase := .dispatched, calls := s.calls + 1, usedAttempts := attempt :: s.usedAttempts, reserved := s.reserved + cost }
  else none

/-- Reopening an operation after its first recorded dispatch is forbidden.
    Continuing the second call within the exclusive original runner is separate. -/
def reopen (s : State) : Option State :=
  if s.calls == 0 then some s else none

theorem dispatched_operation_cannot_reopen (s : State) (h : 0 < s.calls) :
    reopen s = none := by
  have hn : s.calls ≠ 0 := by omega
  simp [reopen, hn]

def verify (s : State) (v : Verification) : State :=
  if s.phase != .dispatched then s else
  match v with
  | .validSource => { s with phase := .reviewReady }
  | .explanation => { s with phase := .suggestion }
  | .deterministicInvalid =>
    if s.calls < 2 then { s with phase := .awaitingConsent } else { s with phase := .invalid }
  | _ => { s with phase := .terminal }

theorem dispatch_preserves_history (s t : State) (c : Consent) (p a n cost limit : Nat)
    (auth durable : Bool) (h : dispatch s c p a n cost limit auth durable = some t) :
    t.history = s.history := by
  unfold dispatch at h
  split at h
  · cases Option.some.inj h; rfl
  · contradiction

theorem dispatch_call_bound (s t : State) (c : Consent) (p a n cost limit : Nat)
    (auth durable : Bool) (h : dispatch s c p a n cost limit auth durable = some t) :
    t.calls ≤ 2 := by
  unfold dispatch at h
  split at h
  · rename_i guard
    simp only [Bool.and_eq_true, decide_eq_true_eq] at guard
    cases Option.some.inj h
    simp only
    omega
  · contradiction

theorem dispatch_reservation_bound (s t : State) (c : Consent) (p a n cost limit : Nat)
    (auth durable : Bool) (h : dispatch s c p a n cost limit auth durable = some t) :
    t.reserved ≤ limit := by
  unfold dispatch at h
  split at h
  · rename_i guard
    simp only [Bool.and_eq_true, decide_eq_true_eq] at guard
    cases Option.some.inj h
    exact guard.2
  · contradiction

theorem dispatch_records_attempt (s t : State) (c : Consent) (p a n cost limit : Nat)
    (auth durable : Bool) (h : dispatch s c p a n cost limit auth durable = some t) :
    a ∈ t.usedAttempts := by
  unfold dispatch at h
  split at h
  · cases Option.some.inj h; simp
  · contradiction

theorem duplicate_attempt_denied (s : State) (c : Consent) (p a n cost limit : Nat)
    (auth durable : Bool) (h : a ∈ s.usedAttempts) :
    dispatch s c p a n cost limit auth durable = none := by simp [dispatch, h]
theorem changed_payload_denied (s : State) (c : Consent) (p a n cost limit : Nat)
    (auth durable : Bool) (h : c.payload ≠ p) :
    dispatch s c p a n cost limit auth durable = none := by simp [dispatch, h]
theorem different_attempt_needs_consent (s : State) (c : Consent) (p a n cost limit : Nat)
    (auth durable : Bool) (h : c.attempt ≠ a) :
    dispatch s c p a n cost limit auth durable = none := by simp [dispatch, h]
theorem no_durable_intent_no_dispatch (s : State) (c : Consent) (p a n cost limit : Nat)
    (auth : Bool) : dispatch s c p a n cost limit auth false = none := by simp [dispatch]
theorem no_authority_no_dispatch (s : State) (c : Consent) (p a n cost limit : Nat)
    (durable : Bool) : dispatch s c p a n cost limit false durable = none := by simp [dispatch]
theorem limit_two (s : State) (c : Consent) (p a n cost limit : Nat)
    (auth durable : Bool) (h : 2 ≤ s.calls) :
    dispatch s c p a n cost limit auth durable = none := by
  have hn : ¬ s.calls < 2 := by omega
  simp [dispatch, hn]

theorem verify_preserves_history (s : State) (v : Verification) : (verify s v).history = s.history := by
  cases v <;> simp [verify] <;> split <;> simp_all (config := { failIfUnchanged := false }) <;> split <;> rfl

theorem terminal_failures (s : State) (v : Verification) (h : s.phase = .dispatched)
    (bad : v = .unavailable ∨ v = .authDenied ∨ v = .budgetDenied ∨ v = .uncertain ∨ v = .malformedEnvelope) :
    (verify s v).phase = .terminal := by
  rcases bad with r | r | r | r | r <;> subst v <;> simp [verify, h]

theorem unknown_keeps_reservation (s : State) : (verify s .uncertain).reserved = s.reserved := by
  simp [verify]
  split <;> simp_all

theorem second_invalid_terminal (s : State) (h : s.phase = .dispatched) (calls : 2 ≤ s.calls) :
    (verify s .deterministicInvalid).phase = .invalid := by
  have hn : ¬ s.calls < 2 := by omega
  simp [verify, h, hn]

def initial : State := ⟨.awaitingConsent, 1, 0, [], 0, 44⟩
def c1 : Consent := ⟨10, 1, 1, 100⟩
def c2 : Consent := ⟨11, 2, 1, 100⟩
def first : State := ⟨.dispatched, 1, 1, [1], 50, 44⟩
def repair : State := ⟨.awaitingConsent, 1, 1, [1], 50, 44⟩
def second : State := ⟨.dispatched, 1, 2, [2, 1], 100, 44⟩
theorem first_call_positive : dispatch initial c1 10 1 1 50 100 true true = some first := by decide
theorem invalid_opens_consent : verify first .deterministicInvalid = repair := by decide
theorem second_call_positive : dispatch repair c2 11 2 2 50 100 true true = some second := by decide
theorem valid_review_ready : (verify second .validSource).phase = .reviewReady := by decide
theorem twice_invalid : (verify second .deterministicInvalid).phase = .invalid := by decide
theorem explanation_suggestion : (verify first .explanation).phase = .suggestion := by decide
theorem unknown_terminal : (verify first .uncertain).phase = .terminal := by decide

end Allow.AiLangGraphImplementation
