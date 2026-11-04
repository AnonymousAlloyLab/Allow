import Allow.Evidence

namespace Allow

inductive NodeTag where
  | hole | truth | ref | not | and | or | implies | union | someRel | existsRel
  deriving DecidableEq, Repr

inductive RuleTag where
  | andComm | andAssoc | andIdem | orComm | orAssoc | orIdem | doubleNot | deMorgan
  deriving DecidableEq, Repr

structure KernelConfig where
  version : String
  typePolicy : String
  nodes : List NodeTag
  atomLimit : Nat
  rules : List RuleTag
  statuses : List SolverStatus
  analysisLabel : String
  ragEnabled : Bool
  releaseEnabled : Bool
  toolchain : String
  deriving DecidableEq, Repr

/-- Configuration coherence only; framework integration and release are future gates. -/
def Coherent (c : KernelConfig) : Prop :=
  c.version = "allow-kernel-v1" ∧
  c.typePolicy = "exact_nominal_nonempty_relation_schema" ∧
  c.nodes = [.hole, .truth, .ref, .not, .and, .or, .implies, .union, .someRel, .existsRel] ∧
  0 < c.atomLimit ∧ c.atomLimit ≤ 8 ∧
  c.rules = [.andComm, .andAssoc, .andIdem, .orComm, .orAssoc, .orIdem, .doubleNot, .deMorgan] ∧
  c.statuses = [.SAT, .UNSAT, .UNKNOWN, .TIMEOUT, .CANCELLED, .ERROR] ∧
  c.analysisLabel = "BOUNDED_ONLY" ∧ c.ragEnabled = false ∧ c.releaseEnabled = false ∧
  c.toolchain = "leanprover/lean4:v4.34.1"

end Allow
