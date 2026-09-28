# Replacement timing harness audit

The initial fresh-executable harness encountered uninterruptible shared
filesystem reads. Its external process deadline could therefore expire before
the method's computation clock or result export completed. Those runs must be
retained as infrastructure-contaminated evidence, not silently converted into
algorithm timeouts or pooled with replacement measurements. The frozen test
instances, mathematical encodings, solver settings and per-method budgets
remain unchanged for the replacement run.

Reviewed `co_benchmark_ipc.py` and `co_benchmark_preload.py`. A forkserver warms
the same independent tiny model, all libraries and shared object pages before
any test problems. Each problem receives a fresh isolated child, fresh
problem-specific model and empty query cache, on a pinned physical core.
Preload state carries no test-specific solution or learned clauses. Model
parsing, construction, solving, witness checking, interface serialization and
reload in memory, and query-record JSON remain within the measured method
clock. Query methods receive the same target stream and candidate universe.

Common startup, per-child startup, IPC transfer and durable archival are
recorded separately. In particular these measurements concern an in-memory
query service; they do not establish cold-start deployment or durable-storage
throughput. Parent archive delays cannot manufacture solver NO answers or
change the model. Aggregate CPU tokens, memory limits and the original
campaign deadline still apply while archiving.

Two audit fixes were requested before main testing:

- A forcibly killed or memory-limited child must retain observed elapsed work
  with its clock/proxy status. Filling its elapsed time with the nominal budget
  invents work, especially for an early memory failure. Startup failure has no
  completed method duration. PAR-2 can still use its separately declared cap.
- Receiving a computed result without the full query/interface payload is an
  infrastructure failure. Preserve the computed status as a separate field,
  abort further testing, and do not publish a successful workflow with absent
  receipts. This differs from a solver returning a valid partial interface.

The implementation also corrected a smoke-discovered race where a very fast
child exited before process inspection, and used Linux abstract Unix-domain
IPC because the external work filesystem rejects filesystem socket creation.
Failed smoke invocations and the contaminated first timing run remain separate.

An independent audit of `ipc-smoke-queries-v4` passed. It checked ten
history/method jobs, 10,098 unique target-query units, matching target identity
and order, contiguous receipt counts, and partial-interface safety. Every
query unit had at least two decided methods and all decided answers agreed.
The smaller history had 49 YES and 49 NO across all five methods. In the
larger history, the partial reference interface returned 6,398 YES and 3,602
UNKNOWN; it did not infer NO from missing kernels. Incremental SAT and the
complete SAT interface both returned 8,251 YES and 1,749 NO. Two reference
online workflows reached their whole-history development timeouts. These
development results test the harness and are not primary test evidence.

The machine-readable receipt is
`campaign-v1/benchmark/ipc-smoke-queries-v4/INDEPENDENT_QUERY_SMOKE_AUDIT.json`.
Final source snapshots and the main run's freeze determine the executed
harness revision. The report audits all common resolved answers again,
preserves UNKNOWN and not-processed prefixes, and records startup/archival
costs beside the in-memory computational measurements.
