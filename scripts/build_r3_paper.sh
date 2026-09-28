#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"
WOWFS_R3_BUILD="$WOWFS_WORK_ROOT/tmp/r3-gold/paper"
WOWFS_R3_DEST="$WOWFS_WORK_ROOT/artifacts/r3-gold/paper"
mkdir -p "$WOWFS_R3_BUILD" "$WOWFS_R3_DEST"
export SOURCE_DATE_EPOCH=1790208000
"$WOWFS_WORK_ROOT/envs/tectonic-0.17.0/tectonic" \
  -Z "search-path=$WOWFS_WORK_ROOT/external/AISTATS2027PaperPack/AISTATS2027PaperPack" \
  -Z "search-path=$WOWFS_WORK_ROOT/artifacts/r3-gold/figures" \
  -Z paper-size=letter --keep-logs --keep-intermediates --outdir "$WOWFS_R3_BUILD" \
  "$WOWFS_SOURCE_ROOT/paper/r3_main.tex" > "$WOWFS_WORK_ROOT/logs/r3-gold/paper-build.log" 2>&1
cp "$WOWFS_R3_BUILD/r3_main.pdf" "$WOWFS_R3_DEST/r3_main.pdf"
printf '%s\n' "$WOWFS_R3_DEST/r3_main.pdf"
