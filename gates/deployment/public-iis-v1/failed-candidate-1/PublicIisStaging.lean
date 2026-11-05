import Std

/- Finite policy model, not IIS/HTTP.sys/TLS/PowerShell implementation refinement.
   Concrete certificate validation, ACLs, races and target acceptance remain separate. -/
namespace Allow.PublicIisStaging

structure Preflight where
  elevatedWindows : Bool
  newDedicatedNames : Bool
  exactOnlyWebConfig : Bool
  canonicalMatchingOrigin : Bool
  requiredModulesArr : Bool
  noBindingConflict : Bool
  certificatePrivateKeyDates : Bool
  sslDnsTrustRevocation : Bool
  deriving DecidableEq, Repr

def preflightPass (p : Preflight) : Bool :=
  p.elevatedWindows && p.newDedicatedNames && p.exactOnlyWebConfig &&
  p.canonicalMatchingOrigin && p.requiredModulesArr && p.noBindingConflict &&
  p.certificatePrivateKeyDates && p.sslDnsTrustRevocation

inductive Mode where
  | preflightOnly | stage
  deriving DecidableEq, Repr

def mayMutate (p : Preflight) (mode : Mode) : Bool := preflightPass p && mode == .stage

theorem preflight_only_never_mutates (p : Preflight) : mayMutate p .preflightOnly = false := by
  simp [mayMutate]
theorem failed_preflight_never_mutates (p : Preflight) (mode : Mode)
    (h : preflightPass p = false) : mayMutate p mode = false := by simp [mayMutate, h]
theorem mutation_requires_preflight (p : Preflight) (mode : Mode)
    (h : mayMutate p mode = true) : preflightPass p = true := by
  simp [mayMutate] at h
  exact h.1

theorem unavailable_revocation_rejects (p : Preflight) (h : p.sslDnsTrustRevocation = false) :
    preflightPass p = false := by simp [preflightPass, h]
theorem untrusted_certificate_rejects (p : Preflight) (h : p.certificatePrivateKeyDates = false) :
    preflightPass p = false := by simp [preflightPass, h]
theorem binding_conflict_rejects (p : Preflight) (h : p.noBindingConflict = false) :
    preflightPass p = false := by simp [preflightPass, h]

structure Site where
  exists : Bool
  running : Bool
  autoStart : Bool
  sniConfigured : Bool
  logSecretsExcluded : Bool
  publicAccepted : Bool
  deriving DecidableEq, Repr

def stagedSite : Site := ⟨true, false, false, true, true, false⟩
def install (p : Preflight) (mode : Mode) (before : Site) : Site :=
  if mayMutate p mode then stagedSite else before

theorem stage_stays_stopped : stagedSite.running = false ∧ stagedSite.autoStart = false := by decide
theorem stage_has_sni_and_safe_logs : stagedSite.sniConfigured = true ∧
    stagedSite.logSecretsExcluded = true := by decide
theorem staging_not_public_acceptance : stagedSite.publicAccepted = false := rfl
theorem failed_preflight_state_unchanged (p : Preflight) (mode : Mode) (before : Site)
    (h : preflightPass p = false) : install p mode before = before := by
  simp [install, mayMutate, h]
theorem preflight_only_state_unchanged (p : Preflight) (before : Site) :
    install p .preflightOnly before = before := by simp [install, mayMutate]
theorem successful_stage_stopped (p : Preflight) (before : Site)
    (h : preflightPass p = true) :
    (install p .stage before).running = false ∧ (install p .stage before).autoStart = false := by
  simp [install, mayMutate, h, stagedSite]

structure Resource where
  invocationCreated : Bool
  exactIdentityVerified : Bool
  preexisting : Bool
  deriving DecidableEq, Repr

def mayCleanup (r : Resource) : Bool :=
  r.invocationCreated && r.exactIdentityVerified && !r.preexisting

theorem cleanup_requires_invocation_owner (r : Resource) (h : mayCleanup r = true) :
    r.invocationCreated = true ∧ r.exactIdentityVerified = true := by
  simp [mayCleanup] at h
  exact ⟨h.1.1, h.1.2⟩
theorem preexisting_resource_preserved (r : Resource) (h : r.preexisting = true) :
    mayCleanup r = false := by simp [mayCleanup, h]
theorem uncertain_identity_preserved (r : Resource) (h : r.exactIdentityVerified = false) :
    mayCleanup r = false := by simp [mayCleanup, h]

def cleanupFailureVisible (failedMutation cleanupEstablished : Bool) : Bool :=
  failedMutation && !cleanupEstablished

theorem uncertain_cleanup_keeps_failure : cleanupFailureVisible true false = true := by decide

structure Exposure where
  targetResolved : Bool
  audienceAccepted : Bool
  nativeAcceptance : Bool
  intentionalStart : Bool
  intentionalIngress : Bool
  deriving DecidableEq, Repr

def exposurePermitted (e : Exposure) : Bool :=
  e.targetResolved && e.audienceAccepted && e.nativeAcceptance && e.intentionalStart && e.intentionalIngress

theorem unresolved_target_never_exposed (e : Exposure) (h : e.targetResolved = false) :
    exposurePermitted e = false := by simp [exposurePermitted, h]
theorem unresolved_audience_never_exposed (e : Exposure) (h : e.audienceAccepted = false) :
    exposurePermitted e = false := by simp [exposurePermitted, h]
theorem missing_native_acceptance_never_exposed (e : Exposure) (h : e.nativeAcceptance = false) :
    exposurePermitted e = false := by simp [exposurePermitted, h]
theorem no_default_public_start (e : Exposure) (h : e.intentionalStart = false) :
    exposurePermitted e = false := by simp [exposurePermitted, h]

inductive Check where
  | rootHtml | absentBearer | invalidBearer | hostileOrigin | hostileHost | forwarded | encodedAlias | matrixAlias
  deriving DecidableEq, Repr

def fixedChecks : List Check :=
  [.rootHtml, .absentBearer, .invalidBearer, .hostileOrigin, .hostileHost, .forwarded, .encodedAlias, .matrixAlias]
theorem finite_request_count : fixedChecks.length = 8 := by decide

structure ProbeInput where
  canonicalHttpsOrigin : Bool
  noRealBearerOrLaunchUrl : Bool
  trustedTls : Bool
  noAmbientProxyCookies : Bool
  fixedAuthorityPaths : Bool
  sequentialFinite : Bool
  deriving DecidableEq, Repr

def inputSafe (p : ProbeInput) : Bool :=
  p.canonicalHttpsOrigin && p.noRealBearerOrLaunchUrl && p.trustedTls &&
  p.noAmbientProxyCookies && p.fixedAuthorityPaths && p.sequentialFinite

structure Observation where
  expectedStatus : Bool
  requiredHeaders : Bool
  rootHtmlWhenRequired : Bool
  withinTimeout : Bool
  withinBodyCap : Bool
  noRedirect : Bool
  noProtocolError : Bool
  deriving DecidableEq, Repr

def observationPass (o : Observation) : Bool :=
  o.expectedStatus && o.requiredHeaders && o.rootHtmlWhenRequired &&
  o.withinTimeout && o.withinBodyCap && o.noRedirect && o.noProtocolError

def probePass (input : ProbeInput) (rows : List Observation) : Bool :=
  inputSafe input && rows.length == fixedChecks.length && rows.all observationPass

theorem real_authority_input_rejected (p : ProbeInput) (h : p.noRealBearerOrLaunchUrl = false)
    (rows : List Observation) : probePass p rows = false := by simp [probePass, inputSafe, h]
theorem tls_bypass_rejected (p : ProbeInput) (h : p.trustedTls = false)
    (rows : List Observation) : probePass p rows = false := by simp [probePass, inputSafe, h]
theorem redirect_fails (o : Observation) (h : o.noRedirect = false) :
    observationPass o = false := by simp [observationPass, h]
theorem body_overflow_fails (o : Observation) (h : o.withinBodyCap = false) :
    observationPass o = false := by simp [observationPass, h]
theorem timeout_fails (o : Observation) (h : o.withinTimeout = false) :
    observationPass o = false := by simp [observationPass, h]
theorem missing_required_headers_fails (o : Observation) (h : o.requiredHeaders = false) :
    observationPass o = false := by simp [observationPass, h]
theorem wrong_status_fails (o : Observation) (h : o.expectedStatus = false) :
    observationPass o = false := by simp [observationPass, h]
theorem incomplete_probe_fails (p : ProbeInput) (rows : List Observation)
    (h : rows.length ≠ fixedChecks.length) : probePass p rows = false := by
  simp [probePass, h]

inductive ErrorCategory where
  | none | network | tls | protocol | redirect | limit | expectation
  deriving DecidableEq, Repr

structure RawResult where
  check : Check
  status : Nat
  passed : Bool
  elapsed : Nat
  category : ErrorCategory
  responseBody : Nat
  responseHeaders : Nat
  secret : Nat
  deriving DecidableEq, Repr

structure Evidence where
  check : Check
  status : Nat
  passed : Bool
  elapsed : Nat
  category : ErrorCategory
  deriving DecidableEq, Repr

def redact (r : RawResult) : Evidence := ⟨r.check, r.status, r.passed, r.elapsed, r.category⟩
theorem evidence_independent_of_body_headers_secrets (r : RawResult) (body headers secret : Nat) :
    redact { r with responseBody := body, responseHeaders := headers, secret := secret } = redact r := rfl

/-- Probe outcome is not an acceptance credential; only separate native target evidence can accept. -/
def publicAcceptance (_probeOutcome : Bool) (nativeTargetEvidence : Bool) : Bool := nativeTargetEvidence
theorem probe_success_not_acceptance : publicAcceptance true false = false := rfl

def safePreflight : Preflight := ⟨true, true, true, true, true, true, true, true⟩
def safeInput : ProbeInput := ⟨true, true, true, true, true, true⟩
def safeObservation : Observation := ⟨true, true, true, true, true, true, true⟩
def passingRows : List Observation := List.replicate 8 safeObservation

theorem preflight_positive : preflightPass safePreflight = true := by decide
theorem stage_positive : install safePreflight .stage ⟨false, false, false, false, false, false⟩ = stagedSite := by decide
theorem owned_cleanup_positive : mayCleanup ⟨true, true, false⟩ = true := by decide
theorem probe_positive : probePass safeInput passingRows = true := by decide
theorem separately_accepted_exposure_positive : exposurePermitted ⟨true, true, true, true, true⟩ = true := by decide

end Allow.PublicIisStaging
