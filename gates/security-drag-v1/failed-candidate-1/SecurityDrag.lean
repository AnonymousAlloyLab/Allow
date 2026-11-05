import Std

/- Finite policy supplement only. It does not establish implementation refinement,
   OS race freedom, cryptography, semantic completeness or visual usability. -/
namespace Allow.SecurityDrag

inductive PathClass where
  | root | index | approvedAsset | protected | alias
  deriving DecidableEq, Repr
inductive Method where
  | get | head | other
  deriving DecidableEq, Repr
inductive Bearer where
  | exactValid | absent | invalid | duplicate
  deriving DecidableEq, Repr

structure Http where
  path : PathClass
  method : Method
  bearer : Bearer
  exactHostOrigin : Bool
  forwardedAuthority : Bool
  deriving DecidableEq, Repr

def publicResource (r : Http) : Bool :=
  (r.path == .root || r.path == .index || r.path == .approvedAsset) &&
  (r.method == .get || r.method == .head)
def admitted (r : Http) : Bool :=
  r.path != .alias && r.exactHostOrigin && (publicResource r || r.bearer == .exactValid)

theorem aliases_always_rejected (r : Http) (h : r.path = .alias) : admitted r = false := by
  simp [admitted, h]
theorem public_exception_exact (r : Http) : publicResource r = true ↔
    (r.path = .root ∨ r.path = .index ∨ r.path = .approvedAsset) ∧
    (r.method = .get ∨ r.method = .head) := by
  simp [publicResource]
theorem protected_default_requires_bearer (r : Http) (h : publicResource r = false)
    (pass : admitted r = true) : r.bearer = .exactValid := by
  simpa [admitted, h] using pass.2.2
