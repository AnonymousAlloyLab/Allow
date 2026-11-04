import Allow
import Allow.Associativity
import Allow.PartialTypes
example : (∀ {Γ : List Allow.Ty} {e : Allow.Raw} {t : Allow.Ty}, Allow.inferType Γ e = some t → Allow.HasType Γ e t) := @Allow.infer_sound
example : (∀ {Γ : List Allow.Ty} {e : Allow.Raw} {t : Allow.Ty}, Allow.HasType Γ e t → Allow.HoleFree e) := @Allow.typed_hole_free
example : (∀ {Γ : List Allow.Ty} {t : Allow.Ty} {e : Allow.Raw}, Allow.checkSlot Γ t e = true → Allow.HasType Γ e t) := @Allow.checkSlot_sound
example : (∀ (s : Allow.State) (base : Nat) (Γ : List Allow.Ty) (e : Allow.Raw), ¬ (base = s.revision ∧ Allow.checkSlot Γ Allow.Ty.formula e = true) → Allow.commit s base Γ e = s) := @Allow.reject_preserves
example : (∀ (s : Allow.State) (base : Nat) (Γ : List Allow.Ty) (e : Allow.Raw), s.Valid → (Allow.commit s base Γ e).Valid) := @Allow.commit_preserves
example : (∀ (s : Allow.State) (Γ : List Allow.Ty) (e : Allow.Raw), Allow.checkSlot Γ Allow.Ty.formula e = true → (Allow.commit s s.revision Γ e).revision = s.revision + 1) := @Allow.commit_revision
example : (∀ {p : Allow.Presentation} {e : Allow.Evidence}, Allow.visible p e = true → e.key = p.key ∧ e.epoch = p.epoch ∧ p.draftHash = p.key.sourceHash) := @Allow.visible_is_current
example : (∀ {n : Nat} (a b : Allow.Formula n), Allow.canonical a = Allow.canonical b ↔ ∀ (v : Fin n → Bool), Allow.eval v a = Allow.eval v b) := @Allow.canonical_eq_iff
example : (∀ {n : Nat} {a b : Allow.Formula n}, Allow.Certificate a b → ∀ (v : Fin n → Bool), Allow.eval v a = Allow.eval v b) := @Allow.certificate_sound
example : (∀ {n : Nat} {a b : Allow.ContextualFormula n}, Allow.CertifiedMerge a b → Allow.canonicalKey a = Allow.canonicalKey b) := @Allow.certified_merge_canonical
example : (∀ (k : Allow.CommandKind) (s : Allow.SolverStatus), Allow.report k s ≠ Allow.Conclusion.unboundedValidity) := @Allow.no_unbounded_claim
example : (∀ (k : Allow.CommandKind) (s : Allow.SolverStatus), s = Allow.SolverStatus.UNKNOWN ∨ s = Allow.SolverStatus.TIMEOUT ∨ s = Allow.SolverStatus.CANCELLED ∨ s = Allow.SolverStatus.ERROR → ¬ Allow.Absence (Allow.report k s)) := @Allow.unknown_is_not_unsat
example : (∀ {s : Allow.RetrievalScope} {rows : List Allow.Row} {r : Allow.Row}, r ∈ Allow.retrieve s rows → r.scope = s ∧ r.deleted = false ∧ r.permitted = true) := @Allow.retrieval_is_authorized
example : (∀ {target : Allow.TargetContext} {pool : Allow.Polarity} {run : Allow.Run} {w : Allow.Witness}, Allow.admitPair target pool run w = true → run.query.target = target ∧ run.query.polarity = pool ∧ w.ownQuery = run.query ∧ run.status = Allow.SolverStatus.SAT ∧ w.validated = true) := @Allow.pair_admission_bound
example : (∃ c : Allow.KernelConfig, c = Allow.generatedKernel ∧ Allow.Coherent c) := @Allow.contract_has_witness
example : (((∃ _ : Empty, True) ∨ True) ∧ ¬ (∃ _ : Empty, True ∨ True)) := @Allow.empty_domain_counterexample
example : (∀ {n : Nat} (t : Allow.Table n), Allow.tabulate n (Allow.lookup t) = t) := @Allow.canonical_idempotent
example : (∀ {n : Nat} (a b : Allow.ContextualFormula n), a.inventory ≠ b.inventory → Allow.canonicalKey a ≠ Allow.canonicalKey b) := @Allow.distinct_inventories_distinct_keys
example : (∀ (p : Allow.Presentation) (e : Allow.Evidence) (draft : String), e.epoch = p.epoch → Allow.visible (Allow.edit p draft) e = false) := @Allow.edit_hides_old
example : (Allow.inferType [] (.existsRel 7 (.someRel (.ref 0))) = some .formula) := @Allow.accepted_formula_witness
example : (Allow.inferType [.relation 7 []] (.and (.ref 0) .truth) = none) := @Allow.rejected_bad_drop_witness
example : ((Allow.commit ⟨[], .truth, 0⟩ 0 [] (.not .truth)).revision = 1) := @Allow.accepted_commit_witness
example : (Allow.visible ⟨Allow.sampleKey, 4, "source"⟩ ⟨Allow.sampleKey, 4⟩ = true) := @Allow.visible_evidence_witness
example : (Allow.admitPair Allow.sampleTarget .positive ⟨Allow.positiveQuery, .SAT⟩ ⟨Allow.positiveQuery, "instanceA", true⟩ = true ∧ Allow.admitPair Allow.sampleTarget .negative ⟨Allow.negativeQuery, .SAT⟩ ⟨Allow.negativeQuery, "instanceB", true⟩ = true ∧ Allow.positiveQuery ≠ Allow.negativeQuery) := @Allow.admitted_pools_witness
example : (Allow.canonical (Allow.Formula.truth : Allow.Formula 1) ≠ Allow.canonical Allow.Formula.falsity) := @Allow.nontrivial_canonical_witness
example : (∀ (p : Allow.Slots.Presented) (labels : Allow.Slots.Slot → String), Allow.Slots.anonymous {p with names := labels} = Allow.Slots.anonymous p) := @Allow.Slots.names_do_not_affect_payload
example : (∀ (p : Allow.Slots.Presented) (labels : Allow.Slots.Slot → String) (source origin : String), Allow.Slots.embedding {p with names := labels, source := source, origin := origin} = Allow.Slots.embedding p) := @Allow.Slots.names_do_not_affect_embedding
example : (∀ (a b : Allow.Slots.Slot), a ≠ b → Allow.Slots.Tree.reference a ≠ Allow.Slots.Tree.reference b) := @Allow.Slots.distinct_slots_remain_distinct
example : (∀ (p : Allow.Slots.Presented), Allow.Slots.embedding p = (⟨1, p.resolved⟩ : Allow.Slots.EmbeddingInput)) := @Allow.Slots.embedding_has_no_presentation
example : (∀ {active capacity next : Nat}, Allow.Foundation.admit active capacity = some next → next ≤ capacity) := @Allow.Foundation.admission_bounded
example : (∀ (prior incoming : Allow.SolverStatus), Allow.Foundation.finish (.terminal prior) incoming = .terminal prior) := @Allow.Foundation.terminal_is_final
example : (Allow.Foundation.cancel .running = .terminal .CANCELLED ∧ ∀ incoming, Allow.Foundation.finish (Allow.Foundation.cancel .running) incoming = .terminal .CANCELLED) := @Allow.Foundation.cancel_is_not_unsat
example : (∀ {m : Allow.Foundation.MethodMetadata}, Allow.Foundation.acceptable m = true → m.lines ≤ 30 ∧ m.documented = true ∧ m.encapsulated = true) := @Allow.Foundation.accepted_style_bounded
example : (∀ {n : Nat} {a b : Allow.Formula n}, Allow.EGraph.Rule a b → ∀ (v : Fin n → Bool), Allow.eval v a = Allow.eval v b) := @Allow.EGraph.rule_sound
example : (∀ {n : Nat} {a b : Allow.Formula n}, Allow.EGraph.Derivation a b → ∀ (v : Fin n → Bool), Allow.eval v a = Allow.eval v b) := @Allow.EGraph.derivation_sound
example : (∀ {n : Nat} {g : Allow.EGraph.Graph n} {a b : Allow.ContextualFormula n}, Allow.EGraph.Merge g a b → Allow.canonicalKey a = Allow.canonicalKey b) := @Allow.EGraph.merge_preserves_key
example : (∀ {n : Nat} {a b : Allow.Formula n} (g : Allow.EGraph.Graph n), g.sameClass a b → ∀ (v : Fin n → Bool), Allow.eval v a = Allow.eval v b) := @Allow.EGraph.class_sound
example : (∀ {n : Nat} (g : Allow.EGraph.Graph n) (root extracted : Allow.Formula n), g.sameClass root extracted → ∀ (v : Fin n → Bool), Allow.eval v root = Allow.eval v extracted) := @Allow.EGraph.extraction_sound
example : (∀ (remaining : Bool) (reason : Allow.EGraph.StopReason), reason ≠ Allow.EGraph.StopReason.saturated → Allow.EGraph.stopReason remaining reason = Allow.EGraph.StopReason.saturated → remaining = false) := @Allow.EGraph.bounded_run_no_false_saturation
example : (∀ {n : Nat} {Tuple : Type} {a b : Allow.EGraph.RelExpr n}, Allow.EGraph.RelRule a b → ∀ (v : Fin n → Allow.EGraph.Relation Tuple), Allow.EGraph.evalRelation v a = Allow.EGraph.evalRelation v b) := @Allow.EGraph.rel_rule_sound
example : (∀ {n : Nat} {Tuple : Type} {a b : Allow.EGraph.RelExpr n}, Allow.EGraph.RelDerivation a b → ∀ (v : Fin n → Allow.EGraph.Relation Tuple), Allow.EGraph.evalRelation v a = Allow.EGraph.evalRelation v b) := @Allow.EGraph.rel_derivation_sound
example : (∀ {n : Nat} {Tuple : Type} {g : Allow.EGraph.RelGraph n} {a b : Allow.EGraph.ContextualRelation n}, Allow.EGraph.RelMerge g a b → a.context = b.context ∧ a.schema = b.schema ∧ a.inventory = b.inventory ∧ ∀ (v : Fin n → Allow.EGraph.Relation Tuple), Allow.EGraph.evalRelation v a.body = Allow.EGraph.evalRelation v b.body) := @Allow.EGraph.rel_merge_sound
example : (∀ {n : Nat} {Tuple : Type} (g : Allow.EGraph.RelGraph n) (root extracted : Allow.EGraph.RelExpr n), g.sameClass root extracted → ∀ (v : Fin n → Allow.EGraph.Relation Tuple), Allow.EGraph.evalRelation v root = Allow.EGraph.evalRelation v extracted) := @Allow.EGraph.rel_extraction_sound
example : (∀ {n : Nat} {Tuple : Type} {a b : Allow.EGraph.RelExpr n}, Allow.EGraph.RelDerivation a b → ∀ (v : Fin n → Allow.EGraph.Relation Tuple), (∃ x, Allow.EGraph.evalRelation v a x = true) ↔ ∃ x, Allow.EGraph.evalRelation v b x = true) := @Allow.EGraph.rel_nonempty_congruence
example : (∀ {n : Nat} {Tuple : Type} {a b : Allow.EGraph.RelExpr n}, Allow.EGraph.RelDerivation a b → ∀ (v : Fin n → Allow.EGraph.Relation Tuple), (¬∃ x, Allow.EGraph.evalRelation v a x = true) ↔ ¬∃ x, Allow.EGraph.evalRelation v b x = true) := @Allow.EGraph.rel_empty_congruence
example : (∀ (a b : Bool), (!a || b) = if a = true then b else true) := @Allow.EGraph.implication_lowering
example : (∀ (a b : Bool), ((!a || b) && (!b || a)) = (a == b)) := @Allow.EGraph.iff_lowering
example : (Allow.EGraph.Derivation ((Allow.Formula.atom (0 : Fin 2)).and ((Allow.Formula.atom (0 : Fin 2)).or (Allow.Formula.atom (1 : Fin 2)))) (Allow.Formula.atom (0 : Fin 2))) := @Allow.EGraph.witness_boolean_absorption
example : (Allow.EGraph.RelDerivation ((Allow.EGraph.RelExpr.atom (0 : Fin 2)).inter ((Allow.EGraph.RelExpr.atom (0 : Fin 2)).union (Allow.EGraph.RelExpr.atom (1 : Fin 2)))) (Allow.EGraph.RelExpr.atom (0 : Fin 2))) := @Allow.EGraph.witness_relation_absorption
example : (Allow.EGraph.RelDerivation ((Allow.EGraph.RelExpr.atom (0 : Fin 1)).diff (Allow.EGraph.RelExpr.atom (0 : Fin 1))) Allow.EGraph.RelExpr.empty) := @Allow.EGraph.witness_relation_difference
example : (Allow.EGraph.stopReason true Allow.EGraph.StopReason.nodeLimit ≠ Allow.EGraph.StopReason.saturated) := @Allow.EGraph.witness_budget_stop
example : (∀ {n bn rn : Nat} {Tuple : Type} (σ : Fin n → Allow.EGraph.MixedFormula bn rn) (a : Allow.Formula n) (bv : Fin bn → Bool) (rv : Fin rn → Allow.EGraph.Relation Tuple) (domain : List Tuple), Allow.EGraph.evalMixed bv rv domain (Allow.EGraph.substB σ a) = Allow.eval (fun i => Allow.EGraph.evalMixed bv rv domain (σ i)) a) := @Allow.EGraph.eval_substB
example : (∀ {bn rn : Nat} {Tuple : Type} {a b : Allow.EGraph.MixedFormula bn rn}, Allow.EGraph.MixedDerivation a b → ∀ (bv : Fin bn → Bool) (rv : Fin rn → Allow.EGraph.Relation Tuple) (domain : List Tuple), Allow.EGraph.evalMixed bv rv domain a = Allow.EGraph.evalMixed bv rv domain b) := @Allow.EGraph.mixed_sound
example : (∀ {n : Nat} {t : Allow.TargetContext} {pos neg : List Allow.Retrieval.Member}, Allow.Retrieval.ready n t pos neg → 3 ≤ n ∧ n ≤ 5) := @Allow.Retrieval.ready_bounds
example : (∀ {n : Nat} {t : Allow.TargetContext} {pos neg : List Allow.Retrieval.Member}, Allow.Retrieval.ready n t pos neg → pos.length = n) := @Allow.Retrieval.ready_positive_size
example : (∀ {n : Nat} {t : Allow.TargetContext} {pos neg : List Allow.Retrieval.Member}, Allow.Retrieval.ready n t pos neg → neg.length = n) := @Allow.Retrieval.ready_negative_size
example : (∀ {n : Nat} {t : Allow.TargetContext} {pos neg : List Allow.Retrieval.Member}, Allow.Retrieval.ready n t pos neg → (List.map (fun m => m.witness.fullInstanceHash) pos).Nodup) := @Allow.Retrieval.ready_positive_distinct
example : (∀ {n : Nat} {t : Allow.TargetContext} {pos neg : List Allow.Retrieval.Member}, Allow.Retrieval.ready n t pos neg → (List.map (fun m => m.witness.fullInstanceHash) neg).Nodup) := @Allow.Retrieval.ready_negative_distinct
example : (∀ {n : Nat} {t : Allow.TargetContext} {pos neg : List Allow.Retrieval.Member} {m : Allow.Retrieval.Member}, Allow.Retrieval.ready n t pos neg → m ∈ pos → Allow.Retrieval.admitted t Allow.Polarity.positive m) := @Allow.Retrieval.ready_positive_admitted
example : (∀ {n : Nat} {t : Allow.TargetContext} {pos neg : List Allow.Retrieval.Member} {m : Allow.Retrieval.Member}, Allow.Retrieval.ready n t pos neg → m ∈ neg → Allow.Retrieval.admitted t Allow.Polarity.negative m) := @Allow.Retrieval.ready_negative_admitted
example : (∀ {n : Nat} {t : Allow.TargetContext} {pos neg : List Allow.Retrieval.Member}, n < 3 → ¬Allow.Retrieval.ready n t pos neg) := @Allow.Retrieval.below_range_not_ready
example : (∀ {n : Nat} {t : Allow.TargetContext} {pos neg : List Allow.Retrieval.Member}, 5 < n → ¬Allow.Retrieval.ready n t pos neg) := @Allow.Retrieval.above_range_not_ready
example : (∀ {n : Nat} {t : Allow.TargetContext} {pos neg : List Allow.Retrieval.Member}, pos.length < n → ¬Allow.Retrieval.ready n t pos neg) := @Allow.Retrieval.partial_not_ready
example : (∀ (f p : Bool), Allow.Retrieval.queryEval Allow.Polarity.positive f p = (f && p)) := @Allow.Retrieval.positive_query
example : (∀ (f p : Bool), Allow.Retrieval.queryEval Allow.Polarity.negative f p = (f && !p)) := @Allow.Retrieval.negative_query
example : (∀ (f p : Bool), ¬(Allow.Retrieval.queryEval Allow.Polarity.positive f p = true ∧ Allow.Retrieval.queryEval Allow.Polarity.negative f p = true)) := @Allow.Retrieval.opposite_polarities_disjoint
example : ((∀ (x : Bool), x ∈ [false] → (fun _x => false) x = (fun x => x) x) ∧ ¬∀ (x : Bool), (fun _x => false) x = (fun x => x) x) := @Allow.Retrieval.finite_samples_incomplete
example : (∀ {α : Type} (p q : α → Bool) (x : α), p x = true → q x = false → ¬∀ (y : α), p y = q y) := @Allow.Retrieval.opposing_witness_refutes_equivalence
example : (∀ (a b c d : Allow.Retrieval.Block) (i : Fin 768), Allow.Retrieval.pack4 a b c d (Allow.Retrieval.index0 i) = a i) := @Allow.Retrieval.pack4_context
example : (∀ (a b c d : Allow.Retrieval.Block) (i : Fin 768), Allow.Retrieval.pack4 a b c d (Allow.Retrieval.index1 i) = b i) := @Allow.Retrieval.pack4_predicate
example : (∀ (a b c d : Allow.Retrieval.Block) (i : Fin 768), Allow.Retrieval.pack4 a b c d (Allow.Retrieval.index2 i) = c i) := @Allow.Retrieval.pack4_positive
example : (∀ (a b c d : Allow.Retrieval.Block) (i : Fin 768), Allow.Retrieval.pack4 a b c d (Allow.Retrieval.index3 i) = d i) := @Allow.Retrieval.pack4_negative
example : (∀ (v : Allow.Retrieval.Embedding), Allow.Retrieval.vectorWidth v = 3072) := @Allow.Retrieval.vector_width
example : (4 * 768 = 3072) := @Allow.Retrieval.four_blocks_width
example : (∀ (c p n : Nat), c ≤ 1000 → p ≤ 1000 → n ≤ 1000 → Allow.Retrieval.score c p n ≤ 1000) := @Allow.Retrieval.score_bounded
example : (Allow.Retrieval.score 0 0 0 = 0) := @Allow.Retrieval.score_zero
example : (Allow.Retrieval.score 1000 1000 1000 = 1000) := @Allow.Retrieval.score_max
example : (∀ (shared : Nat), Allow.Retrieval.overlap false shared = 0) := @Allow.Retrieval.incompatible_overlap_zero
example : (∀ {current result : Allow.Retrieval.Snapshot} {complete : Bool}, Allow.Retrieval.commit current result complete = true → current = result ∧ complete = true) := @Allow.Retrieval.commit_current
example : (∀ {current result : Allow.Retrieval.Snapshot} {complete : Bool}, current ≠ result → Allow.Retrieval.commit current result complete = false) := @Allow.Retrieval.stale_cannot_commit
example : (∀ (current result : Allow.Retrieval.Snapshot), Allow.Retrieval.commit current result false = false) := @Allow.Retrieval.partial_cannot_commit
example : (∀ (committed : Bool), Allow.Retrieval.visible committed true = false) := @Allow.Retrieval.revoked_invisible
example : (∀ {t : Allow.TargetContext} {p : Allow.Polarity} {m : Allow.Retrieval.Member}, Allow.Retrieval.admitted t p m → m.run.query.target = t ∧ m.run.query.polarity = p ∧ m.witness.ownQuery = m.run.query ∧ m.run.status = Allow.SolverStatus.SAT ∧ m.witness.validated = true) := @Allow.Retrieval.admitted_evidence
example : (Allow.Retrieval.ready 3 Allow.sampleTarget [Allow.Retrieval.sampleMember Allow.positiveQuery "a", Allow.Retrieval.sampleMember Allow.positiveQuery "b", Allow.Retrieval.sampleMember Allow.positiveQuery "c"] [Allow.Retrieval.sampleMember Allow.negativeQuery "d", Allow.Retrieval.sampleMember Allow.negativeQuery "e", Allow.Retrieval.sampleMember Allow.negativeQuery "f"]) := @Allow.Retrieval.ready_three_witness
example : (∀ {p : Allow.SqlRouting.Request} {r : Allow.SqlRouting.Report}, Allow.SqlRouting.admitted p r → r.sql = p.sql) := @Allow.SqlRouting.exact_request
example : (∀ {p : Allow.SqlRouting.Request} {r : Allow.SqlRouting.Report}, Allow.SqlRouting.admitted p r → r.binary = p.binary ∧ r.profile = p.profile ∧ r.policy = p.policy) := @Allow.SqlRouting.pinned_identity
example : (∀ {p : Allow.SqlRouting.Request} {r : Allow.SqlRouting.Report}, r.sql ≠ p.sql → ¬ Allow.SqlRouting.admitted p r) := @Allow.SqlRouting.mismatch_denied
example : (∀ {p : Allow.SqlRouting.Request} {r : Allow.SqlRouting.Report}, r.binary ≠ p.binary → ¬ Allow.SqlRouting.admitted p r) := @Allow.SqlRouting.binary_mismatch_denied
example : (∀ {p : Allow.SqlRouting.Request} {r : Allow.SqlRouting.Report}, r.profile ≠ p.profile → ¬ Allow.SqlRouting.admitted p r) := @Allow.SqlRouting.profile_mismatch_denied
example : (∀ {p : Allow.SqlRouting.Request} {r : Allow.SqlRouting.Report}, r.success = false → ¬ Allow.SqlRouting.admitted p r) := @Allow.SqlRouting.parser_failure_denied
example : (∀ {p : Allow.SqlRouting.Request} {r : Allow.SqlRouting.Report}, r.isOpaque = true → ¬ Allow.SqlRouting.admitted p r) := @Allow.SqlRouting.isOpaque_denied
example : (∀ {p : Allow.SqlRouting.Request} {e : Allow.SqlRouting.CacheEntry}, Allow.SqlRouting.cacheReuse p e → p = e.request ∧ Allow.SqlRouting.admitted p e.report) := @Allow.SqlRouting.cache_exact
example : (∀ {s : Allow.SqlRouting.State} {name : String} {p : Allow.SqlRouting.Portal}, Allow.SqlRouting.Reachable s → Allow.SqlRouting.execute s name = some p → Allow.SqlRouting.admitted p.request p.report) := @Allow.SqlRouting.execute_accepted
example : (Allow.SqlRouting.admitted Allow.SqlRouting.sampleRequest Allow.SqlRouting.sampleReport) := @Allow.SqlRouting.admission_witness
example : (Allow.SqlRouting.execute Allow.SqlRouting.sampleState "p" = some Allow.SqlRouting.samplePortal) := @Allow.SqlRouting.execution_witness
example : (¬ Allow.SqlRouting.admitted Allow.SqlRouting.sampleRequest { Allow.SqlRouting.sampleReport with isOpaque := true }) := @Allow.SqlRouting.denial_witness
example : (∀ (s : Allow.SqlRouting.State) (st : Allow.SqlRouting.Statement) (name : String), Allow.SqlRouting.Reachable s → Allow.SqlRouting.admitted st.request st.report → Allow.SqlRouting.Reachable (Allow.SqlRouting.bind (Allow.SqlRouting.parse s st) name st) ∧ Allow.SqlRouting.execute (Allow.SqlRouting.bind (Allow.SqlRouting.parse s st) name st) name = some ⟨name, st.request, st.report⟩) := @Allow.SqlRouting.parse_bind_execute
example : (∀ {p : Allow.SqlRouting.Request} {r : Allow.SqlRouting.Report}, r.derivation = false → ¬ Allow.SqlRouting.admitted p r) := @Allow.SqlRouting.derivation_failure_denied
example : (∀ {p : Allow.SqlRouting.Request} {r : Allow.SqlRouting.Report}, r.preserved = false → ¬ Allow.SqlRouting.admitted p r) := @Allow.SqlRouting.preservation_failure_denied
example : (∀ {s : Allow.SqlRouting.State}, Allow.SqlRouting.Reachable s → Allow.SqlRouting.wellFormed s) := @Allow.SqlRouting.reachable_wellFormed
example : (∀ {s : Allow.SqlRouting.State} {name : String} {q : Allow.SqlRouting.Request} {r : Allow.SqlRouting.Report}, Allow.SqlRouting.Reachable s → Allow.SqlRouting.nativeExecute s name q r → Allow.SqlRouting.admitted q r ∧ ∃ st, s.statements.find? (fun x => x.name == name) = some st ∧ Allow.SqlRouting.admitted st.request st.report) := @Allow.SqlRouting.native_execute_provenance
example : (∀ {s : Allow.SqlRouting.State} {name : String} {q : Allow.SqlRouting.Request} {r : Allow.SqlRouting.Report}, s.statements.find? (fun x => x.name == name) = none → ¬ Allow.SqlRouting.nativeExecute s name q r) := @Allow.SqlRouting.native_unknown_denied
example : (∀ (s : Allow.SqlRouting.State) (p : Allow.SqlRouting.NativePrepare) (portal : String), Allow.SqlRouting.Reachable s → Allow.SqlRouting.admitted p.statement.request p.statement.report → Allow.SqlRouting.bodyPart p → Allow.SqlRouting.Reachable (Allow.SqlRouting.bind (Allow.SqlRouting.nativePrepare s p) portal p.statement) ∧ Allow.SqlRouting.execute (Allow.SqlRouting.bind (Allow.SqlRouting.nativePrepare s p) portal p.statement) portal = some ⟨portal, p.statement.request, p.statement.report⟩) := @Allow.SqlRouting.native_prepare_bind
example : (∀ (s : Allow.SqlRouting.State) (e : Allow.SqlRouting.CacheEntry), (Allow.SqlRouting.cacheLookup s e).statements = s.statements) := @Allow.SqlRouting.cache_does_not_prepare
example : (Allow.SqlRouting.Reachable (Allow.SqlRouting.nativePrepare ⟨[], []⟩ Allow.SqlRouting.sampleNative) ∧ Allow.SqlRouting.bodyPart Allow.SqlRouting.sampleNative) := @Allow.SqlRouting.native_prepare_witness
example : (Allow.SqlRouting.nativeExecute (Allow.SqlRouting.nativePrepare ⟨[], []⟩ Allow.SqlRouting.sampleNative) "s" Allow.SqlRouting.sampleExecuteRequest Allow.SqlRouting.sampleExecuteReport) := @Allow.SqlRouting.native_execute_witness
example : (∀ (s : Allow.SqlRouting.CycleState) (cycle : Nat), cycle ∈ s.pending → ¬ Allow.SqlRouting.sourceAllowed s) := @Allow.SqlRouting.pending_blocks_source
example : (∀ (s : Allow.SqlRouting.CycleState) (cycle : Nat), ¬ Allow.SqlRouting.sourceAllowed (Allow.SqlRouting.forwardEffect s cycle)) := @Allow.SqlRouting.forward_blocks_source
example : (∀ (s : Allow.SqlRouting.CycleState) (ack : Nat), Allow.SqlRouting.completeCycle s ack false = s) := @Allow.SqlRouting.unvalidated_retains
example : (∀ (s : Allow.SqlRouting.CycleState) (ack cycle : Nat), cycle ∈ s.pending → ack < cycle → cycle ∈ (Allow.SqlRouting.completeCycle s ack true).pending) := @Allow.SqlRouting.completed_retains_newer
example : (∀ (s : Allow.SqlRouting.CycleState) (ack cycle : Nat), cycle ≤ ack → cycle ∉ (Allow.SqlRouting.completeCycle s ack true).pending) := @Allow.SqlRouting.completed_removes_older
example : (¬ Allow.SqlRouting.sourceAllowed (Allow.SqlRouting.forwardEffect ⟨[]⟩ 2) ∧ (Allow.SqlRouting.completeCycle ⟨[1, 2]⟩ 1 true).pending = [2] ∧ Allow.SqlRouting.sourceAllowed (Allow.SqlRouting.completeCycle ⟨[1]⟩ 1 true)) := @Allow.SqlRouting.cycle_barrier_witness
