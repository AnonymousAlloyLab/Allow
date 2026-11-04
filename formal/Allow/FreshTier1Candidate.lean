import Std

/- Inactive finite model. Argument-list equalities are syntactic, not claims
   about JIT semantics, Java output equivalence, OS isolation or measured speed. -/
namespace Allow.FreshTier1

inductive Variant where
  | baseline | tier1
  deriving DecidableEq, Repr

inductive Operation where
  | advisory | durable | solver
  deriving DecidableEq, Repr

/-- Required arguments are an opaque frozen extraction from the actual launcher.
    Runtime correspondence must establish both lists and the insertion boundary. -/
structure RequiredArgs where
  beforeOption : List String
  afterOption : List String
  deriving DecidableEq, Repr

def tier1Flag : String := "-XX:TieredStopAtLevel=1"

def options (operation : Operation) (variant : Variant) : List String :=
  if operation = .advisory ∧ variant = .tier1 then [tier1Flag] else []

def arguments (required : RequiredArgs) (operation : Operation) (variant : Variant) : List String :=
  required.beforeOption ++ options operation variant ++ required.afterOption

theorem advisory_inserts_only_fixed_flag (required : RequiredArgs) :
    arguments required .advisory .tier1 = required.beforeOption ++ [tier1Flag] ++ required.afterOption ∧
    arguments required .advisory .baseline = required.beforeOption ++ required.afterOption := by
  simp [arguments, options]

theorem durable_arguments_unchanged (required : RequiredArgs) (variant : Variant) :
    arguments required .durable variant = arguments required .durable .baseline := by
  simp [arguments, options]

theorem solver_arguments_unchanged (required : RequiredArgs) (variant : Variant) :
    arguments required .solver variant = arguments required .solver .baseline := by
  simp [arguments, options]

theorem argument_delta_exactly_one (required : RequiredArgs) :
    (arguments required .advisory .tier1).length =
      (arguments required .advisory .baseline).length + 1 := by
  simp [arguments, options]
  omega

inductive Phase where
  | fresh | running | retiring | reaped
  deriving DecidableEq, Repr

structure Worker where
  phase : Phase
  identity : Nat
  launches : Nat
  consumed : Nat
  staged : Nat
  delivered : Nat
  poisoned : Bool
  buildChecked : Bool
  solverChecked : Bool
  durable : Nat
  deriving DecidableEq, Repr

def initial (identity durable : Nat) : Worker :=
  ⟨.fresh, identity, 0, 0, 0, 0, false, false, false, durable⟩

def poison (s : Worker) : Worker :=
  { s with poisoned := true, phase := if s.phase = .reaped then .reaped else .retiring }

/-- No transition resets a fresh process owner or accepts a second request. -/
inductive Step : Worker → Worker → Prop where
  | launch (s : Worker) (fresh : s.phase = .fresh) (buildCurrent solverCurrent : Bool)
      (buildPass : buildCurrent = true) (solverPass : solverCurrent = true) :
      Step s { s with phase := .running, launches := 1, consumed := 1,
                      buildChecked := buildCurrent, solverChecked := solverCurrent }
  | stage (s : Worker) (running : s.phase = .running) (responseIdentity : Nat)
      (matching : responseIdentity = s.identity) :
      Step s { s with phase := .retiring, staged := 1 }
  | retire (s : Worker) (launched : s.phase ≠ .fresh) : Step s (poison s)
  | reap (s : Worker) (retiring : s.phase = .retiring) (observedIdentity : Nat)
      (owned : observedIdentity = s.identity) : Step s { s with phase := .reaped }
  | deliver (s : Worker) (reaped : s.phase = .reaped) (responseIdentity : Nat)
      (matching : responseIdentity = s.identity) (clean : s.poisoned = false)
      (complete : s.staged = 1) (undelivered : s.delivered = 0) :
      Step s { s with delivered := 1 }

inductive Reachable (identity durable : Nat) : Worker → Prop where
  | initial : Reachable identity durable (initial identity durable)
  | next {s t : Worker} : Reachable identity durable s → Step s t → Reachable identity durable t

inductive Trace : Worker → Worker → Prop where
  | initial (s : Worker) : Trace s s
  | next {s middle t : Worker} : Trace s middle → Step middle t → Trace s t

def Invariant (s : Worker) : Prop :=
  s.launches ≤ 1 ∧ s.consumed = s.launches ∧ s.staged ≤ s.consumed ∧
  s.delivered ≤ s.staged ∧
  (s.phase = .fresh → s.launches = 0 ∧ s.staged = 0 ∧ s.delivered = 0) ∧
  (s.phase = .running → s.consumed = 1 ∧ s.staged = 0) ∧
  (s.phase ≠ .fresh → s.buildChecked = true ∧ s.solverChecked = true)

theorem step_preserves_invariant {s t : Worker} (safe : Invariant s)
    (transition : Step s t) : Invariant t := by
  cases transition <;> simp_all [Invariant, poison]
  all_goals first | omega | (split <;> simp_all <;> omega)

theorem reachable_invariant {identity durable : Nat} {s : Worker}
    (reachable : Reachable identity durable s) : Invariant s := by
  induction reachable with
  | initial => simp [Invariant, initial]
  | next previous transition ih => exact step_preserves_invariant ih transition

theorem at_most_one_launch_and_request {identity durable : Nat} {s : Worker}
    (reachable : Reachable identity durable s) : s.launches ≤ 1 ∧ s.consumed ≤ 1 := by
  have safe := reachable_invariant reachable
  simp only [Invariant] at safe
  omega

theorem delivery_staging_consumption_order {identity durable : Nat} {s : Worker}
    (reachable : Reachable identity durable s) : s.delivered ≤ s.staged ∧ s.staged ≤ s.consumed := by
  have safe := reachable_invariant reachable
  exact ⟨safe.2.2.2.1, safe.2.2.1⟩

theorem running_requires_both_identity_checks {identity durable : Nat} {s : Worker}
    (reachable : Reachable identity durable s) (running : s.phase = .running) :
    s.buildChecked = true ∧ s.solverChecked = true := by
  exact (reachable_invariant reachable).2.2.2.2.2.2 (by simp [running])

theorem delivery_requires_owned_reap {s t : Worker} (transition : Step s t)
    (more : s.delivered < t.delivered) : s.phase = .reaped := by
  cases transition <;> simp_all [poison] <;> omega

theorem no_return_to_fresh {s t : Worker} (transition : Step s t) : t.phase ≠ .fresh := by
  cases transition <;> simp_all [poison]
  split <;> simp_all

theorem retirement_cannot_resume {s t : Worker} (transition : Step s t)
    (retired : s.phase = .retiring ∨ s.phase = .reaped) :
    t.phase = .retiring ∨ t.phase = .reaped := by
  cases transition <;> simp_all [poison]
  exact Classical.em _ |>.symm

theorem step_preserves_identity_and_durable {s t : Worker} (transition : Step s t) :
    t.identity = s.identity ∧ t.durable = s.durable := by
  cases transition <;> exact ⟨rfl, rfl⟩

theorem reachable_preserves_identity_and_durable {identity durable : Nat} {s : Worker}
    (reachable : Reachable identity durable s) : s.identity = identity ∧ s.durable = durable := by
  induction reachable with
  | initial => exact ⟨rfl, rfl⟩
  | next previous transition ih =>
    have fixed := step_preserves_identity_and_durable transition
    exact ⟨fixed.1.trans ih.1, fixed.2.trans ih.2⟩

theorem step_poison_sticky {s t : Worker} (transition : Step s t)
    (failed : s.poisoned = true) : t.poisoned = true := by
  cases transition <;> simp_all [poison]

theorem poisoned_trace_cannot_deliver {s t : Worker} (trace : Trace s t)
    (failed : s.poisoned = true) : t.poisoned = true ∧ t.delivered = s.delivered := by
  induction trace with
  | initial => exact ⟨failed, rfl⟩
  | next previous transition ih =>
    have sticky := step_poison_sticky transition ih.1
    constructor
    · exact sticky
    · cases transition <;> simp_all [poison]

/-- Values are observations supplied by a future registered runtime verifier.
    Their measurement accuracy and output-equivalence interpretation are excluded. -/
structure Run where
  nodes : Nat
  warmups : Nat
  measured : Nat
  failures : Nat
  p95Micros : Nat
  profileMatches : Bool
  peakBytes : Nat
  pairedBaselineP95Micros : Nat
  deriving DecidableEq, Repr

def RunPass (run : Run) : Prop :=
  run.nodes = 500 ∧ run.warmups = 100 ∧ run.measured = 1000 ∧
  run.failures = 0 ∧ run.p95Micros < 300000 ∧ run.profileMatches = true ∧
  run.peakBytes ≤ 5368709120 ∧ run.p95Micros < run.pairedBaselineP95Micros

def SelectTier1 (wholeResponsesMatch containmentMatch : Bool) (runs : List Run) : Prop :=
  wholeResponsesMatch = true ∧ containmentMatch = true ∧ runs.length = 3 ∧
  ∀ run ∈ runs, RunPass run

theorem selection_requires_complete_comparison {same contained : Bool} {runs : List Run}
    (selected : SelectTier1 same contained runs) : same = true ∧ contained = true :=
  ⟨selected.1, selected.2.1⟩

theorem selection_requires_three_runs {same contained : Bool} {runs : List Run}
    (selected : SelectTier1 same contained runs) : runs.length = 3 := selected.2.2.1

theorem selection_requires_every_run_target {same contained : Bool} {runs : List Run} {run : Run}
    (selected : SelectTier1 same contained runs) (member : run ∈ runs) :
    run.failures = 0 ∧ run.p95Micros < 300000 := by
  have passed := selected.2.2.2 run member
  exact ⟨passed.2.2.2.1, passed.2.2.2.2.1⟩

theorem failed_or_slow_run_blocks_selection {same contained : Bool} {runs : List Run} {run : Run}
    (member : run ∈ runs) (bad : run.failures ≠ 0 ∨ 300000 ≤ run.p95Micros) :
    ¬ SelectTier1 same contained runs := by
  intro selected
  have passed := selection_requires_every_run_target selected member
  omega

def witnessStart : Worker := initial 7 42
def witnessRunning : Worker :=
  ⟨.running, 7, 1, 1, 0, 0, false, true, true, 42⟩
def witnessStaged : Worker := { witnessRunning with phase := .retiring, staged := 1 }
def witnessReaped : Worker := { witnessStaged with phase := .reaped }
def witnessDelivered : Worker := { witnessReaped with delivered := 1 }

theorem successful_fresh_worker_witness :
    Reachable 7 42 witnessDelivered ∧ witnessDelivered.delivered = 1 ∧ witnessDelivered.consumed = 1 := by
  have a : Reachable 7 42 witnessStart := Reachable.initial
  have b : Reachable 7 42 witnessRunning := Reachable.next a (Step.launch _ rfl true true rfl rfl)
  have c : Reachable 7 42 witnessStaged := Reachable.next b (Step.stage _ rfl 7 rfl)
  have d : Reachable 7 42 witnessReaped := Reachable.next c (Step.reap _ rfl 7 rfl)
  exact ⟨Reachable.next d (Step.deliver _ rfl 7 rfl rfl rfl rfl), rfl, rfl⟩

/-- Hypothetical observations establish inhabitation, never measured performance. -/
theorem abstract_selection_witness :
    SelectTier1 true true (List.replicate 3 (Run.mk 500 100 1000 0 240000 true 4000000000 400000)) := by
  simp [SelectTier1, RunPass]

end Allow.FreshTier1
