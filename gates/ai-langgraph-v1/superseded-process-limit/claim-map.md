# LangGraph finite protocol claim map

Frozen supplement SHA-256 `6cbded4769020790882fe1b3542696385b5c98c5212d070ababde0534e004cff`. The following is a guarded abstraction, not an implementation or refinement proof. IDs and payload hashes are equality tokens. The host establishes scope of the fixed synthetic grant; the model treats it and ordinary consent as trusted exact consent. It does not prove Python/LangGraph behavior, provider pricing/protocol, filesystem durability, locks, clock, authentication, verifier results, sandboxing, or distributed exactly-once billing.

| Supplement | Model declarations |
| --- | --- |
| `graph.topology`, `graph.loopback`, `bounds.max_provider_calls` | `dispatch_call_bound`, `limit_two`, `invalid_opens_consent`, `second_call_positive`, `second_invalid_terminal`, `twice_invalid`, `valid_review_ready`. Deterministic invalidity is a trusted verifier classification. |
| `graph.consent`, `graph.authority` | `changed_payload_denied`, `different_attempt_needs_consent`, `no_authority_no_dispatch`, `first_call_positive`. Owner, expiry and exact consent are also guard fields. Authentic callback and fixture-scope enforcement remain external. |
| `journal.contents`, `journal.replay` | `no_durable_intent_no_dispatch`, `dispatch_records_attempt`, `duplicate_attempt_denied`, `dispatched_operation_cannot_reopen`. The state and durable-observation flag abstract the exclusive ledger; they do not prove atomic fsync, locking or operation ID storage. |
| `provider.budget`, `graph.terminal_failures` | `dispatch_reservation_bound`, `unknown_keeps_reservation`, `terminal_failures`, `unknown_terminal`. Cost bounds and reserve durability are trusted. No settlement is modeled. |
| `graph.publication` | `verify_preserves_history`, `dispatch_preserves_history`, `valid_review_ready`, `explanation_suggestion`. History is an opaque token; no actual persistence or application is modeled. |

The full general state domain admits arbitrarily constructed states; guards and examples describe the specified transitions, not reachability from arbitrary forged host state. Cancellation, timeout duration, exact diagnostic codes, ledger file integrity, build verification, and individual classed runtime errors beyond the model's enumerations remain implementation and test obligations. Normal integration remains a future Spring authority boundary.

The revised execution/publication deadline and fail-closed cleanup boundary, including cooperative callback enforcement, supervised hashing, process-group reap and dedicated-UID constraints, are not formalized by this model. OS progress, ownership and cleanup correctness remain runtime and test obligations.
