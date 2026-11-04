import Allow.Evidence

namespace Allow.Foundation

def admit (active capacity : Nat) : Option Nat :=
  if active < capacity then some (active + 1) else none

theorem admission_bounded (h : admit active capacity = some next) : next ≤ capacity := by
  unfold admit at h
  split at h
  · simp only [Option.some.injEq] at h
    omega
  · simp at h

inductive Job where
  | running
  | terminal (status : SolverStatus)
  deriving DecidableEq, Repr

def finish (job : Job) (result : SolverStatus) : Job :=
  match job with
  | .running => .terminal result
  | .terminal prior => .terminal prior

theorem terminal_is_final (prior incoming : SolverStatus) :
    finish (.terminal prior) incoming = .terminal prior := rfl

def cancel (job : Job) : Job := finish job .CANCELLED

theorem cancel_is_not_unsat :
    cancel .running = .terminal .CANCELLED ∧
    ∀ incoming, finish (cancel .running) incoming = .terminal .CANCELLED := by
  exact ⟨rfl, fun _ => rfl⟩

structure MethodMetadata where
  lines : Nat
  documented : Bool
  encapsulated : Bool

def acceptable (m : MethodMetadata) : Bool :=
  decide (m.lines ≤ 30 ∧ m.documented = true ∧ m.encapsulated = true)

theorem accepted_style_bounded (h : acceptable m = true) :
    m.lines ≤ 30 ∧ m.documented = true ∧ m.encapsulated = true := by
  simpa [acceptable] using h

example : admit 0 1 = some 1 := by decide
example : admit 1 1 = none := by decide
example : acceptable ⟨31, true, true⟩ = false := by decide

end Allow.Foundation
