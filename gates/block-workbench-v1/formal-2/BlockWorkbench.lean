import Std

/- Finite policy supplement. Concrete allocator, checker, renderer, solver,
   transport, runtime and UI correspondence are outside this model. -/
namespace Allow.BlockWorkbench

inductive Ref where
  | bound (id : Nat) | external (id : Nat)
  deriving DecidableEq, Repr
inductive Expr where
  | leaf (node : Nat) (ref : Ref)
  | bind (node binder : Nat) (body : Expr)
  | pair (node : Nat) (left right : Expr)
  deriving DecidableEq, Repr

def cloneRef (fresh : Nat → Nat) : Ref → Ref
  | .bound id => .bound (fresh id)
  | .external id => .external id

def clone (fresh : Nat → Nat) : Expr → Expr
  | .leaf n r => .leaf (fresh n) (cloneRef fresh r)
  | .bind n b e => .bind (fresh n) (fresh b) (clone fresh e)
  | .pair n a b => .pair (fresh n) (clone fresh a) (clone fresh b)

def externalRefs : Expr → List Nat
  | .leaf _ (.external id) => [id]
  | .leaf _ (.bound _) => []
  | .bind _ _ e => externalRefs e
  | .pair _ a b => externalRefs a ++ externalRefs b

def owned : Expr → List Nat
  | .leaf n _ => [n]
  | .bind n b e => n :: b :: owned e
  | .pair n a b => n :: (owned a ++ owned b)

theorem clone_external (f : Nat → Nat) (e : Expr) :
    externalRefs (clone f e) = externalRefs e := by
  induction e with
  | leaf n r => cases r <;> rfl
  | bind n b e ih => exact ih
  | pair n a b ia ib => simp [clone, externalRefs, ia, ib]

theorem clone_owned (f : Nat → Nat) (e : Expr) :
    owned (clone f e) = (owned e).map f := by
  induction e with
  | leaf n r => rfl
  | bind n b e ih => simp [clone, owned, ih]
  | pair n a b ia ib => simp [clone, owned, ia, ib]

theorem clone_fresh (f : Nat → Nat) (e : Expr) (occupied : List Nat)
    (fresh : ∀ x ∈ owned e, f x ∉ occupied) :
    ∀ x ∈ owned (clone f e), x ∉ occupied := by
  rw [clone_owned]
  intro x hx
  obtain ⟨y, hy, rfl⟩ := List.mem_map.mp hx
  exact fresh y hy

theorem clone_bound_consistent (f : Nat → Nat) (n b : Nat) :
    clone f (.bind n b (.leaf n (.bound b))) =
      .bind (f n) (f b) (.leaf (f n) (.bound (f b))) := rfl

theorem clone_distinct (f : Nat → Nat) (a b : Nat)
    (inj : Function.Injective f) (h : a ≠ b) : f a ≠ f b := by
  intro eq
  exact h (inj eq)

inductive Status where | compatible | unresolved | incompatible | unavailable
  deriving DecidableEq, Repr
structure Guard where
  sameDocument : Bool
  sameEnvironment : Bool
  currentContent : Bool
  currentDestination : Bool
  dependenciesInScope : Bool
  freshIds : Bool
  withinLimits : Bool
  status : Status
  deriving DecidableEq, Repr

def prepared (g : Guard) : Bool :=
  g.sameDocument && g.sameEnvironment && g.currentContent && g.currentDestination &&
  g.dependenciesInScope && g.freshIds && g.withinLimits &&
  (g.status == .compatible || g.status == .unresolved)

structure State where
  draft : Nat
  accepted : Nat
  library : List Nat
  generation : Nat
  deriving DecidableEq, Repr

def insert (g : Guard) (s : State) (candidate : Nat) : State :=
  if prepared g then {s with draft := candidate, generation := s.generation + 1} else s

theorem rejection_atomic (g : Guard) (s : State) (c : Nat)
    (h : prepared g = false) : insert g s c = s := by simp [insert, h]
theorem never_accepts (g : Guard) (s : State) (c : Nat) :
    (insert g s c).accepted = s.accepted ∧ (insert g s c).library = s.library := by
  unfold insert
  split <;> simp

theorem success_requires_guards (g : Guard) (h : prepared g = true) :
    g.sameDocument = true ∧ g.sameEnvironment = true ∧ g.currentContent = true ∧
    g.currentDestination = true ∧ g.dependenciesInScope = true ∧ g.freshIds = true ∧
    g.withinLimits = true ∧ (g.status = .compatible ∨ g.status = .unresolved) := by
  simpa [prepared, Bool.and_eq_true, Bool.or_eq_true, and_assoc] using h

theorem unavailable_rejected (g : Guard) (h : g.status = .unavailable) :
    prepared g = false := by simp [prepared, h]
theorem incompatible_rejected (g : Guard) (h : g.status = .incompatible) :
    prepared g = false := by simp [prepared, h]

inductive Category where | both | leftOnly | rightOnly | neither
  deriving DecidableEq, Repr

def category : Bool → Bool → Category
  | true, true => .both | true, false => .leftOnly
  | false, true => .rightOnly | false, false => .neither

theorem category_both (a b : Bool) : category a b = .both ↔ a = true ∧ b = true := by cases a <;> cases b <;> decide
theorem category_left (a b : Bool) : category a b = .leftOnly ↔ a = true ∧ b = false := by cases a <;> cases b <;> decide
theorem category_right (a b : Bool) : category a b = .rightOnly ↔ a = false ∧ b = true := by cases a <;> cases b <;> decide
theorem category_neither (a b : Bool) : category a b = .neither ↔ a = false ∧ b = false := by cases a <;> cases b <;> decide

/-- Both arms are evaluated on the same assignment. -/
def categoryAt (A B : α → Bool) (assignment : α) := category (A assignment) (B assignment)
theorem no_difference_agreement (A B : α → Bool) (admissible : α → Prop)
    (left : ∀ x, admissible x → categoryAt A B x ≠ .leftOnly)
    (right : ∀ x, admissible x → categoryAt A B x ≠ .rightOnly) :
    ∀ x, admissible x → A x = B x := by
  intro x hx
  have l := left x hx
  have r := right x hx
  cases ha : A x <;> cases hb : B x <;> simp_all [categoryAt, category]

inductive Outcome where | sat | unsat | timeout | error | unsupported | unavailable
  deriving DecidableEq, Repr

def agreementReported (left right : Outcome) : Bool := left == .unsat && right == .unsat

theorem agreement_requires_both_unsat (l r : Outcome) :
    agreementReported l r = true ↔ l = .unsat ∧ r = .unsat := by
  simp [agreementReported]

theorem timeout_not_agreement (r : Outcome) : agreementReported .timeout r = false := by simp [agreementReported]

def good : Guard := ⟨true,true,true,true,true,true,true,.unresolved⟩
theorem positive_unresolved : prepared good = true := by decide
theorem positive_partition : category true false = .leftOnly ∧ category false true = .rightOnly := by decide

/- File identity values and normalized background are abstract: concrete SHA-256,
   parsing, alpha normalization and dependency analysis remain trusted. -/
structure FileSide where
  sourceHash : Nat
  predicate : Nat
  background : List Nat
  parameters : List (List Nat)
  selectedDependency : Bool
  deriving DecidableEq, Repr

structure FileRequest where
  left : FileSide
  right : FileSide
  document : Nat
  draft : Nat
  scope : Nat
  deriving DecidableEq, Repr

def matched (l r : FileSide) : Bool :=
  l.background == r.background && l.parameters == r.parameters &&
  !l.selectedDependency && !r.selectedDependency

def filePublish (request current : FileRequest) : Bool :=
  request == current && matched request.left request.right

theorem matched_requires_background_and_parameters (l r : FileSide)
    (h : matched l r = true) :
    l.background = r.background ∧ l.parameters = r.parameters ∧
    l.selectedDependency = false ∧ r.selectedDependency = false := by
  simpa [matched, Bool.and_eq_true, and_assoc] using h

theorem dependency_rejected_left (l r : FileSide) (h : l.selectedDependency = true) :
    matched l r = false := by simp [matched, h]
theorem dependency_rejected_right (l r : FileSide) (h : r.selectedDependency = true) :
    matched l r = false := by simp [matched, h]

theorem publish_exact_request (request current : FileRequest)
    (h : filePublish request current = true) : request = current := by
  simp [filePublish] at h
  exact h.1

theorem publish_matched (request current : FileRequest)
    (h : filePublish request current = true) : matched request.left request.right = true := by
  simp [filePublish] at h
  exact h.2

theorem changed_hash_cannot_publish (request current : FileRequest)
    (h : request.left.sourceHash ≠ current.left.sourceHash) :
    filePublish request current = false := by
  cases hp : filePublish request current with
  | false => rfl
  | true =>
    have eq := publish_exact_request request current hp
    exact False.elim (h (congrArg (fun x => x.left.sourceHash) eq))

theorem changed_predicate_cannot_publish (request current : FileRequest)
    (h : request.right.predicate ≠ current.right.predicate) :
    filePublish request current = false := by
  cases hp : filePublish request current with
  | false => rfl
  | true =>
    have eq := publish_exact_request request current hp
    exact False.elim (h (congrArg (fun x => x.right.predicate) eq))

def exampleSide : FileSide := ⟨1, 2, [3,4], [[5,6]], false⟩
theorem matched_positive : matched exampleSide {exampleSide with sourceHash := 9, predicate := 8} = true := by decide
end Allow.BlockWorkbench
