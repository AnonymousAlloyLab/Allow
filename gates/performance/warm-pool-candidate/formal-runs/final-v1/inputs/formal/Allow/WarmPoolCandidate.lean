import Std
set_option linter.unusedSimpArgs false

/- Standalone candidate model. Evidence constructors denote trusted adapter
   observations, not proofs of Linux, cgroups, sealed images, Java or SQL. -/
namespace Allow.WarmPool

inductive Phase where
  | vacant | reserved | starting | ready | busy | fresh | retiring | reaped
  deriving DecidableEq, Repr

inductive Event where
  | reserve | attempt | attach | ready | handoff | stage | poison | observe | noSpawn | fence | publish | release
  | freshReserve | freshAttempt | freshAttach | freshRetire
  deriving DecidableEq, Repr

structure Owner where
  epoch : Nat
  slot : Nat
  generation : Nat
  nonce : Nat
  image : Nat
  deriving DecidableEq, Repr

structure CleanContext where
  requestNonce : Nat
  proxyGeneration : Nat
  admittedAt : Nat
  clean : Bool
  successPermitted : Bool
  deriving DecidableEq, Repr

structure Cleanup where
  owner : Owner
  childReaped : Bool
  groupEmpty : Bool
  transportClosed : Bool
  deriving DecidableEq, Repr

structure Worker where
  phase : Phase := .vacant
  owner : Owner
  attempted : Bool := false
  childKnown : Bool := false
  readyBound : Bool := false
  contextClean : Bool := false
  cleanup : Bool := false
  finalFence : Bool := false
  poisoned : Bool := false
  consumed : Nat := 0
  staged : Nat := 0
  delivered : Nat := 0
  requestNonce : Nat := 0
  startDeadline : Nat := 0
  idleDeadline : Nat := 0
  requestDeadline : Nat := 0
  deriving DecidableEq, Repr

def initialWorker (slot : Nat) : Worker := ⟨.vacant, ⟨1, slot, 0, 0, 0⟩, false, false, false,
  false, false, false, false, 0, 0, 0, 0, 0, 0, 0⟩

def unassigned (s : Worker) : Nat := match s.phase with
  | .reserved | .starting | .ready => 1
  | _ => 0

def occupied (s : Worker) : Nat := if s.phase = .vacant then 0 else 1

def active (s : Worker) : Nat := if s.phase ≠ .vacant ∧ s.consumed = 1 then 1 else 0

def poisonState (s : Worker) : Worker :=
  { s with phase := if s.phase = .reaped then .reaped else .retiring, poisoned := true }

def reserved (s : Worker) (now nonce image : Nat) : Worker :=
  { owner := { s.owner with generation := s.owner.generation + 1, nonce := nonce, image := image },
    phase := .reserved, startDeadline := now + 5000 }

/-- Fresh operation results remain outside the warm protocol; only their shared slot is modeled. -/
def freshReserved (s : Worker) (now nonce image : Nat) : Worker :=
  { reserved s now nonce image with phase := .fresh, consumed := 1, poisoned := true }

/-- Each action changes exactly one allocated slot, with the other slot visible atomically. -/
inductive LocalStep (now : Nat) : Event → Worker → Worker → Worker → Prop where
  | reserve (s peer : Worker) (nonce image : Nat) (free : s.phase = .vacant)
      (oneStandby : unassigned peer = 0) : LocalStep now .reserve s peer (reserved s now nonce image)
  | freshReserve (s peer : Worker) (nonce image : Nat) (free : s.phase = .vacant)
      (oneActive : active peer = 0) : LocalStep now .freshReserve s peer (freshReserved s now nonce image)
  | freshAttempt (s peer : Worker) (fresh : s.phase = .fresh) (never : s.attempted = false) :
      LocalStep now .freshAttempt s peer { s with attempted := true }
  | freshAttach (s peer : Worker) (fresh : s.phase = .fresh) (attempted : s.attempted = true)
      (identity : Owner) (owned : identity = s.owner) :
      LocalStep now .freshAttach s peer { s with childKnown := true }
  | freshRetire (s peer : Worker) (fresh : s.phase = .fresh) :
      LocalStep now .freshRetire s peer { s with phase := .retiring }
  | attempt (s peer : Worker) (held : s.phase = .reserved) (inTime : now < s.startDeadline) :
      LocalStep now .attempt s peer { s with phase := .starting, attempted := true }
  | attach (s peer : Worker) (starting : s.phase = .starting) (identity : Owner)
      (owned : identity = s.owner) (inTime : now < s.startDeadline) :
      LocalStep now .attach s peer { s with childKnown := true }
  | ready (s peer : Worker) (starting : s.phase = .starting) (known : s.childKnown = true)
      (identity : Owner) (owned : identity = s.owner) (inTime : now < s.startDeadline) :
      LocalStep now .ready s peer { s with phase := .ready, readyBound := true, idleDeadline := now + 30000 }
  | handoff (s peer : Worker) (ready : s.phase = .ready) (unconsumed : s.consumed = 0)
      (oneActive : active peer = 0) (identity : Owner) (owned : identity = s.owner)
      (currentImage : Nat) (freshBuild : currentImage = s.owner.image)
      (receipt : CleanContext) (requestNonce proxyGeneration : Nat)
      (nonceMatches : receipt.requestNonce = requestNonce) (proxyMatches : receipt.proxyGeneration = proxyGeneration)
      (clean : receipt.clean = true) (permitted : receipt.successPermitted = true)
      (notExpired : now < s.idleDeadline) (admitted : receipt.admittedAt ≤ now)
      (requestTime : now < receipt.admittedAt + 10000) :
      LocalStep now .handoff s peer { s with phase := .busy, consumed := 1, contextClean := true, requestNonce := requestNonce, requestDeadline := receipt.admittedAt + 10000 }
  | stage (s peer : Worker) (busy : s.phase = .busy) (identity : Owner) (owned : identity = s.owner)
      (nonce : Nat) (matching : nonce = s.requestNonce) (inTime : now < s.requestDeadline) :
      LocalStep now .stage s peer { s with phase := .retiring, staged := 1 }
  | poison (s peer : Worker) (held : s.phase ≠ .vacant) : LocalStep now .poison s peer (poisonState s)
  | observe (s peer : Worker) (retiring : s.phase = .retiring) (known : s.childKnown = true)
      (proof : Cleanup) (owned : proof.owner = s.owner) (reaped : proof.childReaped = true)
      (empty : proof.groupEmpty = true) (closed : proof.transportClosed = true) :
      LocalStep now .observe s peer { s with phase := .reaped, cleanup := true }
  | noSpawn (s peer : Worker) (retiring : s.phase = .retiring) (neverAttempted : s.attempted = false)
      (identity : Owner) (owned : identity = s.owner) :
      LocalStep now .noSpawn s peer { s with phase := .reaped, cleanup := true }
  | fence (s peer : Worker) (reaped : s.phase = .reaped) (identity : Owner) (owned : identity = s.owner)
      (currentImage : Nat) (current : currentImage = s.owner.image) (clean : s.poisoned = false)
      (inTime : now < s.requestDeadline) :
      LocalStep now .fence s peer { s with finalFence := true }
  | publish (s peer : Worker) (reaped : s.phase = .reaped) (cleaned : s.cleanup = true)
      (fenced : s.finalFence = true) (identity : Owner) (owned : identity = s.owner)
      (currentImage : Nat) (current : currentImage = s.owner.image)
      (nonce : Nat) (matching : nonce = s.requestNonce) (clean : s.poisoned = false)
      (complete : s.staged = 1) (once : s.delivered = 0) (inTime : now < s.requestDeadline) :
      LocalStep now .publish s peer { s with delivered := 1 }
  | release (s peer : Worker) (reaped : s.phase = .reaped) (cleaned : s.cleanup = true)
      (identity : Owner) (owned : identity = s.owner)
      (resolved : s.poisoned = true ∨ s.delivered = 1 ∨ s.consumed = 0) :
      LocalStep now .release s peer { s with phase := .vacant }

def afterCrash (event : Event) : Prop :=
  event = .poison ∨ event = .observe ∨ event = .noSpawn ∨ event = .release

structure Pool where
  first : Worker := initialWorker 0
  second : Worker := initialWorker 1
  now : Nat := 0
  online : Bool := true
  durable : Nat := 0
  deriving DecidableEq, Repr

def initial : Pool := {}

inductive Step : Pool → Pool → Prop where
  | first (p : Pool) (event : Event) (worker : Worker)
      (allowed : p.online = true ∨ afterCrash event)
      (move : LocalStep p.now event p.first p.second worker) :
      Step p { p with first := worker }
  | second (p : Pool) (event : Event) (worker : Worker)
      (allowed : p.online = true ∨ afterCrash event)
      (move : LocalStep p.now event p.second p.first worker) :
      Step p { p with second := worker }
  | tick (p : Pool) (later : Nat) (monotone : p.now ≤ later) : Step p { p with now := later }
  | crash (p : Pool) : Step p { p with online := false }
  | observedMismatch (p : Pool) (observed expected : Nat) (different : observed ≠ expected) :
      Step p { p with online := false }

inductive Reachable : Pool → Prop where
  | initial : Reachable initial
  | next {p q : Pool} : Reachable p → Step p q → Reachable q

def WorkerSafe (s : Worker) : Prop :=
  s.consumed ≤ 1 ∧ s.staged ≤ s.consumed ∧ s.delivered ≤ s.staged ∧
  (s.phase = .reserved ∨ s.phase = .starting ∨ s.phase = .ready → s.consumed = 0) ∧
  (s.phase = .busy → s.consumed = 1 ∧ s.staged = 0 ∧ s.contextClean = true ∧ s.readyBound = true) ∧
  (s.phase = .ready → s.readyBound = true) ∧
  (s.phase = .reaped → s.cleanup = true)

def Safe (p : Pool) : Prop := WorkerSafe p.first ∧ WorkerSafe p.second ∧
  unassigned p.first + unassigned p.second ≤ 1 ∧ active p.first + active p.second ≤ 1 ∧
  p.first.owner.slot = 0 ∧ p.second.owner.slot = 1

theorem local_preserves_safety {now : Nat} {event : Event} {s peer t : Worker}
    (safe : WorkerSafe s) (step : LocalStep now event s peer t) : WorkerSafe t := by
  cases step <;> simp_all [WorkerSafe, reserved, freshReserved, poisonState]
  all_goals first | omega | (split <;> simp_all)

theorem local_preserves_standby_bound {now : Nat} {event : Event} {s peer t : Worker}
    (bound : unassigned s + unassigned peer ≤ 1) (step : LocalStep now event s peer t) :
    unassigned t + unassigned peer ≤ 1 := by
  cases step <;> simp_all [unassigned, reserved, freshReserved, poisonState]
  all_goals cases h : s.phase <;> simp_all [unassigned] <;> omega

theorem local_preserves_active_bound {now : Nat} {event : Event} {s peer t : Worker}
    (safe : WorkerSafe s) (bound : active s + active peer ≤ 1) (step : LocalStep now event s peer t) :
    active t + active peer ≤ 1 := by
  cases step <;> simp_all [WorkerSafe, active, reserved, freshReserved, poisonState]
  all_goals split <;> simp_all <;> omega

theorem local_slot_unchanged {now : Nat} {event : Event} {s peer t : Worker}
    (step : LocalStep now event s peer t) : t.owner.slot = s.owner.slot := by
  cases step <;> rfl

theorem step_preserves_safety {p q : Pool} (safe : Safe p) (step : Step p q) : Safe q := by
  rcases safe with ⟨first, second, standby, activeBound, firstSlot, secondSlot⟩
  cases step with
  | first event worker allowed move =>
    exact ⟨local_preserves_safety first move, second, local_preserves_standby_bound standby move,
      local_preserves_active_bound first activeBound move, (local_slot_unchanged move).trans firstSlot, secondSlot⟩
  | second event worker allowed move =>
    have standby' : unassigned p.second + unassigned p.first ≤ 1 := by omega
    have active' : active p.second + active p.first ≤ 1 := by omega
    exact ⟨first, local_preserves_safety second move,
      by change unassigned p.first + unassigned worker ≤ 1; have := local_preserves_standby_bound standby' move; omega,
      by change active p.first + active worker ≤ 1; have := local_preserves_active_bound second active' move; omega,
      firstSlot, (local_slot_unchanged move).trans secondSlot⟩
  | tick => exact ⟨first, second, standby, activeBound, firstSlot, secondSlot⟩
  | crash => exact ⟨first, second, standby, activeBound, firstSlot, secondSlot⟩
  | observedMismatch => exact ⟨first, second, standby, activeBound, firstSlot, secondSlot⟩

theorem reachable_safety {p : Pool} (reach : Reachable p) : Safe p := by
  induction reach with
  | initial => simp [Safe, WorkerSafe, initial, initialWorker, unassigned, active]
  | next previous step ih => exact step_preserves_safety ih step

theorem two_live_reservations (p : Pool) : occupied p.first + occupied p.second ≤ 2 := by
  simp only [occupied]; split <;> split <;> omega

theorem at_most_one_unassigned {p : Pool} (reach : Reachable p) :
    unassigned p.first + unassigned p.second ≤ 1 := (reachable_safety reach).2.2.1

theorem at_most_one_assigned {p : Pool} (reach : Reachable p) :
    active p.first + active p.second ≤ 1 := (reachable_safety reach).2.2.2.1

theorem distinct_slot_owners {p : Pool} (reach : Reachable p) : p.first.owner ≠ p.second.owner := by
  have safe := reachable_safety reach
  have leftSlot := safe.2.2.2.2.1
  have rightSlot := safe.2.2.2.2.2
  intro equality
  have slots := congrArg Owner.slot equality
  omega

theorem first_request_count_order {p : Pool} (reach : Reachable p) :
    p.first.delivered ≤ p.first.staged ∧ p.first.staged ≤ p.first.consumed ∧ p.first.consumed ≤ 1 := by
  have safe := (reachable_safety reach).1
  exact ⟨safe.2.2.1, safe.2.1, safe.1⟩

theorem second_request_count_order {p : Pool} (reach : Reachable p) :
    p.second.delivered ≤ p.second.staged ∧ p.second.staged ≤ p.second.consumed ∧ p.second.consumed ≤ 1 := by
  have safe := (reachable_safety reach).2.1
  exact ⟨safe.2.2.1, safe.2.1, safe.1⟩

theorem no_busy_to_ready {now : Nat} {event : Event} {s peer t : Worker}
    (step : LocalStep now event s peer t) (busy : s.phase = .busy) : t.phase ≠ .ready := by
  cases step <;> simp_all [reserved, freshReserved, poisonState]

theorem release_requires_cleanup {now : Nat} {s peer t : Worker}
    (step : LocalStep now .release s peer t) : s.phase = .reaped ∧ s.cleanup = true := by
  cases step; simp_all

def releaseOwned (s : Worker) (identity : Owner) : Option Worker :=
  if identity = s.owner ∧ s.phase = .reaped ∧ s.cleanup = true ∧
      (s.poisoned = true ∨ s.delivered = 1 ∨ s.consumed = 0) then
    some { s with phase := .vacant }
  else none

theorem stale_release_rejected (s : Worker) (identity : Owner) (stale : identity ≠ s.owner) :
    releaseOwned s identity = none := by simp [releaseOwned, stale]

theorem owned_release_refines_step {now : Nat} {s peer t : Worker} {identity : Owner}
    (released : releaseOwned s identity = some t) : LocalStep now .release s peer t := by
  unfold releaseOwned at released
  split at released
  next valid =>
    simp only [Option.some.injEq] at released
    subst t
    exact LocalStep.release s peer valid.2.1 valid.2.2.1 identity valid.1 valid.2.2.2
  next invalid => contradiction

theorem no_spawn_requires_never_attempted {now : Nat} {s peer t : Worker}
    (step : LocalStep now .noSpawn s peer t) : s.attempted = false := by cases step; assumption

theorem attempted_cannot_use_no_spawn {now : Nat} {s peer t : Worker}
    (attempted : s.attempted = true) : ¬ LocalStep now .noSpawn s peer t := by
  intro step; have := no_spawn_requires_never_attempted step; simp_all

theorem publish_requires_exit_fence_and_time {now : Nat} {s peer t : Worker}
    (step : LocalStep now .publish s peer t) :
    s.phase = .reaped ∧ s.cleanup = true ∧ s.finalFence = true ∧ s.poisoned = false ∧ now < s.requestDeadline := by
  cases step; simp_all

theorem poison_prevents_publication {now : Nat} {s peer t : Worker}
    (poisoned : s.poisoned = true) : ¬ LocalStep now .publish s peer t := by
  intro step; have := publish_requires_exit_fence_and_time step; simp_all

theorem poison_sticky_same_generation {now : Nat} {event : Event} {s peer t : Worker}
    (step : LocalStep now event s peer t) (poisoned : s.poisoned = true)
    (same : t.owner.generation = s.owner.generation) : t.poisoned = true := by
  cases step <;> simp_all [reserved, freshReserved, poisonState] <;> omega

theorem attempted_sticky_same_generation {now : Nat} {event : Event} {s peer t : Worker}
    (step : LocalStep now event s peer t) (attempted : s.attempted = true)
    (same : t.owner.generation = s.owner.generation) : t.attempted = true := by
  cases step <;> simp_all [reserved, freshReserved, poisonState] <;> omega

theorem consumption_monotone_same_generation {now : Nat} {event : Event} {s peer t : Worker}
    (step : LocalStep now event s peer t) (same : t.owner.generation = s.owner.generation) :
    s.consumed ≤ t.consumed := by
  cases step <;> simp_all [reserved, freshReserved, poisonState] <;> omega

theorem generation_changes_only_on_vacant_reservation {now : Nat} {event : Event} {s peer t : Worker}
    (step : LocalStep now event s peer t) (changed : t.owner.generation ≠ s.owner.generation) :
    (event = .reserve ∨ event = .freshReserve) ∧ s.phase = .vacant ∧ t.owner.generation = s.owner.generation + 1 := by
  cases step <;> simp_all [reserved, freshReserved, poisonState]

theorem startup_deadline_checked {now : Nat} {s peer t : Worker}
    (step : LocalStep now .ready s peer t) : now < s.startDeadline := by cases step; assumption

theorem idle_deadline_checked {now : Nat} {s peer t : Worker}
    (step : LocalStep now .handoff s peer t) : now < s.idleDeadline := by cases step; assumption

theorem handoff_sets_clean_context {now : Nat} {s peer t : Worker}
    (step : LocalStep now .handoff s peer t) : t.contextClean = true ∧ now < t.requestDeadline := by
  cases step; simp_all

theorem admission_deadline_not_reset {now : Nat} {s peer t : Worker}
    (step : LocalStep now .handoff s peer t) :
    ∃ receipt : CleanContext, receipt.clean = true ∧ receipt.successPermitted = true ∧
      receipt.requestNonce = t.requestNonce ∧ t.requestDeadline = receipt.admittedAt + 10000 ∧ receipt.admittedAt ≤ now := by
  cases step
  refine ⟨_, ?_, ?_, ?_, rfl, ?_⟩ <;> assumption

theorem shutdown_is_absorbing {p q : Pool} (step : Step p q) (offline : p.online = false) : q.online = false := by
  cases step <;> simp_all

theorem shutdown_forbids_publish (p : Pool) (offline : p.online = false) :
    ¬ (p.online = true ∨ afterCrash .publish) := by simp [offline, afterCrash]

theorem offline_step_preserves_delivery {p q : Pool} (step : Step p q) (offline : p.online = false) :
    q.first.delivered = p.first.delivered ∧ q.second.delivered = p.second.delivered := by
  cases step with
  | first event worker allowed move => cases move <;> simp_all [afterCrash, poisonState]
  | second event worker allowed move => cases move <;> simp_all [afterCrash, poisonState]
  | tick => exact ⟨rfl, rfl⟩
  | crash => exact ⟨rfl, rfl⟩
  | observedMismatch => exact ⟨rfl, rfl⟩

theorem time_does_not_release (p : Pool) (later : Nat) :
    occupied ({ p with now := later }.first) + occupied ({ p with now := later }.second) =
      occupied p.first + occupied p.second := rfl

theorem advisory_preserves_durable {p q : Pool} (step : Step p q) : q.durable = p.durable := by
  cases step <;> rfl

private def w0 := initialWorker 0
private def w1 := reserved w0 0 11 99
private def w2 : Worker := { w1 with phase := .starting, attempted := true }
private def w3 : Worker := { w2 with childKnown := true }
private def w4 : Worker := { w3 with phase := .ready, readyBound := true, idleDeadline := 30000 }
private def receipt : CleanContext := ⟨7, 8, 0, true, true⟩
private def w5 : Worker := { w4 with phase := .busy, consumed := 1, contextClean := true, requestNonce := 7, requestDeadline := 10000 }
private def w6 : Worker := { w5 with phase := .retiring, staged := 1 }
private def w7 : Worker := { w6 with phase := .reaped, cleanup := true }
private def w8 : Worker := { w7 with finalFence := true }
private def w9 : Worker := { w8 with delivered := 1 }
private def state (w : Worker) : Pool := { first := w }

private theorem liftFirst {s t : Worker} {event : Event} (reach : Reachable (state s))
    (move : LocalStep 0 event s (initialWorker 1) t) : Reachable (state t) :=
  Reachable.next reach (Step.first (state s) event t (Or.inl rfl) move)

private theorem witnessReady : Reachable (state w4) := by
  have r0 : Reachable (state w0) := Reachable.initial
  have r1 := liftFirst r0 (LocalStep.reserve w0 (initialWorker 1) 11 99 rfl rfl)
  have r2 := liftFirst r1 (LocalStep.attempt w1 (initialWorker 1) rfl (by decide))
  have r3 := liftFirst r2 (LocalStep.attach w2 (initialWorker 1) rfl w2.owner rfl (by decide))
  exact liftFirst r3 (LocalStep.ready w3 (initialWorker 1) rfl rfl w3.owner rfl (by decide))

private theorem witnessBeforePublish : Reachable (state w8) := by
  have r5 := liftFirst witnessReady (LocalStep.handoff w4 (initialWorker 1) rfl rfl rfl w4.owner rfl 99 rfl
    receipt 7 8 rfl rfl rfl rfl (by decide) (by decide) (by decide))
  have r6 := liftFirst r5 (LocalStep.stage w5 (initialWorker 1) rfl w5.owner rfl 7 rfl (by decide))
  have r7 := liftFirst r6 (LocalStep.observe w6 (initialWorker 1) rfl rfl ⟨w6.owner, true, true, true⟩ rfl rfl rfl rfl)
  exact liftFirst r7 (LocalStep.fence w7 (initialWorker 1) rfl w7.owner rfl 99 rfl rfl (by decide))

theorem successful_one_use_witness :
    ∃ p : Pool, Reachable p ∧ p.first.delivered = 1 ∧ p.first.cleanup = true ∧ p.first.contextClean = true := by
  refine ⟨state w9, ?_, rfl, rfl, rfl⟩
  exact liftFirst witnessBeforePublish (LocalStep.publish w8 (initialWorker 1) rfl rfl rfl w8.owner rfl 99 rfl 7 rfl rfl rfl rfl (by decide))

theorem cancellation_after_fence_witness :
    ∃ p : Pool, Reachable p ∧ p.first.phase = .reaped ∧ p.first.finalFence = true ∧
      p.first.poisoned = true ∧ p.first.delivered = 0 ∧
      ∀ t : Worker, ¬ LocalStep p.now .publish p.first p.second t := by
  refine ⟨state (poisonState w8), ?_, rfl, rfl, rfl, rfl, ?_⟩
  · exact liftFirst witnessBeforePublish (LocalStep.poison w8 (initialWorker 1) (by decide))
  · intro t; exact poison_prevents_publication rfl

theorem ready_and_fresh_coexist_witness :
    ∃ p : Pool, Reachable p ∧ occupied p.first + occupied p.second = 2 ∧
      unassigned p.first + unassigned p.second = 1 ∧ active p.first + active p.second = 1 := by
  let fresh := freshReserved (initialWorker 1) 0 12 99
  refine ⟨{ state w4 with second := fresh }, ?_, rfl, rfl, rfl⟩
  exact Reachable.next witnessReady (Step.second (state w4) .freshReserve fresh (Or.inl rfl)
    (LocalStep.freshReserve (initialWorker 1) w4 12 99 rfl rfl))

end Allow.WarmPool
