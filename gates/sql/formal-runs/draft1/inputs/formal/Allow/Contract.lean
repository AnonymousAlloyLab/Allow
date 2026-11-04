import Allow.Generated
import Allow.Typing
import Allow.Canonical

namespace Allow

theorem generated_coherent : Coherent generatedKernel := by
  unfold Coherent
  decide

theorem contract_has_witness : ∃ c : KernelConfig, c = generatedKernel ∧ Coherent c := by
  exact ⟨generatedKernel, rfl, generated_coherent⟩

theorem accepted_formula_witness :
    inferType [] (.existsRel 7 (.someRel (.ref 0))) = some .formula := by decide

theorem rejected_bad_drop_witness :
    inferType [.relation 7 []] (.and (.ref 0) .truth) = none := by decide

theorem accepted_commit_witness :
    (commit ⟨[], .truth, 0⟩ 0 [] (.not .truth)).revision = 1 := by decide

theorem visible_evidence_witness :
    visible ⟨sampleKey, 4, "source"⟩ ⟨sampleKey, 4⟩ = true := by decide

theorem admitted_pools_witness :
    admitPair sampleTarget .positive ⟨positiveQuery, .SAT⟩
      ⟨positiveQuery, "instanceA", true⟩ = true ∧
    admitPair sampleTarget .negative ⟨negativeQuery, .SAT⟩
      ⟨negativeQuery, "instanceB", true⟩ = true ∧ positiveQuery ≠ negativeQuery := by decide

theorem nontrivial_canonical_witness :
    canonical (Formula.truth : Formula 1) ≠ canonical Formula.falsity := by decide

end Allow
