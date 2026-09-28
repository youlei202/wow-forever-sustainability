# Executed workflows

The authoritative expanded command lines, timestamps and source/config hashes
are in the included provenance receipts. These were new external output
directories; no frozen historical run was rewritten. On the original server,
every Python/test invocation first sourced `scripts/env.sh`.

The maintained entry points actually used were:

```text
python tests/test_co_exact.py --audit-out <new audit directory> --count 1200
python -m wowfs.experiments.co_runner --phase confirm \
  --config <CONFIRM16384_CONFIG.json> --run-root <campaign-v1> --workers 48
python -m wowfs.experiments.co_native_analysis --registry <frozen registry> \
  --batch <confirm16384> --thresholds <DEV_THRESHOLDS.json> \
  --output <confirmation-v1> --mode confirm --predictions <predictions-v1>
python -m wowfs.experiments.co_obligation_audit run --analysis <confirmation-v1> \
  --protocol <OBLIGATION_AUDIT_PROTOCOL.json> --output <obligation-audit-v1>
python -m wowfs.experiments.co_benchmark_ipc --registry <test-registry> \
  --output <test-existence-v2> --workers 8 --budget 60 --query-budget 900 --workflow existence
python -m wowfs.experiments.co_benchmark_ipc --registry <native-test-registry> \
  --output <native-existence-v2> --workers 8 --budget 60 --query-budget 900 --workflow existence
python -m wowfs.experiments.co_query_benchmark --registry <test-registry> \
  --output <test-queries-v2> --workers 8 --budget 60 --query-budget 900 --workflow queries
python -m wowfs.experiments.co_query_benchmark --registry <native-test-registry> \
  --output <native-queries-v2> --workers 8 --budget 60 --query-budget 900 --workflow queries
```

Angle-bracket text above is a reading aid, not a literal runnable command or a
claim that every helper invocation is listed. The benchmark `*-COMMAND*.json`
receipts contain the exact argv arrays; `provenance/native/NATIVE_REAL_COMMANDS.md`
contains actual native/projection/diagnostic paths and commands. Portable commands
that can be run on another machine are in `REPRODUCE.md`.

The original copied paper's `run_checks.sh` completed its mathematical and native
reanalysis checks, then failed its manuscript-display check because `pdftotext`
was unavailable. Its failure is retained. The initial development native batch
failed before launching the engine because `psutil` was missing; corrected
preflight ran the same declared development stage in `dev256-v2`. The whole first
timing suite was excluded after shared-filesystem stalls were identified, then
all its frozen inputs and solvers were rerun under the documented isolated method
clock. These infrastructure events are included in the negative ledger.

No paid model API, public submission, remote push, or manuscript rewrite was
performed. The secondary unused alpha and unexecuted optional heavy/multithread
tiers are explicit in `RESOURCE_USE.json`.
