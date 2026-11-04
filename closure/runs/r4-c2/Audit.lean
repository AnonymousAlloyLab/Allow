import Allow
example : (∀ {Γ : List Allow.Ty} {e : Allow.Raw} {t : Allow.Ty}, Allow.inferType Γ e = some t → Allow.HasType Γ e t) := @Allow.infer_sound
#check Allow.infer_sound
#print axioms Allow.infer_sound
example : (∀ {Γ : List Allow.Ty} {e : Allow.Raw} {t : Allow.Ty}, Allow.HasType Γ e t → Allow.HoleFree e) := @Allow.typed_hole_free
#check Allow.typed_hole_free
#print axioms Allow.typed_hole_free
example : (∀ {Γ : List Allow.Ty} {t : Allow.Ty} {e : Allow.Raw}, Allow.checkSlot Γ t e = true → Allow.HasType Γ e t) := @Allow.checkSlot_sound
#check Allow.checkSlot_sound
#print axioms Allow.checkSlot_sound
example : (∀ (s : Allow.State) (base : Nat) (Γ : List Allow.Ty) (e : Allow.Raw), ¬ (base = s.revision ∧ Allow.checkSlot Γ Allow.Ty.formula e = true) → Allow.commit s base Γ e = s) := @Allow.reject_preserves
#check Allow.reject_preserves
#print axioms Allow.reject_preserves
example : (∀ (s : Allow.State) (base : Nat) (Γ : List Allow.Ty) (e : Allow.Raw), s.Valid → (Allow.commit s base Γ e).Valid) := @Allow.commit_preserves
#check Allow.commit_preserves
#print axioms Allow.commit_preserves
example : (∀ (s : Allow.State) (Γ : List Allow.Ty) (e : Allow.Raw), Allow.checkSlot Γ Allow.Ty.formula e = true → (Allow.commit s s.revision Γ e).revision = s.revision + 1) := @Allow.commit_revision
#check Allow.commit_revision
#print axioms Allow.commit_revision
example : (∀ {p : Allow.Presentation} {e : Allow.Evidence}, Allow.visible p e = true → e.key = p.key ∧ e.epoch = p.epoch ∧ p.draftHash = p.key.sourceHash) := @Allow.visible_is_current
#check Allow.visible_is_current
#print axioms Allow.visible_is_current
example : (∀ {n : Nat} (a b : Allow.Formula n), Allow.canonical a = Allow.canonical b ↔ ∀ (v : Fin n → Bool), Allow.eval v a = Allow.eval v b) := @Allow.canonical_eq_iff
#check Allow.canonical_eq_iff
#print axioms Allow.canonical_eq_iff
example : (∀ {n : Nat} {a b : Allow.Formula n}, Allow.Certificate a b → ∀ (v : Fin n → Bool), Allow.eval v a = Allow.eval v b) := @Allow.certificate_sound
#check Allow.certificate_sound
#print axioms Allow.certificate_sound
example : (∀ {n : Nat} {a b : Allow.ContextualFormula n}, Allow.CertifiedMerge a b → Allow.canonicalKey a = Allow.canonicalKey b) := @Allow.certified_merge_canonical
#check Allow.certified_merge_canonical
#print axioms Allow.certified_merge_canonical
example : (∀ (k : Allow.CommandKind) (s : Allow.SolverStatus), Allow.report k s ≠ Allow.Conclusion.unboundedValidity) := @Allow.no_unbounded_claim
#check Allow.no_unbounded_claim
#print axioms Allow.no_unbounded_claim
example : (∀ (k : Allow.CommandKind) (s : Allow.SolverStatus), s = Allow.SolverStatus.UNKNOWN ∨ s = Allow.SolverStatus.TIMEOUT ∨ s = Allow.SolverStatus.CANCELLED ∨ s = Allow.SolverStatus.ERROR → ¬ Allow.Absence (Allow.report k s)) := @Allow.unknown_is_not_unsat
#check Allow.unknown_is_not_unsat
#print axioms Allow.unknown_is_not_unsat
example : (∀ {s : Allow.RetrievalScope} {rows : List Allow.Row} {r : Allow.Row}, r ∈ Allow.retrieve s rows → r.scope = s ∧ r.deleted = false ∧ r.permitted = true) := @Allow.retrieval_is_authorized
#check Allow.retrieval_is_authorized
#print axioms Allow.retrieval_is_authorized
example : (∀ {target : Allow.TargetContext} {pool : Allow.Polarity} {run : Allow.Run} {w : Allow.Witness}, Allow.admitPair target pool run w = true → run.query.target = target ∧ run.query.polarity = pool ∧ w.ownQuery = run.query ∧ run.status = Allow.SolverStatus.SAT ∧ w.validated = true) := @Allow.pair_admission_bound
#check Allow.pair_admission_bound
#print axioms Allow.pair_admission_bound
example : (∃ c : Allow.KernelConfig, c = Allow.generatedKernel ∧ Allow.Coherent c) := @Allow.contract_has_witness
#check Allow.contract_has_witness
#print axioms Allow.contract_has_witness
example : (((∃ _ : Empty, True) ∨ True) ∧ ¬ (∃ _ : Empty, True ∨ True)) := @Allow.empty_domain_counterexample
#check Allow.empty_domain_counterexample
#print axioms Allow.empty_domain_counterexample
example : (∀ {n : Nat} (t : Allow.Table n), Allow.tabulate n (Allow.lookup t) = t) := @Allow.canonical_idempotent
#check Allow.canonical_idempotent
#print axioms Allow.canonical_idempotent
example : (∀ {n : Nat} (a b : Allow.ContextualFormula n), a.inventory ≠ b.inventory → Allow.canonicalKey a ≠ Allow.canonicalKey b) := @Allow.distinct_inventories_distinct_keys
#check Allow.distinct_inventories_distinct_keys
#print axioms Allow.distinct_inventories_distinct_keys
example : (∀ (p : Allow.Presentation) (e : Allow.Evidence) (draft : String), e.epoch = p.epoch → Allow.visible (Allow.edit p draft) e = false) := @Allow.edit_hides_old
#check Allow.edit_hides_old
#print axioms Allow.edit_hides_old
example : (Allow.inferType [] (.existsRel 7 (.someRel (.ref 0))) = some .formula) := @Allow.accepted_formula_witness
#check Allow.accepted_formula_witness
#print axioms Allow.accepted_formula_witness
example : (Allow.inferType [.relation 7 []] (.and (.ref 0) .truth) = none) := @Allow.rejected_bad_drop_witness
#check Allow.rejected_bad_drop_witness
#print axioms Allow.rejected_bad_drop_witness
example : ((Allow.commit ⟨[], .truth, 0⟩ 0 [] (.not .truth)).revision = 1) := @Allow.accepted_commit_witness
#check Allow.accepted_commit_witness
#print axioms Allow.accepted_commit_witness
example : (Allow.visible ⟨Allow.sampleKey, 4, "source"⟩ ⟨Allow.sampleKey, 4⟩ = true) := @Allow.visible_evidence_witness
#check Allow.visible_evidence_witness
#print axioms Allow.visible_evidence_witness
example : (Allow.admitPair Allow.sampleTarget .positive ⟨Allow.positiveQuery, .SAT⟩ ⟨Allow.positiveQuery, "instanceA", true⟩ = true ∧ Allow.admitPair Allow.sampleTarget .negative ⟨Allow.negativeQuery, .SAT⟩ ⟨Allow.negativeQuery, "instanceB", true⟩ = true ∧ Allow.positiveQuery ≠ Allow.negativeQuery) := @Allow.admitted_pools_witness
#check Allow.admitted_pools_witness
#print axioms Allow.admitted_pools_witness
example : (Allow.canonical (Allow.Formula.truth : Allow.Formula 1) ≠ Allow.canonical Allow.Formula.falsity) := @Allow.nontrivial_canonical_witness
#check Allow.nontrivial_canonical_witness
#print axioms Allow.nontrivial_canonical_witness
