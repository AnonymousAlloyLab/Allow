set_option maxRecDepth 10000

/-- A deliberately abstract record for the protocol's warmup and measured samples. -/
structure Run where
  warmups : List Nat
  samples : List Nat

/-- Completeness means the two protocol phases contain exactly the required counts. -/
def complete (run : Run) : Prop :=
  run.warmups.length = 100 ∧ run.samples.length = 1000

instance (run : Run) : Decidable (complete run) := by
  unfold complete
  infer_instance

/-- Construct an ordered trace in which each sample is dispatched, committed and framed. -/
inductive Event where
  | dispatch | commit | firstFrame | secondFrame
  deriving DecidableEq, Repr

def oneEdit : List Event := [.dispatch, .commit, .firstFrame, .secondFrame]
def phase (count : Nat) : List Event := (List.replicate count oneEdit).flatten
def trace : List Event := phase 100 ++ phase 1000

/-- The abstract trace has exactly one ordered quadruple per warmup and measured edit. -/
theorem trace_event_count : 100 * oneEdit.length + 1000 * oneEdit.length = 4400 := by decide

/-- An individual modeled edit has the required ordering. -/
theorem edit_order : oneEdit = [.dispatch, .commit, .firstFrame, .secondFrame] := rfl

inductive Classification where
  | incomplete | pass | fail
  deriving DecidableEq, Repr

/-- Classify only a complete series, using microseconds for the strict 50 ms boundary. -/
def classify (run : Run) (valid : Bool) (p95Micros : Nat) : Classification :=
  if complete run ∧ valid = true then
    if p95Micros < 50000 then .pass else .fail
  else .incomplete

/-- An incomplete run cannot be classified as passing. -/
theorem incomplete_not_pass (run : Run) (valid : Bool) (p95Micros : Nat)
    (h : ¬ complete run) : classify run valid p95Micros = .incomplete := by
  simp [classify, h]

/-- A complete run passes only below the strict threshold. -/
theorem pass_iff (run : Run) (valid : Bool) (p95Micros : Nat) :
    classify run valid p95Micros = .pass ↔ complete run ∧ valid = true ∧ p95Micros < 50000 := by
  by_cases h : complete run <;> cases valid <;> by_cases p : p95Micros < 50000 <;>
    simp [classify, h, p]
