# Full portable confirmation audit

The complete compact-data recheck passed on 2026-09-26. The authoritative
receipt is `checks/PORTABLE_RECHECK_FULL_CONFIRMATION_V4.json`, with execution
log `audit/portable-confirmation-v4.log`. Its 29.05-second runtime is an audit
measurement, not a solver benchmark observation.

The audit ran from an unrelated working directory on CPU 120 using a sealed
270-file staging bundle. A Python import guard rejected SAT, CP, MILP and SMT
packages, and a filesystem audit hook rejected reads from the original source
repository. Every loaded `wowfs` module resolved inside the copied bundle.
Output and Python caches were outside the sealed bundle. The input consisted
of compact paired means/covariances, frozen tables, event definitions and
certificates; no native engine, raw trajectories or server catalogue database
was needed. The final archive receives its own fresh integrity check after
packaging; the intermediate staging hash is not its ZIP hash.

| Recomputed object | Coverage |
|---|---:|
| Fresh native exact mean and confidence questions | 16 catalogues, 24 menu contracts, 192 queries |
| Primary full/value-only confidence publications | 163,840 |
| Registered tolerance consequences | 16 catalogues, 512 queries |
| Four-task to two-task contract projections | 8 menu contracts, 64 queries |
| Source-obligation relaxations | 24 menu contracts, 192 queries × 8 scopes |
| Inherited parameter consequences | 2,000 query decisions |
| Independent inherited full-subset corner challenges | 49,152 publications |
| Frozen positive prediction witnesses | 67: 43 base, 24 expanded |

The exact mean checker uses a separate rational mask implementation and
enumerates every publication; it imports no solver. It checks the exact
sub-float-ulp boundaries rather than converting rational values to solver
integers. Confidence bounds are rebuilt from the saved full covariance,
reference mapping and finite coefficient family. The checker compares event
size, critical value, coefficients, all certificate masks, exhaustive rejection
counts, trace hashes and saved positive witnesses. Source-obligation replay has
a separate enumeration implementation. These checks reproduce finite-event
consequences; they do not establish the approximate paired-t event's coverage
without its statistical assumptions.

The 192 base/expanded confidence rows reproduce 65 YES, 112 NO and 15 UNKNOWN.
These nested rows are not 192 independent ecological observations; the primary
base denominator remains 16 catalogues × 8 targets. Across the 43 frozen base
positive witnesses, all remain valid on fresh exact means, while 38 have
supported population margins. Across 24 expanded witnesses, 22 remain valid
on fresh exact means and 18 have supported margins. The two invalid expanded
witnesses are Warrior validation 01, targets q00 and q02. Their existence
questions still have alternative completions. The recheck verifies both the
original prediction identities and the archived fresh-witness report, so these
failures cannot disappear through replacement of a returned witness.

Thirteen checker/oracle tests passed, including 160 rational random models,
1,280 direct-definition query comparisons, an exact boundary smaller than
floating-point resolution, manifest/path tampering, a resealed false decision,
extra exact-query rejection, required-section omission, frozen-prediction
mismatch and independent obligation replay. A final manifest declaring
`required_sections` must include native, secondary-tolerance, projection,
obligations and sensitivity directories; missing declared sections fail rather
than silently returning NOT_INCLUDED. The final archive also requires the
benchmark directory. Permitting that additional declared section was the only
checker change after the v4 numerical replay; the final archive receives a new
recheck with its exact sealed code.

No frozen primary scientific source changed: all 18 protocol hashes were
rechecked. Only the review checker gained denominator, section and frozen
witness checks. Earlier staging remains preserved: v1 lacked the complete
obligation section; v2 failed during copying before analysis because the build
script requested a nonexistent namespace-package `__init__.py`; v3 passed the
full numerical replay before the extra witness/provenance checks were added.

The portable check does not recreate native battle trajectories, inspect
battle-level tails, reproduce wall-clock timing measurements or constitute a
machine-checked theorem proof. Optional solver reexecution uses a separate
external source/work layout and remeasures performance on the reviewer's
machine. Main fresh inference spends total alpha .04 under the stated paired-t
approximation; secondary propagation spends no new alpha. Inherited event
coverage and fresh event coverage remain separately accounted.
