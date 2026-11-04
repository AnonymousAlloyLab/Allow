# ML handoff: code frozen, final measurement pending SQL adapter

The production ML source is frozen. Eleven ML tests pass on the isolated CPython 3.12.3 runtime. The final 62-package audit reports no known advisory matches; this does not certify whole-application security. See `dependency-security.json`, the hash-locked wheels, and `ml-verification.json`.

The exact original CPU encoder, adapter and validation decision must remain unchanged. Do not retrain, select a new checkpoint, retune weights, move families, or overwrite the prior reports.

## Preserved evidence

- Original 46-record export: `.runtime/corpus/manifests/records-3d255e2ad3cfc699c3a684afd3f41d3a3c62fce9ec0c6c9409fad6740656dfe9.json`.
- Original pilot: `.runtime/corpus/ml/pilot-3d255e2a-py312/`. Its evaluation SHA256 is `8836d6428445438905e2d9a1ec1614869fec0b6ba63fd78794a2768631df9d25`. It fitted 32 train pairs for 20 epochs. One test-family query lacked a checked augmentation; only 12 eligible families and one test family remained, so its quality gate is OPEN.
- Frozen adapter: original pilot `trained/adapter.npy`, SHA256 `298aea35c56a3a56698af4e58316ccafe22e847995ef1db9494415f212c65026`.
- Frozen validation decision: original pilot `validation-decision.json`, SHA256 `4de8368c3db4b8c298a364c70ebaed1fc349e6a5d124f383253b94dab73e5f83`. Weights are `[0.45, 0.1375, 0.41250000000000003]`.
- Repaired export: `.runtime/corpus/manifests/records-9c5e756785fb24e02337e6c06d8cf4088b6ae5e89bac481ea69e90a40647c113.json`. All original content IDs, content, contexts, families and splits are unchanged. Only one missing test augmentation was appended as a derived proof.
- Intermediate first repair measurement: `.runtime/corpus/ml/repair-9c5e7567-py312/`. **Do not promote using this artifact.** It measured MRR@10 of 1.0 for both methods, with 13 families and two test families, but audit found an incomplete promotion envelope and no independent replay binding for original heldout caches. Preserve it as exploratory history.

The frozen learned model ID is `allow-e5-hierarchy-v1-query-480-8192-32-membermean-bd2196e165ce0e20ecaf017f20e33d80ed88371197af1e459af1bf67ee7b9272`. The baseline model ID ends in `a40f0d4e5d9dd1cc213cbb55676491a47044352a7bd98a25120c774d6746b259`.

## Final measurement after SQL adapter integrity approval

Call `evaluation.rerun_repaired_holdout` with the repaired export, original pilot directory, a **new** output directory, and `integrity_pass=True` only after root authorizes the latest complete integrity gate. The required repair evidence includes:

```python
repair_evidence = {
    "original_export_path": ".runtime/corpus/manifests/records-3d255e2ad3cfc699c3a684afd3f41d3a3c62fce9ec0c6c9409fad6740656dfe9.json",
    "original_export_id": "3d255e2ad3cfc699c3a684afd3f41d3a3c62fce9ec0c6c9409fad6740656dfe9",
    "reason": "Direct pinned B_AND_TRUE proof repairs a generator omission; no records, family assignments, fit or weights changed",
    "derived_proof_row": "606b030b327e58691e33728099aafc4e98a26823cc67e1fef1cfc5e60068c9c1",
    # Add the latest approved SQL/runtime/HTTP gate paths and hashes here.
}
```

The helper validates historical export and eligible-manifest digests, unchanged historical projections and certificates, the checkpoint and decision hashes, and old certificate identities. It independently re-encodes **all 45 original canonical and exact certificate-bound variant inputs**, requiring bit-identical cached arrays. Training-cache hashes are additionally checked against the original training manifest. New cache hashes are explicitly repair-input bindings, not invented historical hashes. Only the formerly excluded test row may be added. No fitting or weight selection runs.

The new envelope includes `validation_decision_sha256`. After the measurement, root/Sol1 must independently validate and publish it through the SQL-adapted repository. This helper makes no database promotion call. Refresh public aggregate summaries and metadata hashes only after acceptance; retain the original and intermediate reports.

The original incomplete test subset was already observed. Any repaired measurement must say it is a technical-repair rerun, **not a fresh blind holdout**. Equality with the pretrained MRR supports the predeclared non-regression rule and does not demonstrate an improvement or broad semantic retrieval quality.
