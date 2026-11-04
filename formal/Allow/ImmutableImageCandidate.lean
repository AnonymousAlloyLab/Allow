import Allow.SqlRouting

namespace Allow.ImmutableImageCandidate
/-- Abstract kernel object, deliberately distinct from a reusable descriptor number. -/
structure Image where
  object : Nat
  bytes : String
  size : Nat
  deriving DecidableEq
structure Pin where
  bytes : String
  size : Nat
  deriving DecidableEq
structure Observation where
  image : Image
  writeSeal : Bool
  growSeal : Bool
  shrinkSeal : Bool
  sealSeal : Bool
  live : Bool

def initialized (p : Pin) (i : Image) : Prop := i.bytes = p.bytes ∧ i.size = p.size

def checked (i : Image) (o : Observation) : Prop :=
  o.image = i ∧ o.live = true ∧ o.writeSeal = true ∧
  o.growSeal = true ∧ o.shrinkSeal = true ∧ o.sealSeal = true

/-- Correspondence to real Linux observations is a runtime/trust obligation. -/
theorem checked_preserves_pin {p : Pin} {i : Image} {o : Observation}
    (hi : initialized p i) (ho : checked i o) :
    o.image.bytes = p.bytes ∧ o.image.size = p.size := by
  rw [ho.1]
  exact hi

theorem closed_denied {i : Image} {o : Observation}
    (h : o.live = false) : ¬ checked i o := by
  intro a
  have b := a.2.1
  rw [h] at b
  cases b

theorem different_object_denied {i : Image} {o : Observation}
    (h : o.image.object ≠ i.object) : ¬ checked i o := by
  intro a
  exact h (congrArg Image.object a.1)

structure CacheEntry where
  generation : Nat
  entry : SqlRouting.CacheEntry

def reuse (generation : Nat) (i : Image) (o : Observation)
    (request : SqlRouting.Request) (entry : CacheEntry) : Prop :=
  checked i o ∧ entry.generation = generation ∧ SqlRouting.cacheReuse request entry.entry

theorem reuse_exact {g : Nat} {i : Image} {o : Observation}
    {q : SqlRouting.Request} {e : CacheEntry} (h : reuse g i o q e) :
    q = e.entry.request ∧ SqlRouting.admitted q e.entry.report :=
  SqlRouting.cache_exact h.2.2

theorem stale_generation_denied {g : Nat} {i : Image} {o : Observation}
    {q : SqlRouting.Request} {e : CacheEntry} (h : e.generation ≠ g) :
    ¬ reuse g i o q e := fun a => h a.2.1

/-- Explicit assumption isolates the kernel preservation premise, not a Lean axiom. -/
theorem stable_image {p : Pin} {before after : Image}
    (h : initialized p before) (kernelPreserves : after = before) : initialized p after := by
  rw [kernelPreserves]
  exact h

inductive Failure where
  | policyDenied
  | parserFailure
  | infrastructureFailure
  deriving DecidableEq

structure Status where
  generation : Nat
  image : Image
  policy : String
  live : Bool

/-- Runtime introspection refers to the pinned image, never a fresh disk hash. -/
def ready (s : Status) : Prop := s.live = true ∧ s.policy = "sql-routing-v7-sealed-image"

theorem stopped_not_ready {s : Status} (h : s.live = false) : ¬ ready s := by
  intro a
  have b := a.1
  rw [h] at b
  cases b

end Allow.ImmutableImageCandidate
