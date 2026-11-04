import Std

namespace Allow

/-- Exact nominal schemas are a conservative elaborated fragment, not full Alloy types. -/
inductive Ty where
  | formula
  | relation (head : Nat) (tail : List Nat)
  deriving DecidableEq, Repr

inductive Raw where
  | hole
  | truth
  | ref (index : Nat)
  | not (a : Raw)
  | and (a b : Raw)
  | or (a b : Raw)
  | implies (a b : Raw)
  | union (a b : Raw)
  | someRel (a : Raw)
  | existsRel (sort : Nat) (body : Raw)
  deriving DecidableEq, Repr

/-- Binding indices have already been elaborated in this exact context. -/
inductive HasType : List Ty → Raw → Ty → Prop where
  | truth : HasType Γ .truth .formula
  | ref : Γ[i]? = some t → HasType Γ (.ref i) t
  | not : HasType Γ a .formula → HasType Γ (.not a) .formula
  | and : HasType Γ a .formula → HasType Γ b .formula → HasType Γ (.and a b) .formula
  | or : HasType Γ a .formula → HasType Γ b .formula → HasType Γ (.or a b) .formula
  | implies : HasType Γ a .formula → HasType Γ b .formula → HasType Γ (.implies a b) .formula
  | union : HasType Γ a (.relation s ss) → HasType Γ b (.relation s ss) →
      HasType Γ (.union a b) (.relation s ss)
  | someRel : HasType Γ a (.relation s ss) → HasType Γ (.someRel a) .formula
  | existsRel : HasType (.relation s [] :: Γ) b .formula →
      HasType Γ (.existsRel s b) .formula

/-- Executable inference returns a derivation, rather than trusting a Boolean flag. -/
def infer (Γ : List Ty) : (e : Raw) → Option {t : Ty // HasType Γ e t}
  | .hole => none
  | .truth => some ⟨.formula, .truth⟩
  | .ref i => match h : Γ[i]? with
    | none => none
    | some t => some ⟨t, .ref h⟩
  | .not a => match infer Γ a with
    | some ⟨.formula, ha⟩ => some ⟨.formula, .not ha⟩
    | _ => none
  | .and a b => match infer Γ a, infer Γ b with
    | some ⟨.formula, ha⟩, some ⟨.formula, hb⟩ => some ⟨.formula, .and ha hb⟩
    | _, _ => none
  | .or a b => match infer Γ a, infer Γ b with
    | some ⟨.formula, ha⟩, some ⟨.formula, hb⟩ => some ⟨.formula, .or ha hb⟩
    | _, _ => none
  | .implies a b => match infer Γ a, infer Γ b with
    | some ⟨.formula, ha⟩, some ⟨.formula, hb⟩ => some ⟨.formula, .implies ha hb⟩
    | _, _ => none
  | .union a b => match infer Γ a, infer Γ b with
    | some ⟨.relation s ss, ha⟩, some ⟨.relation t ts, hb⟩ =>
      if h : Ty.relation t ts = .relation s ss then
        some ⟨.relation s ss, .union ha (h ▸ hb)⟩
      else none
    | _, _ => none
  | .someRel a => match infer Γ a with
    | some ⟨.relation _ _, ha⟩ => some ⟨.formula, .someRel ha⟩
    | _ => none
  | .existsRel s b => match infer (.relation s [] :: Γ) b with
    | some ⟨.formula, hb⟩ => some ⟨.formula, .existsRel hb⟩
    | _ => none

def inferType (Γ : List Ty) (e : Raw) : Option Ty := (infer Γ e).map Subtype.val

theorem infer_sound (h : inferType Γ e = some t) : HasType Γ e t := by
  unfold inferType at h
  cases hi : infer Γ e with
  | none => simp [hi] at h
  | some p =>
    simp [hi] at h
    exact h ▸ p.property

def HoleFree : Raw → Prop
  | .hole => False
  | .truth | .ref _ => True
  | .not a | .someRel a | .existsRel _ a => HoleFree a
  | .and a b | .or a b | .implies a b | .union a b => HoleFree a ∧ HoleFree b

theorem typed_hole_free (h : HasType Γ e t) : HoleFree e := by
  induction h <;> simp_all [HoleFree]

def checkSlot (Γ : List Ty) (expected : Ty) (e : Raw) : Bool :=
  inferType Γ e == some expected

theorem checkSlot_sound (h : checkSlot Γ t e = true) : HasType Γ e t := by
  apply infer_sound
  simpa [checkSlot] using h

structure State where
  context : List Ty
  body : Raw
  revision : Nat
  deriving DecidableEq, Repr

def State.Valid (s : State) : Prop := HasType s.context s.body .formula

/-- Full candidate context/body, after scope elaboration; raw text drafts are separate. -/
def commit (s : State) (base : Nat) (Γ : List Ty) (e : Raw) : State :=
  if base = s.revision ∧ checkSlot Γ .formula e = true then
    ⟨Γ, e, s.revision + 1⟩
  else s

theorem reject_preserves (s : State) (base : Nat) (Γ : List Ty) (e : Raw)
    (h : ¬ (base = s.revision ∧ checkSlot Γ .formula e = true)) :
    commit s base Γ e = s := by simp [commit, h]

theorem commit_preserves (s : State) (base : Nat) (Γ : List Ty) (e : Raw)
    (valid : s.Valid) : (commit s base Γ e).Valid := by
  unfold commit
  split
  · rename_i h
    exact checkSlot_sound h.2
  · exact valid

theorem commit_revision (s : State) (Γ : List Ty) (e : Raw)
    (h : checkSlot Γ .formula e = true) :
    (commit s s.revision Γ e).revision = s.revision + 1 := by simp [commit, h]

/-- Non-vacuous examples and negative controls are kernel reduced. -/
example : inferType [] (.existsRel 7 (.someRel (.ref 0))) = some .formula := by decide
example : inferType [.relation 7 []] (.and (.ref 0) .truth) = none := by decide
example : inferType [.relation 7 [], .relation 8 []] (.union (.ref 0) (.ref 1)) = none := by decide
example : inferType [] (.ref 0) = none := by decide
example : inferType [] (.and .truth .hole) = none := by decide
example : (commit ⟨[], .truth, 0⟩ 0 [] (.not .truth)).revision = 1 := by decide

end Allow
