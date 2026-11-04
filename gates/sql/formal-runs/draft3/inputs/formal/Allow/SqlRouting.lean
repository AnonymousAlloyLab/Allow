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
  statementName : String
structure State where
  statements : List Statement
  portals : List Portal
def execute (s : State) (name : String) : Prop :=
  ∃ p, s.portals.find? (fun p => p.name == name) = some p ∧
    ∃ st, s.statements.find? (fun st => st.name == p.statementName) = some st ∧ admitted st.request st.report
theorem execute_accepted {s : State} {name : String} (h : execute s name) :
  ∃ p, s.portals.find? (fun p => p.name == name) = some p ∧
    ∃ st, s.statements.find? (fun st => st.name == p.statementName) = some st ∧ admitted st.request st.report := h
/-- Parse and Bind extend only this connection's state; Bind carries no SQL. -/
def parse (s : State) (st : Statement) : State := ⟨st :: s.statements, s.portals⟩
def bind (s : State) (p : Portal) : State := ⟨s.statements, p :: s.portals⟩
theorem parse_bind_execute (s : State) (st : Statement) (p : Portal)
    (named : st.name = p.statementName) (valid : admitted st.request st.report) :
    execute (bind (parse s st) p) p.name := by
  refine ⟨p, by simp [bind], st, ?_, valid⟩
  simp [bind, parse, named]
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
def samplePortal : Portal := ⟨"p", "s"⟩
def sampleState : State := ⟨[sampleStatement], [samplePortal]⟩
theorem admission_witness : admitted sampleRequest sampleReport := by simp [admitted, sampleRequest, sampleReport]
theorem execution_witness : execute sampleState "p" := by simp [execute, sampleState, samplePortal, sampleStatement, admitted, sampleRequest, sampleReport]
theorem denial_witness : ¬ admitted sampleRequest { sampleReport with isOpaque := true } := by
  apply isOpaque_denied
  rfl
end Allow.SqlRouting
