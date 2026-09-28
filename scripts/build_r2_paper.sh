#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"
WOWFS_R2_BUILD="$WOWFS_WORK_ROOT/tmp/r2-discovery/paper"
WOWFS_R2_DEST="$WOWFS_WORK_ROOT/artifacts/r2-discovery/latest/paper"
mkdir -p "$WOWFS_R2_BUILD" "$WOWFS_R2_DEST"
export SOURCE_DATE_EPOCH=1790208000
"$WOWFS_WORK_ROOT/envs/tectonic-0.17.0/tectonic" \
  -Z "search-path=$WOWFS_WORK_ROOT/external/AISTATS2027PaperPack/AISTATS2027PaperPack" \
  -Z "search-path=$WOWFS_WORK_ROOT/artifacts/r2-discovery/latest/figures" \
  -Z paper-size=letter --keep-logs --keep-intermediates --outdir "$WOWFS_R2_BUILD" \
  "$WOWFS_SOURCE_ROOT/paper/r2_main.tex" > "$WOWFS_WORK_ROOT/logs/r2-discovery/paper-build.log" 2>&1
cp "$WOWFS_R2_BUILD/r2_main.pdf" "$WOWFS_R2_DEST/r2_main.pdf"
printf '%s\n' "$WOWFS_R2_DEST/r2_main.pdf"
