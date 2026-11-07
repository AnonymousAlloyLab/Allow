# Oracle parity finite policy claim map

Contract SHA-256: `32a9af30e99a53b4020a52ab3d34ac8044a039a1f9ca492126b6b6b4638d554d` (`spec/oracle-parity.json`). Model: `formal/Allow/OracleParity.lean`, SHA-256 `d9c433f35ef75d3d7454856fdd32d1e02fa1a0f4d16720ce16a390da6ef9b8b1`.

- `xor_categories`: Boolean disagreement is precisely the candidate-only or oracle-only truth category.
- `green_requirements`: green implies validation, four resolved outcomes, UNSAT in both directional differences, and SAT in at least one same-truth category.
- `red_requirements`: red implies validation, four resolved outcomes, and SAT in a directional difference.
- `unresolved_neutral`, `invalid_neutral`, `vacuous_neutral`: unknown/failure, failed validation, and four UNSAT outcomes are neutral.
- `binding_required`, `stale_neutral`, `disabled_neutral`, `offline_neutral`, `incomplete_neutral`, `unsupported_neutral`, `source_draft_neutral`: publication depends on exact binding and the stated lifecycle conditions. Any change in a modeled binding field makes a distinct binding stale.
- `advisory_preserves_revision`: the abstract advisory operation retains the revision.

The model abstracts validation and replay to a Boolean, identities to exact values, and completeness/authority/lifecycle to Boolean inputs. It does not establish that the implementation supplies these inputs correctly, that hashes are collision-free, that queries implement these categories, or that callbacks, parser, solver, replay, transport, UI, workers, or revision storage refine this model. It does not prove unbounded equivalence, oracle correctness, or commercial readiness. In particular the advisory theorem describes the modeled operation, not a proof about production mutation paths.

Using `leanprover/lean4:v4.34.1`, two independent direct compilations of the same source with `lake env lean -o /tmp/oracle-parity-{1,2}.olean Allow/OracleParity.lean` succeeded, with matching `.olean` SHA-256 `65055e8c28ef9a0771cbe68c924b8daf9656831b61e7ecebde4a7d3cdf021e71`. The two audit outputs matched SHA-256 `3e066836c32f02940fb5ccedc75fbbec30cbbbec0dc5b605712ff750262bdaca`; see `formal-axioms.txt`. Only Lean's standard `propext` appears, with no `sorryAx` or custom axioms. These are clean direct compilations, not claims about a full repository build or concrete implementation.
