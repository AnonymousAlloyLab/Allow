import Std

/- Isolated design model. A syntactic tree gives every occurrence one owner;
   declaration and binder IDs are leaves. Runtime adapters and persistence are trusted. -/
namespace Allow.DocumentDraft
abbrev Id := Nat
abbrev Schema := List Id
abbrev Bytes := List UInt8

def SchemaOK (sigs : List Id) (s : Schema) : Prop :=
  s ≠ [] ∧ s.length ≤ 8 ∧ ∀ x ∈ s, x ∈ sigs
inductive Ty where
  | formula | relation (columns : Schema)
  deriving DecidableEq, Repr
inductive BoolOp where | and | or | implies | iff deriving DecidableEq, Repr
inductive TestOp where | some | no | one | lone deriving DecidableEq, Repr
inductive CompareOp where | equal | subset deriving DecidableEq, Repr
inductive SetOp where | union | inter | diff deriving DecidableEq, Repr
inductive QuantOp where | all | some deriving DecidableEq, Repr
inductive Expr where
  | sigRef (id : Id) | fieldRef (id : Id) | varRef (id : Id)
  | call (id : Id) (args : List Expr)
  | not (a : Expr) | bool (op : BoolOp) (a b : Expr)
  | test (op : TestOp) (a : Expr) | compare (op : CompareOp) (a b : Expr)
  | set (op : SetOp) (a b : Expr) | product (a b : Expr) | join (a b : Expr)
  | transpose (a : Expr) | quant (op : QuantOp) (binder sort : Id) (body : Expr)

structure Field where
  id : Id
  owner : Id
  range : Schema
  deriving DecidableEq, Repr
structure Pred where
  id : Id
  params : List (Id × Schema)
  body : Expr

structure Module where
  sigs : List Id
  fields : List Field
  preds : List Pred
  roots : List Expr

abbrev Env := List (Id × Schema)
def lookup (e : Env) (id : Id) : Option Schema := (e.find? (fun p => p.1 == id)).map Prod.snd

def fieldsEnv (m : Module) : Env := m.fields.map (fun f => (f.id, f.owner :: f.range))
def predsEnv (m : Module) : List (Id × List Schema) := m.preds.map (fun p => (p.id, p.params.map Prod.snd))
def lookupPred (m : Module) (id : Id) : Option (List Schema) :=
  (predsEnv m |>.find? (fun p => p.1 == id)).map Prod.snd

mutual
inductive Typed (m : Module) : Env → Expr → Ty → Prop where
  | sigRef : ident ∈ m.sigs → Typed m Γ (.sigRef ident) (.relation [ident])
  | fieldRef : lookup (fieldsEnv m) ident = some s → Typed m Γ (.fieldRef ident) (.relation s)
  | varRef : lookup Γ ident = some s → Typed m Γ (.varRef ident) (.relation s)
  | call : lookupPred m ident = some ss → TypedArgs m Γ args ss → Typed m Γ (.call ident args) .formula
  | not : Typed m Γ a .formula → Typed m Γ (.not a) .formula
  | bool : Typed m Γ a .formula → Typed m Γ b .formula → Typed m Γ (.bool op a b) .formula
  | test : Typed m Γ a (.relation s) → SchemaOK m.sigs s → Typed m Γ (.test op a) .formula
  | compare : Typed m Γ a (.relation s) → Typed m Γ b (.relation s) → SchemaOK m.sigs s → Typed m Γ (.compare op a b) .formula
  | set : Typed m Γ a (.relation s) → Typed m Γ b (.relation s) → SchemaOK m.sigs s → Typed m Γ (.set op a b) (.relation s)
  | product : Typed m Γ a (.relation s) → Typed m Γ b (.relation t) → SchemaOK m.sigs s → SchemaOK m.sigs t → SchemaOK m.sigs (s ++ t) → Typed m Γ (.product a b) (.relation (s ++ t))
  | join : Typed m Γ a (.relation (left ++ [endpoint])) → Typed m Γ b (.relation (endpoint :: right)) → SchemaOK m.sigs (left ++ right) → Typed m Γ (.join a b) (.relation (left ++ right))
  | transpose : Typed m Γ a (.relation [s,t]) → Typed m Γ (.transpose a) (.relation [t,s])
  | quant : sort ∈ m.sigs → lookup Γ binder = none → Typed m ((binder,[sort]) :: Γ) body .formula → Typed m Γ (.quant op binder sort body) .formula
inductive TypedArgs (m : Module) : Env → List Expr → List Schema → Prop where
  | nil : TypedArgs m Γ [] []
  | cons : Typed m Γ a (.relation s) → TypedArgs m Γ as ss → TypedArgs m Γ (a :: as) (s :: ss)
end

theorem variable_resolves {m Γ id s} (h : Typed m Γ (.varRef id) (.relation s)) : lookup Γ id = some s := by
  cases h with | varRef h => exact h

theorem join_nonempty_bounded {m Γ a b s} (h : Typed m Γ (.join a b) (.relation s)) : s ≠ [] ∧ s.length ≤ 8 := by
  cases h with | join _ _ ok => exact ⟨ok.1, ok.2.1⟩

/- The finite edge list is supplied by a separately tested AST traversal adapter. -/
def Ranked (edges : List (Id × Id)) (rank : Id → Nat) : Prop :=
  ∀ a b, (a,b) ∈ edges → rank b < rank a
inductive Path (edges : List (Id × Id)) : Id → Id → Prop where
  | edge : (a,b) ∈ edges → Path edges a b
  | step : (a,b) ∈ edges → Path edges b c → Path edges a c

theorem ranked_path {edges rank a b} (h : Ranked edges rank) (p : Path edges a b) : rank b < rank a := by
  induction p with
  | edge e => exact h _ _ e
  | step e _ ih => exact Nat.lt_trans ih (h _ _ e)
theorem ranked_acyclic {edges rank} (h : Ranked edges rank) (a : Id) : ¬ Path edges a a := by
  intro p
  exact (Nat.lt_irrefl _) (ranked_path h p)

/- A call occurrence is reached through syntax children, including argument lists. -/
inductive Calls : Expr → Id → Prop where
  | here : Calls (.call ident args) ident
  | callArg : a ∈ args → Calls a ident → Calls (.call target args) ident
  | not : Calls a ident → Calls (.not a) ident
  | boolLeft : Calls a ident → Calls (.bool op a b) ident
  | boolRight : Calls b ident → Calls (.bool op a b) ident
  | test : Calls a ident → Calls (.test op a) ident
  | compareLeft : Calls a ident → Calls (.compare op a b) ident
  | compareRight : Calls b ident → Calls (.compare op a b) ident
  | setLeft : Calls a ident → Calls (.set op a b) ident
  | setRight : Calls b ident → Calls (.set op a b) ident
  | productLeft : Calls a ident → Calls (.product a b) ident
  | productRight : Calls b ident → Calls (.product a b) ident
  | joinLeft : Calls a ident → Calls (.join a b) ident
  | joinRight : Calls b ident → Calls (.join a b) ident
  | transpose : Calls a ident → Calls (.transpose a) ident
  | quant : Calls a ident → Calls (.quant op binder sort a) ident

structure CheckedModule (m : Module) (edges : List (Id × Id)) (rank : Id → Nat) : Prop where
  sigUnique : m.sigs.Nodup
  fieldUnique : (m.fields.map Field.id).Nodup
  predUnique : (m.preds.map Pred.id).Nodup
  fieldsValid : ∀ f ∈ m.fields, f.owner ∈ m.sigs ∧ SchemaOK m.sigs f.range ∧ SchemaOK m.sigs (f.owner :: f.range)
  paramsUnique : ∀ p ∈ m.preds, (p.params.map Prod.fst).Nodup
  paramsValid : ∀ p ∈ m.preds, ∀ x ∈ p.params, SchemaOK m.sigs x.2
  predBodies : ∀ p ∈ m.preds, Typed m p.params p.body .formula
  rootsTyped : ∀ e ∈ m.roots, Typed m [] e .formula
  callEdges : ∀ p ∈ m.preds, ∀ callee, Calls p.body callee → (p.id, callee) ∈ edges
  callsRanked : Ranked edges rank

theorem checked_roots {m edges rank} (h : CheckedModule m edges rank) {e} (he : e ∈ m.roots) : Typed m [] e .formula := h.rootsTyped e he
theorem checked_no_cycle {m edges rank} (h : CheckedModule m edges rank) (id : Id) : ¬ Path edges id id := ranked_acyclic h.callsRanked id

/- Prefix conversion is defined over Unicode scalars. The adapter establishes
   valid scalar values and converts parser byte boundaries to prefix lengths. -/
structure Scalar where
  val : Nat
  valid : val ≤ 0x10ffff ∧ ¬ (0xd800 ≤ val ∧ val ≤ 0xdfff)
def utf8Width (s : Scalar) : Nat := if s.val < 0x80 then 1 else if s.val < 0x800 then 2 else if s.val < 0x10000 then 3 else 4
def utf16Width (s : Scalar) : Nat := if s.val < 0x10000 then 1 else 2
def widthSum (w : Scalar → Nat) (xs : List Scalar) : Nat := (xs.map w).sum

theorem width_append (w : Scalar → Nat) (xs ys : List Scalar) : widthSum w (xs ++ ys) = widthSum w xs + widthSum w ys := by
  simp [widthSum]
theorem prefix_bound (w : Scalar → Nat) (xs ys : List Scalar) : widthSum w xs ≤ widthSum w (xs ++ ys) := by
  rw [width_append]; exact Nat.le_add_right _ _
structure Occurrence where
  revision : Nat
  source : Bytes
  startPrefix : List Scalar
  remaining : List Scalar
  node : Id

def OccurrenceBound (o : Occurrence) : Prop := widthSum utf16Width o.startPrefix ≤ widthSum utf16Width (o.startPrefix ++ o.remaining)
theorem occurrence_bound (o : Occurrence) : OccurrenceBound o := prefix_bound _ _ _

/- Serialized atomic specification, not a proof of database refinement. -/
structure Scope where
  principal : Id
  launch : Id
  workspace : Id
  document : Id
  key : Id
  deriving DecidableEq, Repr
structure Request where
  bytes : Bytes
  digest : Bytes
  base : Nat
  policy : Nat
  deriving DecidableEq, Repr
structure Artifact where
  bytes : Bytes
  deriving DecidableEq, Repr
structure Receipt where
  scope : Scope
  requestBytes : Bytes
  digest : Bytes
  outcome : Nat
  deriving DecidableEq, Repr
structure State where
  revision : Nat
  history : List Artifact
  receipts : List Receipt
  policy : Nat
  deriving DecidableEq, Repr
def receipt (s : State) (k : Scope) : Option Receipt := s.receipts.find? (fun r => r.scope == k)
inductive Result where | replay (revision : Nat) | collision | accepted (revision : Nat) | rejected | unknown deriving DecidableEq, Repr
inductive Step (authorized : Prop) (valid : Artifact → Prop) : State → Scope → Request → Artifact → Result → State → Prop where
  | replay : authorized → receipt s k = some r → r.requestBytes = q.bytes → Step authorized valid s k q a (.replay r.outcome) s
  | collision : authorized → receipt s k = some r → r.requestBytes ≠ q.bytes → Step authorized valid s k q a .collision s
  | accept : authorized → receipt s k = none → q.base = s.revision → q.policy = s.policy → valid a →
      Step authorized valid s k q a (.accepted (s.revision + 1))
        ⟨s.revision + 1, s.history ++ [a], ⟨k,q.bytes,q.digest,s.revision + 1⟩ :: s.receipts, s.policy⟩
  | reject : receipt s k = none → Step authorized valid s k q a .rejected s
  | unknown : authorized → receipt s k = none → q.base = s.revision → q.policy = s.policy → valid a →
      Step authorized valid s k q a .unknown
        ⟨s.revision + 1, s.history ++ [a], ⟨k,q.bytes,q.digest,s.revision + 1⟩ :: s.receipts, s.policy⟩

theorem replay_available {auth valid s k q a r} (ha : auth) (hr : receipt s k = some r) (hb : r.requestBytes = q.bytes) : Step auth valid s k q a (.replay r.outcome) s := .replay ha hr hb
theorem collision_unchanged {auth valid s k q a out} (h : Step auth valid s k q a .collision out) : out = s := by cases h; rfl
theorem accepted_appends {auth valid s k q a n out} (h : Step auth valid s k q a (.accepted n) out) : out.revision = s.revision + 1 ∧ out.history = s.history ++ [a] := by cases h; exact ⟨rfl,rfl⟩
theorem rejected_unchanged {auth valid s k q a out} (h : Step auth valid s k q a .rejected out) : out = s := by cases h; rfl

/- Undo/redo is a checked historical selection, then the same append transition.
   Direction and target are included by the request-bytes adapter. -/
inductive Direction where | undo | redo deriving DecidableEq, Repr
inductive HistoricalStep (authorized : Prop) (valid : Artifact → Prop)
    (target : Artifact) : State → Scope → Request → Direction → Result → State → Prop where
  | restore : target ∈ s.history → Step authorized valid s k q target result out →
      HistoricalStep authorized valid target s k q direction result out

theorem historical_accept_appends {auth valid target s k q direction n out}
    (h : HistoricalStep auth valid target s k q direction (.accepted n) out) :
    target ∈ s.history ∧ out.history = s.history ++ [target] := by
  cases h with
  | restore hist st => exact ⟨hist, (accepted_appends st).2⟩

theorem receipt_head (s : State) (k : Scope) (q : Request) (n : Nat) :
    receipt ⟨s.revision, s.history, ⟨k,q.bytes,q.digest,n⟩ :: s.receipts, s.policy⟩ k =
      some ⟨k,q.bytes,q.digest,n⟩ := by
  simp [receipt]

theorem committed_retry {auth valid s k q a n out}
    (ha : auth) (h : Step auth valid s k q a (.accepted n) out) :
    Step auth valid out k q a (.replay n) out := by
  cases h with
  | accept _ _ _ _ _ =>
    exact Step.replay (r := ⟨k,q.bytes,q.digest,s.revision + 1⟩) ha (receipt_head _ _ _ _) rfl

theorem unknown_retry {auth valid s k q a out}
    (ha : auth) (h : Step auth valid s k q a .unknown out) :
    Step auth valid out k q a (.replay (s.revision + 1)) out := by
  cases h with
  | unknown _ _ _ _ _ =>
    exact Step.replay (r := ⟨k,q.bytes,q.digest,s.revision + 1⟩) ha (receipt_head _ _ _ _) rfl

/- Append-only state gives indefinite retention inside this transition system;
   admission, finite storage quotas and external deletion are outside it. -/
theorem receipts_preserved {auth valid s k q a result out}
    (h : Step auth valid s k q a result out) :
    ∀ r ∈ s.receipts, r ∈ out.receipts := by
  cases h <;> simp_all

theorem history_preserved {auth valid s k q a result out}
    (h : Step auth valid s k q a result out) :
    ∀ old ∈ s.history, old ∈ out.history := by
  cases h <;> simp_all

def exModule : Module := ⟨[1], [], [], [.test .some (.sigRef 1)]⟩
example : Typed exModule [] (.test .some (.sigRef 1)) .formula := by
  apply Typed.test (s := [1])
  · apply Typed.sigRef; simp [exModule]
  · simp [SchemaOK, exModule]
example : ¬ Typed exModule [] (.varRef 7) (.relation [1]) := by
  intro h
  have v := variable_resolves h
  simp [lookup] at v
def exampleScope : Scope := ⟨1,2,3,4,5⟩
def exampleRequest : Request := ⟨[1], [9], 0, 3⟩
def exampleArtifact : Artifact := ⟨[7]⟩
def exampleState : State := ⟨0, [], [], 3⟩
example : Step True (fun _ => True) exampleState exampleScope exampleRequest exampleArtifact
    (.accepted 1) ⟨1,[exampleArtifact],[⟨exampleScope,[1],[9],1⟩],3⟩ := by
  apply Step.accept
  all_goals simp [receipt, exampleState, exampleRequest]

example : Step True (fun _ => False)
    ⟨1,[exampleArtifact],[⟨exampleScope,[1],[9],1⟩],4⟩ exampleScope
    exampleRequest exampleArtifact (.replay 1)
    ⟨1,[exampleArtifact],[⟨exampleScope,[1],[9],1⟩],4⟩ := by
  apply Step.replay (r := ⟨exampleScope,[1],[9],1⟩)
  all_goals simp [receipt, exampleRequest]

example : Step True (fun _ => True)
    ⟨1,[exampleArtifact],[⟨exampleScope,[2],[9],1⟩],3⟩ exampleScope
    exampleRequest exampleArtifact .collision
    ⟨1,[exampleArtifact],[⟨exampleScope,[2],[9],1⟩],3⟩ := by
  apply Step.collision (r := ⟨exampleScope,[2],[9],1⟩)
  all_goals simp [receipt, exampleRequest]

end Allow.DocumentDraft
