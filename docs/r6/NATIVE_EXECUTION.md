# R6 native execution and identity contract

The formal R5 note was read completely before R6 implementation resumed. Its
SHA-256 is `a2160fda7467f3618797c91f2257f6dac39b284804774cf0751eac1d92cd8dd2`;
every native run archives an exact copy under `inputs/r5-theory/THEORY.md`.
Provisional suggestions made before this comparison did not launch physics or
create R6 code. The R3 engine binary remains unchanged:
`59f42b32e2c834321773188db482419238ae57556942f6f1825258722fc0aafe`.

`src/wowfs/experiments/r6_native.py` provides `r3_base`, `define_alias`,
`instantiate` and `run_jobs`. Research identities are explicit aliases of an
existing native item plus its actual parameter overrides. Alias names never
become invented official item IDs. Alternatives assigned to the same slot
cannot coexist. One native base ID may have only one override specification
and must identify exactly one equipped item; this avoids pretending the
engine's global item override supports independent copies in different slots.
The wrapper checks all 17 slots, hands, unique-item restrictions and Warrior
class legality against the pinned native database.

Each run freezes full native inputs, scientific protocol, source files,
imported inputs, executable and timestamp before dispatch. Its cache key is
the executable hash plus complete engine input. Research labels and logical
reuse do not add physical battles. Incomplete R6 cache entries are preserved
and not overwritten by an automatic retry. Runtime products stay under
`$WOWFS_WORK_ROOT/{runs,cache,artifacts}/r6-theory-native`.

## Calibration panel

The separate stress panel uses one Human Warrior, high-armor 180-second combat,
the native Recklessness policy, Thunderfury off hand and HoJ/Blackhand trinkets.
Only the Blood Talon main-hand alternative expands. Its prospective base-DPS
interval [1,175] and periodic tick damage interval [0,500] are explicit research
amplitudes beyond the original R3 box; they are not official item claims.
The physical tick timing remains fixed at three seconds.

Before outcomes, three calibration points (0,0), (180,0), (0,500) and a heldout
point (90,250) were frozen at 2,048 seeds starting 609240001. The designated old
research anchor (180,0) has sampled mean DPS 254.6379938. The heldout per-seed
affine residual is at most 1.14e-13 DPS. Maximum per-action mean fight-damage
residual is 1.46e-11, while aggregate control metrics and normalized first-seed
event traces agree exactly across all four points. This is a coupled-seed
structural check; separate fresh-seed confirmation remains necessary.

The R5 theorem requires an affine observable behavior map. Raw action-channel
DPS divided by a fixed old-frontier scalar has that form within the verified
reward family. Fractions divided by each candidate's varying total utility
are generally fractional-linear; they must not be silently substituted for
the theorem's affine map. The stress-panel normalization therefore differs
from the original R3 behavior fractions.

## Native set-gate feasibility

The bounded A probe freezes four glove choices and three leg choices, including
all off-diagonal, old-anchor/repair and core/repair combinations. Two extra
controls remove only the matching four-piece set bonus while retaining the
exact same equipment and all other set tiers. No research stat tuning was
used. The complete mapping and source audit are in
`NATIVE_CASCADE_FEASIBILITY.md`; raw data are in `native-gate-probe-v1`.

The actual matching set effects improve their corresponding loadouts by
3.1926 DPS (Heroism) and 1.0674 DPS (Stormshroud) at the sampled means. They do
not establish the R5 cascade assumptions: the old frontier is 175.6577 DPS,
the core is 173.7891 DPS, and both matching repair loadouts remain weaker than
their respective old source witnesses. No cascade was constructed by this
probe. There was no outcome-driven stat adjustment; larger gate constructions
and the statistical locality experiment were not run here.

## Independent count audit

The final quiescent audit at 2026-09-24 22:11:50 UTC verifies **1,140 native calls
and 1,753,088 physical battles**, all Human Warrior, with zero failed receipts,
incomplete invocations, audit errors or pending native runs. The six stages
are stress calibration (4 calls / 8,192 battles), neutral development
(2 / 4,096), neutral confirmation (16 / 16,384), capacity confirmation
(368 / 188,416), final capacity precision (736 / 1,507,328), and native gate
feasibility (14 / 28,672).

`scripts/audit_r6_native.py` checks raw output hashes, iteration counts,
frozen source/binary/import hashes, full archived job/result/cache joins and
post-scan file signatures. It separates reused older native data from new R6
calls and never counts mathematical checks as combat. The artifact
`INDEPENDENT_NATIVE_AUDIT.json` has SHA-256
`c9889b7a5cbea487ca7698b12b77a0f38fda3086b12da8dbcef6b7e6942d4b21`.
Its physical ledger is under `audit-20260924T221148537081Z` with SHA-256
`66a83c0bc3b1780413d3aad55ebbda9081ddaeb479e45e2bbf68ba88346e14a8`.

There are **1,746,944 distinct exact-design/seed observations**, across 40
combat designs. The 6,144 repeated design/seed iterations were still executed
and remain in the physical count. Initial capacity and neutral confirmation
share 3,072 seed values; two common designs produce those 6,144 duplicate
observations. The native gate and neutral confirmation stages also share
1,024 seed values, although their combat designs differ. Shared labeled seeds
couple different designs too; these stages are not globally independent.
`SEED_OVERLAP.json` records both forms of overlap. The final capacity precision
panel starts at 614000001 with stride 10000, and has **zero seed intersection
with every one of the five preceding stages**. Native source
`sim/core/sim.go:235,333` confirms that iteration i uses start seed + i.

These counts establish executed coverage and provenance, not the ecological
or population-level validity of a sequence; those conclusions have separate
analysis records.
