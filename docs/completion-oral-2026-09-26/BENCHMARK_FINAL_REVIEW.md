# Final benchmark interpretation and figure audit

The authoritative computational report is
`campaign-v1/benchmark/report-final-v2`. Its compact recheck passes 1,254
decision attempts and 495,454 recorded query answers at 972 registered
prefixes. All 288 distinct decision questions have resolved consensus across
the available solvers; all 85,701 distinct target queries have a resolved
answer from at least one backend, with no conflicting decided answer.
The report independently checked 451 distinct decision witnesses and 6,610
distinct query witnesses. NO answers are solver-issued, not proof-log checked.

## Actual service results

The table reports resolved queries and total measured work spent, including
preparation. A row that leaves queries unresolved is not a cost-to-solve result.
Synthetic, new native and inherited native questions are separate strata.
The native objects are exact numerical tables of retained sample means;
their algorithm comparisons do not themselves establish population claims.

| Workflow | Synthetic: resolved / 67,445; seconds | New native: resolved / 6,160; seconds | Inherited: resolved / 12,096; seconds |
|---|---:|---:|---:|
| Reference fresh | 58,878; 1178.10 | 5,972; 1021.45 | 12,096; 117.983 |
| Reference cached | 67,445; 709.751 | 6,160; 298.628 | 12,096; 16.8551 |
| Reference full interface | 50,156; 1730.74 | 6,160; 14.5671 | 12,096; 0.213345 |
| SAT incremental + cache | 67,445; 2.13893 | 6,160; 0.098607 | 12,096; 0.110445 |
| SAT full interface | 61,053; 769.346 | 6,160; 0.096197 | 12,096; 0.107382 |
| SAT maximal-witness cache | 67,445; 2.70304 | 6,160; 0.099529 | 12,096; 0.112438 |

The reference interface does reuse useful work: on each of the 16 new and
eight inherited native histories it overtakes cached reference solving by the
registered 10-query prefix. This does not establish an advantage over strong
generic solving. Ordinary persistent SAT with completion/core caches already
resolves every registered target, and its aggregate native costs are close to
those of a complete SAT interface or a maximal-witness cache.

Across the 16 new native histories, SAT's full interface first crosses ordinary
incremental SAT at an observed prefix in 12 histories: once at 1 query, twice
at 10, twice at 100, and seven times only at the full 385-query stream. Four
have no observed crossing. Against maximal-witness caching, it crosses in
11/16. In inherited histories the corresponding counts are 5/8 and 8/8.
These are measured crossings at registered prefixes, not interpolated or
permanent thresholds. The aggregate advantage over incremental SAT is only
about 2.4 ms for all 6,160 new-native queries and about 3.1 ms for all 12,096
inherited queries. Query timing was not independently repeated; these tiny
differences do not support a robust practical speed-advantage claim.

The readable reference full interface crosses incremental SAT in only 1/16
new-native histories and 0/8 inherited histories. Its broad speed advantage
is rejected even though the representation and reuse contract are useful.
The useful capability is a backend-independent, exact completion service and
auditable reusable representation. The measurements favor choosing its
backend and degree of precomputation according to output size and demand.

## Failures and finite output cost

Workflow COMPLETE means that the scheduled stream was traversed. It does not
mean all targets were resolved or the compiled interface is complete.

- The reference interface completes 11 synthetic workflows but fully resolves
  only 10. Its concentrated-conflict partial representation contains 8,508
  valid kernels and resolves 2,711 of 10,000 targets, leaving 7,289 UNKNOWN.
- On the output-heavy synthetic case, the reference workflow reaches its
  whole-history deadline before returning a serialized interface or querying
  any target. Kernel count and preparation timing are unavailable, not zero.
- SAT's interface completes all 12 synthetic workflows, but fully resolves
  only 11. On that output-heavy case its 12,659 returned valid kernels resolve
  3,608 targets and leave 6,392 UNKNOWN.
- Fresh reference solving leaves 8,565 synthetic targets unprocessed and
  records two query timeouts. On the new druid validation-00 history it leaves
  187 targets unprocessed and records one query timeout. Cached reference and
  both SAT online strategies resolve all registered targets.

The registered output-heavy model has 31 disjoint optional conflict pairs.
Each endpoint has an anchor-supported score of 11, each forbidden diagonal
scores 14, and the cap is 12. Choosing one endpoint from each pair yields
exactly `2^31 = 2,147,483,648` maximal gaining completions. This untimed check
is recorded in `checks/OUTPUT_HEAVY_INTERFACE_SIZE_AUDIT.json`. It is a standard
matching construction, not a novelty claim or native evidence. It explains
why explicitly listing every maximal completion can be unaffordable while
the 10,000 registered existential queries remain easy for an online solver.

The two reference costs should remain distinct: a small conflict cover does
not eliminate its frontier-enumeration cost, and a huge extensional output
cannot be made small merely by accelerating the solver. Neither observation
establishes intrinsic hardness of the existential query instances; generic
solvers resolve them rapidly.

## Preparation, marginal work and storage

Returned native interfaces contain zero to four kernels per history.
The reference's total preparation for the 16 new native histories is 14.5200 s;
SAT's is 0.05045 s, with measured SAT compile calls totaling 0.04718 s.
Preparation starts after model parsing and includes compile/build, verification
and in-memory serialization/reload. Initial parsing remains in total/prefix
clocks but was not separately emitted for query workflows.

The 720-second allowance bounds search/enumeration. Output postprocessing uses
the remaining common 900-second whole-history budget. For example, the
reference concentrated-conflict compile call takes 767.21 s and preparation
takes 770.07 s. It would be incorrect to describe 720 s as a hard bound on that
whole compile call. Missing return values do not imply no work was performed.

`QUERY_MARGINAL_COSTS.csv` subtracts adjacent fully resolved prefix timestamps.
For new-native intervals the descriptive median cost per additional query is
about 6.27 microseconds for SAT interfaces, 11.65 for ordinary incremental SAT,
and 10.65 for maximal-witness caching. These are correlated intervals from one
frozen execution, include query-record serialization, and exclude preparation
already paid before the first endpoint. They do not establish stable timing
distributions or justify extrapolating an unobserved break-even point.

Method clocks describe an in-memory service with common libraries loaded.
Startup and durable NAS archival are separate observed costs. One native
incremental-SAT startup subtotal exceeds 900 s because of NAS stalls, although
its measured service work is about 0.11 s. The report itself and its tests also
experienced storage waits. These are infrastructure observations, not solver
timeouts or cold-deployment speed claims. No primary receipt reports an
infrastructure failure, ERROR, or NOT_RUN after recovery.

## Figure audit

All seven standalone PDFs compiled and were rendered and visually inspected.
The primary decision panels separate fixed and unknown frontiers; the pooled
panel is supplementary. The common-prefix panels retain all 12 synthetic,
16 new-native and eight inherited histories with all six methods. Their x-axis
uses actual requested unique targets after each finite universe is exhausted;
their y-axis shows cumulative work spent. Open red markers identify unresolved
work rather than presenting it as completed service. The supplementary
throughput panel shows how many correct answers that work actually obtains.
No figure clips labels or equates COMPLETE with all queries resolved. Preview
images are outside the immutable report directory, and the report's hashes
remain unchanged.
