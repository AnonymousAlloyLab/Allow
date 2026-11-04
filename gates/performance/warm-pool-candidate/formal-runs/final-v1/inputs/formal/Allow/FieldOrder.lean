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

/- Only steps that append a fresh artifact inspect its field order. Receipt
   lookup and denial paths remain independent of candidate validation. -/
def OrderRequired (a : Artifact) (result : Result) : Prop :=
  match result with
  | .accepted _ | .unknown => CandidateOrder a
  | _ => True

def GuardedStep (auth : Prop) (s : State) (k : Scope) (q : Request)
    (a : Artifact) (result : Result) (out : State) : Prop :=
  OrderRequired a result ∧ Step auth s k q a result out

def GuardedAdmittedStep (decoder : WireDecoder) (parser : ParserAdmission)
    (frame : CheckedFrameBinding) (auth : Prop) (s : State) (k : Scope)
    (q : Request) (a : Artifact) (result : Result) (out : State) : Prop :=
  OrderRequired a result ∧ AdmittedStep decoder parser frame auth s k q a result out

theorem guarded_admitted_replay {decoder parser frame auth s k q a r}
    (ha : auth) (hr : receipt s k = some r) (same : r.requestWire = q.wire) :
    GuardedAdmittedStep decoder parser frame auth s k q a (.replay r.outcome) s :=
  ⟨True.intro, AdmittedStep.replay ha hr same⟩

theorem guarded_admitted_collision {decoder parser frame auth s k q a r}
    (ha : auth) (hr : receipt s k = some r) (different : r.requestWire ≠ q.wire) :
    GuardedAdmittedStep decoder parser frame auth s k q a .collision s :=
  ⟨True.intro, AdmittedStep.collision ha hr different⟩

theorem guarded_admitted_deny_auth {decoder parser frame auth s k q a} (denied : ¬ auth) :
    GuardedAdmittedStep decoder parser frame auth s k q a .rejected s :=
  ⟨True.intro, AdmittedStep.denyAuth denied⟩

theorem guarded_success_checked {auth s k q a n out}
    (h : GuardedStep auth s k q a (.accepted n) out) : CandidateValid a q.policy :=
  accepted_checked h.2

theorem guarded_success_ordered {auth s k q a n out m}
    (h : GuardedStep auth s k q a (.accepted n) out) (block : a.moduleIR = some m) :
    groupedFields m.sigs m.fields = m.fields := by
  have ordered := h.1
  simp only [OrderRequired, CandidateOrder, block] at ordered
  exact (accepts_exact m.sigs m.fields).mp ordered

theorem guarded_unknown_success_ordered {auth s k q a out m}
    (h : GuardedStep auth s k q a .unknown out) (block : a.moduleIR = some m) :
    groupedFields m.sigs m.fields = m.fields := by
  have ordered := h.1
  simp only [OrderRequired, CandidateOrder, block] at ordered
  exact (accepts_exact m.sigs m.fields).mp ordered

theorem empty_order_accepts : accepts [] [] = true := by decide

theorem grouped_order_accepts : accepts [1,2]
    [⟨7,1,[1],.set⟩,⟨9,1,[1],.set⟩,⟨8,2,[1],.set⟩] = true := by decide

theorem interleaved_order_denied : accepts [1,2]
    [⟨7,1,[1],.set⟩,⟨8,2,[1],.set⟩,⟨9,1,[1],.set⟩] = false := by decide

def unorderedModule : Module :=
  ⟨[1,2], [⟨7,1,[1],.set⟩,⟨8,2,[1],.set⟩,⟨9,1,[1],.set⟩], [], [],
   [(1,.set),(2,.set)], [], [], []⟩
def unorderedArtifact : Artifact := {exampleArtifact with moduleIR := some unorderedModule}
def replayState : State :=
  ⟨1,[initialArtifact,exampleArtifact],
   [⟨exampleScope,⟨[10],[11],[1]⟩,[9],.committed 1 []⟩],3⟩

theorem unordered_candidate_denied : ¬ CandidateOrder unorderedArtifact := by
  simp [CandidateOrder,unorderedArtifact,unorderedModule,accepts,groupedFields]

theorem unordered_candidate_receipt_replay :
    GuardedAdmittedStep (fun _ => none) (fun _ => False) (fun _ _ _ _ => False) True
      replayState exampleScope exampleRequest unorderedArtifact (.replay (.committed 1 [])) replayState := by
  apply guarded_admitted_replay (r := ⟨exampleScope,⟨[10],[11],[1]⟩,[9],.committed 1 []⟩)
  · trivial
  · simp [receipt,replayState]
  · rfl

theorem unordered_candidate_collision :
    GuardedAdmittedStep (fun _ => none) (fun _ => False) (fun _ _ _ _ => False) True
      replayState exampleScope staleTextRequest unorderedArtifact .collision replayState := by
  apply guarded_admitted_collision (r := ⟨exampleScope,⟨[10],[11],[1]⟩,[9],.committed 1 []⟩)
  · trivial
  · simp [receipt,replayState]
  · simp [staleTextRequest]

end Allow.DocumentOrder
