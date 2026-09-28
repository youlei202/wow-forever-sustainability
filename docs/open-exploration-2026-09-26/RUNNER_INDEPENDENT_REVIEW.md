# Independent runner review — initial version, 2026-09-26

Reviewed `src/wowfs/experiments/oe_runner.py`, SHA-256
`8dd6201e9ef425835ff53406ecda111c67199ba7ccaa6d58658d3dbe21123009`,
and its direct `fc_native`, `r2_native`, `paths` dependencies. This is a review of that version, not a blanket approval of later changes. No production runner or native cache was modified by this review.

## Findings requiring attention

1. **Cache hits do not verify stored output integrity.** The cache branch checks input equality, the claimed cache key and existence of `output.json.gz`, but does not check `output_sha256`, parse the output, or validate the cached summary against raw output. An isolated synthetic regression produced a successful cache hit with an intentionally wrong output hash, invalid native output text, and invented cached DPS 999. This is a software test with zero native calls/battles, recorded in `checks/RUNNER_CACHE_INTEGRITY_SYNTHETIC.json`. Validate the decompressed raw hash and receipt fields; validate parsed raw output/sample counts and summary consistency or use a separately integrity-checked summary receipt.
2. **Frozen executable and copied source integrity are not checked on resume.** A resume compares the current live binary/source protocol, but then executes `batch/native.frozen` without checking that copy. Verify the copied binary after creation and on every resume, and verify the frozen source tree against its manifest. Otherwise a damaged frozen executable could run while receipts claim the original binary hash. Freeze publication should be atomic or use a complete-freeze marker so an interrupted copy cannot leave a seemingly resumable batch.
3. **Progress call counts exclude failed native invocations.** `new_calls_this_invocation` only increments after a successful future, although failed attempts may already have invoked the engine and consumed battles. Receipts for failures omit requested/completed iterations. Distinguish native attempts, successful calls, completed observed battles, requested iterations and unknown/partial battle counts. An execution failure must not be silently represented as zero computational work.

## Other operational observations

- The shared flock token directory limits native processes across this campaign's batches rather than giving each branch its own allowance. Current cgroup CPU limit is 64 CPUs; current memory limit is 192,000,000,000 bytes and the runner's 128 GiB soft threshold is below 80% of that allocation. The per-process environment sets `GOMAXPROCS=1`; `scripts/env.sh` constrains BLAS/OpenMP threads.
- The original campaign deadline persists across resume. The stored `CAMPAIGN.json` still has nominal resource limits while the effective allocation can be tightened in memory at execution time; record effective CPU/memory constraints in the batch receipt for audit clarity.
- A smaller `--max-wall-hours` on resume does not tighten the original deadline. That is acceptable only if documented as an immutable original budget parameter; it should not appear to implement a newly requested shorter budget.
- Cache keys include binary, complete physical input (including policies/tasks/seeds), observation definition and source hashes. That is strict, but adding unrelated `oe_*.py` analysis code changes cache keys. Count distinct physical design/seed observations separately from execution/cache keys; otherwise the same physical observation rerun after a source-only change can be presented as an independent sample.
- The first attempt directory is created before acquiring a worker token. A deadline while waiting for resources can consume an attempt number without calling native, and its failure path differs from a subprocess failure. Retry/call accounting should distinguish these statuses.
- Thread futures waiting on an existing cell lock are not themselves native processes; the native subprocess timeout is bounded by the campaign deadline. Imported native summarization checks iteration count, all-values length, finiteness and mean consistency for fresh runs.

These findings do not show that any completed smoke result is wrong. They identify paths that could invalidate a resumed or corrupted-cache campaign and should be fixed before large-scale execution/confirmation. The first finding is directly reproduced; the others follow from the reviewed control flow.

## Follow-up after runner changes

Rechecked runner SHA-256 `012923291fabdafa9228bfd737c56a2cb416d4728a1c9ddfd131cd84b13b2295`.
The exact synthetic corruption used above now raises `ValueError: cached native output hash mismatch`; the original failed regression evidence remains unchanged. The new cache path checks raw SHA and every recomputed summary field. Frozen executable and source hashes are checked both after copying and on resume. Failed-invocation receipts now retain requested/completed iterations and progress distinguishes unknown completed battles.

Added only `tests/test_oe_runner.py` as maintained regression coverage. **10 tests passed**: valid cached output, changed raw output, changed cached mean/iteration count/sample vector, changed input, original campaign deadline and extension refusal, inclusion of environment-audit time, and independently damaged frozen binary/source (each after a successful intact resume). No native process was launched by these tests. Test source SHA-256: `e7db3aea8362bc65572c5c8b9350a87ce5a38dd615abbeac6af2fb2a08e56107`.

Evidence: `checks/RUNNER_CACHE_INTEGRITY_RECHECK.json` and `checks/RUNNER_REGRESSION_TESTS.log`.

```bash
source scripts/env.sh
pytest -q tests/test_oe_runner.py --basetemp /work/Users/leiyo/wow-forever-sustainability-work/tmp/oe-runner-review-tests-v1
```

The three primary issues are addressed in this version. Freeze completion is still not transactional, but a missing/corrupt copy fails closed rather than executing an unverified artifact. The lower-priority operational observations above remain relevant. A `started` receipt is created just before the subprocess call; interpret this as an invocation attempt, not proof that an operating-system process ran if process creation itself fails. Historical smoke/benchmark batches use their original frozen runner and are not changed by the fix.
