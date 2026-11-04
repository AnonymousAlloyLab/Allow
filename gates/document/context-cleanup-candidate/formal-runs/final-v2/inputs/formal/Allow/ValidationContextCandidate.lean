import Std

/- Candidate model for one immutable scoped database snapshot. PostgreSQL MVCC,
   RLS, JSON decoding, definition extraction and runtime correspondence remain
   explicit trusted/tested boundaries, not conclusions of these propositions. -/
namespace Allow.ValidationContextCandidate

structure Scope where
  principal : Nat
  workspace : Nat
  deriving DecidableEq, Repr

structure Key where
  scope : Scope
  document : Nat
  deriving DecidableEq, Repr

inductive Kind where
  | signature | field | predicate | fact | assertion | command | binder | expression
  deriving DecidableEq, Repr

structure Definition where
  id : Nat
  kind : Kind
  deriving DecidableEq, Repr

structure Artifact where
  revision : Nat
  content : String
  definitions : List Definition
  deriving DecidableEq, Repr

structure Snapshot where
  key : Key
  head : Nat
  history : List Artifact
  deriving DecidableEq, Repr

structure Request where
  key : Key
  base : Nat
  wanted : List Nat
  deriving DecidableEq, Repr

structure Context where
  key : Key
  base : Nat
  headObserved : Nat
  artifact : Artifact
  inventory : List Definition
  deriving DecidableEq, Repr

/-- Identical historical definitions collapse; different kinds remain detectable. -/
def inventory (s : Snapshot) (wanted : List Nat) : List Definition :=
  ((s.history.flatMap Artifact.definitions).filter fun d => d.id ∈ wanted).eraseDups

/-- A conflicting requested ID is rejected instead of choosing an arbitrary kind. -/
def collision (values : List Definition) : Bool :=
  values.any fun left => values.any fun right => left.id == right.id && left.kind != right.kind

/-- Exact immutable base lookup; uniqueness is supplied by the database key model. -/
def baseArtifact (s : Snapshot) (revision : Nat) : Option Artifact :=
  s.history.find? fun a => a.revision == revision

/-- Pure read; there is no mutator, authorization cache or checked-result cache. -/
def readContext (s : Snapshot) (q : Request) : Option Context :=
  if s.key != q.key || s.head < q.base then none
  else match baseArtifact s q.base with
    | none => none
    | some a =>
      let ids := inventory s q.wanted
      if collision ids then none
      else some ⟨q.key, q.base, s.head, a, ids⟩

theorem inventory_membership (s : Snapshot) (wanted : List Nat) (d : Definition) :
    d ∈ inventory s wanted ↔ d ∈ s.history.flatMap Artifact.definitions ∧ d.id ∈ wanted := by
  simp [inventory]

theorem inventory_requested {s : Snapshot} {wanted : List Nat} {d : Definition}
    (h : d ∈ inventory s wanted) : d.id ∈ wanted := (inventory_membership s wanted d).mp h |>.2

theorem inventory_historical {s : Snapshot} {wanted : List Nat} {d : Definition}
    (h : d ∈ inventory s wanted) : ∃ a ∈ s.history, d ∈ a.definitions := by
  have found := (inventory_membership s wanted d).mp h |>.1
  simpa using found

theorem inventory_complete {s : Snapshot} {wanted : List Nat} {d : Definition}
    (owned : d ∈ s.history.flatMap Artifact.definitions) (requested : d.id ∈ wanted) :
    d ∈ inventory s wanted := (inventory_membership s wanted d).mpr ⟨owned, requested⟩

theorem empty_requested_empty (s : Snapshot) : inventory s [] = [] := by
  apply List.eq_nil_iff_forall_not_mem.mpr
  intro d member
  have h := inventory_requested member
  simp at h

theorem foreign_definition_excluded {s : Snapshot} {wanted : List Nat} {d : Definition}
    (h : d ∉ s.history.flatMap Artifact.definitions) : d ∉ inventory s wanted := by
  intro accepted
  exact h ((inventory_membership s wanted d).mp accepted).1

theorem collision_detected {values : List Definition} {left right : Definition}
    (hl : left ∈ values) (hr : right ∈ values) (same : left.id = right.id)
    (different : left.kind ≠ right.kind) : collision values = true := by
  simp only [collision, List.any_eq_true]
  exact ⟨left, hl, right, hr, by simp [same, different]⟩

theorem no_collision_unique_kind {values : List Definition} (clean : collision values = false)
    {left right : Definition} (hl : left ∈ values) (hr : right ∈ values)
    (same : left.id = right.id) : left.kind = right.kind := by
  by_cases sameKind : left.kind = right.kind
  · exact sameKind
  · have found := collision_detected hl hr same sameKind
    rw [clean] at found
    cases found

/-- Complete exact result shape, retained as a useful correspondence obligation. -/
theorem context_exact {s : Snapshot} {q : Request} {c : Context} (h : readContext s q = some c) :
    s.key = q.key ∧ q.base ≤ s.head ∧ baseArtifact s q.base = some c.artifact ∧
    c.key = q.key ∧ c.base = q.base ∧ c.headObserved = s.head ∧
    c.inventory = inventory s q.wanted ∧ collision c.inventory = false := by
  unfold readContext at h
  split at h
  · cases h
  · rename_i allowed
    have guards : s.key = q.key ∧ q.base ≤ s.head := by simpa using allowed
    split at h
    · cases h
    · rename_i a found
      dsimp only at h
      split at h
      · cases h
      · rename_i clean
        cases h
        exact ⟨guards.1, guards.2, found, rfl, rfl, rfl, rfl, by simpa using clean⟩

theorem wrong_scope_denied {s : Snapshot} {q : Request} (h : s.key.scope ≠ q.key.scope) :
    readContext s q = none := by
  have keys : s.key ≠ q.key := fun same => h (congrArg Key.scope same)
  simp [readContext, keys]

theorem wrong_document_denied {s : Snapshot} {q : Request} (h : s.key.document ≠ q.key.document) :
    readContext s q = none := by
  have keys : s.key ≠ q.key := fun same => h (congrArg Key.document same)
  simp [readContext, keys]

theorem future_base_denied {s : Snapshot} {q : Request} (h : s.head < q.base) :
    readContext s q = none := by
  simp [readContext, h]

theorem missing_base_denied {s : Snapshot} {q : Request} (h : baseArtifact s q.base = none) :
    readContext s q = none := by
  simp [readContext, h]

theorem conflicting_inventory_denied {s : Snapshot} {q : Request}
    (h : collision (inventory s q.wanted) = true) : readContext s q = none := by
  unfold readContext
  split
  · rfl
  · cases baseArtifact s q.base <;> simp [h]

theorem returned_base_exact {s : Snapshot} {q : Request} {c : Context} (h : readContext s q = some c) :
    baseArtifact s q.base = some c.artifact := (context_exact h).2.2.1

theorem observed_head_is_snapshot_head {s : Snapshot} {q : Request} {c : Context}
    (h : readContext s q = some c) : c.headObserved = s.head := (context_exact h).2.2.2.2.2.1

theorem returned_inventory_requested {s : Snapshot} {q : Request} {c : Context} {d : Definition}
    (h : readContext s q = some c) (member : d ∈ c.inventory) : d.id ∈ q.wanted := by
  rw [(context_exact h).2.2.2.2.2.2.1] at member
  exact inventory_requested member

theorem returned_inventory_unique {s : Snapshot} {q : Request} {c : Context}
    (h : readContext s q = some c) {left right : Definition}
    (hl : left ∈ c.inventory) (hr : right ∈ c.inventory) (same : left.id = right.id) :
    left.kind = right.kind := no_collision_unique_kind (context_exact h).2.2.2.2.2.2.2 hl hr same

/-- Read transport returns an observation without changing durable state. -/
def readOnly (durable observed : Snapshot) (q : Request) : Snapshot × Option Context :=
  (durable, readContext observed q)

theorem read_preserves_durable (durable observed : Snapshot) (q : Request) :
    (readOnly durable observed q).1 = durable := rfl

/-- Once a snapshot is fixed, later commits cannot replace its result. -/
theorem concurrent_commit_does_not_mix (before after observed : Snapshot) (q : Request) :
    (readOnly before observed q).2 = (readOnly after observed q).2 := rfl

/-- Exact byte content survives appending later immutable revisions. -/
theorem existing_base_survives_append (s : Snapshot) (later : List Artifact) (r : Nat) (a : Artifact)
    (h : baseArtifact s r = some a) :
    baseArtifact { s with history := s.history ++ later } r = some a := by
  unfold baseArtifact at *
  rw [List.find?_append, h]
  rfl

def witnessKey : Key := ⟨⟨1, 2⟩, 3⟩
def witnessArtifact : Artifact := ⟨0, "exact source\r\n", [⟨7, .signature⟩]⟩
def witnessSnapshot : Snapshot := ⟨witnessKey, 0, [witnessArtifact]⟩
def witnessRequest : Request := ⟨witnessKey, 0, [7]⟩
def witnessContext : Context := ⟨witnessKey, 0, 0, witnessArtifact, [⟨7, .signature⟩]⟩

theorem nonvacuous_context : readContext witnessSnapshot witnessRequest = some witnessContext := by
  decide

end Allow.ValidationContextCandidate
