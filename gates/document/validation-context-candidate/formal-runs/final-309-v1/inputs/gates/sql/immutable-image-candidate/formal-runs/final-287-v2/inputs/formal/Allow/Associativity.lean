import Allow.FieldOrder

/- Pure Boolean abstraction of ordered static AND/OR regrouping. Parser,
   source-ID correspondence, stack limits and runtime adapters are not modeled. -/
namespace Allow.DocumentAssociativity
inductive Op where | and | or deriving DecidableEq, Repr
inductive Tree (α : Type) where
  | empty
  | leaf (value : α)
  | node (left right : Tree α)
  deriving DecidableEq, Repr

def combine : Op → Bool → Bool → Bool
  | .and, a, b => a && b
  | .or, a, b => a || b

def identity : Op → Bool | .and => true | .or => false

def eval (op : Op) (value : α → Bool) : Tree α → Bool
  | .empty => identity op
  | .leaf atom => value atom
  | .node left right => combine op (eval op value left) (eval op value right)

def leaves : Tree α → List α
  | .empty => []
  | .leaf value => [value]
  | .node left right => leaves left ++ leaves right

def fold (op : Op) (xs : List Bool) : Bool := xs.foldr (combine op) (identity op)

theorem combine_assoc (op : Op) (a b c : Bool) :
    combine op (combine op a b) c = combine op a (combine op b c) := by
  cases op <;> cases a <;> cases b <;> cases c <;> rfl

theorem fold_append (op : Op) (xs ys : List Bool) :
    fold op (xs ++ ys) = combine op (fold op xs) (fold op ys) := by
  induction xs with
  | nil => cases op <;> simp [fold,combine,identity]
  | cons x xs ih =>
    simp only [fold, List.cons_append, List.foldr_cons] at *
    rw [ih, combine_assoc]

theorem eval_leaves (op : Op) (value : α → Bool) (t : Tree α) : eval op value t = fold op ((leaves t).map value) := by
  induction t with
  | empty => rfl
  | leaf v => cases op <;> cases h : value v <;> simp [eval,leaves,fold,combine,identity,h]
  | node l r ihl ihr => simp only [eval,leaves,ihl,ihr,List.map_append,fold_append]

def chain : List α → Tree α
  | [] => .empty
  | [x] => .leaf x
  | x :: y :: xs => .node (.leaf x) (chain (y :: xs))

theorem chain_leaves (xs : List α) : leaves (chain xs) = xs := by
  induction xs using chain.induct with
  | case1 => rfl
  | case2 => rfl
  | case3 x y xs ih => simp [chain, leaves, ih]

/- Fuel bounds this mathematical construction; a right-fold fallback retains
   leaves if exhausted. This is not an implementation stack-safety proof. The
   adapter must reject incomplete construction and independently enforce limits. -/
def balanced : Nat → List α → Tree α
  | 0, xs => chain xs
  | _ + 1, [] => .empty
  | _ + 1, [x] => .leaf x
  | fuel + 1, x :: y :: xs =>
      let all := x :: y :: xs
      let half := all.length / 2
      .node (balanced fuel (all.take half)) (balanced fuel (all.drop half))

theorem balanced_leaves (fuel : Nat) (xs : List α) : leaves (balanced fuel xs) = xs := by
  induction fuel generalizing xs with
  | zero => exact chain_leaves xs
  | succ fuel ih =>
    cases xs with
    | nil => rfl
    | cons x tail =>
      cases tail with
      | nil => rfl
      | cons y rest =>
        simp only [balanced,leaves,ih]
        exact List.take_append_drop _ _

theorem balanced_semantics (op : Op) (value : α → Bool) (fuel : Nat) (xs : List α) :
    eval op value (balanced fuel xs) = fold op (xs.map value) := by
  rw [eval_leaves, balanced_leaves]

theorem regroup_semantics (op : Op) (value : α → Bool) (original : Tree α) (fuel : Nat) :
    eval op value (balanced fuel (leaves original)) = eval op value original := by
  rw [balanced_semantics, eval_leaves]

def leftAcc (initial : Tree α) (xs : List α) : Tree α :=
  xs.foldl (fun tree x => .node tree (.leaf x)) initial

theorem leftAcc_leaves (initial : Tree α) (xs : List α) :
    leaves (leftAcc initial xs) = leaves initial ++ xs := by
  induction xs generalizing initial with
  | nil => simp [leftAcc]
  | cons x xs ih =>
    simp only [leftAcc,List.foldl_cons]
    rw [← leftAcc, ih]
    simp [leaves, List.append_assoc]

def leftChain : List α → Tree α
  | [] => .empty
  | x :: xs => leftAcc (.leaf x) xs

theorem leftChain_leaves (xs : List α) : leaves (leftChain xs) = xs := by
  cases xs with
  | nil => rfl
  | cons x xs => simp [leftChain,leftAcc_leaves,leaves]

/- Leaf represents a formula test with a referenced signature: two syntax
   nodes and depth 2, as in the frozen headless fixture. -/
def nodes : Tree α → Nat
  | .empty => 0
  | .leaf _ => 2
  | .node a b => 1 + nodes a + nodes b

def depth : Tree α → Nat
  | .empty => 0
  | .leaf _ => 2
  | .node a b => 1 + max (depth a) (depth b)

theorem depth_le_nodes (t : Tree α) : depth t ≤ nodes t := by
  induction t with
  | empty => simp [depth,nodes]
  | leaf _ => simp [depth,nodes]
  | node a b ha hb =>
    simp only [depth,nodes]
    have left : depth a ≤ nodes a + nodes b := Nat.le_trans ha (Nat.le_add_right _ _)
    have right : depth b ≤ nodes a + nodes b := Nat.le_trans hb (Nat.le_add_left _ _)
    have both := Nat.max_le.mpr ⟨left,right⟩
    omega

def PublicBounded (t : Tree α) : Prop := nodes t ≤ 512 ∧ depth t ≤ 32
def IntermediateBounded (t : Tree α) : Prop := nodes t ≤ 512 ∧ depth t ≤ 512

theorem public_implies_intermediate {t : Tree α} (h : PublicBounded t) : IntermediateBounded t := by
  exact ⟨h.1, Nat.le_trans h.2 (by decide)⟩

theorem node_bound_implies_intermediate {t : Tree α} (h : nodes t ≤ 512) : IntermediateBounded t :=
  ⟨h, Nat.le_trans (depth_le_nodes t) h⟩

/- The amendment does not change the prior acceptance relation. These are
   projections of the existing checked-module and field-order obligations. -/
theorem accepted_public_limits_preserved
    {auth s k q a n out m}
    (step : Allow.DocumentOrder.GuardedStep auth s k q a (.accepted n) out)
    (block : a.moduleIR = some m) :
    Allow.DocumentDraft.moduleNodeCount m ≤ 512 ∧
      (∀ e ∈ Allow.DocumentDraft.moduleExpressions m, Allow.DocumentDraft.exprDepth e ≤ 32) ∧
      Allow.DocumentOrder.groupedFields m.sigs m.fields = m.fields := by
  have valid := Allow.DocumentDraft.accepted_checked step.2
  have mode := valid.2
  rw [block] at mode
  obtain ⟨_, ⟨edges,rank,checked⟩, _⟩ := mode
  exact ⟨checked.nodeBound, checked.depthBound, Allow.DocumentOrder.guarded_success_ordered step block⟩

def fixtureValues : List Nat := List.range 167
def fixtureBalanced : Tree Nat := balanced 16 fixtureValues
def fixtureLeftDeep : Tree Nat := leftChain fixtureValues

set_option maxRecDepth 8192 in
set_option maxHeartbeats 4000000 in
theorem fixture_balanced_witness : nodes fixtureBalanced = 500 ∧ depth fixtureBalanced = 10 := by
  decide

set_option maxRecDepth 8192 in
set_option maxHeartbeats 4000000 in
theorem fixture_left_witness : nodes fixtureLeftDeep = 500 ∧ depth fixtureLeftDeep = 168 := by
  decide

theorem fixture_public_vs_transient : PublicBounded fixtureBalanced ∧
    IntermediateBounded fixtureLeftDeep ∧ ¬ PublicBounded fixtureLeftDeep := by
  have h := fixture_balanced_witness
  have j := fixture_left_witness
  simp [PublicBounded,IntermediateBounded,h.1,h.2,j.1,j.2]
end Allow.DocumentAssociativity
