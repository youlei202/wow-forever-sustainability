# Final figure guide and confirmed mechanism boundaries

The final four English vector panels are in
`$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/figures/final-v3/`.
Use that directory for a review package; preceding directories under `figures/`
are preserved previews. Each panel has PDF, SVG, PNG and provenance JSON.
Standalone LaTeX include-graphics sources are in this documentation directory's
`figures/` subdirectory. The vector PDFs are generated directly by matplotlib.
All four wrappers were also compiled successfully with the existing TeX Live
2026 `pdflatex`, with no installation and no shell escape. The separately named
`*_standalone.pdf` outputs and logs are under `final-v3/compiled-wrappers/`;
the original vector PDFs were not overwritten. Portable instructions for
redefining `FigureRoot` to `.` are in `figures/README.md`.

The source is `src/wowfs/reporting/oe_figures.py`, SHA256
`8c77f2a4194a4cbe8b3cb0447ef48c2b526345ff85458cae2266113450d44b3e`.
The figure reader starts from the completed, freeze-verified
`analysis/confirm-v2-results/` products. It does not simulate, refit thresholds,
reselect tasks, or construct new confidence intervals. The displayed percentage
limits are the stored paired-contrast limits divided by the same observed
positive old-reference mean; this display rescaling is not a ratio confidence
interval. Inference remains the campaign's approximate simultaneous t method,
not distribution-free inference.

## A: complete coverage, without converting unconfirmed mechanisms to failures

`A_native_coverage` displays all 18 registered mechanism families: 12 research
variant families and six actual-catalog families. The 108 development worlds
remain visible whether or not they reached independent confirmation. The held-out
column counts additional frozen domains. A value of zero means no completed
worlds at that stage; it does not mean zero performance or an absent mechanism.
An analyzed confirmation world also does not necessarily support its claim.

The companion coverage CSV retains all eight strict faction-tag caveats in
the broad research worlds. Coverage refers to the engine's executed physical
domain; faction acquisition validity must not be inferred from execution.

## B: the first release creates a source-specific future obligation

`B_first_update_capacity` shows simultaneous lower/upper bounds on **additional
release rounds after** each frozen first update. Bounds coincide at the values
below, for both B=1 and B=2, locally and in the predeclared duration holdout.
Every first prefix is supported feasible, and the two resulting frontiers pass
the two-direction 0.25% equivalence requirement on both tasks.

| Actual-catalog domain | First release | Retain every published source | Same domain, retention disabled |
|---|---|---:|---:|
| Magister, 14 glove × 4 leg choices | Arcanist Gloves (a05) | 1 | 3 |
| Magister, same domain | Sorcerer's Gloves (a13) | 2 | 3 |
| Trinkets, 12 trinket × 4 off-hand choices | Second Wind (a07) | 0 | 1 |
| Trinkets, same domain | Spellbound Tome (x3) | 1 | 1 |

Supported B=1 witnesses, shared by local and held-out domains, are:

- After Arcanist Gloves: Magister's Leggings (x1).
- After Sorcerer's Gloves: Magister's Leggings (x1), then Magister's Gloves (a01).
- After Second Wind: no further release is possible within the declared domain.
- After Spellbound Tome: Draconic Infused Emblem (a03).

These witnesses begin from the actual original a00/x0 history plus the first
release. Every published component remains a source obligation. The optimistic
upper-graph paths are explicitly marked as **not** true feasible witnesses in
`B_SOURCE_HISTORY_PATHS.json`. `B_SOURCE_IDENTITIES.csv` maps aliases to actual
native item IDs and names; `B_MATCHED_FIRST_EQUIVALENCE.json` retains every
equivalence direction and task. The value-only comparison disables only source
retention, preserving the same physical configurations, cap, gain and history.

The consequential design issue is therefore not merely that DPS changes
nonlinearly. Two presently matched updates leave different future release
capacity because they preserve different sources. The equal value-only capacity
is an explicit challenge to a current-value-only explanation. This finite native
result is a promising paper core, subject to the independent prior-work review;
these examples alone do not establish a general originality claim.

## C: a transferred interaction need not transfer its cap violation

`C_joint_cap_comparison` includes every task for the main pairs, locally and
held out. It compares actual primary-only and partner-only replacements, their
additive forecast, and the real joint configuration. Positive margin means
below the frozen cap; negative margin means above it.

The Mage result has a **resolved transfer failure**, not merely an inconclusive
interval. At h=4.3%, its resistance75 local joint margin is −0.9220% of the old
mean, with simultaneous limits [−1.0490%, −0.7950%]. The additive forecast margin
is +0.8161%, limits [+0.6696%, +0.9626%], so the local additive screening failure
is clear. In the held-out setting the actual joint margin becomes **+0.5905%**,
limits **[+0.4815%, +0.6996%]**. The resistance0 margin is positive as well.
The joint configuration is consequently supported cap-safe on every task.

The held-out multipliers were fixed before observation: penetration ×1.0989691
and spell power ×0.9539467 across the entire research library. Both baseline
and primary-only configurations remain below 75 penetration, while both
x3-containing configurations remain saturated. Thus the basic saturation
pattern persists. The mixed interaction remains strongly positive, increasing
from +1.7381% locally to +1.8464% held out. Positive interaction did **not** imply
that the predetermined 4.3% cap would still be violated. This distinguishes a
mechanism result from a robust update-admission conclusion.

The Druid result transfers within the one declared held-out setting. At h=5.5%,
the long-task additive forecast margins are +0.6433%, limits
[+0.5593%, +0.7273%], locally and +0.4956%, limits [+0.4112%, +0.5801%], held out.
The actual joint margins are −0.4976%, limits [−0.5675%, −0.4276%], and
−0.5639%, limits [−0.6340%, −0.4938%]. Short-task outcomes remain in the figure.
Both worlds are engine-supported stat variants, not unchanged catalog items.
One held-out setting is not population-wide validation.

## D: signed controls limit the mechanism explanation

`D_mechanism_controls` includes all 20 prespecified pair/task/context mixed
contrasts. The main/control comparisons share their declared joint-family
alpha; repeated alpha labels in the underlying records are not additional
allocations. No interval crossing zero is interpreted as evidence of absence.

For Mage, a04+x3 creates redundant penetration rather than the main pair's
complementarity. Its resistance75 mixed effect is negative both locally
[−5.9124%, −5.6656%] and held out [−4.3498%, −4.1382%]. In the resistance0 task,
all three pairs have only machine-precision interaction residuals. The closer
a10+x0 control is unresolved near zero locally [−0.1602%, +0.0341%], but has a
small resolved negative held-out effect [−0.2123%, −0.0115%]. Calling both
settings “no interaction” would be incorrect.

For Druid, a16+x3 sends both replacements toward more MP5 and less spell power.
Its long-task mixed effect is negative locally [−1.4919%, −1.3485%] and held out
[−1.6053%, −1.4590%], while the main a16+x0 interaction is positive locally
[+1.0859%, +1.1958%] and held out [+1.0011%, +1.1180%]. The small main-pair
short-task effect is unresolved locally [−0.1525%, +0.0064%] and positive held
out [+0.0448%, +0.1900%]. These observations reject a blanket zero-effect
description of the short task.

The earlier source/action audit explains why the Druid mechanism should be
described as resource-dependent action allocation and damage-per-cast
complementarity. MP5 regeneration itself is implemented linearly. The tested
Starfire mana guard cannot explain the long-task effect: no Starfire was cast
in any of its four development corners, and changing that guard left the
long-task samples unchanged. The complete development history, including
256/512-seed threshold instability and short-task sign reversals, remains in
`DEEP_JOINT_MECHANISM_AUDIT.md` and the associated immutable analysis artifacts.

## Verification and reproduction

`VERIFICATION.json` records 18 family rows, 108 development-world rows, 32
capacity rows, 100 contrast rows, 20 mixed-control rows and valid PDF/SVG
outputs. The CSV interval ordering and capacity lower/upper directions were
checked against the completed input schema, and all four panels were visually
inspected. The reporting module starts no native jobs and modifies no frozen
experiment source or result.

From the repository, source `scripts/env.sh` and run:

```bash
python -m wowfs.reporting.oe_figures \
  --run-root "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1" \
  --confirmation "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/analysis/confirm-v2-results" \
  --output "$WOWFS_WORK_ROOT/artifacts/open-exploration-2026-09-26/campaign-v1/figures/reproduction-new" \
  --wrapper-dir docs/open-exploration-2026-09-26/figures
```

Use a new output directory. The module refuses to overwrite previous figure
artifacts and refuses partial or unverified confirmation analysis products.
