import Std

/- Finite anonymous workspace policy only. Opaque numbers represent allocated
   identities/capabilities, not cryptographic strength or implementation refinement. -/
namespace Allow.AnonymousWorkspaces

structure Scope where
  principal : Nat
  workspace : Nat
  launch : Nat
  deriving DecidableEq, Repr

inductive Phase where
  | provisioning | active | draining | quarantined
  deriving DecidableEq, Repr

structure Session where
  scope : Scope
  capability : Nat
  incarnation : Nat
  deadline : Nat
  phase : Phase
  deriving DecidableEq, Repr

def live (s : Session) (now incarnation : Nat) : Bool :=
  s.phase == .active && decide (now < s.deadline) && s.incarnation == incarnation

def resolve (s : Session) (presented now incarnation : Nat) : Option Scope :=
  if s.capability == presented && live s now incarnation then some s.scope else none

theorem wrong_capability_rejected (s : Session) (presented now incarnation : Nat)
    (h : s.capability ≠ presented) : resolve s presented now incarnation = none := by
  simp [resolve, h]
theorem resolved_scope_server_owned (s : Session) (presented now incarnation : Nat) (scope : Scope)
    (h : resolve s presented now incarnation = some scope) : scope = s.scope := by
  unfold resolve at h
  split at h
  · exact (Option.some.inj h).symm
  · contradiction

theorem expired_session_inaccessible (s : Session) (now incarnation : Nat)
    (h : s.deadline ≤ now) : live s now incarnation = false := by
  have expired : ¬ now < s.deadline := by omega
  simp [live, expired]
theorem expired_capability_rejected (s : Session) (presented now incarnation : Nat)
    (h : s.deadline ≤ now) : resolve s presented now incarnation = none := by
  simp [resolve, expired_session_inaccessible s now incarnation h]
theorem restarted_incarnation_rejected (s : Session) (now incarnation : Nat)
    (h : s.incarnation ≠ incarnation) : live s now incarnation = false := by simp [live, h]
theorem provisioning_not_accessible (s : Session) (now incarnation : Nat)
    (h : s.phase = .provisioning) : live s now incarnation = false := by simp [live, h]
theorem draining_not_accessible (s : Session) (now incarnation : Nat)
    (h : s.phase = .draining) : live s now incarnation = false := by simp [live, h]
theorem quarantined_not_accessible (s : Session) (now incarnation : Nat)
    (h : s.phase = .quarantined) : live s now incarnation = false := by simp [live, h]

inductive ResourceKind where
  | document | revision | history | receipt | identifierInventory | job | result | cancel
  deriving DecidableEq, Repr

structure Resource where
  owner : Scope
  kind : ResourceKind
  opaqueId : Nat
  deriving DecidableEq, Repr

def mayAccess (s : Session) (r : Resource) (now incarnation : Nat) : Bool :=
  live s now incarnation && s.scope == r.owner

theorem cross_scope_resource_denied (s : Session) (r : Resource) (now incarnation : Nat)
    (h : s.scope ≠ r.owner) : mayAccess s r now incarnation = false := by simp [mayAccess, h]
theorem known_id_cannot_grant_scope (s : Session) (r : Resource) (now incarnation id : Nat) :
    mayAccess s { r with opaqueId := id } now incarnation = mayAccess s r now incarnation := rfl

def receiptKey (scope : Scope) (key : Nat) : Scope × Nat := (scope, key)
theorem same_key_different_scope_independent (a b : Scope) (key : Nat) (h : a ≠ b) :
    receiptKey a key ≠ receiptKey b key := by
  intro equal
  exact h (congrArg Prod.fst equal)

/-- Completion alone cannot publish a response: current liveness is rechecked. -/
def mayPublish (s : Session) (now incarnation : Nat) (internallyComplete : Bool) : Bool :=
  internallyComplete && live s now incarnation

theorem completed_after_expiry_not_published (s : Session) (now incarnation : Nat)
    (h : s.deadline ≤ now) : mayPublish s now incarnation true = false := by
  simp [mayPublish, expired_session_inaccessible s now incarnation h]
theorem publication_requires_live_scope (s : Session) (now incarnation : Nat) (done : Bool)
    (h : mayPublish s now incarnation done = true) : live s now incarnation = true := by
  simp [mayPublish] at h
  exact h.2

def absoluteDeadline (reservedAt : Nat) : Nat := reservedAt + 1800
/-- Activity cannot extend the fixed reservation deadline. -/
def deadlineAfterActivity (reservedAt _lastActivity : Nat) : Nat := absoluteDeadline reservedAt

theorem thirty_minute_fixed_lifetime (reservedAt activity : Nat) :
    deadlineAfterActivity reservedAt activity = reservedAt + 1800 := rfl

/-- Every listed phase consumes a slot; no expiry or failure silently frees it. -/
def reserve (occupied : List Session) (fresh : Session) : List Session :=
  if occupied.length < 4 then occupied ++ [fresh] else occupied

theorem full_capacity_no_change (occupied : List Session) (fresh : Session)
    (h : 4 ≤ occupied.length) : reserve occupied fresh = occupied := by
  have full : ¬ occupied.length < 4 := by omega
  simp [reserve, full]
theorem reservation_never_evicts (occupied : List Session) (fresh old : Session)
    (h : old ∈ occupied) : old ∈ reserve occupied fresh := by
  unfold reserve
  split
  · exact List.mem_append_left _ h
  · exact h

theorem reservation_bound_four (occupied : List Session) (fresh : Session)
    (h : occupied.length ≤ 4) : (reserve occupied fresh).length ≤ 4 := by
  unfold reserve
  split
  · simp only [List.length_append, List.length_cons, List.length_nil]
    omega
  · exact h


def allocate (usedScopes : List Scope) (usedCapabilities : List Nat)
    (occupied : List Session) (fresh : Session) : List Session :=
  if fresh.scope ∈ usedScopes ∨ fresh.capability ∈ usedCapabilities then occupied
  else reserve occupied fresh

theorem reused_scope_not_allocated (scopes : List Scope) (capabilities : List Nat)
    (occupied : List Session) (fresh : Session) (h : fresh.scope ∈ scopes) :
    allocate scopes capabilities occupied fresh = occupied := by simp [allocate, h]
theorem reused_capability_not_allocated (scopes : List Scope) (capabilities : List Nat)
    (occupied : List Session) (fresh : Session) (h : fresh.capability ∈ capabilities) :
    allocate scopes capabilities occupied fresh = occupied := by simp [allocate, h]

structure DrainEvidence where
  noActiveOwners : Bool
  queuedStartRacesResolved : Bool
  actualChildrenReaped : Bool
  sqlContextClean : Bool
  scopedSqlPurgeCertain : Bool
  registryVerifiedPublicScope : Bool
  deriving DecidableEq, Repr

def mayRelease (s : Session) (e : DrainEvidence) : Bool :=
  s.phase == .draining && e.noActiveOwners && e.queuedStartRacesResolved &&
  e.actualChildrenReaped && e.sqlContextClean && e.scopedSqlPurgeCertain && e.registryVerifiedPublicScope

theorem cleanup_uncertain_no_reuse (s : Session) (e : DrainEvidence)
    (h : e.scopedSqlPurgeCertain = false) : mayRelease s e = false := by simp [mayRelease, h]
theorem unreaped_children_no_reuse (s : Session) (e : DrainEvidence)
    (h : e.actualChildrenReaped = false) : mayRelease s e = false := by simp [mayRelease, h]
theorem unresolved_queue_no_reuse (s : Session) (e : DrainEvidence)
    (h : e.queuedStartRacesResolved = false) : mayRelease s e = false := by simp [mayRelease, h]
theorem uncertain_context_no_reuse (s : Session) (e : DrainEvidence)
    (h : e.sqlContextClean = false) : mayRelease s e = false := by simp [mayRelease, h]
theorem private_scope_never_purged (s : Session) (e : DrainEvidence)
    (h : e.registryVerifiedPublicScope = false) : mayRelease s e = false := by simp [mayRelease, h]
theorem quarantined_slot_not_released (s : Session) (e : DrainEvidence)
    (h : s.phase = .quarantined) : mayRelease s e = false := by simp [mayRelease, h]


/-- A deletion/reuse decision cannot be inferred from an expired or CANCELLED label. -/
def release (s : Session) (e : DrainEvidence) : Option Session :=
  if mayRelease s e then none else some s

theorem uncertain_cleanup_retains_slot (s : Session) (e : DrainEvidence)
    (h : e.scopedSqlPurgeCertain = false) : release s e = some s := by
  simp [release, cleanup_uncertain_no_reuse s e h]
theorem quarantined_retains_slot (s : Session) (e : DrainEvidence)
    (h : s.phase = .quarantined) : release s e = some s := by
  simp [release, quarantined_slot_not_released s e h]

def mayStartQueued (s : Session) (job : Resource) (now incarnation : Nat) : Bool :=
  job.kind == .job && mayAccess s job now incarnation

theorem expired_queued_job_never_starts (s : Session) (job : Resource) (now incarnation : Nat)
    (h : s.deadline ≤ now) : mayStartQueued s job now incarnation = false := by
  simp [mayStartQueued, mayAccess, expired_session_inaccessible s now incarnation h]

structure Quota where
  documents : Nat
  reservedDocuments : Nat
  revisions : Nat
  reservedRevisions : Nat
  receipts : Nat
  reservedReceipts : Nat
  bytes : Nat
  reservedBytes : Nat
  deriving DecidableEq, Repr

def withinQuota (q : Quota) : Prop :=
  q.documents + q.reservedDocuments ≤ 3 ∧ q.revisions + q.reservedRevisions ≤ 128 ∧
  q.receipts + q.reservedReceipts ≤ 256 ∧ q.bytes + q.reservedBytes ≤ 16777216
instance (q : Quota) : Decidable (withinQuota q) := inferInstanceAs (Decidable (_ ∧ _))

theorem quota_counts_reservations (q : Quota) (h : withinQuota q) :
    q.bytes + q.reservedBytes ≤ 16777216 := h.2.2.2
theorem stored_bytes_alone_insufficient (q : Quota) (h : 16777216 < q.bytes + q.reservedBytes) :
    ¬ withinQuota q := by
  intro allowed
  have bound := quota_counts_reservations q allowed
  omega

theorem four_slot_accounting_bound (slots bytesPerSlot : Nat)
    (slotsBound : slots ≤ 4) (bytesBound : bytesPerSlot ≤ 16777216) :
    slots * bytesPerSlot ≤ 67108864 := by
  exact Nat.mul_le_mul slotsBound bytesBound

def guardedRequestAllowed (globalActive sessionActive : Nat) : Bool :=
  decide (globalActive < 8 ∧ sessionActive < 2)
def expensiveOperationAllowed (outstanding : Nat) : Bool := decide (outstanding = 0)

theorem global_request_cap (session : Nat) : guardedRequestAllowed 8 session = false := by
  simp [guardedRequestAllowed]
theorem session_request_cap (global : Nat) : guardedRequestAllowed global 2 = false := by
  simp [guardedRequestAllowed]
theorem second_expensive_operation_rejected : expensiveOperationAllowed 1 = false := by decide

inductive Mode where
  | privateMode | anonymous
  deriving DecidableEq, Repr
inductive Authority where
  | privateLaunch | resolvedAnonymous | none
  deriving DecidableEq, Repr
inductive Route where
  | enrollment | workspace | corpus
  deriving DecidableEq, Repr

def routeAllowed (mode : Mode) (authority : Authority) (route : Route) : Bool :=
  match mode, route with
  | .anonymous, .corpus => false
  | .anonymous, .enrollment => true
  | .anonymous, .workspace => authority == .resolvedAnonymous
  | .privateMode, .enrollment => false
  | .privateMode, _ => authority == .privateLaunch

theorem anonymous_corpus_disabled (authority : Authority) :
    routeAllowed .anonymous authority .corpus = false := rfl
theorem private_token_no_anonymous_authority : routeAllowed .anonymous .privateLaunch .workspace = false := by decide
theorem anonymous_token_no_private_authority : routeAllowed .privateMode .resolvedAnonymous .workspace = false := by decide
theorem private_mode_no_public_enrollment (authority : Authority) :
    routeAllowed .privateMode authority .enrollment = false := rfl

structure Enrollment where
  exactHost : Bool
  exactSingleOrigin : Bool
  exactEmptyJson : Bool
  withinOneKiB : Bool
  canonicalNoQuery : Bool
  installationReconciled : Bool
  ratePermit : Bool
  capacityPermit : Bool
  deriving DecidableEq, Repr

def mayEnroll (e : Enrollment) : Bool :=
  e.exactHost && e.exactSingleOrigin && e.exactEmptyJson && e.withinOneKiB &&
  e.canonicalNoQuery && e.installationReconciled && e.ratePermit && e.capacityPermit

theorem unready_restart_blocks_enrollment (e : Enrollment) (h : e.installationReconciled = false) :
    mayEnroll e = false := by simp [mayEnroll, h]
theorem enrollment_requires_capacity (e : Enrollment) (h : e.capacityPermit = false) :
    mayEnroll e = false := by simp [mayEnroll, h]
theorem enrollment_requires_rate_permit (e : Enrollment) (h : e.ratePermit = false) :
    mayEnroll e = false := by simp [mayEnroll, h]

inductive SqlRoute where
  | pinnedParser | directBackend
  deriving DecidableEq, Repr
def sqlAllowed (route : SqlRoute) : Bool := route == .pinnedParser
theorem all_sql_requires_parser : sqlAllowed .directBackend = false := by decide

structure Target where
  wslPrerequisites : Bool
  isolationRuntimeAccepted : Bool
  nativeIisLoopbackTlsAccepted : Bool
  rebootRecoveryAccepted : Bool
  intentionalExposure : Bool
  deriving DecidableEq, Repr

def publicExposure (t : Target) : Bool :=
  t.wslPrerequisites && t.isolationRuntimeAccepted && t.nativeIisLoopbackTlsAccepted &&
  t.rebootRecoveryAccepted && t.intentionalExposure

theorem wsl_prerequisites_not_acceptance : publicExposure ⟨true, false, false, false, false⟩ = false := by decide
theorem no_default_public_exposure (t : Target) (h : t.intentionalExposure = false) :
    publicExposure t = false := by simp [publicExposure, h]

def scopeA : Scope := ⟨1, 11, 111⟩
def scopeB : Scope := ⟨2, 22, 222⟩
def sessionA : Session := ⟨scopeA, 1001, 1, 1800, .active⟩
def sessionB : Session := ⟨scopeB, 2002, 1, 1800, .active⟩
def cleanDrain : DrainEvidence := ⟨true, true, true, true, true, true⟩

theorem own_session_positive : resolve sessionA 1001 1 1 = some scopeA := by decide
theorem other_session_capability_denied : resolve sessionA 2002 1 1 = none := by decide
theorem cross_session_document_denied : mayAccess sessionA ⟨scopeB, .document, 77⟩ 1 1 = false := by decide
theorem own_document_positive : mayAccess sessionA ⟨scopeA, .document, 77⟩ 1 1 = true := by decide
theorem own_job_positive : mayAccess sessionB ⟨scopeB, .job, 88⟩ 1 1 = true := by decide
theorem expiry_boundary_denied : mayPublish sessionA 1800 1 true = false := by decide
theorem drained_release_positive : mayRelease { sessionA with phase := .draining } cleanDrain = true := by decide
theorem bounded_reservation_positive : (reserve [sessionA] sessionB).length = 2 := by decide
theorem quota_positive : withinQuota ⟨1, 1, 10, 1, 20, 1, 1024, 4194304⟩ := by decide
theorem enrollment_positive : mayEnroll ⟨true, true, true, true, true, true, true, true⟩ = true := by decide
theorem request_admission_positive : guardedRequestAllowed 0 0 = true := by decide
theorem parser_route_positive : sqlAllowed .pinnedParser = true := by decide

end Allow.AnonymousWorkspaces
