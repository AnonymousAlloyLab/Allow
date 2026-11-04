namespace Allow.SqlRouting
structure Request where
  sql : String
  binary : String
  profile : String
  policy : String
  deriving DecidableEq
structure Report where
  sql : String
  binary : String
  profile : String
  policy : String
  success : Bool
  derivation : Bool
  preserved : Bool
  isOpaque : Bool
  deriving DecidableEq
def admitted (p : Request) (r : Report) : Prop :=
  r.sql = p.sql ∧ r.binary = p.binary ∧ r.profile = p.profile ∧ r.policy = p.policy ∧
  r.success = true ∧ r.derivation = true ∧ r.preserved = true ∧ r.isOpaque = false
theorem exact_request {p : Request} {r : Report} (h : admitted p r) : r.sql = p.sql := h.1
theorem pinned_identity {p : Request} {r : Report} (h : admitted p r) : r.binary = p.binary ∧ r.profile = p.profile ∧ r.policy = p.policy := ⟨h.2.1, h.2.2.1, h.2.2.2.1⟩
theorem mismatch_denied {p : Request} {r : Report} (h : r.sql ≠ p.sql) : ¬ admitted p r := fun a => h a.1
theorem binary_mismatch_denied {p : Request} {r : Report} (h : r.binary ≠ p.binary) : ¬ admitted p r := fun a => h a.2.1
theorem profile_mismatch_denied {p : Request} {r : Report} (h : r.profile ≠ p.profile) : ¬ admitted p r := fun a => h a.2.2.1
theorem parser_failure_denied {p : Request} {r : Report} (h : r.success = false) : ¬ admitted p r := by
  intro a
  have bad := a.2.2.2.2.1
  rw [h] at bad
  cases bad
theorem isOpaque_denied {p : Request} {r : Report} (h : r.isOpaque = true) : ¬ admitted p r := by
  intro a
  have bad := a.2.2.2.2.2.2.2
  rw [h] at bad
  cases bad
structure CacheEntry where
  request : Request
  report : Report
def cacheReuse (p : Request) (e : CacheEntry) : Prop := p = e.request ∧ admitted e.request e.report
theorem cache_exact {p : Request} {e : CacheEntry} (h : cacheReuse p e) : p = e.request ∧ admitted p e.report := by
  rcases h with ⟨same, accepted⟩
  exact ⟨same, same ▸ accepted⟩
structure Statement where
  name : String
  request : Request
  report : Report
structure Portal where
  name : String
  request : Request
  report : Report
structure State where
  statements : List Statement
  portals : List Portal
def parse (s : State) (st : Statement) : State := ⟨st :: s.statements, s.portals⟩
def bind (s : State) (name : String) (st : Statement) : State :=
  ⟨s.statements, ⟨name, st.request, st.report⟩ :: s.portals⟩
/-- The parser must supply the body span of the whole PREPARE source. Classification
    and the correctness of this span remain trusted adapter obligations. -/
structure NativePrepare where
  statement : Statement
  body : String
def bodyPart (p : NativePrepare) : Prop :=
  p.body ≠ "" ∧ ∃ before after, p.statement.request.sql = before ++ p.body ++ after
def nativePrepare (s : State) (p : NativePrepare) : State := parse s p.statement
/-- SQL EXECUTE is admitted itself and resolves the shared statement namespace. -/
def nativeExecute (s : State) (name : String) (q : Request) (r : Report) : Prop :=
  admitted q r ∧ ∃ st, s.statements.find? (fun x => x.name == name) = some st
/-- Cache lookup is pure; successful reuse does not create a server statement. -/
def cacheLookup (s : State) (_entry : CacheEntry) : State := s

def wellFormed (s : State) : Prop :=
  (∀ st ∈ s.statements, admitted st.request st.report) ∧
  (∀ p ∈ s.portals, admitted p.request p.report)
inductive Reachable : State → Prop where
  | initial : Reachable ⟨[], []⟩
  | parsed {s : State} {st : Statement} : Reachable s → admitted st.request st.report → Reachable (parse s st)
  | nativePrepared {s : State} {p : NativePrepare} : Reachable s →
      admitted p.statement.request p.statement.report → bodyPart p → Reachable (nativePrepare s p)
  | bound {s : State} {st : Statement} (name : String) : Reachable s →
      s.statements.find? (fun x => x.name == st.name) = some st → Reachable (bind s name st)
theorem reachable_wellFormed {s : State} (h : Reachable s) : wellFormed s := by
  induction h with
  | initial => simp [wellFormed]
  | parsed prev valid ih =>
      constructor
      · intro st member
        simp only [parse, List.mem_cons] at member
        rcases member with same | member
        · subst st; exact valid
        · exact ih.1 st member
      · exact ih.2
  | nativePrepared prev valid body ih =>
      constructor
      · intro st member
        simp only [nativePrepare, parse, List.mem_cons] at member
        rcases member with same | member
        · subst st; exact valid
        · exact ih.1 st member
      · exact ih.2
  | bound name prev found ih =>
      constructor
      · exact ih.1
      · intro p member
        simp only [bind, List.mem_cons] at member
        rcases member with same | member
        · subst p; exact ih.1 _ (List.mem_of_find?_eq_some found)
        · exact ih.2 p member
def execute (s : State) (name : String) : Option Portal :=
  s.portals.find? (fun p => p.name == name)
theorem execute_accepted {s : State} {name : String} {p : Portal}
    (reachable : Reachable s) (found : execute s name = some p) : admitted p.request p.report := by
  exact (reachable_wellFormed reachable).2 p (List.mem_of_find?_eq_some found)
theorem parse_bind_execute (s : State) (st : Statement) (name : String)
    (reachable : Reachable s) (valid : admitted st.request st.report) :
    Reachable (bind (parse s st) name st) ∧
    execute (bind (parse s st) name st) name = some ⟨name, st.request, st.report⟩ := by
  constructor
  · apply Reachable.bound name (Reachable.parsed reachable valid)
    simp [parse]
  · simp [execute, bind]
theorem native_execute_provenance {s : State} {name : String} {q : Request} {r : Report}
    (reachable : Reachable s) (h : nativeExecute s name q r) :
    admitted q r ∧ ∃ st, s.statements.find? (fun x => x.name == name) = some st ∧ admitted st.request st.report := by
  rcases h with ⟨own, st, found⟩
  exact ⟨own, st, found, (reachable_wellFormed reachable).1 st (List.mem_of_find?_eq_some found)⟩
theorem native_unknown_denied {s : State} {name : String} {q : Request} {r : Report}
    (unknown : s.statements.find? (fun x => x.name == name) = none) : ¬ nativeExecute s name q r := by
  intro h
  rcases h.2 with ⟨st, found⟩
  rw [unknown] at found
  cases found
theorem native_prepare_bind (s : State) (p : NativePrepare) (portal : String)
    (reachable : Reachable s) (valid : admitted p.statement.request p.statement.report)
    (body : bodyPart p) :
    Reachable (bind (nativePrepare s p) portal p.statement) ∧
    execute (bind (nativePrepare s p) portal p.statement) portal = some ⟨portal, p.statement.request, p.statement.report⟩ := by
  constructor
  · apply Reachable.bound portal (Reachable.nativePrepared reachable valid body)
    simp [nativePrepare, parse]
  · simp [execute, bind]
theorem cache_does_not_prepare (s : State) (e : CacheEntry) :
    (cacheLookup s e).statements = s.statements := rfl
theorem derivation_failure_denied {p : Request} {r : Report} (h : r.derivation = false) : ¬ admitted p r := by
  intro a
  have bad := a.2.2.2.2.2.1
  rw [h] at bad
  cases bad
theorem preservation_failure_denied {p : Request} {r : Report} (h : r.preserved = false) : ¬ admitted p r := by
  intro a
  have bad := a.2.2.2.2.2.2.1
  rw [h] at bad
  cases bad
def sampleRequest : Request := ⟨"SELECT 1", "pinned", "profile", "v1"⟩
def sampleReport : Report := ⟨"SELECT 1", "pinned", "profile", "v1", true, true, true, false⟩
def sampleStatement : Statement := ⟨"s", sampleRequest, sampleReport⟩
def samplePortal : Portal := ⟨"p", sampleRequest, sampleReport⟩
def sampleState : State := ⟨[sampleStatement], [samplePortal]⟩
theorem admission_witness : admitted sampleRequest sampleReport := by simp [admitted, sampleRequest, sampleReport]
theorem execution_witness : execute sampleState "p" = some samplePortal := by simp [execute, sampleState, samplePortal]
def sampleNative : NativePrepare :=
  ⟨⟨"s", ⟨"PREPARE s AS SELECT 1", "pinned", "profile", "v1"⟩,
    ⟨"PREPARE s AS SELECT 1", "pinned", "profile", "v1", true, true, true, false⟩⟩, "SELECT 1"⟩
theorem native_prepare_witness :
    Reachable (nativePrepare ⟨[], []⟩ sampleNative) ∧ bodyPart sampleNative := by
  constructor
  · apply Reachable.nativePrepared Reachable.initial
    · simp [sampleNative, admitted]
    · exact ⟨by decide, "PREPARE s AS ", "", by rfl⟩
  · exact ⟨by decide, "PREPARE s AS ", "", by rfl⟩
def sampleExecuteRequest : Request := ⟨"EXECUTE s", "pinned", "profile", "v1"⟩
def sampleExecuteReport : Report := ⟨"EXECUTE s", "pinned", "profile", "v1", true, true, true, false⟩
theorem native_execute_witness :
    nativeExecute (nativePrepare ⟨[], []⟩ sampleNative) "s" sampleExecuteRequest sampleExecuteReport := by
  constructor
  · simp [admitted, sampleExecuteRequest, sampleExecuteReport]
  · exact ⟨sampleNative.statement, by simp [nativePrepare, parse, sampleNative]⟩
theorem denial_witness : ¬ admitted sampleRequest { sampleReport with isOpaque := true } := by
  apply isOpaque_denied
  rfl
/-- Abstract effect-cycle state. Cycle identifiers and the association of an
    acknowledgement to the ordered Q/Sync barriers are supplied by the adapter. -/
structure CycleState where
  pending : List Nat

def sourceAllowed (s : CycleState) : Prop := s.pending = []
def forwardEffect (s : CycleState) (cycle : Nat) : CycleState := ⟨cycle :: s.pending⟩
/-- Acknowledgement can release effects only after lexical statuses are validated. -/
def completeCycle (s : CycleState) (ack : Nat) (validated : Bool) : CycleState :=
  if validated then ⟨s.pending.filter (fun cycle => ack < cycle)⟩ else s

theorem pending_blocks_source (s : CycleState) (cycle : Nat)
    (h : cycle ∈ s.pending) : ¬ sourceAllowed s := by
  intro allowed
  change s.pending = [] at allowed
  rw [allowed] at h
  exact List.not_mem_nil h

theorem forward_blocks_source (s : CycleState) (cycle : Nat) :
    ¬ sourceAllowed (forwardEffect s cycle) := by
  simp [sourceAllowed, forwardEffect]

theorem unvalidated_retains (s : CycleState) (ack : Nat) :
    completeCycle s ack false = s := by
  rfl

theorem completed_retains_newer (s : CycleState) (ack cycle : Nat)
    (member : cycle ∈ s.pending) (newer : ack < cycle) :
    cycle ∈ (completeCycle s ack true).pending := by
  simp [completeCycle, member, newer]

theorem completed_removes_older (s : CycleState) (ack cycle : Nat)
    (older : cycle ≤ ack) : cycle ∉ (completeCycle s ack true).pending := by
  simp [completeCycle, Nat.not_lt_of_ge older]

theorem cycle_barrier_witness :
    ¬ sourceAllowed (forwardEffect ⟨[]⟩ 2) ∧
    (completeCycle ⟨[1, 2]⟩ 1 true).pending = [2] ∧
    sourceAllowed (completeCycle ⟨[1]⟩ 1 true) := by
  simp [sourceAllowed, forwardEffect, completeCycle]
end Allow.SqlRouting
