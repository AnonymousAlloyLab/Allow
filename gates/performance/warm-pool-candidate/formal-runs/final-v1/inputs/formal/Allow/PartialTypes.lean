import Std

/- Candidate only. This proves facts about an abstract constraint denotation,
   not refinement of the browser checker, solver completeness, or runtime safety. -/
namespace Allow.DocumentPartialTypes
abbrev Schema := List Nat
inductive ResultSort where | formula | relation deriving DecidableEq, Repr
inductive Ty where
  | formula | relation (columns : Schema)
  deriving DecidableEq, Repr

def Ty.sort : Ty → ResultSort
  | .formula => .formula
  | .relation _ => .relation

/-- Partial facts retain constructor sort independently of child completeness. -/
inductive Fact where
  | unknown | formula | relation (columns : Option Schema)
  deriving DecidableEq, Repr

def denotes : Fact → Ty → Prop
  | .unknown, _ => True
  | .formula, .formula => True
  | .relation none, .relation _ => True
  | .relation (some a), .relation b => a = b
  | _, _ => False

/-- Destination constraints are conjunctive, including any explicit hole constraint. -/
inductive Constraint where
  | sort (s : ResultSort) | exact (t : Ty) | width (n : Nat)
  deriving DecidableEq, Repr

def satisfies : Constraint → Ty → Prop
  | .sort s, t => t.sort = s
  | .exact a, b => a = b
  | .width n, .relation s => s.length = n
  | .width _, .formula => False

def compatible (f : Fact) (cs : List Constraint) : Prop :=
  ∃ t, denotes f t ∧ ∀ c ∈ cs, satisfies c t

/-- The closed 23-operator profile; holes are a separate draft constructor. -/
inductive Op where
  | signatureRef | fieldRef | variableRef | predicateCall
  | not | someTest | noTest | oneTest | loneTest | transpose
  | and | or | implies | iff | equal | subset
  | union | intersection | difference | join | product | allQuant | someQuant
  deriving DecidableEq, Repr

def result : Op → Fact
  | .signatureRef | .fieldRef | .variableRef | .transpose
  | .union | .intersection | .difference | .join | .product => .relation none
  | _ => .formula

/-- Required immediate child sorts; declaration schemas refine these requirements. -/
def inputs : Op → List ResultSort
  | .signatureRef | .fieldRef | .variableRef | .predicateCall => []
  | .not | .allQuant | .someQuant => [.formula]
  | .and | .or | .implies | .iff => [.formula, .formula]
  | .someTest | .noTest | .oneTest | .loneTest | .transpose => [.relation]
  | _ => [.relation, .relation]

/-- Typed holes are constraints and cannot manufacture a resolved inferred type. -/
def holeResult : Fact := .unknown

theorem formula_rejected_in_relation (cs : List Constraint)
    (h : Constraint.sort .relation ∈ cs) : ¬ compatible .formula cs := by
  rintro ⟨t, ht, hc⟩
  cases t with
  | formula => exact ResultSort.noConfusion (hc _ h)
  | relation s => exact ht

theorem relation_rejected_in_formula (schema : Option Schema) (cs : List Constraint)
    (h : Constraint.sort .formula ∈ cs) : ¬ compatible (.relation schema) cs := by
  rintro ⟨t, ht, hc⟩
  cases t with
  | formula => cases schema <;> exact ht
  | relation s => exact ResultSort.noConfusion (hc _ h)

theorem nominal_mismatch_rejected (a b : Schema) (h : a ≠ b) :
    ¬ compatible (.relation (some a)) [.exact (.relation b)] := by
  rintro ⟨t, ht, hc⟩
  have he := hc (.exact (.relation b)) (by simp)
  change Ty.relation b = t at he
  subst t
  exact h ht

theorem unknown_schema_not_guessed (s : Schema) :
    compatible (.relation none) [.exact (.relation s)] := by
  refine ⟨.relation s, trivial, ?_⟩
  intro c hc
  simp only [List.mem_singleton] at hc
  subst c
  rfl

theorem unresolved_hole_preserved (s : Schema) :
    compatible holeResult [.exact (.relation s)] := by
  refine ⟨.relation s, trivial, ?_⟩
  intro c hc
  simp only [List.mem_singleton] at hc
  subst c
  rfl

theorem conjunction_preserves_rejection (f : Fact) (a b : List Constraint)
    (h : ¬ compatible f a) : ¬ compatible f (a ++ b) := by
  rintro ⟨t, ht, hc⟩
  exact h ⟨t, ht, fun c hm => hc c (List.mem_append_left b hm)⟩

theorem not_hole_rejected_under_some :
    ¬ compatible (result .not) [.sort .relation] :=
  formula_rejected_in_relation _ (by simp)

theorem product_holes_rejected_at_formula_root :
    ¬ compatible (result .product) [.sort .formula] :=
  relation_rejected_in_formula _ _ (by simp)

/-- Every profile result has a fixed sort, even without any operand facts. -/
theorem every_operator_has_known_result_sort (op : Op) :
    result op ≠ .unknown := by
  cases op <;> simp [result]

/-- Rejection is destination independent of whether an operator's operands are holes. -/
theorem profile_rejects_opposite_sort (op : Op) :
    (result op = .formula → ¬ compatible (result op) [.sort .relation]) ∧
    (result op = .relation none → ¬ compatible (result op) [.sort .formula]) := by
  constructor
  · intro h
    rw [h]
    exact formula_rejected_in_relation _ (by simp)
  · intro h
    rw [h]
    exact relation_rejected_in_formula _ _ (by simp)
/-- Existing nominal, nonempty and width bounds remain independent obligations. -/
def schemaOK (declared : List Nat) (s : Schema) : Prop :=
  s ≠ [] ∧ s.length ≤ 8 ∧ ∀ column ∈ s, column ∈ declared

def productConstraint (a b out : Schema) : Prop :=
  out = a ++ b ∧ out ≠ [] ∧ out.length ≤ 8

def joinConstraint (a b out : Schema) : Prop :=
  a ≠ [] ∧ b ≠ [] ∧ a.getLast? = b.head? ∧
  out = a.dropLast ++ b.tail ∧ out ≠ [] ∧ out.length ≤ 8

def transposeConstraint (a out : Schema) : Prop :=
  a.length = 2 ∧ out = a.reverse

theorem product_overflow_rejected (a b out : Schema)
    (h : 8 < a.length + b.length) : ¬ productConstraint a b out := by
  rintro ⟨rfl, _, hw⟩
  simp only [List.length_append] at hw
  omega

theorem join_endpoint_mismatch_rejected (a b out : Schema)
    (h : a.getLast? ≠ b.head?) : ¬ joinConstraint a b out := by
  intro hc
  exact h hc.2.2.1

theorem transpose_wrong_width_rejected (a out : Schema)
    (h : a.length ≠ 2) : ¬ transposeConstraint a out := by
  intro hc
  exact h hc.1
end Allow.DocumentPartialTypes
