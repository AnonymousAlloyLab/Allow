import Std

/- Finite policy abstraction, not a proof of systemd, filesystem, UID isolation,
   backup correctness or implementation correspondence. Observation Booleans are
   trusted inputs whose actual measurement remains a separate runtime obligation. -/
namespace Allow.StagedPublicCutover

inductive Slot where
  | primary | publicReplacement
  deriving DecidableEq, Repr

def parseSlot : Option String → Option Slot
  | none => some .primary
  | some "PRIMARY" => some .primary
  | some "PUBLIC_REPLACEMENT" => some .publicReplacement
  | _ => none

structure Binding where
  root : String
  account : String
  service : String
  anonymous : Bool
  wsl : Bool
  backendPort : Nat
  tunnelPort : Nat
  deriving DecidableEq, Repr

def replacement : Binding :=
  ⟨"/opt/allow-public", "allow-public", "allow-public.service", true, true, 18081, 18081⟩

def bindingAccepted (slot : Slot) (b : Binding) (legacyValid : Bool) : Bool :=
  match slot with
  | .primary => legacyValid
  | .publicReplacement => b == replacement

theorem missing_slot_preserves_primary : parseSlot none = some .primary := rfl
theorem primary_name_accepted : parseSlot (some "PRIMARY") = some .primary := rfl
theorem replacement_name_accepted : parseSlot (some "PUBLIC_REPLACEMENT") = some .publicReplacement := rfl
theorem unknown_slot_rejected : parseSlot (some "PUBLIC") = none := by decide
theorem primary_validation_unchanged (b : Binding) (valid : Bool) :
    bindingAccepted .primary b valid = valid := rfl
theorem replacement_positive : bindingAccepted .publicReplacement replacement false = true := by decide
theorem mixed_binding_rejected (b : Binding) (valid : Bool) (h : b ≠ replacement) :
    bindingAccepted .publicReplacement b valid = false := by simp [bindingAccepted, h]
theorem old_root_rejected : bindingAccepted .publicReplacement
    { replacement with root := "/opt/allow" } true = false := by decide
theorem old_account_rejected : bindingAccepted .publicReplacement
    { replacement with account := "allow" } true = false := by decide
theorem old_service_rejected : bindingAccepted .publicReplacement
    { replacement with service := "allow.service" } true = false := by decide
theorem private_mode_rejected : bindingAccepted .publicReplacement
    { replacement with anonymous := false } true = false := by decide
theorem ssh_transport_rejected : bindingAccepted .publicReplacement
    { replacement with wsl := false } true = false := by decide
theorem wrong_port_rejected : bindingAccepted .publicReplacement
    { replacement with backendPort := 8080 } true = false := by decide

structure Guard where
  oldLoaded : Bool
  oldInactive : Bool
  oldDisabled : Bool
  oldMainAbsent : Bool
  oldJobAbsent : Bool
  oldCgroupEmpty : Bool
  oldOwnerProtected : Bool
  publicRootProtected : Bool
  publicOwnerCorrect : Bool
  distinctNonrootUids : Bool
  privateReadDenied : Bool
  privateWriteDenied : Bool
  privateExecuteDenied : Bool
  deriving DecidableEq, Repr

def ready (g : Guard) : Bool :=
  g.oldLoaded && g.oldInactive && g.oldDisabled && g.oldMainAbsent && g.oldJobAbsent &&
  g.oldCgroupEmpty && g.oldOwnerProtected && g.publicRootProtected && g.publicOwnerCorrect &&
  g.distinctNonrootUids && g.privateReadDenied && g.privateWriteDenied && g.privateExecuteDenied

def goodGuard : Guard := ⟨true, true, true, true, true, true, true, true, true, true, true, true, true⟩

theorem ready_positive : ready goodGuard = true := by decide
theorem active_legacy_denied (g : Guard) (h : g.oldInactive = false) : ready g = false := by simp [ready, h]
theorem enabled_legacy_denied (g : Guard) (h : g.oldDisabled = false) : ready g = false := by simp [ready, h]
theorem legacy_main_denied (g : Guard) (h : g.oldMainAbsent = false) : ready g = false := by simp [ready, h]
theorem legacy_job_denied (g : Guard) (h : g.oldJobAbsent = false) : ready g = false := by simp [ready, h]
theorem nonempty_cgroup_denied (g : Guard) (h : g.oldCgroupEmpty = false) : ready g = false := by simp [ready, h]
theorem missing_legacy_denied (g : Guard) (h : g.oldLoaded = false) : ready g = false := by simp [ready, h]
theorem shared_or_root_uid_denied (g : Guard) (h : g.distinctNonrootUids = false) : ready g = false := by simp [ready, h]
theorem private_read_access_denied (g : Guard) (h : g.privateReadDenied = false) : ready g = false := by simp [ready, h]
theorem private_write_access_denied (g : Guard) (h : g.privateWriteDenied = false) : ready g = false := by simp [ready, h]
theorem private_execute_access_denied (g : Guard) (h : g.privateExecuteDenied = false) : ready g = false := by simp [ready, h]
theorem wrong_public_owner_denied (g : Guard) (h : g.publicOwnerCorrect = false) : ready g = false := by simp [ready, h]

structure State where
  privateIdentity : Nat
  privateContents : Nat
  publicIdentity : Nat
  publicContents : Nat
  legacyActive : Bool
  publicActive : Bool
  publicPrepared : Bool
  exposed : Bool
  deriving DecidableEq, Repr

def prepare (s : State) (b : Binding) (g : Guard) (freshIdentity : Nat) : Option State :=
  if bindingAccepted .publicReplacement b false && ready g && !s.legacyActive && !s.publicActive &&
      decide (freshIdentity ≠ s.privateIdentity) then
    some { s with publicIdentity := freshIdentity, publicContents := 0, publicPrepared := true, exposed := false }
  else none

def start (s : State) (g : Guard) : Option State :=
  if ready g && s.publicPrepared && !s.legacyActive && !s.publicActive then
    some { s with publicActive := true, exposed := false }
  else none

def editPublic (s : State) (contents : Nat) : State := { s with publicContents := contents }
def stopPublic (s : State) : State := { s with publicActive := false, exposed := false }

theorem prepare_preserves_private (s t : State) (b : Binding) (g : Guard) (fresh : Nat)
    (h : prepare s b g fresh = some t) :
    t.privateIdentity = s.privateIdentity ∧ t.privateContents = s.privateContents := by
  unfold prepare at h
  split at h
  · cases Option.some.inj h; exact ⟨rfl, rfl⟩
  · contradiction
theorem prepare_is_not_exposure (s t : State) (b : Binding) (g : Guard) (fresh : Nat)
    (h : prepare s b g fresh = some t) : t.exposed = false := by
  unfold prepare at h
  split at h
  · cases Option.some.inj h; rfl
  · contradiction
theorem prepare_rejects_private_identity_reuse (s : State) (b : Binding) (g : Guard) :
    prepare s b g s.privateIdentity = none := by simp [prepare]
theorem prepare_rejects_active_legacy (s : State) (b : Binding) (g : Guard) (fresh : Nat)
    (h : s.legacyActive = true) : prepare s b g fresh = none := by simp [prepare, h]
theorem prepare_guard_failure_has_no_transition (s : State) (b : Binding) (g : Guard) (fresh : Nat)
    (h : ready g = false) : prepare s b g fresh = none := by simp [prepare, h]
theorem public_edit_preserves_private (s : State) (contents : Nat) :
    (editPublic s contents).privateIdentity = s.privateIdentity ∧
    (editPublic s contents).privateContents = s.privateContents := ⟨rfl, rfl⟩
theorem public_stop_preserves_private (s : State) :
    (stopPublic s).privateIdentity = s.privateIdentity ∧
    (stopPublic s).privateContents = s.privateContents := ⟨rfl, rfl⟩
theorem start_preserves_private (s t : State) (g : Guard) (h : start s g = some t) :
    t.privateIdentity = s.privateIdentity ∧ t.privateContents = s.privateContents := by
  unfold start at h
  split at h
  · cases Option.some.inj h; exact ⟨rfl, rfl⟩
  · contradiction
theorem start_requires_inactive_legacy (s t : State) (g : Guard) (h : start s g = some t) :
    s.legacyActive = false := by
  unfold start at h
  split at h
  · rename_i guard
    simp only [Bool.and_eq_true] at guard
    cases value : s.legacyActive <;> simp_all
  · contradiction
theorem start_rejects_unprepared (s : State) (g : Guard) (h : s.publicPrepared = false) :
    start s g = none := by simp [start, h]
theorem start_never_exposes (s t : State) (g : Guard) (h : start s g = some t) :
    t.exposed = false := by
  unfold start at h
  split at h
  · cases Option.some.inj h; rfl
  · contradiction

structure Acceptance where
  nativeWsl : Bool
  tlsRouting : Bool
  isolationExpiry : Bool
  restartRecovery : Bool
  resources : Bool
  intentionalExposure : Bool
  deriving DecidableEq, Repr

def mayExpose (s : State) (a : Acceptance) : Bool :=
  s.publicActive && !s.legacyActive && a.nativeWsl && a.tlsRouting &&
  a.isolationExpiry && a.restartRecovery && a.resources && a.intentionalExposure

theorem no_native_acceptance_no_exposure (s : State) (a : Acceptance) (h : a.nativeWsl = false) :
    mayExpose s a = false := by simp [mayExpose, h]
theorem no_tls_acceptance_no_exposure (s : State) (a : Acceptance) (h : a.tlsRouting = false) :
    mayExpose s a = false := by simp [mayExpose, h]
theorem no_restart_acceptance_no_exposure (s : State) (a : Acceptance) (h : a.restartRecovery = false) :
    mayExpose s a = false := by simp [mayExpose, h]
theorem active_legacy_prevents_exposure (s : State) (a : Acceptance) (h : s.legacyActive = true) :
    mayExpose s a = false := by simp [mayExpose, h]
theorem no_intent_no_exposure (s : State) (a : Acceptance) (h : a.intentionalExposure = false) :
    mayExpose s a = false := by simp [mayExpose, h]

def rollback (s : State) (publicCleanup ingressRestricted privateIntact : Bool) : Option State :=
  if !s.publicActive && publicCleanup && ingressRestricted && privateIntact then
    some { s with legacyActive := true, exposed := false }
  else none

theorem rollback_requires_restricted_ingress (s : State) (clean intact : Bool) :
    rollback s clean false intact = none := by simp [rollback]
theorem rollback_requires_cleanup (s : State) (restricted intact : Bool) :
    rollback s false restricted intact = none := by simp [rollback]
theorem rollback_refuses_active_public (s : State) (clean restricted intact : Bool)
    (h : s.publicActive = true) : rollback s clean restricted intact = none := by simp [rollback, h]
theorem rollback_never_exposes_legacy (s t : State) (clean restricted intact : Bool)
    (h : rollback s clean restricted intact = some t) : t.exposed = false := by
  unfold rollback at h
  split at h
  · cases Option.some.inj h; rfl
  · contradiction
theorem rollback_keeps_both_stores (s t : State) (clean restricted intact : Bool)
    (h : rollback s clean restricted intact = some t) :
    t.privateContents = s.privateContents ∧ t.publicContents = s.publicContents := by
  unfold rollback at h
  split at h
  · cases Option.some.inj h; exact ⟨rfl, rfl⟩
  · contradiction

def stopped : State := ⟨1, 42, 0, 0, false, false, false, false⟩
def staged : State := ⟨1, 42, 2, 0, false, false, true, false⟩
def serving : State := ⟨1, 42, 2, 0, false, true, true, false⟩
theorem fresh_preparation_positive : prepare stopped replacement goodGuard 2 = some staged := by decide
theorem public_start_positive : start staged goodGuard = some serving := by decide
theorem fully_accepted_exposure_positive :
    mayExpose serving ⟨true, true, true, true, true, true⟩ = true := by decide
theorem restricted_rollback_positive :
    rollback (stopPublic (editPublic serving 99)) true true true =
      some ⟨1, 42, 2, 99, true, false, true, false⟩ := by decide

end Allow.StagedPublicCutover
