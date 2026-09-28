# Reuse a native certificate for a different target

`co_certificate_service.py` exposes the existing statistical certificate as a
small reusable query object. It compiles each menu's sufficient and necessary
interval models into two complete maximal antichains. For a new target D, a
supported antichain member containing D supplies a YES witness. If no possible
antichain member contains D, completeness supplies NO. The remaining cases are
UNKNOWN. INVALID_INITIAL and UNKNOWN_INITIAL remain separate initial-state
outcomes. An incomplete possible interface cannot issue NO.

The fixed simultaneous event already covers every relevant configuration pair.
The service therefore supports arbitrary targets inside the same menu, including
targets selected after previous answers, without further native calls or alpha.
This is a deterministic consequence of that event. The original approximate
fixed-N paired-t coverage assumptions remain unchanged. Possible publications
satisfy necessary interval conditions; they need not be population-feasible.

History, allowed gear/policies, tasks/weights, thresholds, physical support rows
and event identity are fixed by a contract hash. A change in those objects
requires a different interface. Out-of-menu item IDs are rejected as invalid
queries, not assigned NO. The empty target is allowed but still requires the
original positive gain. The service makes no claim about all release orders.

Compilation verifies the bundle manifest and the source certificate's identity,
then enumerates every permitted publication once. Its counts and trace hashes
must match the original certificate before reduction. Both antichains are
formed from the cached full feasible-mask lists. Reduction considers arbitrary
strict supersets, so mutually supporting helpers are not lost by a single-add
maximality shortcut. The saved representation has its own integrity hash and
the source-certificate and contract hashes. Hashes establish content identity,
not external authenticity independent of the review archive's published hash.

With the portable environment from `REPRODUCE.md`, compile into external storage:

```bash
python -m wowfs.experiments.co_certificate_service compile \
  --bundle "$BUNDLE" --world co_mage_timed_resources__validation_00 \
  --variant base --output "$RECHECK_WORK/mage-base-interface.json"
python -m wowfs.experiments.co_certificate_service query \
  --interface "$RECHECK_WORK/mage-base-interface.json" \
  --target a01 a02 --output "$RECHECK_WORK/new-target-answer.json"
```

The sample target is within the measured menu. The actual command returned NO;
this is a symbolic reuse demonstration, not an additional registered native
observation. Omit `--target` for an any-gain query. Supplying
`--contract-sha256` on a query additionally checks the contract expected by the
caller. Existing outputs and writes inside the source bundle are rejected.

The correctness gate reproduced all 192 registered answers across 24 base and
expanded menu contracts. An independent oracle checked every publication using
the original witness verifier and formed its full target-subset closure. All
73,728 target masks across the base and expanded Warrior validation-01 and Mage
validation-00 models agreed, including YES, NO and UNKNOWN. Six directed tests
cover cyclic helpers, target monotonicity, incomplete-interface direction,
invalid/uncertain initial states, unknown gear and contract/content tampering.
The 24 JSON interfaces total 562,937 bytes in this demonstration; this is a
representation-size observation, not a comparative timing result.

Receipts and interfaces are under `audit/certificate-service-v1/` in the work
archive; `checks/CERTIFICATE_SERVICE_AUDIT.json` summarizes the gate. The review
bundle places the completed interfaces under `data/certificate-interfaces/`.
The service was also rerun from a separately sealed copy, from an unrelated
working directory, with reads of the original source and imports of all solver
libraries blocked. The CLI example, 192 registered answers and 73,728 target
masks passed again. `checks/CERTIFICATE_SERVICE_PORTABILITY_NO_BYTECODE.json`
records the copied-module paths and manifest identity. The earlier normal
bytecode attempt also passed after a shared-filesystem stall; both attempts and
their separate outputs are preserved. These portability checks add no native
observations and make no timing claim.
This review utility was added after confirmation. It is neither a seventh
performance baseline nor new prospectively registered empirical evidence, and
it does not change the frozen primary analysis.
