# Finite specification/model verification

This directory records the original specification-only phase. Its frozen inputs
are archived in `archives/r4-c2/`; later source edits are outside that report.
For the current implementation supplement, use `../scripts/verify_formal.py`
and `../gates/g1/formal-report.json`. The current implementation tests are
reported separately and are not certified by this original closure package.

Run the existing frozen package from the repository root with a fresh run name:

```bash
python3 closure/scripts/verify.py --run-id independent-replay
```

This requires the pinned local Lean 4.34.1 distribution, Python and jsonschema.
The installation paths and environment trust are in `closure-config.json` and
`tcb.json`. No external Lean packages are used. Each run copies frozen proof
sources into two fresh temporary directories and invokes the installed compiler;
it does not reuse this repository's `.lake` build outputs.

`reports/closure-report.json` points to the latest run. Each `runs/<id>/` directory
preserves its own logs, evidence, compiled-artifact hashes, proposition audit,
metadata and authoritative report. Existing run directories cannot be overwritten.
Exit codes are 0 for VERIFIED, 1 for BLOCKED and 2 for INFRASTRUCTURE_FAILURE.

The manifest binds the exact JSON contract/schema, proof sources, expected theorem
types, scripts, configuration, claims, trust, registry, provenance and council
reports. It excludes itself and the derived `input-root.json` to avoid recursive
hashing. Evidence/report outputs and the explanatory Markdown are not verification
inputs. The input root is SHA-256 of sorted, compact canonical manifest JSON.

The 25 claims are 19 fixed Lean propositions and six mechanical checks: schema,
projection, concrete witnesses, clean-build determinism, proof escape/axiom audit,
and final council-record binding. The record check confirms the required six
dispatches and final contract references; it does not certify reviewer judgment
or independently attest provider model execution.

Every theorem and witness is applied to a separately frozen expected proposition
in a generated Lean audit. Builds compare `.olean` hashes, proof inventory,
correspondence, provenance metadata and proof-status sets. Temporary paths, log
timings, run timestamps and editor/cache metadata are excluded from determinism
as declared before execution.

The finite TCB includes Lean and its standard logic/runtime, Lake, Python and
jsonschema, the verification scripts, SHA-256, OS/filesystem/process semantics,
hardware and interpretation of requirement prose. All are explicitly TRUSTED;
the verifier itself is not formally proved. Runtime Java/React/SQL correspondence
is absent and excluded, not implicitly discharged.

To change the candidate, preserve any failed run, edit the source/specification,
assign a new closure ID with `scripts/prepare.py`, and rerun. A prior VERIFIED
report does not apply to edited inputs. Preparation freezes a candidate; it does
not itself verify anything. Never repair evidence files by hand.
