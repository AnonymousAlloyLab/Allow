import Allow.Canonical

namespace Allow.EGraph

/-- Rules are explicitly enumerated; each constructor is a semantic obligation. -/
inductive Rule : Formula n → Formula n → Prop where
  | base : Certificate a b → Rule a b
  | andTrue (a) : Rule (.and a .truth) a
  | andFalse (a) : Rule (.and a .falsity) .falsity
  | orFalse (a) : Rule (.or a .falsity) a
  | orTrue (a) : Rule (.or a .truth) .truth
  | andAbsorb (a b) : Rule (.and a (.or a b)) a
  | orAbsorb (a b) : Rule (.or a (.and a b)) a
  | andDistrib (a b c) : Rule (.and a (.or b c)) (.or (.and a b) (.and a c))
  | orDistrib (a b c) : Rule (.or a (.and b c)) (.and (.or a b) (.or a c))
  | andComplement (a) : Rule (.and a (.not a)) .falsity
  | orComplement (a) : Rule (.or a (.not a)) .truth
  | notTrue : Rule (.not .truth) .falsity
  | notFalse : Rule (.not .falsity) .truth
  | deMorganOr (a b) : Rule (.not (.or a b)) (.and (.not a) (.not b))

theorem rule_sound (h : Rule a b) : ∀ v, eval v a = eval v b := by
  cases h with
  | base h => exact certificate_sound h
  | notTrue | notFalse => intro v; rfl
  | andTrue a | andFalse a | orFalse a | orTrue a | andComplement a | orComplement a =>
    intro v; simp [eval]
  | andAbsorb => intro v; simp [eval]; exact fun h => Or.inl h
  | orAbsorb => intro v; simp [eval]; exact fun h _ => h
  | deMorganOr x y =>
    intro v; cases hx : eval v x <;> cases hy : eval v y <;> simp [eval, hx, hy]
  | andDistrib a b c | orDistrib a b c =>
    intro v; cases ha : eval v a <;> cases hb : eval v b <;> cases hc : eval v c <;>
      simp [eval, ha, hb, hc]

/-- The least equivalence and operator congruence containing the certified rules. -/
inductive Derivation : Formula n → Formula n → Prop where
  | rule : Rule a b → Derivation a b
  | refl (a) : Derivation a a
  | symm : Derivation a b → Derivation b a
  | trans : Derivation a b → Derivation b c → Derivation a c
  | notCong : Derivation a b → Derivation (.not a) (.not b)
  | andCong : Derivation a b → Derivation c d → Derivation (.and a c) (.and b d)
  | orCong : Derivation a b → Derivation c d → Derivation (.or a c) (.or b d)

theorem derivation_sound (h : Derivation a b) : ∀ v, eval v a = eval v b := by
  induction h with
  | rule h => exact rule_sound h
  | refl => intro v; rfl
  | symm _ ih => intro v; exact (ih v).symm
  | trans _ _ ih₁ ih₂ => intro v; exact (ih₁ v).trans (ih₂ v)
  | notCong _ ih => intro v; simp only [eval, ih v]
  | andCong _ _ ih₁ ih₂ => intro v; simp only [eval, ih₁ v, ih₂ v]
  | orCong _ _ ih₁ ih₂ => intro v; simp only [eval, ih₁ v, ih₂ v]

/-- A graph's class relation is justified by derivations in one fixed context and inventory. -/
structure Graph (n : Nat) where
  context : String
  inventory : Fin n → String
  sameClass : Formula n → Formula n → Prop
  justified : ∀ {a b}, sameClass a b → Derivation a b

def Merge (g : Graph n) (a b : ContextualFormula n) : Prop :=
  a.context = g.context ∧ b.context = g.context ∧
  a.inventory = g.inventory ∧ b.inventory = g.inventory ∧ Derivation a.body b.body

theorem merge_preserves_key (h : Merge g a b) : canonicalKey a = canonicalKey b := by
  rcases h with ⟨ha, hb, ia, ib, hd⟩
  exact Prod.ext (ha.trans hb.symm) (Prod.ext (ia.trans ib.symm)
    ((canonical_eq_iff _ _).mpr (derivation_sound hd)))

theorem class_sound (g : Graph n) (h : g.sameClass a b) :
    ∀ v, eval v a = eval v b := derivation_sound (g.justified h)

/-- Extraction is only meaningful when accompanied by class membership. -/
theorem extraction_sound (g : Graph n) (root extracted : Formula n)
    (member : g.sameClass root extracted) : ∀ v, eval v root = eval v extracted :=
  class_sound g member

/-- A bounded run may claim saturation only when the worklist is actually empty. -/
inductive StopReason where
  | saturated | nodeLimit | iterationLimit | timeLimit
  deriving DecidableEq, Repr

def stopReason (workRemaining : Bool) (budgetExhausted : StopReason) : StopReason :=
  if workRemaining then budgetExhausted else .saturated

theorem bounded_run_no_false_saturation (remaining : Bool) (reason : StopReason)
    (h : reason ≠ .saturated) :
    stopReason remaining reason = .saturated → remaining = false := by
  cases remaining <;> simp_all [stopReason]

/-- Pointwise relation algebra over a fixed, typed tuple domain. -/
abbrev Relation (Tuple : Type) := Tuple → Bool

def union (a b : Relation Tuple) : Relation Tuple := fun x => a x || b x
def inter (a b : Relation Tuple) : Relation Tuple := fun x => a x && b x
def diff (a b : Relation Tuple) : Relation Tuple := fun x => a x && !(b x)

theorem relation_union_comm (a b : Relation Tuple) : union a b = union b a := by
  funext x; exact Bool.or_comm _ _
theorem relation_inter_comm (a b : Relation Tuple) : inter a b = inter b a := by
  funext x; exact Bool.and_comm _ _
theorem relation_inter_distrib (a b c : Relation Tuple) :
    inter a (union b c) = union (inter a b) (inter a c) := by
  funext x; cases ha : a x <;> cases hb : b x <;> cases hc : c x <;>
    simp [inter, union, ha, hb, hc]
theorem relation_diff_self (a : Relation Tuple) : diff a a = fun _ => false := by
  funext x; cases h : a x <;> simp [diff, h]

/-- Relational expressions all share one tuple type and one atom inventory. -/
inductive RelExpr (n : Nat) where
  | atom (i : Fin n)
  | empty
  | union (a b : RelExpr n)
  | inter (a b : RelExpr n)
  | diff (a b : RelExpr n)
  deriving DecidableEq, Repr

def evalRelation (v : Fin n → Relation Tuple) : RelExpr n → Relation Tuple
  | .atom i => v i
  | .empty => fun _ => false
  | .union a b => union (evalRelation v a) (evalRelation v b)
  | .inter a b => inter (evalRelation v a) (evalRelation v b)
  | .diff a b => diff (evalRelation v a) (evalRelation v b)

inductive RelRule : RelExpr n → RelExpr n → Prop where
  | unionComm (a b) : RelRule (.union a b) (.union b a)
  | unionAssoc (a b c) : RelRule (.union (.union a b) c) (.union a (.union b c))
  | unionIdem (a) : RelRule (.union a a) a
  | unionEmpty (a) : RelRule (.union a .empty) a
  | interComm (a b) : RelRule (.inter a b) (.inter b a)
  | interAssoc (a b c) : RelRule (.inter (.inter a b) c) (.inter a (.inter b c))
  | interIdem (a) : RelRule (.inter a a) a
  | interEmpty (a) : RelRule (.inter a .empty) .empty
  | interAbsorb (a b) : RelRule (.inter a (.union a b)) a
  | unionAbsorb (a b) : RelRule (.union a (.inter a b)) a
  | interDistrib (a b c) : RelRule (.inter a (.union b c)) (.union (.inter a b) (.inter a c))
  | diffSelf (a) : RelRule (.diff a a) .empty
  | diffEmpty (a) : RelRule (.diff a .empty) a

theorem rel_rule_sound {a b : RelExpr n} (h : RelRule a b) :
    ∀ (v : Fin n → Relation Tuple), evalRelation v a = evalRelation v b := by
  cases h <;> intro v <;> funext x <;>
    simp [evalRelation, union, inter, diff, Bool.or_comm, Bool.and_comm,
      Bool.or_assoc, Bool.and_assoc, Bool.and_or_distrib_left]
  all_goals intros; assumption

inductive RelDerivation : RelExpr n → RelExpr n → Prop where
  | rule : RelRule a b → RelDerivation a b
  | refl (a) : RelDerivation a a
  | symm : RelDerivation a b → RelDerivation b a
  | trans : RelDerivation a b → RelDerivation b c → RelDerivation a c
  | unionCong : RelDerivation a b → RelDerivation c d → RelDerivation (.union a c) (.union b d)
  | interCong : RelDerivation a b → RelDerivation c d → RelDerivation (.inter a c) (.inter b d)
  | diffCong : RelDerivation a b → RelDerivation c d → RelDerivation (.diff a c) (.diff b d)

theorem rel_derivation_sound {a b : RelExpr n} (h : RelDerivation a b) :
    ∀ (v : Fin n → Relation Tuple), evalRelation v a = evalRelation v b := by
  induction h with
  | rule h => exact rel_rule_sound h
  | refl => intro v; rfl
  | symm _ ih => intro v; exact (ih v).symm
  | trans _ _ ih₁ ih₂ => intro v; exact (ih₁ v).trans (ih₂ v)
  | unionCong _ _ ih₁ ih₂ => intro v; simp only [evalRelation, ih₁ v, ih₂ v]
  | interCong _ _ ih₁ ih₂ => intro v; simp only [evalRelation, ih₁ v, ih₂ v]
  | diffCong _ _ ih₁ ih₂ => intro v; simp only [evalRelation, ih₁ v, ih₂ v]

structure RelGraph (n : Nat) where
  context : String
  schema : List String
  inventory : Fin n → String
  sameClass : RelExpr n → RelExpr n → Prop
  justified : ∀ {a b}, sameClass a b → RelDerivation a b

structure ContextualRelation (n : Nat) where
  context : String
  schema : List String
  inventory : Fin n → String
  body : RelExpr n

def RelMerge (g : RelGraph n) (a b : ContextualRelation n) : Prop :=
  a.context = g.context ∧ b.context = g.context ∧
  a.schema = g.schema ∧ b.schema = g.schema ∧
  a.inventory = g.inventory ∧ b.inventory = g.inventory ∧ RelDerivation a.body b.body

theorem rel_merge_sound {g : RelGraph n} {a b : ContextualRelation n} (h : RelMerge g a b) :
    a.context = b.context ∧ a.schema = b.schema ∧ a.inventory = b.inventory ∧
    ∀ (v : Fin n → Relation Tuple), evalRelation v a.body = evalRelation v b.body := by
  rcases h with ⟨ca, cb, sa, sb, ia, ib, hd⟩
  exact ⟨ca.trans cb.symm, sa.trans sb.symm, ia.trans ib.symm, rel_derivation_sound hd⟩

theorem rel_extraction_sound (g : RelGraph n) (root extracted : RelExpr n)
    (member : g.sameClass root extracted) :
    ∀ (v : Fin n → Relation Tuple), evalRelation v root = evalRelation v extracted :=
  rel_derivation_sound (g.justified member)

theorem rel_nonempty_congruence {a b : RelExpr n} (h : RelDerivation a b) (v : Fin n → Relation Tuple) :
    (∃ x, evalRelation v a x = true) ↔ (∃ x, evalRelation v b x = true) := by
  rw [rel_derivation_sound h v]

theorem rel_empty_congruence {a b : RelExpr n} (h : RelDerivation a b)
    (v : Fin n → Relation Tuple) :
    (¬ ∃ x, evalRelation v a x = true) ↔ (¬ ∃ x, evalRelation v b x = true) := by
  rw [rel_derivation_sound h v]

theorem implication_lowering (a b : Bool) : (!a || b) = (if a then b else true) := by
  cases a <;> cases b <;> rfl

theorem iff_lowering (a b : Bool) : ((!a || b) && (!b || a)) = (a == b) := by
  cases a <;> cases b <;> rfl

/-- Mixed Boolean expressions with finite-domain relational nonemptiness. -/
inductive MixedFormula (bn rn : Nat) where
  | atom (i : Fin bn)
  | truth | falsity
  | not (a : MixedFormula bn rn)
  | and (a b : MixedFormula bn rn)
  | or (a b : MixedFormula bn rn)
  | some (a : RelExpr rn)
  | no (a : RelExpr rn)

def evalMixed (bv : Fin bn → Bool) (rv : Fin rn → Relation Tuple)
    (domain : List Tuple) : MixedFormula bn rn → Bool
  | .atom i => bv i
  | .truth => true
  | .falsity => false
  | .not a => !(evalMixed bv rv domain a)
  | .and a b => evalMixed bv rv domain a && evalMixed bv rv domain b
  | .or a b => evalMixed bv rv domain a || evalMixed bv rv domain b
  | .some a => domain.any (evalRelation rv a)
  | .no a => !(domain.any (evalRelation rv a))

def substB (σ : Fin n → MixedFormula bn rn) : Formula n → MixedFormula bn rn
  | .atom i => σ i
  | .truth => .truth
  | .falsity => .falsity
  | .not a => .not (substB σ a)
  | .and a b => .and (substB σ a) (substB σ b)
  | .or a b => .or (substB σ a) (substB σ b)

theorem eval_substB (σ : Fin n → MixedFormula bn rn) (a : Formula n)
    (bv : Fin bn → Bool) (rv : Fin rn → Relation Tuple) (domain : List Tuple) :
    evalMixed bv rv domain (substB σ a) = eval (fun i => evalMixed bv rv domain (σ i)) a := by
  induction a <;> simp_all [substB, evalMixed, eval]

inductive MixedDerivation : MixedFormula bn rn → MixedFormula bn rn → Prop where
  | boolean {a b : Formula n} (h : Rule a b) (σ : Fin n → MixedFormula bn rn) :
      MixedDerivation (substB σ a) (substB σ b)
  | refl (a) : MixedDerivation a a
  | symm : MixedDerivation a b → MixedDerivation b a
  | trans : MixedDerivation a b → MixedDerivation b c → MixedDerivation a c
  | notCong : MixedDerivation a b → MixedDerivation (.not a) (.not b)
  | andCong : MixedDerivation a b → MixedDerivation c d → MixedDerivation (.and a c) (.and b d)
  | orCong : MixedDerivation a b → MixedDerivation c d → MixedDerivation (.or a c) (.or b d)
  | someCong : RelDerivation a b → MixedDerivation (.some a) (.some b)
  | noCong : RelDerivation a b → MixedDerivation (.no a) (.no b)

theorem mixed_sound {a b : MixedFormula bn rn} (h : MixedDerivation a b)
    (bv : Fin bn → Bool) (rv : Fin rn → Relation Tuple) (domain : List Tuple) :
    evalMixed bv rv domain a = evalMixed bv rv domain b := by
  induction h with
  | boolean h σ => simp only [eval_substB]; exact rule_sound h _
  | refl => rfl
  | symm _ ih => exact (ih bv rv).symm
  | trans _ _ ih₁ ih₂ => exact (ih₁ bv rv).trans (ih₂ bv rv)
  | notCong _ ih => simp only [evalMixed, ih bv rv]
  | andCong _ _ ih₁ ih₂ => simp only [evalMixed, ih₁ bv rv, ih₂ bv rv]
  | orCong _ _ ih₁ ih₂ => simp only [evalMixed, ih₁ bv rv, ih₂ bv rv]
  | someCong h => simp only [evalMixed, rel_derivation_sound h rv]
  | noCong h => simp only [evalMixed, rel_derivation_sound h rv]

theorem witness_boolean_absorption :
    Derivation (.and (.atom (0 : Fin 2)) (.or (.atom 0) (.atom 1))) (.atom 0) :=
  .rule (.andAbsorb _ _)
theorem witness_relation_absorption :
    RelDerivation (.inter (.atom (0 : Fin 2)) (.union (.atom 0) (.atom 1))) (.atom 0) :=
  .rule (.interAbsorb _ _)
theorem witness_relation_difference :
    RelDerivation (.diff (.atom (0 : Fin 1)) (.atom 0)) .empty :=
  .rule (.diffSelf _)
theorem witness_budget_stop : stopReason true .nodeLimit ≠ .saturated := by decide

end Allow.EGraph
