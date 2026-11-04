import Allow.Document

/- Additional presentation guard only. It does not extend Alloy semantics. -/
namespace Allow.DocumentOrder
open Allow.DocumentDraft

def groupedFields (owners : List Id) (fields : List Field) : List Field :=
  owners.flatMap (fun owner => fields.filter (fun field => field.owner == owner))

def accepts (owners : List Id) (fields : List Field) : Bool :=
  decide (groupedFields owners fields = fields)

theorem accepts_exact (owners : List Id) (fields : List Field) :
    accepts owners fields = true ↔ groupedFields owners fields = fields := by
  simp [accepts]

theorem accepted_ids_preserved {owners fields} (h : accepts owners fields = true) :
    (groupedFields owners fields).map Field.id = fields.map Field.id := by
  rw [(accepts_exact owners fields).mp h]

def CandidateOrder (a : Artifact) : Prop :=
  match a.moduleIR with
  | none => True
  | some m => accepts m.sigs m.fields = true

def GuardedStep (auth : Prop) (s : State) (k : Scope) (q : Request)
    (a : Artifact) (result : Result) (out : State) : Prop :=
  CandidateOrder a ∧ Step auth s k q a result out

theorem guarded_success_checked {auth s k q a n out}
    (h : GuardedStep auth s k q a (.accepted n) out) : CandidateValid a q.policy :=
  accepted_checked h.2

theorem guarded_success_ordered {auth s k q a n out m}
    (h : GuardedStep auth s k q a (.accepted n) out) (block : a.moduleIR = some m) :
    groupedFields m.sigs m.fields = m.fields := by
  have ordered := h.1
  simp only [CandidateOrder, block] at ordered
  exact (accepts_exact m.sigs m.fields).mp ordered

theorem empty_order_accepts : accepts [] [] = true := by decide

theorem grouped_order_accepts : accepts [1,2]
    [⟨7,1,[1],.set⟩,⟨9,1,[1],.set⟩,⟨8,2,[1],.set⟩] = true := by decide

theorem interleaved_order_denied : accepts [1,2]
    [⟨7,1,[1],.set⟩,⟨8,2,[1],.set⟩,⟨9,1,[1],.set⟩] = false := by decide

end Allow.DocumentOrder
