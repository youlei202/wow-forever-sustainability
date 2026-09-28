# Reproduce decisive-value evidence

Run from `/work/Users/leiyo/GitHub/wow-forever-sustainability` after:

```bash
source scripts/env.sh
pytest -q
```

Storage is configured by WOWFS_WORK_ROOT. All new native runs and caches use
`decisive-value`; R1–R6 remain read-only. The pinned native wrapper binary is
`$WOWFS_WORK_ROOT/envs/r3-go/wowfs-native-variants`, SHA256
`59f42b32e2c834321773188db482419238ae57556942f6f1825258722fc0aafe`.
The upstream engine is sage3648/mythicsim-forever-engine at commit
`17d75ccc8c67d027ae0088243ea3ee806d406847`. Build wrapper sources, upstream
license, exact inputs, snapshots and executable hashes are included; third-party
checkout, environments and compiled binaries remain outside source control.

The frozen DESIGN points to all physical parameters and masks. Review the
small direct table without invoking the simulator:

```python
from wowfs.experiments.value_confirmation_data import load_confirmation
x = load_confirmation()
# x.samples: gear25 × policy3 × task8 × paired seeds1024
# x.values, x.behavior, x.sources, x.initial, x.design
```

The NPZ export and META document preserve the same order. The complete raw
receipts permit recomputation independently of that export. Packaged paths
are provenance paths of the originating workspace; relocate them deliberately
when loading raw receipts on another machine. No automatic download or native
reexecution is needed to inspect the tables and figures.

Recompute final derived products from the unchanged runs:

```bash
python -m wowfs.experiments.value_confirm_analysis
python -m wowfs.experiments.value_structural
python -m wowfs.reporting.value_report
python scripts/audit_decisive_value.py
python scripts/audit_value_native.py
```

The last two commands create new audit receipts, not native experiments. Do not
edit a frozen run or rerun its native commands without `--resume` and identical
source/configuration hashes. The independent confirmation is already complete;
rerunning for a more favorable interval would violate this study's protocol.
To independently replicate physics in a separate future study, copy the frozen
protocol to a new namespace and predeclare a new seed panel rather than
changing this study's results.

Development modules are value_demand (lineA), value_combinations (lineB),
value_history/value_history_followup/value_sequences (lineC), value_affine
(primitive calibration), value_construct (model-only candidate search), and
value_theory (exact abstract construction). Cached-line screens use unchanged
R4 baseline data; their exploratory finite means are not fresh native calls.
Construction search has98304 proposals,951 guarded joint-feasible candidates
and3selected pairs. The report distinguishes rejected proposals from feasible
unselected proposals. Exact DP has724 attempted transitions and662 failures.
Neither a timeout nor a missing execution is recoded as zero performance.

The package contains all864 new native receipts and all new frozen run files
except compiled executable copies. It contains maintained source snapshots,
required tables, primary literature links, original R5 theory and this round's
research brief. The old R4 gigabyte table is represented by the required
four-ecology tensor export with original provenance, not counted as new data.
No external upload, remote push, submission or invented Git identity was used.
