import Std

/- Standalone finite deployment policy model. No implementation refinement,
   cryptographic, IIS/SSH execution, performance or licensing claim. -/
namespace Allow.IisDeployment

inductive Host where
  | tunnel | public | hostile | absent | duplicate
  deriving DecidableEq, Repr
inductive Origin where
  | absent | configured | hostile | duplicate
  deriving DecidableEq, Repr
inductive Capability where
  | valid | absent | invalid | duplicate
  deriving DecidableEq, Repr

structure Request where
  host : Host
  origin : Origin
  capability : Capability
  forwardedAuthority : Bool
  deriving DecidableEq, Repr

def route (r : Request) : Prop :=
  r.host = .tunnel ∧ (r.origin = .absent ∨ r.origin = .configured)
instance (r : Request) : Decidable (route r) := inferInstanceAs (Decidable (_ ∧ _))
def api (r : Request) : Prop := route r ∧ r.capability = .valid
instance (r : Request) : Decidable (api r) := inferInstanceAs (Decidable (_ ∧ _))

theorem route_exact (r : Request) : route r ↔
    r.host = .tunnel ∧ (r.origin = .absent ∨ r.origin = .configured) := Iff.rfl

theorem api_requires_exact_capability (r : Request) (h : api r) :
    r.capability = .valid := h.2

theorem hostile_or_duplicate_host_rejected (r : Request)
    (h : r.host = .hostile ∨ r.host = .duplicate ∨ r.host = .public ∨ r.host = .absent) :
    ¬ route r := by
  intro allowed
  rcases h with h | h | h | h <;> simp_all [route]

theorem hostile_or_duplicate_origin_rejected (r : Request)
    (h : r.origin = .hostile ∨ r.origin = .duplicate) : ¬ route r := by
  intro allowed
  rcases h with h | h <;> simp_all [route]

theorem absent_invalid_duplicate_capability_rejected (r : Request)
    (h : r.capability = .absent ∨ r.capability = .invalid ∨ r.capability = .duplicate) :
    ¬ api r := by
  intro allowed
  rcases h with h | h | h <;> simp_all [api]

theorem forwarded_authority_irrelevant (r : Request) (f : Bool) :
    route { r with forwardedAuthority := f } ↔ route r := Iff.rfl

theorem forwarded_authority_cannot_bypass (r : Request) (h : ¬ route r) :
    ¬ api { r with forwardedAuthority := true } := by
  exact fun allowed => h allowed.1

def browserWitness : Request := ⟨.tunnel, .configured, .valid, false⟩
def capabilityClientWitness : Request := ⟨.tunnel, .absent, .valid, true⟩
theorem browser_admissible : api browserWitness := by decide
theorem capability_client_admissible : api capabilityClientWitness := by decide

inductive ConfigValue where
  | default | documentAdvisoryTier1 | unknown
  deriving DecidableEq, Repr
inductive Operation where
  | advisory | durable | solver
  deriving DecidableEq, Repr
inductive Profile where
  | default | tier1
  deriving DecidableEq, Repr

def configured (value : ConfigValue) : Prop := value ≠ .unknown
instance (v : ConfigValue) : Decidable (configured v) := inferInstanceAs (Decidable (_ ≠ _))
def select (value : ConfigValue) (op : Operation) : Profile :=
  if value = .documentAdvisoryTier1 ∧ op = .advisory then .tier1 else .default

theorem unknown_config_rejected : ¬ configured .unknown := by decide
theorem closed_config_values (value : ConfigValue) :
    configured value ↔ value = .default ∨ value = .documentAdvisoryTier1 := by
  cases value <;> decide

theorem advisory_tier1_selected : select .documentAdvisoryTier1 .advisory = .tier1 := by decide
theorem local_default_preserved (op : Operation) : select .default op = .default := by
  simp [select]
theorem durable_default (value : ConfigValue) : select value .durable = .default := by
  simp [select]
theorem solver_default (value : ConfigValue) : select value .solver = .default := by
  simp [select]
theorem tier1_only_advisory (value : ConfigValue) (op : Operation)
    (h : select value op = .tier1) : value = .documentAdvisoryTier1 ∧ op = .advisory := by
  by_cases selected : value = .documentAdvisoryTier1 ∧ op = .advisory
  · exact selected
  · simp [select, selected] at h

def poolEnabled : Bool := false
theorem pool_disabled : poolEnabled = false := rfl

/-- Selection and acceptance are independent inputs: selection supplies no evidence. -/
def accepted (_selection : ConfigValue) (targetEvidence : Bool) : Bool := targetEvidence
theorem profile_selection_does_not_accept (value : ConfigValue) :
    accepted value false = false := rfl
theorem acceptance_requires_evidence (value : ConfigValue) (evidence : Bool)
    (h : accepted value evidence = true) : evidence = true := h

inductive Payload where
  | application | compiled | parser | publicConfig | notice
  | runtime | credentials | dataset | checkpoint | browserState | privateToken | virtualenv
  deriving DecidableEq, Repr

def eligible : Payload → Bool
  | .application | .compiled | .parser | .publicConfig | .notice => true
  | _ => false

def privatePayload (p : Payload) : Prop :=
  p = .runtime ∨ p = .credentials ∨ p = .dataset ∨ p = .checkpoint ∨
  p = .browserState ∨ p = .privateToken ∨ p = .virtualenv
instance (p : Payload) : Decidable (privatePayload p) := inferInstanceAs (Decidable (_ ∨ _))

theorem private_payload_excluded (p : Payload) (h : privatePayload p) : eligible p = false := by
  cases p <;> simp_all [privatePayload, eligible]
theorem eligible_contains_no_private_payload (p : Payload) (h : eligible p = true) :
    ¬ privatePayload p := by
  intro private
  have excluded := private_payload_excluded p private
  simp_all

def witnessPackage : List Payload := [.application, .compiled, .parser, .publicConfig, .notice]
theorem package_positive_witness : witnessPackage ≠ [] ∧
    ∀ p ∈ witnessPackage, eligible p = true := by
  simp [witnessPackage, eligible]

end Allow.IisDeployment
