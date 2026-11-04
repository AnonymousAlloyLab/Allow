import Allow.Associativity

/- Optional advisory-only abstraction. StoreRead, current authorization,
   immutable snapshot retention, worker correctness and implementation/DB
   correspondence are explicitly external trust obligations. -/
namespace Allow.DocumentAdvisoryCache
abbrev Id := Nat
abbrev Bytes := List UInt8

structure Scope where
  principal : Id
  launch : Id
  workspace : Id
  deriving DecidableEq, Repr
structure Key where
  scope : Scope
  document : Id
  revision : Nat
  deriving DecidableEq, Repr
inductive Kind where
  | signature | field | predicate | binder | fact | assertion | command | expression
  deriving DecidableEq, Repr
structure Definition where
  id : Id
  kind : Kind
  deriving DecidableEq, Repr
structure Snapshot where
  content : Bytes
  definitions : List Definition
  deriving DecidableEq, Repr
structure Entry where
  key : Key
  snapshot : Snapshot
  deriving DecidableEq, Repr
abbrev Cache := List Entry
abbrev Store := Key → Option Snapshot

/- Conservative accounting model, not a Java heap-size theorem. -/
def entryWeight (e : Entry) : Nat := 256 + e.snapshot.content.length + 64 * e.snapshot.definitions.length
def cacheWeight (cache : Cache) : Nat := (cache.map entryWeight).sum
def Capacity (cache : Cache) : Prop := cache.length ≤ 8 ∧ cacheWeight cache ≤ 8 * 1024 * 1024

def Valid (store : Store) (cache : Cache) : Prop :=
  Capacity cache ∧ ∀ entry ∈ cache, store entry.key = some entry.snapshot

def cacheLookup (cache : Cache) (key : Key) : Option Entry :=
  cache.find? (fun entry => entry.key == key)

def VerifiedRead (store : Store) (requested returned : Key) (snapshot : Snapshot) : Prop :=
  requested = returned ∧ store returned = some snapshot

theorem mismatched_read_rejected {store requested returned snapshot}
    (mismatch : requested ≠ returned) : ¬ VerifiedRead store requested returned snapshot := by
  intro read
  exact mismatch read.1

def StoreExtends (prior next : Store) : Prop :=
  ∀ key snapshot, prior key = some snapshot → next key = some snapshot

theorem valid_survives_immutable_append {prior next cache} (valid : Valid prior cache)
    (extension : StoreExtends prior next) : Valid next cache :=
  ⟨valid.1, fun entry member => extension entry.key entry.snapshot (valid.2 entry member)⟩

/- Insertion requires a previously successful independently scoped store read.
   The caller also checks the returned document and revision against the exact
   requested key. Eviction and process reset cannot create entries. -/
inductive Change (store : Store) : Cache → Cache → Prop where
  | insert : VerifiedRead store key returned snapshot → Capacity (⟨key,snapshot⟩ :: cache) →
      Change store cache (⟨key,snapshot⟩ :: cache)
  | evict : (∀ entry ∈ retained, entry ∈ cache) → Capacity retained → Change store cache retained
  | reset : Change store cache []

theorem valid_empty (store : Store) : Valid store [] := by
  simp [Valid,Capacity,cacheWeight]

theorem change_preserves_valid {store cache out} (h : Valid store cache) (step : Change store cache out) : Valid store out := by
  cases step with
  | insert read cap =>
    refine ⟨cap, ?_⟩
    intro e he
    simp only [List.mem_cons] at he
    rcases he with rfl | prior
    · simpa [read.1] using read.2
    · exact h.2 e prior
  | evict subset cap =>
    exact ⟨cap, fun e he => h.2 e (subset e he)⟩
  | reset => exact valid_empty store

theorem hit_key {cache key entry} (h : cacheLookup cache key = some entry) : entry.key = key := by
  have found := List.find?_some h
  simpa [cacheLookup] using found

theorem hit_exact_store {store cache key entry} (valid : Valid store cache)
    (hit : cacheLookup cache key = some entry) :
    entry.key = key ∧ store key = some entry.snapshot := by
  have member : entry ∈ cache := List.mem_of_find?_eq_some hit
  have same := hit_key hit
  exact ⟨same, by simpa [same] using valid.2 entry member⟩

theorem wrong_scope_cannot_match {cache key entry}
    (different : entry.key.scope ≠ key.scope) (hit : cacheLookup cache key = some entry) : False := by
  have same := hit_key hit
  exact different (congrArg Key.scope same)

theorem wrong_document_cannot_match {cache key entry}
    (different : entry.key.document ≠ key.document) (hit : cacheLookup cache key = some entry) : False := by
  exact different (congrArg Key.document (hit_key hit))

theorem wrong_revision_cannot_match {cache key entry}
    (different : entry.key.revision ≠ key.revision) (hit : cacheLookup cache key = some entry) : False := by
  exact different (congrArg Key.revision (hit_key hit))

def definitionLookup (snapshot : Snapshot) (id : Id) : Option Definition :=
  snapshot.definitions.find? (fun definition => definition.id == id)

theorem cached_definition_from_exact_revision {store cache key entry id definition}
    (valid : Valid store cache) (hit : cacheLookup cache key = some entry)
    (found : definitionLookup entry.snapshot id = some definition) :
    store key = some entry.snapshot ∧ definition ∈ entry.snapshot.definitions ∧ definition.id = id := by
  have source := (hit_exact_store valid hit).2
  have member : definition ∈ entry.snapshot.definitions := List.mem_of_find?_eq_some found
  have matchProof := List.find?_some found
  exact ⟨source,member,by simpa [definitionLookup] using matchProof⟩

/- Only advisory output is expressible. The worker is supplied current policy
   on every event and may produce diagnostics or an unavailable result. -/
inductive AdvisoryResult where | diagnostics (payload : Bytes) | unavailable
  deriving DecidableEq, Repr
abbrev Candidate := Bytes
abbrev Policy := Nat
abbrev Worker := Policy → Candidate → Snapshot → AdvisoryResult
structure State where
  head : Nat
  history : List Snapshot
  receipts : List Bytes
  cache : Cache
  deriving DecidableEq, Repr

inductive Preview (store : Store) (worker : Worker) (authorized ready permit : Prop)
    (currentPolicy : Policy) (candidate : Candidate) : State → Key → AdvisoryResult → State → Prop where
  | cacheHit : authorized → ready → permit → Valid store s.cache →
      cacheLookup s.cache key = some entry →
      Preview store worker authorized ready permit currentPolicy candidate s key
        (worker currentPolicy candidate entry.snapshot) s
  | storeRead : authorized → ready → permit → VerifiedRead store key returned snapshot →
      Preview store worker authorized ready permit currentPolicy candidate s key
        (worker currentPolicy candidate snapshot) s

theorem preview_preserves_authority {store worker auth ready permit policy candidate s key result out}
    (step : Preview store worker auth ready permit policy candidate s key result out) :
    out.head = s.head ∧ out.history = s.history ∧ out.receipts = s.receipts := by
  cases step <;> exact ⟨rfl,rfl,rfl⟩

theorem preview_requires_worker {store worker auth ready permit policy candidate s key result out}
    (step : Preview store worker auth ready permit policy candidate s key result out) :
    ∃ snapshot, store key = some snapshot ∧ result = worker policy candidate snapshot := by
  cases step with
  | cacheHit _ _ _ valid hit => exact ⟨_, (hit_exact_store valid hit).2, rfl⟩
  | storeRead _ _ _ read => exact ⟨_,by simpa [read.1] using read.2,rfl⟩

theorem preview_requires_current_checks {store worker auth ready permit policy candidate s key result out}
    (step : Preview store worker auth ready permit policy candidate s key result out) : auth ∧ ready ∧ permit := by
  cases step with
  | cacheHit a b c _ _ => exact ⟨a,b,c⟩
  | storeRead a b c _ => exact ⟨a,b,c⟩

/- No Preview result is a document commit, receipt, analysis or evidence value;
   those authorities are not constructors of AdvisoryResult. -/
def exampleKey : Key := ⟨⟨1,2,3⟩,4,5⟩
def exampleSnapshot : Snapshot := ⟨[7,8],[⟨9,.field⟩]⟩
def exampleStore : Store := fun k => if k == exampleKey then some exampleSnapshot else none

theorem example_exact_hit : cacheLookup [⟨exampleKey,exampleSnapshot⟩] exampleKey = some ⟨exampleKey,exampleSnapshot⟩ := by
  simp [cacheLookup]

theorem example_valid_cache : Valid exampleStore [⟨exampleKey,exampleSnapshot⟩] := by
  simp [Valid,Capacity,cacheWeight,entryWeight,exampleStore,exampleSnapshot]

theorem example_insertion_from_scoped_read :
    Change exampleStore [] [⟨exampleKey,exampleSnapshot⟩] := by
  apply Change.insert (returned := exampleKey)
  · simp [VerifiedRead,exampleStore]
  · simp [Capacity,cacheWeight,entryWeight,exampleSnapshot]

theorem example_wrong_returned_revision_rejected :
    ¬ VerifiedRead exampleStore exampleKey ⟨⟨1,2,3⟩,4,6⟩ exampleSnapshot := by
  apply mismatched_read_rejected
  simp [exampleKey]

theorem example_other_revision_miss :
    cacheLookup [⟨exampleKey,exampleSnapshot⟩] ⟨⟨1,2,3⟩,4,6⟩ = none := by
  simp [cacheLookup,exampleKey]

theorem example_other_scope_miss :
    cacheLookup [⟨exampleKey,exampleSnapshot⟩] ⟨⟨10,2,3⟩,4,5⟩ = none := by
  simp [cacheLookup,exampleKey]

theorem example_definition_is_owned :
    definitionLookup exampleSnapshot 9 = some ⟨9,.field⟩ := by
  simp [definitionLookup,exampleSnapshot]
end Allow.DocumentAdvisoryCache
