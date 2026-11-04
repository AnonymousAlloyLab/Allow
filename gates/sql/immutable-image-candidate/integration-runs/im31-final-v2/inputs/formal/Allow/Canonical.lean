import Std

namespace Allow

inductive Formula (n : Nat) where
  | atom (i : Fin n)
  | truth
  | falsity
  | not (a : Formula n)
  | and (a b : Formula n)
  | or (a b : Formula n)
  deriving DecidableEq, Repr

def eval (v : Fin n → Bool) : Formula n → Bool
  | .atom i => v i
  | .truth => true
  | .falsity => false
  | .not a => !(eval v a)
  | .and a b => eval v a && eval v b
  | .or a b => eval v a || eval v b

/-- A full Shannon tree, in fixed atom order. It is finite, serializable and unique. -/
inductive Table : Nat → Type where
  | leaf : Bool → Table 0
  | fork : Table n → Table n → Table (n + 1)
  deriving DecidableEq, Repr

def extend (b : Bool) (v : Fin n → Bool) : Fin (n + 1) → Bool := Fin.cases b v

def tabulate : (n : Nat) → ((Fin n → Bool) → Bool) → Table n
  | 0, f => .leaf (f Fin.elim0)
  | n + 1, f => .fork (tabulate n (fun v => f (extend false v)))
      (tabulate n (fun v => f (extend true v)))

def lookup : {n : Nat} → Table n → (Fin n → Bool) → Bool
  | 0, .leaf b, _ => b
  | _ + 1, .fork lo hi, v => if v 0 then lookup hi (fun i => v i.succ)
      else lookup lo (fun i => v i.succ)

theorem extend_tail (v : Fin (n + 1) → Bool) :
    extend (v 0) (fun i => v i.succ) = v := by
  funext i
  refine Fin.cases ?_ (fun j => ?_) i <;> rfl

theorem lookup_tabulate (n : Nat) (f : (Fin n → Bool) → Bool) (v : Fin n → Bool) :
    lookup (tabulate n f) v = f v := by
  induction n with
  | zero =>
    have h : Fin.elim0 = v := by funext i; exact Fin.elim0 i
    simp [tabulate, lookup, h]
  | succ n ih =>
    simp only [tabulate, lookup]
    split <;> rw [ih]
    · rename_i h
      have hv := extend_tail v
      simp only [h] at hv
      rw [hv]
    · rename_i h
      have hz : v 0 = false := Bool.eq_false_iff.mpr h
      have hv := extend_tail v
      simp only [hz] at hv
      rw [hv]

def canonical (f : Formula n) : Table n := tabulate n (fun v => eval v f)

theorem canonical_eq_iff (a b : Formula n) :
    canonical a = canonical b ↔ ∀ v, eval v a = eval v b := by
  constructor
  · intro h v
    have hh := congrArg (fun t => lookup t v) h
    simpa [canonical, lookup_tabulate] using hh
  · intro h
    unfold canonical
    exact congrArg (tabulate n) (funext h)

theorem canonical_idempotent (t : Table n) : tabulate n (lookup t) = t := by
  induction t with
  | leaf b => rfl
  | fork lo hi hlo hhi =>
    simp [tabulate, lookup, extend, hlo, hhi]

/-- Finite, fully explicit Boolean rewrite calculus; no arbitrary merge axiom. -/
inductive Certificate : Formula n → Formula n → Prop where
  | refl (a) : Certificate a a
  | symm : Certificate a b → Certificate b a
  | trans : Certificate a b → Certificate b c → Certificate a c
  | notCong : Certificate a b → Certificate (.not a) (.not b)
  | andCong : Certificate a b → Certificate c d → Certificate (.and a c) (.and b d)
  | orCong : Certificate a b → Certificate c d → Certificate (.or a c) (.or b d)
  | andComm (a b) : Certificate (.and a b) (.and b a)
  | andAssoc (a b c) : Certificate (.and (.and a b) c) (.and a (.and b c))
  | andIdem (a) : Certificate (.and a a) a
  | orComm (a b) : Certificate (.or a b) (.or b a)
  | orAssoc (a b c) : Certificate (.or (.or a b) c) (.or a (.or b c))
  | orIdem (a) : Certificate (.or a a) a
  | doubleNot (a) : Certificate (.not (.not a)) a
  | deMorgan (a b) : Certificate (.not (.and a b)) (.or (.not a) (.not b))

theorem certificate_sound (h : Certificate a b) : ∀ v, eval v a = eval v b := by
  induction h with
  | refl => intro v; rfl
  | symm _ ih => intro v; exact (ih v).symm
  | trans _ _ ih₁ ih₂ => intro v; exact (ih₁ v).trans (ih₂ v)
  | notCong _ ih => intro v; simp only [eval, ih v]
  | andCong _ _ ih₁ ih₂ => intro v; simp only [eval, ih₁ v, ih₂ v]
  | orCong _ _ ih₁ ih₂ => intro v; simp only [eval, ih₁ v, ih₂ v]
  | andComm a b => intro v; simp [eval, Bool.and_comm]
  | andAssoc a b c => intro v; simp [eval, Bool.and_assoc]
  | andIdem a => intro v; simp [eval]
  | orComm a b => intro v; simp [eval, Bool.or_comm]
  | orAssoc a b c => intro v; simp [eval, Bool.or_assoc]
  | orIdem a => intro v; simp [eval]
  | doubleNot a => intro v; simp [eval]
  | deMorgan a b => intro v; simp [eval, Bool.not_and]

structure ContextualFormula (n : Nat) where
  context : String
  inventory : Fin n → String
  body : Formula n

def CertifiedMerge (a b : ContextualFormula n) : Prop :=
  a.context = b.context ∧ a.inventory = b.inventory ∧ Certificate a.body b.body

def canonicalKey (a : ContextualFormula n) := (a.context, a.inventory, canonical a.body)

theorem certified_merge_canonical (h : CertifiedMerge a b) :
    canonicalKey a = canonicalKey b := by
  exact Prod.ext h.1 (Prod.ext h.2.1
    ((canonical_eq_iff _ _).mpr (certificate_sound h.2.2)))

theorem distinct_inventories_distinct_keys (a b : ContextualFormula n)
    (h : a.inventory ≠ b.inventory) : canonicalKey a ≠ canonicalKey b := by
  intro heq
  exact h (congrArg (fun k => k.2.1) heq)

example : canonicalKey (⟨"module", fun _ => "some A", .atom (0 : Fin 1)⟩ : ContextualFormula 1) ≠
    canonicalKey (⟨"module", fun _ => "some B", .atom (0 : Fin 1)⟩ : ContextualFormula 1) := by
  apply distinct_inventories_distinct_keys
  intro h
  have he := congrFun h (0 : Fin 1)
  contradiction

/-- Unrestricted prenexing fails even before Alloy-specific complications arise. -/
theorem empty_domain_counterexample :
    ((∃ _ : Empty, True) ∨ True) ∧ ¬ (∃ _ : Empty, True ∨ True) := by
  constructor
  · exact Or.inr trivial
  · rintro ⟨x, _⟩; exact Empty.elim x

example : canonical (Formula.and (.atom (0 : Fin 1)) .truth) =
    canonical (Formula.atom (0 : Fin 1)) := by decide
example : canonical (Formula.truth : Formula 1) ≠ canonical Formula.falsity := by decide

end Allow
