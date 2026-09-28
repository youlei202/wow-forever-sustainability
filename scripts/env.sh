#!/usr/bin/env bash
# Source this script; environments and caches stay outside the source tree.
set -euo pipefail
WOWFS_SOURCE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export WOWFS_WORK_ROOT="${WOWFS_WORK_ROOT:-$(dirname -- "$(dirname -- "$WOWFS_SOURCE_ROOT")")/wow-forever-sustainability-work}"
export TMPDIR="$WOWFS_WORK_ROOT/tmp"
export XDG_CACHE_HOME="$WOWFS_WORK_ROOT/cache"
export PIP_CACHE_DIR="$WOWFS_WORK_ROOT/cache/pip"
export PYTHONPYCACHEPREFIX="$WOWFS_WORK_ROOT/cache/pycache"
export MPLCONFIGDIR="$WOWFS_WORK_ROOT/cache/matplotlib"
export PYTHONPATH="$WOWFS_SOURCE_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME" "$MPLCONFIGDIR"
export PATH="$WOWFS_WORK_ROOT/envs/research/bin:$PATH"
