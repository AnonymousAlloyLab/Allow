# Parent pair verifier and release controller

`pair_runner.py` is a separately frozen gate verifier. It changes no prepared installation and never activates a production profile. The original `http_driver.py`, controller, copied source/target, and their historical reports remain unchanged.

The original HTTP driver returns exit 1 and `BLOCKED` when a complete zero-error F0 run misses 300ms. The approved contract requires the strict target for F1; F0 is the comparison baseline. The new wrapper retains that original result as `http-original-report.json` plus `http-original-exit.json`. Only a complete 100+1000, zero-error, correctly bound F0 result may become an outer `PASS` with `classification: MEASURED_BASELINE` and `latency_gate: FAIL`. A request failure, missing sample, changed field/hash, wrong response, invalid identity, memory excess, or unknown cleanup is never waived.

Before the wrapper exits, it retains `driver-final-cgroup.json` after the original driver has exited. This closes the original controller's missing-final-snapshot path on an early driver failure. A valid F0 wrapper then returns success so the original controller also completes its final containment, input and memory checks. A threshold-failing F1 still returns failure and remains `BLOCKED`; its sidecar permits the parent to assess the last counters without inferring them after the cgroup disappears.

After controller cleanup, the parent verifier independently:

- Rechecks the exact source, compiled BuildIdentity, tool/JDK/native inventories, owner/controller manifest agreement and absence of mutable aliases with `installation.verify(fresh=False)`.
- Reconstructs all 1100 distinct edits from the accepted synthetic 500-node module and checks every request byte, event order, phase, length and hash against its premeasurement manifest.
- Checks every retained raw response, complete protocol/data field set, typed identities, request/source hashes, byte count, and zero-error sample. Duplicate JSON keys, boolean/integer confusion, NaN and infinities are rejected.
- Recomputes nearest-rank p50/p95/p99 and maximum from all 1000 measured rows, retaining all 100 warmups and all failures.
- Checks each snapshot's unit/incarnation, exact effective limits, observed task affinity, no OOM/task exhaustion, and cumulative memory peak at most 5GiB.
- Requires explicit `populated=0`, successful owned kill/stop, and absence of every observed process incarnation after cleanup.

The prerequisite receipt contains exactly `finite_semantics`, `comparator_negative_cases`, `p1_regressions`, and `java_safety`. Each entry binds an absolute report path, SHA-256, `success_pointer`, `success_value`, and optional typed JSON-pointer assertions. Current `pair-prerequisites-r1.json` binds the completed 190-case semantic comparison, 31 comparator/selftests, P1 r11 regressions and 12 registered Java safety claims.

Freeze does not release scheduling:

```text
/usr/bin/python3 pair_runner.py freeze --run RUN --pair 1 --variant F0 --history HISTORY --prerequisites RECEIPT --preflight PREFLIGHT_RUN
```

After the root explicitly releases the schedule and confirms unrelated CPU work is finished:

```text
/usr/bin/python3 pair_runner.py run --registration RUN/pair-registration.json --release-schedule
```

The immutable order is pair 1 F0 then F1; pair 2 F1 then F0; pair 3 F0 then F1. Registrations may be frozen ahead of time; execution checks the completed history and holds a per-experiment advisory lock through cleanup. A pair passes only when both trials are valid, F1 p95 is below 300ms, and F1 p95 is strictly lower than its paired F0. Equal p95 cannot pass. Any failed trial/pair records `KEEP_F0`, stops further execution, and labels untouched later trials `NOT_EXECUTED`. After three passing pairs, the output is only `THREE_HTTP_PAIRS_PASSED`: other selection gates, target-host acceptance, and profile activation remain separate.

The wrapper, parent verifier, prerequisite reports, original harness files and prepared manifest are hashed into each `pair-registration.json` and derived controller runtime registration before any workload. Original driver and controller reports are not overwritten. New sidecars and `pair-verification.json` provide the additional bounded evidence. Linux/systemd/hardware, SHA-256, the frozen runtimes and the declared existing harness remain trusted; these finite observations do not prove universal confinement or semantic equivalence.
