import Std

/- Inactive planning model. Guards describe observations a future supervisor
   must establish; Lean does not establish JVM, SQL, cgroup or clock behavior. -/
namespace Allow.PerformancePlan

inductive Phase where
  | vacant | starting | ready | busy | retiring | reaped
  deriving DecidableEq, Repr

structure Worker where
  phase : Phase
  generation : Nat
  consumed : Nat
  staged : Nat
  delivered : Nat
  poisoned : Bool
  durable : Nat
  deriving DecidableEq, Repr

def initial (durable : Nat) : Worker := ⟨.vacant, 0, 0, 0, 0, false, durable⟩

def cancelState (s : Worker) : Worker :=
  { s with phase := if s.phase = .reaped then .reaped else .retiring, poisoned := true }

/-- A generation is a single-use JVM, even when it starts before demand. -/
inductive Step : Worker → Worker → Prop where
  | boot (s : Worker) (vacant : s.phase = .vacant) :
      Step s { s with phase := .starting, generation := s.generation + 1, consumed := 0, staged := 0, delivered := 0, poisoned := false }
  | ready (s : Worker) (starting : s.phase = .starting) :
      Step s { s with phase := .ready }
  | consume (s : Worker) (ready : s.phase = .ready) (unused : s.consumed = 0) :
      Step s { s with phase := .busy, consumed := 1 }
  | stage (s : Worker) (busy : s.phase = .busy) (responseGeneration : Nat)
      (matching : responseGeneration = s.generation) :
      Step s { s with phase := .retiring, staged := 1 }
  | cancel (s : Worker) (live : s.phase ≠ .vacant) : Step s (cancelState s)
  | reap (s : Worker) (retiring : s.phase = .retiring) (observedGeneration : Nat)
      (owned : observedGeneration = s.generation) :
      Step s { s with phase := .reaped }
  | deliver (s : Worker) (reaped : s.phase = .reaped) (responseGeneration : Nat)
      (matching : responseGeneration = s.generation) (clean : s.poisoned = false)
      (complete : s.staged = 1) (undelivered : s.delivered = 0) :
      Step s { s with delivered := 1 }
  | release (s : Worker) (reaped : s.phase = .reaped) :
      Step s { s with phase := .vacant }

inductive Reachable (durable : Nat) : Worker → Prop where
  | initial : Reachable durable (initial durable)
  | next {s t : Worker} : Reachable durable s → Step s t → Reachable durable t

inductive Trace : Worker → Worker → Prop where
  | initial (s : Worker) : Trace s s
  | next {s middle t : Worker} : Trace s middle → Step middle t → Trace s t

def Invariant (s : Worker) : Prop :=
  s.consumed ≤ 1 ∧ s.staged ≤ s.consumed ∧ s.delivered ≤ s.staged ∧
  (s.phase = .starting ∨ s.phase = .ready → s.consumed = 0) ∧
  (s.phase = .busy → s.consumed = 1 ∧ s.staged = 0)

theorem step_preserves_invariant {s t : Worker} (safe : Invariant s)
    (transition : Step s t) : Invariant t := by
  cases transition <;> simp_all [Invariant, cancelState]
  all_goals first | omega | (split <;> simp_all)

theorem reachable_invariant {durable : Nat} {s : Worker}
    (reachable : Reachable durable s) : Invariant s := by
  induction reachable with
  | initial => simp [Invariant, initial]
  | next previous transition ih => exact step_preserves_invariant ih transition

theorem one_request_per_generation {durable : Nat} {s : Worker}
    (reachable : Reachable durable s) : s.consumed ≤ 1 :=
  (reachable_invariant reachable).1

theorem staging_requires_consumption {durable : Nat} {s : Worker}
    (reachable : Reachable durable s) : s.staged ≤ s.consumed :=
  (reachable_invariant reachable).2.1

theorem delivery_requires_staging {durable : Nat} {s : Worker}
    (reachable : Reachable durable s) : s.delivered ≤ s.staged :=
  (reachable_invariant reachable).2.2.1

theorem ready_is_unconsumed {durable : Nat} {s : Worker}
    (reachable : Reachable durable s) (ready : s.phase = .ready) : s.consumed = 0 :=
  (reachable_invariant reachable).2.2.2.1 (Or.inr ready)

theorem step_preserves_durable {s t : Worker} (transition : Step s t) :
    t.durable = s.durable := by cases transition <;> rfl

theorem advisory_never_mutates_durable {durable : Nat} {s : Worker}
    (reachable : Reachable durable s) : s.durable = durable := by
  induction reachable with
  | initial => rfl
  | next previous transition ih => exact (step_preserves_durable transition).trans ih

theorem retirement_cannot_resume {s t : Worker} (transition : Step s t)
    (retiring : s.phase = .retiring) : t.phase = .retiring ∨ t.phase = .reaped := by
  cases transition <;> simp_all [cancelState]

theorem release_requires_reaping {s t : Worker} (transition : Step s t)
    (released : t.phase = .vacant) : s.phase = .reaped := by
  cases transition <;> simp_all [cancelState]
  split at released <;> simp_all

theorem staging_requires_busy {s t : Worker} (transition : Step s t)
    (more : s.staged < t.staged) : s.phase = .busy := by
  cases transition <;> simp_all [cancelState] <;> omega

theorem delivery_requires_reaped {s t : Worker} (transition : Step s t)
    (more : s.delivered < t.delivered) : s.phase = .reaped := by
  cases transition <;> simp_all [cancelState] <;> omega

theorem poison_sticky_in_generation {s t : Worker} (transition : Step s t)
    (poisoned : s.poisoned = true) (sameGeneration : t.generation = s.generation) :
    t.poisoned = true := by
  cases transition <;> simp_all [cancelState] <;> omega

theorem poison_prevents_delivery_in_generation {s t : Worker} (transition : Step s t)
    (poisoned : s.poisoned = true) (sameGeneration : t.generation = s.generation) :
    t.delivered = s.delivered := by
  cases transition <;> simp_all [cancelState] <;> omega

theorem step_generation_monotone {s t : Worker} (transition : Step s t) :
    s.generation ≤ t.generation := by
  cases transition <;> simp [cancelState]

theorem trace_generation_monotone {s t : Worker} (history : Trace s t) :
    s.generation ≤ t.generation := by
  induction history with
  | initial => exact Nat.le_refl _
  | next previous transition ih => exact Nat.le_trans ih (step_generation_monotone transition)

theorem poisoned_trace_cannot_deliver {s t : Worker} (history : Trace s t)
    (poisoned : s.poisoned = true) (sameGeneration : t.generation = s.generation) :
    t.poisoned = true ∧ t.delivered = s.delivered := by
  induction history with
  | initial => exact ⟨poisoned, rfl⟩
  | @next middle finish previous transition ih =>
    have before := trace_generation_monotone previous
    have after := step_generation_monotone transition
    have middleGeneration : middle.generation = s.generation := by omega
    have lastGeneration : finish.generation = middle.generation := by omega
    have middleSafe := ih middleGeneration
    exact ⟨poison_sticky_in_generation transition middleSafe.1 lastGeneration,
      (poison_prevents_delivery_in_generation transition middleSafe.1 lastGeneration).trans middleSafe.2⟩

theorem generation_increases_only_at_boot {s t : Worker} (transition : Step s t)
    (changed : t.generation ≠ s.generation) :
    s.phase = .vacant ∧ t.generation = s.generation + 1 := by
  cases transition <;> simp_all [cancelState]

/-- The response gate is explicit; generation identity is not inferred from process age. -/
def stageReply (s : Worker) (responseGeneration : Nat) : Option Worker :=
  if s.phase = .busy ∧ responseGeneration = s.generation then
    some { s with phase := .retiring, staged := 1 }
  else none

theorem stale_generation_rejected (s : Worker) (responseGeneration : Nat)
    (stale : responseGeneration ≠ s.generation) :
    stageReply s responseGeneration = none := by simp [stageReply, stale]

theorem staged_reply_is_guarded_step {s t : Worker} {responseGeneration : Nat}
    (staged : stageReply s responseGeneration = some t) : Step s t := by
  unfold stageReply at staged
  split at staged
  next valid =>
    simp only [Option.some.injEq] at staged
    subst t
    exact Step.stage s valid.1 responseGeneration valid.2
  next invalid => contradiction

def deliverReply (s : Worker) (responseGeneration : Nat) : Option Worker :=
  if s.phase = .reaped ∧ responseGeneration = s.generation ∧ s.poisoned = false ∧
      s.staged = 1 ∧ s.delivered = 0 then
    some { s with delivered := 1 }
  else none

theorem cancelled_reply_never_delivered (s : Worker) (responseGeneration : Nat) :
    deliverReply (cancelState s) responseGeneration = none := by
  simp [deliverReply, cancelState]

theorem delivered_reply_is_guarded_step {s t : Worker} {responseGeneration : Nat}
    (delivered : deliverReply s responseGeneration = some t) : Step s t := by
  unfold deliverReply at delivered
  split at delivered
  next valid =>
    simp only [Option.some.injEq] at delivered
    subst t
    exact Step.deliver s valid.1 responseGeneration valid.2.1 valid.2.2.1 valid.2.2.2.1 valid.2.2.2.2
  next invalid => contradiction

def occupied (s : Worker) : Nat := if s.phase = .vacant then 0 else 1

/-- Two fixed logical slots; real process-tree registration remains a runtime obligation. -/
structure Pool where
  first : Worker
  second : Worker

def liveSlots (p : Pool) : Nat := occupied p.first + occupied p.second

theorem live_pool_bound (p : Pool) : liveSlots p ≤ 2 := by
  simp only [liveSlots, occupied]
  split <;> split <;> omega

theorem idle_warm_occupies_slot (s : Worker) (ready : s.phase = .ready) :
    occupied s = 1 := by simp [occupied, ready]

inductive DatabasePhase where
  | active | cancelling | terminated | free
  deriving DecidableEq, Repr

structure DatabaseLease where
  phase : DatabasePhase
  ownerGeneration : Nat
  durable : Nat
  deriving DecidableEq, Repr

/-- Timeout initiates cleanup; it never constitutes observed backend termination. -/
def timeout (s : DatabaseLease) : DatabaseLease := { s with phase := .cancelling }

def releaseDatabase (s : DatabaseLease) (observedOwner : Nat) : Option DatabaseLease :=
  if s.phase = .terminated ∧ observedOwner = s.ownerGeneration then
    some { s with phase := .free }
  else none

theorem timeout_cannot_release (s : DatabaseLease) (owner : Nat) :
    releaseDatabase (timeout s) owner = none := by simp [releaseDatabase, timeout]

theorem database_release_requires_observation {s t : DatabaseLease} {owner : Nat}
    (released : releaseDatabase s owner = some t) :
    s.phase = .terminated ∧ owner = s.ownerGeneration := by
  unfold releaseDatabase at released
  split at released
  next yes => exact yes
  next no => contradiction

theorem timeout_preserves_durable (s : DatabaseLease) :
    (timeout s).durable = s.durable := rfl

structure Run where
  p95Micros : Nat
  failures : Nat
  measured : Nat
  warmups : Nat
  profileMatches : Bool
  deriving DecidableEq, Repr

def RunPass (r : Run) : Prop :=
  r.p95Micros < 300000 ∧ r.failures = 0 ∧ r.measured = 1000 ∧
  r.warmups = 100 ∧ r.profileMatches = true

def SeriesPass (runs : List Run) : Prop := runs.length ≥ 3 ∧ ∀ r ∈ runs, RunPass r

theorem acceptance_requires_three_runs {runs : List Run} (accepted : SeriesPass runs) :
    runs.length ≥ 3 := accepted.1

theorem every_accepted_run_meets_target {runs : List Run} {r : Run}
    (accepted : SeriesPass runs) (member : r ∈ runs) : r.p95Micros < 300000 :=
  (accepted.2 r member).1

theorem observed_slow_run_rejects_series {runs : List Run} {r : Run}
    (member : r ∈ runs) (slow : 300000 ≤ r.p95Micros) : ¬ SeriesPass runs := by
  intro accepted
  have fast := every_accepted_run_meets_target accepted member
  omega

def witnessStart : Worker := initial 42
def witnessBoot : Worker := ⟨.starting, 1, 0, 0, 0, false, 42⟩
def witnessReady : Worker := ⟨.ready, 1, 0, 0, 0, false, 42⟩
def witnessBusy : Worker := ⟨.busy, 1, 1, 0, 0, false, 42⟩
def witnessRetiring : Worker := ⟨.retiring, 1, 1, 1, 0, false, 42⟩
def witnessReaped : Worker := ⟨.reaped, 1, 1, 1, 0, false, 42⟩
def witnessDelivered : Worker := ⟨.reaped, 1, 1, 1, 1, false, 42⟩

theorem successful_one_use_witness : Reachable 42 witnessDelivered := by
  have a : Reachable 42 witnessStart := Reachable.initial
  have b : Reachable 42 witnessBoot := Reachable.next a (Step.boot witnessStart rfl)
  have c : Reachable 42 witnessReady := Reachable.next b (Step.ready witnessBoot rfl)
  have d : Reachable 42 witnessBusy := Reachable.next c (Step.consume witnessReady rfl rfl)
  have e : Reachable 42 witnessRetiring := Reachable.next d (Step.stage witnessBusy rfl 1 rfl)
  have f : Reachable 42 witnessReaped := Reachable.next e (Step.reap witnessRetiring rfl 1 rfl)
  exact Reachable.next f (Step.deliver witnessReaped rfl 1 rfl rfl rfl rfl)

theorem accepted_series_witness :
    SeriesPass [⟨200000, 0, 1000, 100, true⟩, ⟨210000, 0, 1000, 100, true⟩,
      ⟨220000, 0, 1000, 100, true⟩] := by
  simp [SeriesPass, RunPass]

end Allow.PerformancePlan
