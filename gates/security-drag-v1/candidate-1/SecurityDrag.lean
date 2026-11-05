import Std

/- Finite policy supplement only. It does not establish implementation refinement,
   OS race freedom, cryptography, semantic completeness or visual usability. -/
namespace Allow.SecurityDrag

inductive PathClass where
  | root | index | approvedAsset | guarded | alias
  deriving DecidableEq, Repr
inductive Method where
  | get | head | other
  deriving DecidableEq, Repr
inductive Bearer where
  | exactValid | absent | invalid | duplicate
  deriving DecidableEq, Repr

structure Http where
  path : PathClass
  method : Method
  bearer : Bearer
  exactHostOrigin : Bool
  forwardedAuthority : Bool
  deriving DecidableEq, Repr

def publicResource (r : Http) : Bool :=
  (r.path == .root || r.path == .index || r.path == .approvedAsset) &&
  (r.method == .get || r.method == .head)
def admitted (r : Http) : Bool :=
  r.path != .alias && r.exactHostOrigin && (publicResource r || r.bearer == .exactValid)

theorem aliases_always_rejected (r : Http) (h : r.path = .alias) : admitted r = false := by
  simp [admitted, h]
theorem public_exception_exact (r : Http) : publicResource r = true ↔
    (r.path = .root ∨ r.path = .index ∨ r.path = .approvedAsset) ∧
    (r.method = .get ∨ r.method = .head) := by
  simp [publicResource, or_assoc]
theorem protected_default_requires_bearer (r : Http) (h : publicResource r = false)
    (pass : admitted r = true) : r.bearer = .exactValid := by
  simp [admitted, h] at pass
  exact pass.2

theorem hostile_authority_rejected (r : Http) (h : r.exactHostOrigin = false) :
    admitted r = false := by simp [admitted, h]
theorem forwarded_authority_irrelevant (r : Http) (f : Bool) :
    admitted { r with forwardedAuthority := f } = admitted r := rfl

def publicWitness : Http := ⟨.approvedAsset, .get, .absent, true, false⟩
def apiWitness : Http := ⟨.guarded, .other, .exactValid, true, true⟩
theorem public_positive : admitted publicWitness = true := by decide
theorem authenticated_positive : admitted apiWitness = true := by decide

structure Bootstrap where
  isolated : Bool
  noBytecode : Bool
  exactVerifiedSource : Bool
  closedInventory : Bool
  trustedOwnership : Bool
  privateFiles : Bool
  deriving DecidableEq, Repr

def bootstrapAllowed (b : Bootstrap) : Bool :=
  b.isolated && b.noBytecode && b.exactVerifiedSource && b.closedInventory &&
  b.trustedOwnership && b.privateFiles

theorem bootstrap_requires_all_checks (b : Bootstrap) : bootstrapAllowed b = true ↔
    b.isolated = true ∧ b.noBytecode = true ∧ b.exactVerifiedSource = true ∧
    b.closedInventory = true ∧ b.trustedOwnership = true ∧ b.privateFiles = true := by
  simp [bootstrapAllowed, and_assoc]
theorem unisolated_bootstrap_rejected (b : Bootstrap) (h : b.isolated = false) :
    bootstrapAllowed b = false := by simp [bootstrapAllowed, h]
theorem bytecode_bootstrap_rejected (b : Bootstrap) (h : b.noBytecode = false) :
    bootstrapAllowed b = false := by simp [bootstrapAllowed, h]
theorem unverified_source_rejected (b : Bootstrap) (h : b.exactVerifiedSource = false) :
    bootstrapAllowed b = false := by simp [bootstrapAllowed, h]
theorem extra_executable_rejected (b : Bootstrap) (h : b.closedInventory = false) :
    bootstrapAllowed b = false := by simp [bootstrapAllowed, h]
theorem unsafe_ownership_rejected (b : Bootstrap) (h : b.trustedOwnership = false) :
    bootstrapAllowed b = false := by simp [bootstrapAllowed, h]
theorem nonprivate_authority_rejected (b : Bootstrap) (h : b.privateFiles = false) :
    bootstrapAllowed b = false := by simp [bootstrapAllowed, h]

structure Installation where
  bootstrap : Bootstrap
  exclusiveOwner : Bool
  unknownRuntime : Bool
  oldGeneratedTools : Bool
  deriving DecidableEq, Repr

def initializeAllowed (i : Installation) : Bool :=
  bootstrapAllowed i.bootstrap && i.exclusiveOwner && !i.unknownRuntime && !i.oldGeneratedTools
/-- All stack, capability and backend effects share one owner gate, including cleanup. -/
def sideEffectsAllowed (i : Installation) : Bool := bootstrapAllowed i.bootstrap && i.exclusiveOwner

theorem fresh_rejects_old_tools (i : Installation) (h : i.oldGeneratedTools = true) :
    initializeAllowed i = false := by simp [initializeAllowed, h]
theorem fresh_rejects_unknown_runtime (i : Installation) (h : i.unknownRuntime = true) :
    initializeAllowed i = false := by simp [initializeAllowed, h]
theorem competing_initializer_rejected (i : Installation) (h : i.exclusiveOwner = false) :
    initializeAllowed i = false := by simp [initializeAllowed, h]
theorem competing_supervisor_no_effects (i : Installation) (h : i.exclusiveOwner = false) :
    sideEffectsAllowed i = false := by simp [sideEffectsAllowed, h]
theorem side_effects_require_owner (i : Installation) (h : sideEffectsAllowed i = true) :
    i.exclusiveOwner = true := by
  simp [sideEffectsAllowed] at h
  exact h.2

def safeBootstrap : Bootstrap := ⟨true, true, true, true, true, true⟩
def freshWitness : Installation := ⟨safeBootstrap, true, false, false⟩
theorem bootstrap_positive : bootstrapAllowed safeBootstrap = true := by decide
theorem fresh_positive : initializeAllowed freshWitness = true := by decide
theorem supervisor_positive : sideEffectsAllowed freshWitness = true := by decide

inductive Compatibility where
  | incompatible | unresolved | checked
  deriving DecidableEq, Repr
inductive Source where
  | constructor | existing | missing | descendantOrSelf
  deriving DecidableEq, Repr

structure Gesture where
  sameEditor : Bool
  activeNonce : Bool
  sameDocument : Bool
  sameBaseRevision : Bool
  sameDraft : Bool
  sameContentGeneration : Bool
  destinationPresent : Bool
  source : Source
  compatibility : Compatibility
  selectionChanged : Bool
  hoverWasChecked : Bool
  deriving DecidableEq, Repr

/-- Hover is advisory; final preparation uses current bound content and scope. -/
def dropAllowed (g : Gesture) : Bool :=
  g.sameEditor && g.activeNonce && g.sameDocument && g.sameBaseRevision &&
  g.sameDraft && g.sameContentGeneration && g.destinationPresent &&
  (g.source == .constructor || g.source == .existing) && g.compatibility != .incompatible

def typeChecked (g : Gesture) : Bool := g.compatibility == .checked

theorem foreign_editor_rejected (g : Gesture) (h : g.sameEditor = false) :
    dropAllowed g = false := by simp [dropAllowed, h]
theorem missing_gesture_rejected (g : Gesture) (h : g.activeNonce = false) :
    dropAllowed g = false := by simp [dropAllowed, h]
theorem stale_document_rejected (g : Gesture) (h : g.sameDocument = false) :
    dropAllowed g = false := by simp [dropAllowed, h]
theorem stale_revision_rejected (g : Gesture) (h : g.sameBaseRevision = false) :
    dropAllowed g = false := by simp [dropAllowed, h]
theorem stale_draft_rejected (g : Gesture) (h : g.sameDraft = false) :
    dropAllowed g = false := by simp [dropAllowed, h]
theorem stale_generation_rejected (g : Gesture) (h : g.sameContentGeneration = false) :
    dropAllowed g = false := by simp [dropAllowed, h]
theorem missing_destination_rejected (g : Gesture) (h : g.destinationPresent = false) :
    dropAllowed g = false := by simp [dropAllowed, h]
theorem missing_source_rejected (g : Gesture) (h : g.source = .missing) :
    dropAllowed g = false := by simp [dropAllowed, h]
theorem descendant_self_rejected (g : Gesture) (h : g.source = .descendantOrSelf) :
    dropAllowed g = false := by simp [dropAllowed, h]
theorem incompatible_rejected (g : Gesture) (h : g.compatibility = .incompatible) :
    dropAllowed g = false := by simp [dropAllowed, h]
theorem unresolved_not_typechecked (g : Gesture) (h : g.compatibility = .unresolved) :
    typeChecked g = false := by simp [typeChecked, h]
theorem selection_only_irrelevant (g : Gesture) (changed : Bool) :
    dropAllowed { g with selectionChanged := changed } = dropAllowed g := rfl
theorem hover_does_not_authorize (g : Gesture) (hover : Bool) :
    dropAllowed { g with hoverWasChecked := hover } = dropAllowed g := rfl

/-- Only durable semantic fields; notice/focus/gesture presentation is outside this state. -/
structure EditorState where
  moduleContent : Nat
  acceptedRevision : Nat
  clipboard : Nat
  contentGeneration : Nat
  provenance : Nat
  deriving DecidableEq, Repr

def publish (state : EditorState) (candidateModule candidateProvenance : Nat) : EditorState :=
  { state with moduleContent := candidateModule, provenance := candidateProvenance,
               contentGeneration := state.contentGeneration + 1 }
def drop (g : Gesture) (s : EditorState) (moduleValue provenanceValue : Nat) : EditorState :=
  if dropAllowed g then publish s moduleValue provenanceValue else s

theorem rejected_drop_no_mutation (g : Gesture) (s : EditorState) (m p : Nat)
    (h : dropAllowed g = false) : drop g s m p = s := by simp [drop, h]
theorem drop_never_commits (g : Gesture) (s : EditorState) (m p : Nat) :
    (drop g s m p).acceptedRevision = s.acceptedRevision := by
  unfold drop
  split <;> rfl
theorem drop_preserves_clipboard (g : Gesture) (s : EditorState) (m p : Nat) :
    (drop g s m p).clipboard = s.clipboard := by
  unfold drop
  split <;> rfl
theorem successful_drop_one_transition (g : Gesture) (s : EditorState) (m p : Nat)
    (h : dropAllowed g = true) :
    (drop g s m p).contentGeneration = s.contentGeneration + 1 := by
  simp [drop, publish, h]

def gestureWitness : Gesture :=
  ⟨true, true, true, true, true, true, true, .constructor, .checked, false, false⟩
theorem valid_gesture_positive : dropAllowed gestureWitness = true := by decide
theorem unresolved_positive_without_checked_claim :
    dropAllowed { gestureWitness with compatibility := .unresolved } = true ∧
    typeChecked { gestureWitness with compatibility := .unresolved } = false := by decide
theorem rejected_witness :
    drop { gestureWitness with sameContentGeneration := false } ⟨1, 2, 3, 4, 5⟩ 99 100 =
      ⟨1, 2, 3, 4, 5⟩ := by decide

end Allow.SecurityDrag
