# Independent review of benchmark reporting

The native-catalogue analyst reviewed `co_benchmark_report.py` independently of
its implementation. This review concerns matching, status semantics, denominators
and interpretation. It is not a new benchmark run or an independent proof of
every solver-issued NO. The six reporting unit tests also passed independently;
their log is `audit/benchmark-report-independent-tests.log`.

Strict prefix comparisons require both workflows to resolve every target in the
same registered prefix, and both prefix costs must remain within the common
history budget. Costs include preparation. Where available, the saved prefix
receipt after JSON recording overrides the earlier per-query clock snapshot.
An unfinished prefix retains actual work spent and its unprocessed target count;
it is never given an invented completion time. UNKNOWN from a partial interface
does not become a correct answer merely because lookup was fast.

Workflow COMPLETE means that the scheduled stream was processed. Separate
fields identify complete streams with all targets resolved and those containing
unresolved queries. The first observed cost crossing is reported only at
registered comparable prefixes. A missing crossing is neither proof of no
future benefit nor evidence that an incompletely evaluated method is slower.
The distribution reports how many histories have any strict comparable prefix.

Single-decision PAR-2 counts unresolved executed valid-history attempts as twice
the time cap. NOT_RUN and INVALID_INITIAL are excluded with explicit counts.
Answers arriving after the common cap remain in the receipts but do not count
as solved within that cap. The performance profile keeps unresolved paired
attempts in its denominator. Common-solved ratios are secondary summaries and
are explicitly conditional on both methods solving.

Synthetic, inherited-native-mean and new-native-mean tables remain separate.
Repeated seeds and fixed/unknown-frontier questions do not create new histories.
Synthetic resampling groups the paired questions by generated history. Native
ratios use registered catalogue clusters when available, otherwise conservative
mechanism families, and receive no bootstrap population interval. Native timing
models are exact numerical objects exported from existing observations, not
additional physical evidence.

This review requested three provenance safeguards. The implementation now
requires every frozen source snapshot and checks its hash; verifies each job's
canonical hash and indexed identity; and checks equality of the exact question
and budget across methods. Query comparison additionally checks the complete
target stream and all relevant budgets. I inspected these added assertions.
Positive witnesses and compiled kernels receive exact contract checks; partial
interfaces are prohibited from issuing NO. Unresolved implementation or
infrastructure errors invalidate a comparative timing interpretation rather
than disappearing from the report.

No blocking conceptual issue was found. Cost
scope is an in-memory service after common library preparation: durable archive
I/O, startup and final solver destruction are outside the method clock, with
separate receipts where available. This scope must remain attached to any
reported reuse benefit. In particular, fast generic solutions to zero-conflict
controls refute a cost prediction for the enumerating reference implementation;
they do not demonstrate intrinsic hardness of those problems.

After all four frozen suites completed, an independent reduction of the final
compact CSVs checked 216 workflow records and 495,454 processed query records.
For the 12 synthetic histories, the reference interface processed 11 complete
streams but resolved all targets in only 10 histories; the SAT interface
processed all 12 streams but resolved all targets in 11. Partial streams retain
7,289 and 6,392 UNKNOWN results, respectively. One reference-interface workflow
timed out before returning its representation. Both persistent SAT approaches
and reference caching resolved all 67,445 synthetic targets.

All six methods resolved all 12,096 inherited-native targets. Five methods
resolved all 6,160 new-native targets; repeated fresh reference solving resolved
5,972, recorded one timeout and left 187 unprocessed. Completed native
aggregate prefix costs were independently reconstructed from each history's
recorded final prefix. On the new tables, reference compilation cost 14.567 s
including queries, against 298.627 s for reference caching. The three SAT
services cost 0.096--0.100 s in aggregate. Their few-millisecond differences are
descriptive observations, not evidence of a robust practical speed advantage.
No unresolved prefix was converted into an invented completion cost.

`checks/FINAL_QUERY_CLAIMS_INDEPENDENT_AUDIT.json` records the compact inputs'
hashes, counts and independent checks. This supplements the reporter's complete
data validation; it is neither a second timing experiment nor a proof of all
solver-issued NO answers. Final archive integrity has its separate gate.
