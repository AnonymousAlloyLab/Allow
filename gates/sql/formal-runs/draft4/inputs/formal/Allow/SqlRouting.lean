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
def wellFormed (s : State) : Prop :=
  (∀ st ∈ s.statements, admitted st.request st.report) ∧
  (∀ p ∈ s.portals, admitted p.request p.report)
inductive Reachable : State → Prop where
  | initial : Reachable ⟨[], []⟩
  | parsed {s : State} {st : Statement} : Reachable s → admitted st.request st.report → Reachable (parse s st)
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
theorem denial_witness : ¬ admitted sampleRequest { sampleReport with isOpaque := true } := by
  apply isOpaque_denied
  rfl
end Allow.SqlRouting
