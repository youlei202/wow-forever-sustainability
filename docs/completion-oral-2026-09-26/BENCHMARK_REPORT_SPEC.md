# Recomputable benchmark reporting

`co_benchmark_report.py` reads the frozen job index and receipts, checks
resolved answers across methods, independently verifies distinct YES
witnesses, and emits compact evidence without copying every job's model.
Multiple existence/query input directories allow a separate native numerical
panel to be added to a new report. It refuses to overwrite an existing report.

The primary decision table uses seed 0. Additional CP-SAT seeds and
deterministic reference/SAT repeats have a separate stability table. Reported
groups retain fixed-frontier versus unknown-frontier tasks, synthetic versus
native tables, and structural family. Exact untimed diagnostics identify
mandatory H union D that already violates the global cap; this separates
trivial presolve exclusions from frontier/source bottlenecks. The supplied
algorithm remains a readable Python reference with unchanged frozen code.

The replacement IPC harness measures an in-memory service after common
data-independent library startup. Each problem gets a fresh isolated process
and fresh problem-specific model/cache. Exact parsing, construction, solving,
verification, interface JSON serialization/reload and query-record JSON remain
inside the clock. Common server startup, per-child startup and durable NAS
archival are recorded separately. This establishes no cold-deployment or
durable-storage throughput claim. Registered prefix costs use the harness's
post-recording snapshots, including the last query's JSON serialization.

PAR-2 uses measured method time for an exact decision delivered by the
declared wall cap. Other executed outcomes on valid histories receive twice
that cap. NOT_RUN and INVALID_INITIAL are excluded and counted explicitly.
Performance profiles use paired executed valid-history units; unsolved
methods remain at infinite ratio, including units nobody solves. Common-solved
geometric runtime ratios are secondary and conditional. Descriptive intervals
resample generated histories while retaining paired fixed/unknown tasks
inside each cluster. Native ratios use explicit registered catalogue clusters
when present, otherwise conservative mechanism-family clusters. Native ratios
receive no bootstrap interval because an independently sampled catalogue
population is not established. New and inherited native data kinds remain
separate. No query, solver seed, or runtime resample is treated as an independent
native catalogue.

For repeated targets, the audit requires the same target identity and order
for every method, checks uniqueness, monotone cost, and complete receipt
denominators. An incomplete interface cannot answer NO. The query CSV records
UNKNOWN, memory failure, invalid histories and cache type separately from
resolved answers. A prefix not reached reports actual work spent and a
NOT_PROCESSED denominator, never an invented completion time. Cost crossings
depend on resolved answers, not workflow status: COMPLETE records that the
stream was traversed, and a partial interface may complete with UNKNOWN.
Metrics separately count complete workflows with and without unresolved targets.
If an outer deadline preempts postprocessing or serialization, a missing
interface artifact means its available kernel count is unknown, not zero.
The history CSV records that state explicitly. Preparation time, when returned,
starts after model parsing and includes building/compilation, exact verification
and in-memory serialization/reload; it is not compilation-only time. Model
parsing remains in total/prefix clocks but is not separately emitted in the
query receipts. Interface compile-call time and the remaining preparation
overhead are retained separately. The nominal 720-second search/enumeration
allowance permits output postprocessing inside the common 900-second whole
workflow cap; actual compile-call time can consequently exceed 720 seconds.
`QUERY_MARGINAL_COSTS.csv` reports measured cost differences between adjacent
fully resolved prefixes within budget, including query-record serialization.
It makes no extrapolation to unseen query volumes.
Cost crossings
are reported only at observed registered prefixes where both methods resolve
all requested targets. There is no extrapolation to a hypothetical break-even.
Both workflows must finish that prefix inside the declared whole-history
budget. `QUERY_MATCHED_PREFIX_COMPARISONS.csv` preserves both measured costs,
resolved counts and eligibility for each pair and prefix;
`QUERY_BREAK_EVEN_DISTRIBUTIONS.csv` retains crossing-prefix frequencies and
the full history denominator, including histories with no comparable prefix.
SAT maximal-cache versus ordinary persistent SAT and cached reference are
included alongside complete-interface versus online comparisons.

The maintained standalone LaTeX panels use the existing blue/orange/green/
purple palette. Separate given-frontier and unknown-frontier decision panels
are primary, with a pooled decision panel retained as a supplement. Three
common-prefix cost panels separate synthetic, new native and inherited native
tables. Their x-axis is the actual total unique targets requested over the
same histories, and their y-axis is measured work spent including preparation.
Open red markers mean unresolved targets remain; such a point is not a
cost-to-solve observation. A supplementary throughput plot displays total
elapsed work versus correctly resolved queries. This preserves the answer
deficit of an incomplete interface rather than treating fast UNKNOWN lookups
as successful query service. `QUERY_HISTORY_COMMON_PREFIX_COSTS.csv` retains
each history and registered common prefix; `QUERY_AGGREGATE_PREFIX_COSTS.csv`
stores panel sums, independently recomputed by `--check`. Compiled PDFs, data and logs
belong in the external report directory. TeX build failure is retained and
cannot erase otherwise valid computational evidence.

The compact outputs are:

- `BENCHMARK_RESULTS.csv`: every registered attempt, status, time, memory,
  witness size, encountered conflict-cover counters and exact diagnostics.
- `QUERY_RESULTS.csv.gz`: processed unique targets, outcomes, cumulative
  costs, cache types and correctness checks.
- `QUERY_HISTORY_RESULTS.csv` and `QUERY_PREFIX_RESULTS.csv`: full history
  denominators, preparation costs, partial results and observed prefixes.
- `COMPILED_INTERFACES.jsonl`: lossless hexadecimal bitsets with declared
  item order, completeness/maximality metadata and source interface hashes.
- `PERFORMANCE_PROFILE.csv`, `METRICS.json`, `CORRECTNESS_REPORT.json`,
  `REPORT_INPUTS.json`, `REPORT_HASHES.json`, and concise Markdown findings.

`--check <report directory>` recomputes metrics and prefixes from compact CSVs
without the original job directories, while verifying the report hashes.
It checks the computational summaries; the separately bundled exact models,
solver code and correctness suite are needed to re-solve the decision objects.
Each report stores the exact reporting source in `source/co_benchmark_report.py`;
run that frozen copy with `--check` when the maintained reporting module has
subsequently changed. Counts and statuses are checked exactly; floating runtime
summaries allow only a declared small numerical tolerance for platform math.

Infrastructure-contaminated runs are retained outside primary timing inputs.
Use `--excluded-suite <directory>` to record the exclusion of an entire run,
not selected slow methods. An input containing
`INFRASTRUCTURE_CONTAMINATED.json` is rejected as a primary suite. Development
and smoke directories are explicitly labelled DEVELOPMENT_ONLY.

The first report smoke was interrupted during TeX package reads while the
shared filesystem stalled. Its partial outputs and INTERRUPTED.json are
retained under `audit/benchmark-report-development-smoke-v1`; they are neither
a completed report nor primary timing evidence. Seven lightweight metric
tests passed, covering censoring/denominators, partial prefix semantics and
compact CSV round-trip recomputation, plus conservative clustering of related
native histories without a misleading catalogue interval, strict matched
prefix budget checks, COMPLETE workflows containing unresolved targets, and
cost-panel history matching/exhaustion with separate native denominators.
Final reporting must run on the complete
replacement timing suite under a new immutable report directory.

`co_report_queue.py` waits for `PRIMARY_ALL_COMPLETE.json`, verifies all four
registered aggregate counts, then creates `benchmark/report-final-v2` once.
The queue emits `REPORT_QUEUE_STATUS.json`; an incomplete or failed suite
prevents a final-report claim. The final report stores its exact source and
can be checked without a running solver or the raw job directories.
