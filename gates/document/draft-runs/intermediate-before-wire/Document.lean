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

inductive Multiplicity where | set | one | lone | some deriving DecidableEq, Repr
structure NamedFormula where
  id : Id
  body : Expr
inductive CommandKind where | runPredicate | runFact | checkAssertion deriving DecidableEq, Repr
structure Command where
  id : Id
  kind : CommandKind
  target : Id
  bound : Nat

structure Module where
  sigs : List Id
  fields : List Field
  preds : List Pred
  roots : List Expr
  sigMultiplicity : List (Id × Multiplicity)
  facts : List NamedFormula
  assertions : List NamedFormula
  commands : List Command

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

/- Executable finite adapter oracle candidate. Until its correspondence to Typed
   is proved, results are experimental and cannot authorize implementations. -/
def schemaOkB (sigs : List Id) (s : Schema) : Bool :=
  !s.isEmpty && s.length ≤ 8 && s.all (fun id => sigs.contains id)

def infer (m : Module) (Γ : Env) : Expr → Option Ty
  | .sigRef i => if m.sigs.contains i then some (.relation [i]) else none
  | .fieldRef i => (lookup (fieldsEnv m) i).map Ty.relation
  | .varRef i => (lookup Γ i).map Ty.relation
  | .call i args =>
      match lookupPred m i with
      | none => none
      | some ss => if args.map (infer m Γ) == ss.map (fun s => some (Ty.relation s)) then some .formula else none
  | .not a => if infer m Γ a == some .formula then some .formula else none
  | .bool _ a b => if infer m Γ a == some .formula && infer m Γ b == some .formula then some .formula else none
  | .test _ a => match infer m Γ a with
      | some (.relation s) => if schemaOkB m.sigs s then some .formula else none
      | _ => none
  | .compare _ a b => match infer m Γ a, infer m Γ b with
      | some (.relation s), some (.relation t) => if s == t && schemaOkB m.sigs s then some .formula else none
      | _, _ => none
  | .set _ a b => match infer m Γ a, infer m Γ b with
      | some (.relation s), some (.relation t) => if s == t && schemaOkB m.sigs s then some (.relation s) else none
      | _, _ => none
  | .product a b => match infer m Γ a, infer m Γ b with
      | some (.relation s), some (.relation t) =>
          if schemaOkB m.sigs s && schemaOkB m.sigs t && schemaOkB m.sigs (s ++ t) then some (.relation (s ++ t)) else none
      | _, _ => none
  | .join a b => match infer m Γ a, infer m Γ b with
      | some (.relation s), some (.relation t) =>
          match s.reverse, t with
          | endpoint :: revLeft, first :: right =>
              if endpoint == first && schemaOkB m.sigs (revLeft.reverse ++ right)
              then some (.relation (revLeft.reverse ++ right)) else none
          | _, _ => none
      | _, _ => none
  | .transpose a => match infer m Γ a with
      | some (.relation [s,t]) => some (.relation [t,s])
      | _ => none
  | .quant _ binder sort body =>
      if m.sigs.contains sort && (lookup Γ binder).isNone && infer m ((binder,[sort]) :: Γ) body == some .formula
      then some .formula else none
termination_by e => sizeOf e

theorem schema_ok_boolean_exact (sigs s : List Id) : schemaOkB sigs s = true ↔ SchemaOK sigs s := by
  simp [schemaOkB, SchemaOK, List.all_eq_true, and_assoc]

theorem infer_sig_sound {m Γ id s} (h : infer m Γ (.sigRef id) = some (.relation s)) :
    Typed m Γ (.sigRef id) (.relation s) := by
  simp only [infer] at h
  split at h
  · rename_i member
    simp only [Option.some.injEq, Ty.relation.injEq] at h
    subst s
    apply Typed.sigRef
    simpa using member
  · contradiction

theorem infer_sig_complete {m Γ id s} (h : Typed m Γ (.sigRef id) (.relation s)) :
    infer m Γ (.sigRef id) = some (.relation s) := by
  cases h with
  | sigRef member => simp [infer, member]

theorem infer_var_sound {m Γ id s} (h : infer m Γ (.varRef id) = some (.relation s)) :
    Typed m Γ (.varRef id) (.relation s) := by
  apply Typed.varRef
  simp [infer] at h
  exact h

theorem infer_var_complete {m Γ id s} (h : Typed m Γ (.varRef id) (.relation s)) :
    infer m Γ (.varRef id) = some (.relation s) := by
  simp [infer, variable_resolves h]

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

def binderIds : Expr → List Id
  | .sigRef _ | .fieldRef _ | .varRef _ => []
  | .call _ args => args.flatMap binderIds
  | .not a | .test _ a | .transpose a => binderIds a
  | .bool _ a b | .compare _ a b | .set _ a b | .product a b | .join a b => binderIds a ++ binderIds b
  | .quant _ binder _ body => binder :: binderIds body
termination_by e => sizeOf e

def exprNodes : Expr → Nat
  | .sigRef _ | .fieldRef _ | .varRef _ => 1
  | .call _ args => 1 + (args.map exprNodes).sum
  | .not a | .test _ a | .transpose a => 1 + exprNodes a
  | .bool _ a b | .compare _ a b | .set _ a b | .product a b | .join a b => 1 + exprNodes a + exprNodes b
  | .quant _ _ _ a => 1 + exprNodes a
termination_by e => sizeOf e

def exprDepth : Expr → Nat
  | .sigRef _ | .fieldRef _ | .varRef _ => 1
  | .call _ args => 1 + (args.map exprDepth).foldl max 0
  | .not a | .test _ a | .transpose a => 1 + exprDepth a
  | .bool _ a b | .compare _ a b | .set _ a b | .product a b | .join a b => 1 + max (exprDepth a) (exprDepth b)
  | .quant _ _ _ a => 1 + exprDepth a
termination_by e => sizeOf e

def children : Expr → List Expr
  | .sigRef _ | .fieldRef _ | .varRef _ => []
  | .call _ args => args
  | .not a | .test _ a | .transpose a | .quant _ _ _ a => [a]
  | .bool _ a b | .compare _ a b | .set _ a b | .product a b | .join a b => [a,b]

def follow : Expr → List Nat → Option Expr
  | e, [] => some e
  | e, i :: rest => (children e)[i]?.bind (fun child => follow child rest)

def moduleExpressions (m : Module) : List Expr :=
  m.preds.map Pred.body ++ m.roots ++ m.facts.map NamedFormula.body ++ m.assertions.map NamedFormula.body

def moduleNodeCount (m : Module) : Nat :=
  (m.preds.map (fun p => exprNodes p.body)).sum + (m.roots.map exprNodes).sum +
  (m.facts.map (fun f => exprNodes f.body)).sum + (m.assertions.map (fun f => exprNodes f.body)).sum

def allDeclarationIds (m : Module) : List Id :=
  m.sigs ++ m.fields.map Field.id ++ m.preds.map Pred.id ++
  m.facts.map NamedFormula.id ++ m.assertions.map NamedFormula.id ++ m.commands.map Command.id

def allBinderIds (m : Module) : List Id :=
  m.preds.flatMap (fun p => p.params.map Prod.fst ++ binderIds p.body) ++
  m.roots.flatMap binderIds ++ m.facts.flatMap (fun f => binderIds f.body) ++
  m.assertions.flatMap (fun f => binderIds f.body)

structure CheckedModule (m : Module) (edges : List (Id × Id)) (rank : Id → Nat) : Prop where
  declarationsUnique : (allDeclarationIds m).Nodup
  declarationBound : (allDeclarationIds m).length ≤ 512
  nodeBound : moduleNodeCount m ≤ 10000
  depthBound : ∀ e ∈ moduleExpressions m, exprDepth e ≤ 128
  allBindersUnique : (allBinderIds m).Nodup
  sigUnique : m.sigs.Nodup
  sigMultiplicityExact : m.sigMultiplicity.map Prod.fst = m.sigs
  factUnique : (m.facts.map NamedFormula.id).Nodup
  assertionUnique : (m.assertions.map NamedFormula.id).Nodup
  commandUnique : (m.commands.map Command.id).Nodup
  factsTyped : ∀ f ∈ m.facts, Typed m [] f.body .formula
  assertionsTyped : ∀ f ∈ m.assertions, Typed m [] f.body .formula
  commandTargets : ∀ c ∈ m.commands, c.bound ≤ 256 ∧
    match c.kind with
    | .runPredicate => c.target ∈ m.preds.map Pred.id
    | .runFact => c.target ∈ m.facts.map NamedFormula.id
    | .checkAssertion => c.target ∈ m.assertions.map NamedFormula.id
  fieldUnique : (m.fields.map Field.id).Nodup
  predUnique : (m.preds.map Pred.id).Nodup
  fieldsValid : ∀ f ∈ m.fields, f.owner ∈ m.sigs ∧ SchemaOK m.sigs f.range ∧ SchemaOK m.sigs (f.owner :: f.range)
  paramsBound : ∀ p ∈ m.preds, p.params.length ≤ 32
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
theorem utf8_positive (s : Scalar) : 0 < utf8Width s := by
  simp only [utf8Width]; split <;> simp_all <;> split <;> simp_all <;> split <;> omega
theorem utf16_positive (s : Scalar) : 0 < utf16Width s := by
  simp only [utf16Width]; split <;> omega

theorem strict_extension (w : Scalar → Nat) (positive : ∀ c, 0 < w c)
    (pre : List Scalar) (c : Scalar) (suffix : List Scalar) :
    widthSum w pre < widthSum w (pre ++ c :: suffix) := by
  rw [width_append]
  simp only [widthSum, List.map_cons, List.sum_cons]
  have h := positive c
  omega

theorem equal_width_of_nested_prefix (w : Scalar → Nat) (positive : ∀ c, 0 < w c)
    {xs ys : List Scalar} (p : xs <+: ys) (h : widthSum w xs = widthSum w ys) : xs = ys := by
  obtain ⟨tail, rfl⟩ := p
  cases tail with
  | nil => simp
  | cons c rest =>
    have lt := strict_extension w positive xs c rest
    omega

theorem boundary_injective (w : Scalar → Nat) (positive : ∀ c, 0 < w c)
    {xs ys full : List Scalar} (hx : xs <+: full) (hy : ys <+: full)
    (h : widthSum w xs = widthSum w ys) : xs = ys := by
  rcases List.prefix_or_prefix_of_prefix hx hy with p | p
  · exact equal_width_of_nested_prefix w positive p h
  · exact (equal_width_of_nested_prefix w positive p h.symm).symm

def encodeScalar (s : Scalar) : Bytes :=
  if s.val < 0x80 then [UInt8.ofNat s.val]
  else if s.val < 0x800 then [UInt8.ofNat (0xc0 + s.val / 64), UInt8.ofNat (0x80 + s.val % 64)]
  else if s.val < 0x10000 then [UInt8.ofNat (0xe0 + s.val / 4096), UInt8.ofNat (0x80 + s.val / 64 % 64), UInt8.ofNat (0x80 + s.val % 64)]
  else [UInt8.ofNat (0xf0 + s.val / 262144), UInt8.ofNat (0x80 + s.val / 4096 % 64), UInt8.ofNat (0x80 + s.val / 64 % 64), UInt8.ofNat (0x80 + s.val % 64)]
def encodeUtf8 (xs : List Scalar) : Bytes := xs.flatMap encodeScalar

inductive OccurrenceRole where | expression | operator | reference | binder deriving DecidableEq, Repr
structure Occurrence where
  id : Id
  source : Bytes
  startPrefix : List Scalar
  selected : List Scalar
  remaining : List Scalar
  rootIndex : Nat
  path : List Nat
  role : OccurrenceRole

def OccurrenceBound (o : Occurrence) : Prop := widthSum utf16Width o.startPrefix ≤ widthSum utf16Width (o.startPrefix ++ o.selected)
theorem occurrence_bound (o : Occurrence) : OccurrenceBound o := prefix_bound _ _ _

structure RevisionOccurrence where
  revision : Nat
  occurrence : Occurrence

/- Serialized atomic specification, not a proof of database refinement. -/
structure Scope where
  principal : Id
  launch : Id
  workspace : Id
  document : Id
  key : Id
  deriving DecidableEq, Repr
structure Artifact where
  bytes : Bytes
  moduleIR : Module
  scalars : List Scalar
  occurrences : List Occurrence

def CandidateValid (a : Artifact) : Prop :=
  (∃ edges rank, CheckedModule a.moduleIR edges rank) ∧
  a.bytes.length ≤ 1048576 ∧ a.occurrences.length ≤ 30000 ∧
  encodeUtf8 a.scalars = a.bytes ∧
  (a.occurrences.map Occurrence.id).Nodup ∧
  (a.occurrences.map (fun o => (o.rootIndex, o.path, o.role))).Nodup ∧
  ∀ o ∈ a.occurrences, o.source = a.bytes ∧
    (o.startPrefix ++ o.selected) ++ o.remaining = a.scalars ∧ OccurrenceBound o ∧
    ((moduleExpressions a.moduleIR)[o.rootIndex]?.bind (fun root => follow root o.path)).isSome
inductive Direction where | undo | redo deriving DecidableEq, Repr
inductive Operation where | replace | restore (direction : Direction) (targetRevision : Nat) deriving DecidableEq, Repr
structure Request where
  bytes : Bytes
  digest : Bytes
  base : Nat
  policy : Nat
  operation : Operation
  candidate : Artifact

inductive Outcome where | committed (revision : Nat) | denied deriving DecidableEq, Repr
structure Receipt where
  scope : Scope
  requestBytes : Bytes
  digest : Bytes
  outcome : Outcome
  deriving DecidableEq, Repr
structure State where
  revision : Nat
  history : List Artifact
  receipts : List Receipt
  policy : Nat

def receipt (s : State) (k : Scope) : Option Receipt := s.receipts.find? (fun r => r.scope == k)
inductive Result where | replay (outcome : Outcome) | collision | accepted (revision : Nat) | rejected | unknown deriving DecidableEq, Repr
def OperationValid (s : State) (q : Request) (a : Artifact) : Prop :=
  match q.operation with
  | .replace => True
  | .restore _ target => 0 < target ∧ s.history[target - 1]? = some a

def Admission (s : State) (q : Request) (a : Artifact) : Prop :=
  s.history.length < 10000 ∧ s.receipts.length < 10000 ∧
  q.bytes.length ≤ 2097152 ∧ a.bytes.length ≤ 1048576
inductive Step (authorized : Prop) : State → Scope → Request → Artifact → Result → State → Prop where
  | replay : authorized → receipt s k = some r → r.requestBytes = q.bytes → Step authorized s k q a (.replay r.outcome) s
  | collision : authorized → receipt s k = some r → r.requestBytes ≠ q.bytes → Step authorized s k q a .collision s
  | accept : authorized → receipt s k = none → Admission s q a → q.base = s.revision → q.policy = s.policy → a = q.candidate → OperationValid s q a → CandidateValid a →
      Step authorized s k q a (.accepted (s.revision + 1))
        ⟨s.revision + 1, s.history ++ [a], ⟨k,q.bytes,q.digest,.committed (s.revision + 1)⟩ :: s.receipts, s.policy⟩
  | reject : authorized → receipt s k = none → Step authorized s k q a .rejected s
  | denyAuth : ¬ authorized → Step authorized s k q a .rejected s
  | deniedReceipt : authorized → receipt s k = none → Admission s q a →
      (q.base ≠ s.revision ∨ q.policy ≠ s.policy ∨ a ≠ q.candidate ∨ ¬ OperationValid s q a ∨ ¬ CandidateValid a) →
      Step authorized s k q a .rejected
        ⟨s.revision, s.history, ⟨k,q.bytes,q.digest,.denied⟩ :: s.receipts, s.policy⟩
  | unknown : authorized → receipt s k = none → Admission s q a → q.base = s.revision → q.policy = s.policy → a = q.candidate → OperationValid s q a → CandidateValid a →
      Step authorized s k q a .unknown
        ⟨s.revision + 1, s.history ++ [a], ⟨k,q.bytes,q.digest,.committed (s.revision + 1)⟩ :: s.receipts, s.policy⟩

theorem replay_available {auth s k q a r} (ha : auth) (hr : receipt s k = some r) (hb : r.requestBytes = q.bytes) : Step auth s k q a (.replay r.outcome) s := .replay ha hr hb
theorem collision_unchanged {auth s k q a out} (h : Step auth s k q a .collision out) : out = s := by cases h; rfl
theorem accepted_checked {auth s k q a n out}
    (h : Step auth s k q a (.accepted n) out) : CandidateValid a := by
  cases h with | accept _ _ _ _ _ _ _ checked => exact checked

theorem accepted_appends {auth s k q a n out} (h : Step auth s k q a (.accepted n) out) : out.revision = s.revision + 1 ∧ out.history = s.history ++ [a] := by cases h; exact ⟨rfl,rfl⟩
theorem rejected_head_unchanged {auth s k q a out} (h : Step auth s k q a .rejected out) :
    out.revision = s.revision ∧ out.history = s.history := by cases h <;> exact ⟨rfl,rfl⟩

theorem same_base_cannot_commit_twice {auth s k1 k2 q1 q2 a1 a2 n1 n2 middle out}
    (first : Step auth s k1 q1 a1 (.accepted n1) middle)
    (second : Step auth middle k2 q2 a2 (.accepted n2) out)
    (sameBase : q2.base = s.revision) : False := by
  have firstRevision := (accepted_appends first).1
  cases second with
  | accept _ _ _ base _ _ _ _ => omega

theorem stale_records_denial {auth s k q a} (ha : auth) (hr : receipt s k = none)
    (quota : Admission s q a) (stale : q.base ≠ s.revision) :
    Step auth s k q a .rejected
      ⟨s.revision,s.history,⟨k,q.bytes,q.digest,.denied⟩ :: s.receipts,s.policy⟩ :=
  Step.deniedReceipt ha hr quota (Or.inl stale)

theorem accepted_can_lose_response {auth s k q a n out}
    (h : Step auth s k q a (.accepted n) out) : Step auth s k q a .unknown out := by
  cases h with
  | accept ha hr quota hb hp hc ho hv => exact Step.unknown ha hr quota hb hp hc ho hv

theorem same_digest_different_bytes_rejected {auth s k q a r}
    (ha : auth) (hr : receipt s k = some r) (_digestSame : r.digest = q.digest)
    (bytesDiffer : r.requestBytes ≠ q.bytes) : Step auth s k q a .collision s := by
  exact Step.collision ha hr bytesDiffer

theorem unauthorized_unchanged {auth s k q a} (h : ¬ auth) :
    Step auth s k q a .rejected s := Step.denyAuth h

theorem stored_denial_replays {auth : Prop} {s : State} {k : Scope} {q : Request} {a : Artifact}
    (ha : auth) :
    Step auth ⟨s.revision, s.history, ⟨k,q.bytes,q.digest,.denied⟩ :: s.receipts, s.policy⟩
      k q a (.replay .denied)
      ⟨s.revision, s.history, ⟨k,q.bytes,q.digest,.denied⟩ :: s.receipts, s.policy⟩ := by
  apply Step.replay (r := ⟨k,q.bytes,q.digest,.denied⟩) ha
  · simp [receipt]
  · rfl

/- Undo/redo is a checked historical selection, then the same append transition.
   Direction and target are included by the request-bytes adapter. -/
inductive HistoricalStep (authorized : Prop)
    (target : Artifact) : State → Scope → Request → Direction → Result → State → Prop where
  | restore : target ∈ s.history → q.operation = .restore direction targetRevision →
      s.history[targetRevision - 1]? = some target → Step authorized s k q target result out →
      HistoricalStep authorized target s k q direction result out

theorem historical_accept_appends {auth target s k q direction n out}
    (h : HistoricalStep auth target s k q direction (.accepted n) out) :
    target ∈ s.history ∧ out.history = s.history ++ [target] := by
  cases h with
  | restore hist _ _ st => exact ⟨hist, (accepted_appends st).2⟩

theorem historical_accept_checked {auth target s k q direction n out}
    (h : HistoricalStep auth target s k q direction (.accepted n) out) :
    CandidateValid target := by
  cases h with
  | restore _ _ _ st => exact accepted_checked st

theorem receipt_head (s : State) (k : Scope) (q : Request) (n : Outcome) :
    receipt ⟨s.revision, s.history, ⟨k,q.bytes,q.digest,n⟩ :: s.receipts, s.policy⟩ k =
      some ⟨k,q.bytes,q.digest,n⟩ := by
  simp [receipt]

theorem same_key_cannot_commit_twice {auth s k q1 q2 a1 a2 n1 n2 middle out}
    (first : Step auth s k q1 a1 (.accepted n1) middle)
    (second : Step auth middle k q2 a2 (.accepted n2) out) : False := by
  cases first with
  | accept _ _ _ _ _ _ _ _ =>
    cases second with
    | accept _ hr _ _ _ _ _ _ =>
      simp [receipt] at hr

theorem committed_retry {auth s k q a n out}
    (ha : auth) (h : Step auth s k q a (.accepted n) out) :
    Step auth out k q a (.replay (.committed n)) out := by
  cases h with
  | accept _ _ _ _ _ _ _ _ =>
    exact Step.replay (r := ⟨k,q.bytes,q.digest,.committed (s.revision + 1)⟩) ha (receipt_head _ _ _ _) rfl

theorem unknown_retry {auth s k q a out}
    (ha : auth) (h : Step auth s k q a .unknown out) :
    Step auth out k q a (.replay (.committed (s.revision + 1))) out := by
  cases h with
  | unknown _ _ _ _ _ _ _ _ =>
    exact Step.replay (r := ⟨k,q.bytes,q.digest,.committed (s.revision + 1)⟩) ha (receipt_head _ _ _ _) rfl

/- Append-only state gives indefinite retention inside this transition system;
   admission, finite storage quotas and external deletion are outside it. -/
theorem receipts_preserved {auth s k q a result out}
    (h : Step auth s k q a result out) :
    ∀ r ∈ s.receipts, r ∈ out.receipts := by
  cases h <;> simp_all

theorem history_preserved {auth s k q a result out}
    (h : Step auth s k q a result out) :
    ∀ old ∈ s.history, old ∈ out.history := by
  cases h <;> simp_all

def RevisionConsistent (s : State) : Prop := s.history.length = s.revision

theorem revision_consistency_preserved {auth s k q a result out}
    (before : RevisionConsistent s) (step : Step auth s k q a result out) :
    RevisionConsistent out := by
  cases step <;> simp_all [RevisionConsistent]

inductive Steps (auth : Prop) : State → State → Prop where
  | refl : Steps auth s s
  | next : Step auth s k q a result middle → Steps auth middle out → Steps auth s out

theorem receipts_retained {auth s out} (h : Steps auth s out) :
    ∀ r ∈ s.receipts, r ∈ out.receipts := by
  induction h with
  | refl => simp
  | next step _ ih =>
    intro r mem
    exact ih r (receipts_preserved step r mem)

theorem history_retained {auth s out} (h : Steps auth s out) :
    ∀ a ∈ s.history, a ∈ out.history := by
  induction h with
  | refl => simp
  | next step _ ih =>
    intro a mem
    exact ih a (history_preserved step a mem)

def exModule : Module := ⟨[1], [], [], [.test .some (.sigRef 1)], [(1,.set)], [], [], []⟩
theorem witness_typed_test : Typed exModule [] (.test .some (.sigRef 1)) .formula := by
  apply Typed.test (s := [1])
  · apply Typed.sigRef; simp [exModule]
  · simp [SchemaOK, exModule]
theorem witness_unbound_denied : ¬ Typed exModule [] (.varRef 7) (.relation [1]) := by
  intro h
  have v := variable_resolves h
  simp [lookup] at v
theorem witness_boolean_family (op : BoolOp) :
    Typed exModule [] (.bool op (.test .some (.sigRef 1)) (.test .no (.sigRef 1))) .formula := by
  apply Typed.bool
  all_goals apply Typed.test (s := [1])
  all_goals first | (apply Typed.sigRef; simp [exModule]) | simp [SchemaOK, exModule]

theorem witness_test_family (op : TestOp) :
    Typed exModule [] (.test op (.sigRef 1)) .formula := by
  apply Typed.test (s := [1])
  · apply Typed.sigRef; simp [exModule]
  · simp [SchemaOK, exModule]

theorem witness_compare_family (op : CompareOp) :
    Typed exModule [] (.compare op (.sigRef 1) (.sigRef 1)) .formula := by
  apply Typed.compare (s := [1])
  · apply Typed.sigRef; simp [exModule]
  · apply Typed.sigRef; simp [exModule]
  · simp [SchemaOK, exModule]

theorem witness_set_family (op : SetOp) :
    Typed exModule [] (.set op (.sigRef 1) (.sigRef 1)) (.relation [1]) := by
  apply Typed.set
  · apply Typed.sigRef; simp [exModule]
  · apply Typed.sigRef; simp [exModule]
  · simp [SchemaOK, exModule]

theorem witness_quant_family (op : QuantOp) :
    Typed exModule [] (.quant op 7 1 (.test .some (.varRef 7))) .formula := by
  apply Typed.quant
  · simp [exModule]
  · rfl
  · apply Typed.test (s := [1])
    · apply Typed.varRef; rfl
    · simp [SchemaOK, exModule]

theorem witness_unary_transpose_denied :
    ¬ ∃ s t, Typed exModule [] (.transpose (.sigRef 1)) (.relation [s,t]) := by
  intro ⟨s,t,h⟩
  cases h with
  | transpose inner => cases inner

theorem witness_unknown_predicate_denied :
    ¬ Typed exModule [] (.call 8 []) .formula := by
  intro h
  cases h with
  | call found _ => simp [lookupPred, predsEnv, exModule] at found

theorem witness_bad_scope_denied :
    ¬ Typed exModule [] (.test .some (.varRef 7)) .formula := by
  intro h
  cases h with
  | test inner _ =>
    cases inner with
    | varRef found => simp [lookup] at found

def relationModule : Module :=
  ⟨[1,2,3], [⟨4,1,[2]⟩,⟨5,2,[3]⟩], [], [], [(1,.set),(2,.set),(3,.set)], [], [], []⟩

theorem witness_join : Typed relationModule [] (.join (.fieldRef 4) (.fieldRef 5)) (.relation [1,3]) := by
  apply Typed.join (left := [1]) (endpoint := 2) (right := [3])
  · apply Typed.fieldRef; rfl
  · apply Typed.fieldRef; rfl
  · simp [SchemaOK, relationModule]

theorem witness_product : Typed relationModule [] (.product (.sigRef 1) (.sigRef 2)) (.relation [1,2]) := by
  apply Typed.product (s := [1]) (t := [2])
  · apply Typed.sigRef; simp [relationModule]
  · apply Typed.sigRef; simp [relationModule]
  · simp [SchemaOK, relationModule]
  · simp [SchemaOK, relationModule]
  · simp [SchemaOK, relationModule]

theorem witness_transpose : Typed relationModule [] (.transpose (.fieldRef 4)) (.relation [2,1]) := by
  apply Typed.transpose
  apply Typed.fieldRef; rfl

def callModule : Module :=
  ⟨[1], [], [⟨5, [(7,[1])], .test .some (.varRef 7)⟩], [], [(1,.set)], [], [], []⟩

theorem witness_predicate_call : Typed callModule [] (.call 5 [.sigRef 1]) .formula := by
  apply Typed.call (ss := [[1]])
  · rfl
  · apply TypedArgs.cons
    · apply Typed.sigRef; simp [callModule]
    · exact TypedArgs.nil

theorem witness_wrong_call_arity : ¬ Typed callModule [] (.call 5 []) .formula := by
  intro h
  cases h with
  | call found args =>
    simp [lookupPred, predsEnv, callModule] at found
    subst_vars
    cases args

set_option linter.unusedSimpArgs false in
theorem oracle_join_accept : infer relationModule [] (.join (.fieldRef 4) (.fieldRef 5)) = some (.relation [1,3]) := by simp [infer, relationModule, exModule, callModule, fieldsEnv, lookup, lookupPred, predsEnv, schemaOkB]
set_option linter.unusedSimpArgs false in
theorem oracle_bad_scope_deny : infer exModule [] (.test .some (.varRef 7)) = none := by simp [infer, relationModule, exModule, callModule, fieldsEnv, lookup, lookupPred, predsEnv, schemaOkB]
set_option linter.unusedSimpArgs false in
theorem oracle_bad_arity_deny : infer callModule [] (.call 5 []) = none := by simp [infer, relationModule, exModule, callModule, fieldsEnv, lookup, lookupPred, predsEnv, schemaOkB]
set_option linter.unusedSimpArgs false in
theorem oracle_call_accept : infer callModule [] (.call 5 [.sigRef 1]) = some .formula := by simp [infer, relationModule, exModule, callModule, fieldsEnv, lookup, lookupPred, predsEnv, schemaOkB]
set_option linter.unusedSimpArgs false in
theorem oracle_unary_transpose_deny : infer exModule [] (.transpose (.sigRef 1)) = none := by simp [infer, relationModule, exModule, callModule, fieldsEnv, lookup, lookupPred, predsEnv, schemaOkB]

def exampleScope : Scope := ⟨1,2,3,4,5⟩
def exampleArtifact : Artifact := ⟨[], exModule, [], []⟩
def exampleRequest : Request := ⟨[1], [9], 0, 3, .replace, exampleArtifact⟩
def exampleState : State := ⟨0, [], [], 3⟩
theorem witness_commit : Step True exampleState exampleScope exampleRequest exampleArtifact
    (.accepted 1) ⟨1,[exampleArtifact],[⟨exampleScope,[1],[9],.committed 1⟩],3⟩ := by
  apply Step.accept
  · trivial
  · simp [receipt, exampleState]
  · simp [Admission, exampleState, exampleRequest, exampleArtifact]
  · rfl
  · rfl
  · rfl
  · simp [OperationValid, exampleRequest]
  · refine ⟨⟨[], fun _ => 0, ?_⟩, ?_⟩
    · change CheckedModule exModule [] (fun _ => 0)
      constructor <;> simp [exModule, Ranked, allBinderIds, binderIds, allDeclarationIds, moduleNodeCount, exprNodes, moduleExpressions, exprDepth]
      apply Typed.test (s := [1])
      · apply Typed.sigRef; simp
      · simp [SchemaOK]
    · simp [exampleArtifact, encodeUtf8]

theorem witness_replay_changed_policy : Step True
    ⟨1,[exampleArtifact],[⟨exampleScope,[1],[9],.committed 1⟩],4⟩ exampleScope
    exampleRequest exampleArtifact (.replay (.committed 1))
    ⟨1,[exampleArtifact],[⟨exampleScope,[1],[9],.committed 1⟩],4⟩ := by
  apply Step.replay (r := ⟨exampleScope,[1],[9],.committed 1⟩)
  all_goals simp [receipt, exampleRequest]

theorem witness_digest_collision : Step True
    ⟨1,[exampleArtifact],[⟨exampleScope,[2],[9],.committed 1⟩],3⟩ exampleScope
    exampleRequest exampleArtifact .collision
    ⟨1,[exampleArtifact],[⟨exampleScope,[2],[9],.committed 1⟩],3⟩ := by
  apply Step.collision (r := ⟨exampleScope,[2],[9],.committed 1⟩)
  all_goals simp [receipt, exampleRequest]

end Allow.DocumentDraft
