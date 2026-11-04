import Std

/- Inactive P1 model. Backend identity, transport closure and observed absence
   are trusted observations supplied to guarded transitions. No theorem proves
   PostgreSQL cancellation, Linux process behavior or adapter correspondence. -/
namespace Allow.ContextCleanup

inductive Phase where
  | vacant | reserved | connecting | keyed | bound | running | retiring | clean | unknown
  deriving DecidableEq, Repr

structure Owner where
  nonce : Nat
  pid : Nat
  startTicks : Nat
  proxyGeneration : Nat
  leaseGeneration : Nat
  deriving DecidableEq, Repr

structure Backend where
  pid : Nat
  startTicks : Nat
  database : Nat
  role : Nat
  proxyGeneration : Nat
  applicationNonce : Nat
  deriving DecidableEq, Repr

/-- The protocol adapter supplies these exact BackendKeyData fields privately. -/
structure KeyData where
  pid : Nat
  cancelSecret : Nat
  deriving DecidableEq, Repr

structure Prelude where
  readOnly : Bool
  repeatableRead : Bool
  statementMillis : Nat
  lockMillis : Nat
  idleMillis : Nat
  deriving DecidableEq, Repr

def GoodPrelude (p : Prelude) : Prop :=
  p.readOnly = true ∧ p.repeatableRead = true ∧
  p.statementMillis = 1500 ∧ p.lockMillis = 250 ∧ p.idleMillis = 1000

inductive RetirementReason where
  | timeout | cancelRequested | cancelAcknowledged | eof | failure
  deriving DecidableEq, Repr

structure Receipt where
  owner : Owner
  successPermitted : Bool
  deriving DecidableEq, Repr

structure Lease where
  phase : Phase
  owner : Owner
  attempted : Bool
  backendKey : Option KeyData
  backend : Option Backend
  prelude : Option Prelude
  transportClosed : Bool
  absent : Option Backend
  ran : Bool
  staged : Bool
  poisoned : Bool
  receipt : Option Receipt
  durable : Nat
  deriving DecidableEq, Repr

def vacant (durable : Nat) : Lease :=
  ⟨.vacant, ⟨0, 0, 0, 0, 0⟩, false, none, none, none, true, none, false, false, false, none, durable⟩

def reserve (s : Lease) (owner : Owner) : Lease :=
  ⟨.reserved, owner, false, none, none, none, true, none, false, false, false, none, s.durable⟩

def markRetiring (s : Lease) (_reason : RetirementReason) : Lease :=
  { s with phase := .retiring, poisoned := true, receipt := none }

def crashState (s : Lease) : Lease :=
  { s with phase := .unknown, poisoned := true, receipt := none }

/-- Absence must identify the exact durable backend tuple; an EOF is insufficient. -/
def CleanupSafe (s : Lease) : Prop :=
  s.transportClosed = true ∧
  (s.attempted = false ∨ ∃ b, s.backend = some b ∧ s.absent = some b)

def BoundPrelude (s : Lease) : Prop :=
  ∃ k b p, s.backendKey = some k ∧ s.backend = some b ∧ k.pid = b.pid ∧
    b.proxyGeneration = s.owner.proxyGeneration ∧ b.applicationNonce = s.owner.nonce ∧
    s.prelude = some p ∧ GoodPrelude p

inductive Step : Lease → Lease → Prop where
  | reserve (s : Lease) (free : s.phase = .vacant) (owner : Owner)
      (fresh : owner.leaseGeneration = s.owner.leaseGeneration + 1) : Step s (reserve s owner)
  | connect (s : Lease) (reserved : s.phase = .reserved) (noReceipt : s.receipt = none)
      (unrun : s.ran = false) (unstaged : s.staged = false) :
      Step s { s with phase := .connecting, attempted := true, transportClosed := false }
  | key (s : Lease) (connecting : s.phase = .connecting) (keyData : KeyData)
      (noReceipt : s.receipt = none) (unrun : s.ran = false) :
      Step s { s with phase := .keyed, backendKey := some keyData }
  | bind (s : Lease) (keyed : s.phase = .keyed) (backend : Backend)
      (keyData : KeyData) (keyBound : s.backendKey = some keyData) (samePid : keyData.pid = backend.pid)
      (sameProxy : backend.proxyGeneration = s.owner.proxyGeneration) (sameNonce : backend.applicationNonce = s.owner.nonce)
      (noReceipt : s.receipt = none) (unrun : s.ran = false) :
      Step s { s with phase := .bound, backend := some backend }
  | prelude (s : Lease) (bound : s.phase = .bound) (p : Prelude) (valid : GoodPrelude p)
      (noReceipt : s.receipt = none) (unrun : s.ran = false) :
      Step s { s with prelude := some p }
  | run (s : Lease) (bound : s.phase = .bound) (ready : BoundPrelude s)
      (noReceipt : s.receipt = none) : Step s { s with phase := .running, ran := true }
  | stage (s : Lease) (running : s.phase = .running) (ran : s.ran = true) :
      Step s { s with phase := .retiring, staged := true }
  | retire (s : Lease) (live : s.phase ≠ .vacant) (reason : RetirementReason) : Step s (markRetiring s reason)
  | crash (s : Lease) (live : s.phase ≠ .vacant) : Step s (crashState s)
  | close (s : Lease) (retiring : s.phase = .retiring ∨ s.phase = .unknown) :
      Step s { s with transportClosed := true }
  | absent (s : Lease) (retiring : s.phase = .retiring ∨ s.phase = .unknown)
      (owner : Owner) (sameOwner : owner = s.owner) (observed : Backend)
      (sameBackend : s.backend = some observed) : Step s { s with absent := some observed }
  | clean (s : Lease) (retiring : s.phase = .retiring ∨ s.phase = .unknown) (observed : CleanupSafe s) :
      Step s { s with phase := .clean, receipt := some ⟨s.owner, !s.poisoned⟩ }
  | release (s : Lease) (clean : s.phase = .clean) : Step s { s with phase := .vacant }

inductive Reachable (durable : Nat) : Lease → Prop where
  | initial : Reachable durable (vacant durable)
  | next {s t : Lease} : Reachable durable s → Step s t → Reachable durable t

def Invariant (s : Lease) : Prop :=
  (s.ran = true → BoundPrelude s) ∧ (s.staged = true → s.ran = true) ∧
  (∀ r, s.receipt = some r → r.owner = s.owner ∧ CleanupSafe s ∧ r.successPermitted = !s.poisoned) ∧
  (s.phase = .clean → ∃ r, s.receipt = some r)

theorem step_preserves_invariant {s t : Lease} (safe : Invariant s)
    (transition : Step s t) : Invariant t := by
  cases transition <;> simp_all [Invariant, reserve, markRetiring, crashState, CleanupSafe, BoundPrelude]

theorem reachable_invariant {durable : Nat} {s : Lease} (reachable : Reachable durable s) :
    Invariant s := by
  induction reachable with
  | initial => simp [Invariant, vacant]
  | next previous transition ih => exact step_preserves_invariant ih transition

theorem application_sql_requires_bound_prelude {durable : Nat} {s : Lease}
    (reachable : Reachable durable s) (ran : s.ran = true) : BoundPrelude s :=
  (reachable_invariant reachable).1 ran

theorem new_application_sql_requires_bound_phase {s t : Lease} (transition : Step s t)
    (unrun : s.ran = false) (ran : t.ran = true) : s.phase = .bound ∧ BoundPrelude s := by
  cases transition <;> simp_all [reserve, markRetiring, crashState]

theorem staged_context_requires_application_sql {durable : Nat} {s : Lease}
    (reachable : Reachable durable s) (staged : s.staged = true) : s.ran = true :=
  (reachable_invariant reachable).2.1 staged

theorem receipt_proves_matching_cleanup {durable : Nat} {s : Lease} {r : Receipt}
    (reachable : Reachable durable s) (receipt : s.receipt = some r) :
    r.owner = s.owner ∧ CleanupSafe s ∧ r.successPermitted = !s.poisoned :=
  (reachable_invariant reachable).2.2.1 r receipt

theorem reachable_clean_has_receipt {durable : Nat} {s : Lease}
    (reachable : Reachable durable s) (clean : s.phase = .clean) : ∃ r, s.receipt = some r :=
  (reachable_invariant reachable).2.2.2 clean

theorem reachable_clean_is_safe {durable : Nat} {s : Lease}
    (reachable : Reachable durable s) (clean : s.phase = .clean) : CleanupSafe s := by
  obtain ⟨r, receipt⟩ := reachable_clean_has_receipt reachable clean
  exact (receipt_proves_matching_cleanup reachable receipt).2.1

theorem release_requires_clean {s t : Lease} (transition : Step s t)
    (free : t.phase = .vacant) : s.phase = .clean := by
  cases transition <;> simp_all [reserve, markRetiring, crashState]

theorem release_requires_observed_cleanup {durable : Nat} {s t : Lease}
    (reachable : Reachable durable s) (transition : Step s t) (free : t.phase = .vacant) :
    CleanupSafe s := reachable_clean_is_safe reachable (release_requires_clean transition free)

theorem step_preserves_durable {s t : Lease} (transition : Step s t) :
    t.durable = s.durable := by cases transition <;> rfl

theorem advisory_cleanup_preserves_durable {durable : Nat} {s : Lease}
    (reachable : Reachable durable s) : s.durable = durable := by
  induction reachable with
  | initial => rfl
  | next previous transition ih => exact (step_preserves_durable transition).trans ih

def occupied (s : Lease) : Nat := if s.phase = .vacant then 0 else 1

theorem context_lease_at_most_one (s : Lease) : occupied s ≤ 1 := by
  simp [occupied]; split <;> omega

theorem unknown_retains_capacity (s : Lease) (unknown : s.phase = .unknown) :
    occupied s = 1 := by simp [occupied, unknown]

theorem nonfree_retains_capacity (s : Lease) (nonfree : s.phase ≠ .vacant) :
    occupied s = 1 := by simp [occupied, nonfree]

theorem replacement_requires_vacant {s t : Lease} (transition : Step s t)
    (reserved : t.phase = .reserved) : s.phase = .vacant := by
  cases transition <;> simp_all [reserve, markRetiring, crashState]

theorem unknown_cannot_be_replaced {s t : Lease} (transition : Step s t)
    (unknown : s.phase = .unknown) : t.phase ≠ .reserved := by
  intro replacement
  have free := replacement_requires_vacant transition replacement
  simp_all

theorem unidentified_attempt_cannot_be_clean (s : Lease)
    (attempted : s.attempted = true) (unidentified : s.backend = none) : ¬ CleanupSafe s := by
  simp [CleanupSafe, attempted, unidentified]

theorem closed_transport_alone_is_insufficient (s : Lease)
    (attempted : s.attempted = true) (unobserved : s.absent = none) : ¬ CleanupSafe s := by
  simp [CleanupSafe, attempted, unobserved]

theorem timeout_ack_or_eof_never_proves_cleanup (s : Lease) (reason : RetirementReason) :
    CleanupSafe (markRetiring s reason) ↔ CleanupSafe s := Iff.rfl

def acceptReceipt (expected : Owner) (r : Receipt) : Bool := decide (r.owner = expected)

theorem stale_receipt_rejected (expected : Owner) (r : Receipt) (stale : r.owner ≠ expected) :
    acceptReceipt expected r = false := by simp [acceptReceipt, stale]

theorem accepted_receipt_exact_owner {expected : Owner} {r : Receipt}
    (accepted : acceptReceipt expected r = true) : r.owner = expected := by
  simpa [acceptReceipt] using accepted

theorem stale_lease_generation_rejected (expected : Owner) (r : Receipt)
    (stale : r.owner.leaseGeneration ≠ expected.leaseGeneration) :
    acceptReceipt expected r = false := by
  apply stale_receipt_rejected
  intro same
  exact stale (congrArg Owner.leaseGeneration same)

def contextOK (s : Lease) (r : Receipt) : Prop :=
  s.staged = true ∧ s.receipt = some r ∧ acceptReceipt s.owner r = true ∧
  r.successPermitted = true ∧ s.poisoned = false

theorem context_ok_requires_cleanup {durable : Nat} {s : Lease} {r : Receipt}
    (reachable : Reachable durable s) (ok : contextOK s r) : CleanupSafe s :=
  (receipt_proves_matching_cleanup reachable ok.2.1).2.1

theorem context_ok_requires_staged_unpoisoned_success {s : Lease} {r : Receipt}
    (ok : contextOK s r) : s.staged = true ∧ r.successPermitted = true ∧ s.poisoned = false :=
  ⟨ok.1, ok.2.2.2.1, ok.2.2.2.2⟩

/-- Conditional arithmetic only: a live-handler bound does not bound surviving
    ordinary PostgreSQL backends or guarantee an available observer/context slot. -/
theorem conditional_postgresql_capacity_arithmetic (ordinaryBackends contextBackends observerBackends : Nat)
    (ordinaryBound : ordinaryBackends ≤ 15) (contextBound : contextBackends ≤ 1)
    (observerBound : observerBackends ≤ 1) :
    ordinaryBackends + contextBackends + observerBackends ≤ 20 - 3 := by omega

def witnessOwner : Owner := ⟨71, 100, 400, 2, 1⟩
def witnessBackend : Backend := ⟨101, 401, 9, 10, 2, 71⟩
def witnessKey : KeyData := ⟨101, 99⟩
def witnessPrelude : Prelude := ⟨true, true, 1500, 250, 1000⟩
def w0 : Lease := vacant 42
def w1 : Lease := reserve w0 witnessOwner
def w2 : Lease := { w1 with phase := .connecting, attempted := true, transportClosed := false }
def w3 : Lease := { w2 with phase := .keyed, backendKey := some witnessKey }
def w4 : Lease := { w3 with phase := .bound, backend := some witnessBackend }
def w5 : Lease := { w4 with prelude := some witnessPrelude }
def w6 : Lease := { w5 with phase := .running, ran := true }
def w7 : Lease := { w6 with phase := .retiring, staged := true }
def w8 : Lease := { w7 with transportClosed := true }
def w9 : Lease := { w8 with absent := some witnessBackend }
def w10 : Lease := { w9 with phase := .clean, receipt := some ⟨witnessOwner, true⟩ }
def wUnknown : Lease := crashState w2

theorem normal_cleanup_witness : Reachable 42 w10 ∧ contextOK w10 ⟨witnessOwner, true⟩ := by
  have a : Reachable 42 w0 := Reachable.initial
  have b : Reachable 42 w1 := Reachable.next a (Step.reserve w0 rfl witnessOwner rfl)
  have c : Reachable 42 w2 := Reachable.next b (Step.connect w1 rfl rfl rfl rfl)
  have d : Reachable 42 w3 := Reachable.next c (Step.key w2 rfl witnessKey rfl rfl)
  have e : Reachable 42 w4 := Reachable.next d (Step.bind w3 rfl witnessBackend witnessKey rfl rfl rfl rfl rfl rfl)
  have valid : GoodPrelude witnessPrelude := by simp [GoodPrelude, witnessPrelude]
  have f : Reachable 42 w5 := Reachable.next e (Step.prelude w4 rfl witnessPrelude valid rfl rfl)
  have bound : BoundPrelude w5 := ⟨witnessKey, witnessBackend, witnessPrelude, rfl, rfl, rfl, rfl, rfl, rfl, valid⟩
  have g : Reachable 42 w6 := Reachable.next f (Step.run w5 rfl bound rfl)
  have h : Reachable 42 w7 := Reachable.next g (Step.stage w6 rfl rfl)
  have i : Reachable 42 w8 := Reachable.next h (Step.close w7 (Or.inl rfl))
  have j : Reachable 42 w9 := Reachable.next i (Step.absent w8 (Or.inl rfl) witnessOwner rfl witnessBackend rfl)
  have clean : CleanupSafe w9 := ⟨rfl, Or.inr ⟨witnessBackend, rfl, rfl⟩⟩
  exact ⟨Reachable.next j (Step.clean w9 (Or.inl rfl) clean),
    by simp [contextOK, w10, w9, w8, w7, w6, w5, w4, w3, w2, w1, reserve, acceptReceipt]⟩

theorem unidentified_crash_witness :
    Reachable 42 wUnknown ∧ occupied wUnknown = 1 ∧ ¬ CleanupSafe wUnknown := by
  have a : Reachable 42 w0 := Reachable.initial
  have b : Reachable 42 w1 := Reachable.next a (Step.reserve w0 rfl witnessOwner rfl)
  have c : Reachable 42 w2 := Reachable.next b (Step.connect w1 rfl rfl rfl rfl)
  have d : Reachable 42 wUnknown := Reachable.next c (Step.crash w2 (by decide))
  exact ⟨d, rfl, by simp [CleanupSafe, wUnknown, crashState, w2, w1, reserve]⟩

end Allow.ContextCleanup
