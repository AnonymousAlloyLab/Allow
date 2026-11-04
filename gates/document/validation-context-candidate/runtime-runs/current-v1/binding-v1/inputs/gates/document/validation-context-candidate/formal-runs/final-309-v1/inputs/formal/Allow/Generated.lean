-- Generated only from spec/allow-contract.json formal_kernel; do not hand edit.
import Allow.Kernel

namespace Allow

def generatedKernel : KernelConfig where
  version := "allow-kernel-v1"
  typePolicy := "exact_nominal_nonempty_relation_schema"
  nodes := [.hole, .truth, .ref, .not, .and, .or, .implies, .union, .someRel, .existsRel]
  atomLimit := 8
  rules := [.andComm, .andAssoc, .andIdem, .orComm, .orAssoc, .orIdem, .doubleNot, .deMorgan]
  statuses := [.SAT, .UNSAT, .UNKNOWN, .TIMEOUT, .CANCELLED, .ERROR]
  analysisLabel := "BOUNDED_ONLY"
  ragEnabled := false
  releaseEnabled := false
  toolchain := "leanprover/lean4:v4.34.1"

end Allow
