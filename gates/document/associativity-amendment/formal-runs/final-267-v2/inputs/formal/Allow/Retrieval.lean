import Allow.Evidence
import Std.Tactic

namespace Allow.Retrieval

/-- The abstraction assumes that the supplied exact identities and validation flags are faithful. -/
structure Member where
  run : Run
  witness : Witness

def admitted (t : TargetContext) (p : Polarity) (m : Member) : Prop :=
  admitPair t p m.run m.witness = true

def ready (n : Nat) (t : TargetContext) (pos neg : List Member) : Prop :=
  3 ≤ n ∧ n ≤ 5 ∧ pos.length = n ∧ neg.length = n ∧
  (pos.map (fun m => m.witness.fullInstanceHash)).Nodup ∧ (neg.map (fun m => m.witness.fullInstanceHash)).Nodup ∧
  (∀ m ∈ pos, admitted t .positive m) ∧ (∀ m ∈ neg, admitted t .negative m)

theorem ready_bounds (h : ready n t pos neg) : 3 ≤ n ∧ n ≤ 5 := ⟨h.1, h.2.1⟩
theorem ready_positive_size (h : ready n t pos neg) : pos.length = n := h.2.2.1
theorem ready_negative_size (h : ready n t pos neg) : neg.length = n := h.2.2.2.1
theorem ready_positive_distinct (h : ready n t pos neg) : (pos.map (fun m => m.witness.fullInstanceHash)).Nodup := h.2.2.2.2.1
theorem ready_negative_distinct (h : ready n t pos neg) : (neg.map (fun m => m.witness.fullInstanceHash)).Nodup := h.2.2.2.2.2.1
theorem ready_positive_admitted (h : ready n t pos neg) (hm : m ∈ pos) : admitted t .positive m := h.2.2.2.2.2.2.1 m hm
theorem ready_negative_admitted (h : ready n t pos neg) (hm : m ∈ neg) : admitted t .negative m := h.2.2.2.2.2.2.2 m hm
theorem below_range_not_ready (h : n < 3) : ¬ ready n t pos neg := by
  intro hr; have := ready_bounds hr; omega
theorem above_range_not_ready (h : 5 < n) : ¬ ready n t pos neg := by
  intro hr; have := ready_bounds hr; omega
theorem partial_not_ready (h : pos.length < n) : ¬ ready n t pos neg := by
  intro hr; have := ready_positive_size hr; omega

def queryEval (p : Polarity) (facts predicate : Bool) : Bool :=
  match p with
  | .positive => facts && predicate
  | .negative => facts && !predicate

theorem positive_query (f p : Bool) : queryEval .positive f p = (f && p) := rfl
theorem negative_query (f p : Bool) : queryEval .negative f p = (f && !p) := rfl
theorem opposite_polarities_disjoint (f p : Bool) :
    ¬ (queryEval .positive f p = true ∧ queryEval .negative f p = true) := by
  cases f <;> cases p <;> decide

/-- A single matching finite sample does not establish universal equivalence. -/
theorem finite_samples_incomplete :
    (∀ x ∈ ([false] : List Bool), (fun _ : Bool => false) x = (fun x => x) x) ∧
    ¬ (∀ x : Bool, (fun _ : Bool => false) x = (fun x => x) x) := by decide

theorem opposing_witness_refutes_equivalence {α : Type} (p q : α → Bool) (x : α)
    (hp : p x = true) (hq : q x = false) : ¬ (∀ y, p y = q y) := by
  intro h; have := h x; simp_all

/-- Four independent fixed-size blocks produce the requested total width. -/
abbrev Block := Fin 768 → Int
abbrev Embedding := Fin 3072 → Int
/-- Concatenate context, predicate, positive and negative blocks in that order. -/
def pack4 (context predicate positive negative : Block) : Embedding := fun i =>
  if h0 : i.val < 768 then context ⟨i.val, h0⟩
  else if h1 : i.val < 1536 then predicate ⟨i.val - 768, by omega⟩
  else if h2 : i.val < 2304 then positive ⟨i.val - 1536, by omega⟩
  else negative ⟨i.val - 2304, by have := i.isLt; omega⟩

def index0 (i : Fin 768) : Fin 3072 := ⟨i.val, by have := i.isLt; omega⟩
def index1 (i : Fin 768) : Fin 3072 := ⟨768 + i.val, by have := i.isLt; omega⟩
def index2 (i : Fin 768) : Fin 3072 := ⟨1536 + i.val, by have := i.isLt; omega⟩
def index3 (i : Fin 768) : Fin 3072 := ⟨2304 + i.val, by have := i.isLt; omega⟩

theorem pack4_context (a b c d : Block) (i : Fin 768) :
    pack4 a b c d (index0 i) = a i := by
  simp [pack4, index0, i.isLt]

theorem pack4_predicate (a b c d : Block) (i : Fin 768) :
    pack4 a b c d (index1 i) = b i := by
  simp [pack4, index1, show ¬ 768 + i.val < 768 by omega,
    show 768 + i.val < 1536 by have := i.isLt; omega]

theorem pack4_positive (a b c d : Block) (i : Fin 768) :
    pack4 a b c d (index2 i) = c i := by
  simp [pack4, index2, show ¬ 1536 + i.val < 768 by omega,
    show ¬ 1536 + i.val < 1536 by omega,
    show 1536 + i.val < 2304 by have := i.isLt; omega]

theorem pack4_negative (a b c d : Block) (i : Fin 768) :
    pack4 a b c d (index3 i) = d i := by
  simp [pack4, index3, show ¬ 2304 + i.val < 768 by omega,
    show ¬ 2304 + i.val < 1536 by omega,
    show ¬ 2304 + i.val < 2304 by omega]

def vectorWidth (_ : Embedding) : Nat := 3072
theorem vector_width (v : Embedding) : vectorWidth v = 3072 := rfl
theorem four_blocks_width : 4 * 768 = 3072 := by decide

/-- Fixed-point model of the default normalized weighted score; implementation floats are trusted. -/
def score (canonical positive negative : Nat) : Nat :=
  (550 * canonical + 225 * positive + 225 * negative) / 1000

theorem score_bounded (c p n : Nat) (hc : c ≤ 1000) (hp : p ≤ 1000) (hn : n ≤ 1000) :
    score c p n ≤ 1000 := by
  unfold score
  apply (Nat.div_le_iff_le_mul (by decide : 0 < 1000)).2
  omega

theorem score_zero : score 0 0 0 = 0 := by decide
theorem score_max : score 1000 1000 1000 = 1000 := by decide

def overlap (sameContext : Bool) (shared : Nat) : Nat := if sameContext then shared else 0
theorem incompatible_overlap_zero (shared : Nat) : overlap false shared = 0 := rfl

structure Snapshot where
  request : Nat
  epoch : Nat
  model : Nat
  index : Nat
  deriving DecidableEq, Repr

def commit (current result : Snapshot) (complete : Bool) : Bool :=
  decide (current = result ∧ complete = true)

theorem commit_current (h : commit current result complete = true) : current = result ∧ complete = true := by
  simpa [commit] using h

theorem stale_cannot_commit (h : current ≠ result) : commit current result complete = false := by
  simp [commit, h]

theorem partial_cannot_commit (current result : Snapshot) : commit current result false = false := by
  simp [commit]

def visible (committed revoked : Bool) : Bool := committed && !revoked

theorem revoked_invisible (committed : Bool) : visible committed true = false := by simp [visible]

theorem admitted_evidence (h : admitted t p m) :
    m.run.query.target = t ∧ m.run.query.polarity = p ∧
    m.witness.ownQuery = m.run.query ∧ m.run.status = .SAT ∧ m.witness.validated = true :=
  pair_admission_bound h

def sampleMember (q : QueryKey) (id : String) : Member :=
  ⟨⟨q, .SAT⟩, ⟨q, id, true⟩⟩

theorem ready_three_witness :
    ready 3 sampleTarget
      [sampleMember positiveQuery "a", sampleMember positiveQuery "b", sampleMember positiveQuery "c"]
      [sampleMember negativeQuery "d", sampleMember negativeQuery "e", sampleMember negativeQuery "f"] := by
  simp [ready, admitted, admitPair, sampleMember, positiveQuery, negativeQuery, sampleTarget]

end Allow.Retrieval
