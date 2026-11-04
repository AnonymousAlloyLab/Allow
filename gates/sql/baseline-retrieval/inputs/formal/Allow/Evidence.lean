import Std

namespace Allow

/-- Tokens stand for exact identities. Faithful hashing/serialization is a trust boundary. -/
structure AnalysisKey where
  workspace : String
  document : String
  revision : Nat
  sourceHash : String
  imports : String
  declarations : String
  command : String
  scopes : String
  integers : String
  sequenceBound : Nat
  temporalPolicy : String
  toolchain : String
  canonicalizer : String
  rewriteTheory : String
  workerOptions : String
  protocol : Nat
  deriving DecidableEq, Repr

structure Presentation where
  key : AnalysisKey
  epoch : Nat
  draftHash : String
  deriving DecidableEq, Repr

structure Evidence where
  key : AnalysisKey
  epoch : Nat
  deriving DecidableEq, Repr

def visible (p : Presentation) (e : Evidence) : Bool :=
  decide (e.key = p.key ∧ e.epoch = p.epoch ∧ p.draftHash = p.key.sourceHash)

theorem visible_is_current (h : visible p e = true) :
    e.key = p.key ∧ e.epoch = p.epoch ∧ p.draftHash = p.key.sourceHash := by
  simpa [visible] using h

def edit (p : Presentation) (draft : String) : Presentation :=
  { p with epoch := p.epoch + 1, draftHash := draft }

theorem edit_hides_old (p : Presentation) (e : Evidence) (draft : String)
    (h : e.epoch = p.epoch) : visible (edit p draft) e = false := by
  simp [visible, edit, h]

inductive SolverStatus where
  | SAT | UNSAT | UNKNOWN | TIMEOUT | CANCELLED | ERROR
  deriving DecidableEq, Repr

inductive CommandKind where
  | run | check
  deriving DecidableEq, Repr

inductive Conclusion where
  | instance | counterexample | noInstanceWithinBounds | noCounterexampleWithinBounds
  | inconclusive | unboundedValidity
  deriving DecidableEq, Repr

/-- Policy on already classified solver outcomes, not a proof about the solver. -/
def report (k : CommandKind) : SolverStatus → Conclusion
  | .SAT => match k with | .run => .instance | .check => .counterexample
  | .UNSAT => match k with
    | .run => .noInstanceWithinBounds
    | .check => .noCounterexampleWithinBounds
  | _ => .inconclusive

theorem no_unbounded_claim (k : CommandKind) (s : SolverStatus) :
    report k s ≠ .unboundedValidity := by cases k <;> cases s <;> decide

def Absence (c : Conclusion) : Prop :=
  c = .noInstanceWithinBounds ∨ c = .noCounterexampleWithinBounds

theorem unknown_is_not_unsat (k : CommandKind) (s : SolverStatus)
    (h : s = .UNKNOWN ∨ s = .TIMEOUT ∨ s = .CANCELLED ∨ s = .ERROR) :
    ¬ Absence (report k s) := by
  rcases h with h | h | h | h <;> subst s <;> cases k <;> simp [Absence, report]

structure RetrievalScope where
  tenant : String
  project : String
  model : String
  schema : Nat
  deriving DecidableEq, Repr

structure Row where
  scope : RetrievalScope
  deleted : Bool
  permitted : Bool
  deriving DecidableEq, Repr

def authorized (s : RetrievalScope) (r : Row) : Bool :=
  decide (r.scope = s ∧ r.deleted = false ∧ r.permitted = true)

def retrieve (s : RetrievalScope) (rows : List Row) := rows.filter (authorized s)

theorem retrieval_is_authorized (h : r ∈ retrieve s rows) :
    r.scope = s ∧ r.deleted = false ∧ r.permitted = true := by
  have hh := (List.mem_filter.mp h).2
  simpa [authorized] using hh

structure TargetContext where
  artifact : String
  environment : String
  bounds : String
  toolchain : String
  target : String
  deriving DecidableEq, Repr

inductive Polarity where
  | positive | negative
  deriving DecidableEq, Repr

structure QueryKey where
  target : TargetContext
  polarity : Polarity
  formulaHash : String
  deriving DecidableEq, Repr

structure Run where
  query : QueryKey
  /-- Existence observation, separate from a later enumeration terminal status. -/
  status : SolverStatus
  deriving DecidableEq, Repr

structure Witness where
  ownQuery : QueryKey
  fullInstanceHash : String
  validated : Bool
  deriving DecidableEq, Repr

/-- One member admission; a pair consists of separately checked positive/negative members. -/
def admitPair (target : TargetContext) (pool : Polarity) (run : Run) (w : Witness) : Bool :=
  decide (run.query.target = target ∧ run.query.polarity = pool ∧
    w.ownQuery = run.query ∧ run.status = .SAT ∧ w.validated = true)

theorem pair_admission_bound (h : admitPair target pool run w = true) :
    run.query.target = target ∧ run.query.polarity = pool ∧
    w.ownQuery = run.query ∧ run.status = .SAT ∧ w.validated = true := by
  simpa [admitPair] using h

def sampleKey : AnalysisKey :=
  ⟨"local", "doc", 1, "source", "imports", "decls", "run P", "scope=3", "bw=4", 3,
    "static", "pinned", "v1", "bool-v1", "options", 1⟩

example : visible ⟨sampleKey, 4, "source"⟩ ⟨sampleKey, 4⟩ = true := by decide
example : visible (edit ⟨sampleKey, 4, "source"⟩ "invalid draft") ⟨sampleKey, 4⟩ = false := by decide
example : retrieve ⟨"t", "p", "m", 1⟩ [⟨⟨"other", "p", "m", 1⟩, false, true⟩] = [] := by decide

def sampleTarget : TargetContext := ⟨"canonical", "env", "scope3", "pinned", "P"⟩
def positiveQuery : QueryKey := ⟨sampleTarget, .positive, "F and P"⟩
def negativeQuery : QueryKey := ⟨sampleTarget, .negative, "F and not P"⟩

example : admitPair sampleTarget .positive ⟨positiveQuery, .SAT⟩
    ⟨positiveQuery, "instanceA", true⟩ = true := by decide
example : admitPair sampleTarget .negative ⟨negativeQuery, .SAT⟩
    ⟨negativeQuery, "instanceB", true⟩ = true := by decide
example : admitPair sampleTarget .negative ⟨positiveQuery, .SAT⟩
    ⟨positiveQuery, "instanceA", true⟩ = false := by decide
example : positiveQuery ≠ negativeQuery := by decide

end Allow
