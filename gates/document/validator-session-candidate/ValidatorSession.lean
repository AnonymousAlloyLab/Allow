import Std

/- Candidate model only. Resource observations, fresh-loader semantics, private
   framing, immutable images and authorization are explicit runtime premises. -/
namespace Allow.ValidatorSessionCandidate

/-- Exact private identities; strings stand for decoded bounded byte identities. -/
structure Binding where
  principal : String
  workspace : String
  launch : String
  policy : String
  dependency : String
  image : String
  generation : Nat
  deriving DecidableEq, Repr

/-- Exact retained content is modeled, not merely a collision-prone hash. -/
structure Request where
  binding : Binding
  sequence : Nat
  nonce : String
  document : String
  revision : Nat
  draft : String
  epoch : Nat
  body : String
  base : String
  inventory : String
  deriving DecidableEq, Repr

inductive Verdict where
  | valid | invalid
  deriving DecidableEq, Repr

structure Output where
  verdict : Verdict
  bytes : String
  deriving DecidableEq, Repr

inductive Phase where
  | idle
  | busy (request : Request)
  | staged (request : Request) (output : Output)
  | retiring
  | dead
  deriving DecidableEq, Repr

structure Session where
  binding : Binding
  next : Nat
  completed : Nat
  phase : Phase
  deriving DecidableEq, Repr

/-- Runtime authority, capacity and resource checks are additional admission facts. -/
def canStart (s : Session) (q : Request) : Prop :=
  s.phase = .idle ∧ q.binding = s.binding ∧ q.sequence = s.next ∧ s.completed < 64

def start (s : Session) (q : Request) : Session := { s with phase := .busy q }

/-- Reset is an observed premise; a Boolean from an untrusted child is insufficient. -/
structure Reset where
  loaderDetached : Bool
  requestReferencesDropped : Bool
  noRequestThreads : Bool
  temporaryFilesRemoved : Bool
  outputDrained : Bool
  deriving DecidableEq, Repr

def clean (r : Reset) : Prop :=
  r.loaderDetached = true ∧ r.requestReferencesDropped = true ∧
  r.noRequestThreads = true ∧ r.temporaryFilesRemoved = true ∧ r.outputDrained = true

/-- Staged output cannot be published before reset, freshness and identity checks. -/
def publishable (s : Session) (current packet : Request) (out : Output) (r : Reset) : Prop :=
  s.phase = .staged current out ∧ packet = current ∧ current.binding = s.binding ∧
  current.sequence = s.next ∧ clean r

def finish (s : Session) : Session :=
  { s with next := s.next + 1, completed := s.completed + 1, phase := .idle }

def retire (s : Session) : Session := { s with phase := .retiring }
def reaped (s : Session) : Session := { s with phase := .dead }

theorem start_requires_idle {s : Session} {q : Request} (h : canStart s q) :
    s.phase = .idle := h.1

theorem start_requires_binding {s : Session} {q : Request} (h : canStart s q) :
    q.binding = s.binding := h.2.1

theorem start_requires_sequence {s : Session} {q : Request} (h : canStart s q) :
    q.sequence = s.next := h.2.2.1

theorem busy_has_no_second_request (s : Session) (first next : Request) :
    ¬ canStart (start s first) next := by
  intro h
  cases h.1

theorem stale_binding_denied {s : Session} {q : Request}
    (h : q.binding ≠ s.binding) : ¬ canStart s q := fun accepted => h accepted.2.1

theorem stale_sequence_denied {s : Session} {q : Request}
    (h : q.sequence ≠ s.next) : ¬ canStart s q := fun accepted => h accepted.2.2.1

theorem publication_exact {s : Session} {current packet : Request} {out : Output} {r : Reset}
    (h : publishable s current packet out r) : packet = current := h.2.1

theorem publication_requires_reset {s : Session} {current packet : Request} {out : Output} {r : Reset}
    (h : publishable s current packet out r) : clean r := h.2.2.2.2

theorem retiring_cannot_publish (s : Session) (current packet : Request) (out : Output) (r : Reset) :
    ¬ publishable (retire s) current packet out r := by
  intro h
  cases h.1

theorem dead_cannot_publish (s : Session) (current packet : Request) (out : Output) (r : Reset) :
    ¬ publishable (reaped s) current packet out r := by
  intro h
  cases h.1

theorem reset_failure_denied {s : Session} {current packet : Request} {out : Output} {r : Reset}
    (h : ¬ clean r) : ¬ publishable s current packet out r :=
  fun accepted => h (publication_requires_reset accepted)

theorem completed_sequence_not_reused (s : Session) (q : Request) (h : q.sequence = s.next) :
    ¬ canStart (finish s) q := by
  intro accepted
  have eq := accepted.2.2.1
  simp only [finish] at eq
  omega

theorem request_cap_denied {s : Session} {q : Request} (h : 64 ≤ s.completed) :
    ¬ canStart s q := by
  intro accepted
  have bound := accepted.2.2.2
  omega

/-- Whole-session CPU is monotone; retaining the old cap bounds each request too. -/
theorem per_request_cpu_from_lifetime (before after : Nat)
    (_monotone : before ≤ after) (cap : after ≤ 12000) : after - before ≤ 12000 := by
  omega

structure Capacity where
  live : Nat
  activePrincipal : Nat
  deriving DecidableEq, Repr

/-- Idle reusable processes continue to consume a global live-process slot. -/
def spawn (c : Capacity) : Capacity := { c with live := c.live + 1 }
def quiesce (c : Capacity) : Capacity := { c with activePrincipal := 0 }
def releaseReaped (c : Capacity) : Capacity := { c with live := c.live - 1 }

theorem spawn_global_bound (c : Capacity) (h : c.live < 2) : (spawn c).live ≤ 2 := by
  simp only [spawn]
  omega

theorem idle_still_counted (c : Capacity) : (quiesce c).live = c.live := rfl

theorem idle_releases_principal (c : Capacity) : (quiesce c).activePrincipal = 0 := rfl

/-- A permit is released only after reaping is a fact in the transition premise. -/
def mayReleaseLive (s : Session) : Prop := s.phase = .dead

theorem retirement_does_not_release_live (s : Session) : ¬ mayReleaseLive (retire s) := by
  intro h
  cases h

theorem reaped_can_release_live (s : Session) : mayReleaseLive (reaped s) := rfl

/-- Advisory transitions do not contain any durable-state update operation. -/
structure Durable where
  head : Nat
  history : List String
  receipts : List String
  deriving DecidableEq, Repr

def advisory (d : Durable) (s : Session) : Durable × Session := (d, s)

theorem advisory_preserves_durable (d : Durable) (s : Session) : (advisory d s).1 = d := rfl

/-- Runtime refinement to fresh validation is assumed, never inferred from reset. -/
def observationallyFresh (fresh session : Request → Output) : Prop :=
  ∀ q, session q = fresh q

theorem fresh_correspondence_is_required (fresh session : Request → Output)
    (h : observationallyFresh fresh session) (q : Request) : session q = fresh q := h q

/-- A concrete modeled exchange witnesses that the admission/reset rules are inhabited. -/
def witnessBinding : Binding := ⟨"principal", "workspace", "launch", "policy", "dependency", "image", 1⟩
def witnessRequest : Request :=
  ⟨witnessBinding, 0, "nonce", "document", 0, "draft", 0, "body", "base", "inventory"⟩
def witnessSession : Session := ⟨witnessBinding, 0, 0, .idle⟩
def witnessReset : Reset := ⟨true, true, true, true, true⟩
def witnessOutput : Output := ⟨.valid, "output"⟩

theorem nonvacuous_advisory_exchange :
    canStart witnessSession witnessRequest ∧
    publishable { witnessSession with phase := .staged witnessRequest witnessOutput }
      witnessRequest witnessRequest witnessOutput witnessReset := by
  simp [canStart, publishable, clean, witnessSession, witnessRequest, witnessReset]

end Allow.ValidatorSessionCandidate
