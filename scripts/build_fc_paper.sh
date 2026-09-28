#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"
WOWFS_FC_BUILD="$WOWFS_WORK_ROOT/tmp/final-completion-capacity/paper"
WOWFS_FC_ARTIFACT="$WOWFS_WORK_ROOT/artifacts/final-completion-capacity"
mkdir -p "$WOWFS_FC_BUILD" "$WOWFS_FC_ARTIFACT/paper" "$WOWFS_WORK_ROOT/logs/final-completion-capacity"
export SOURCE_DATE_EPOCH=1790294400
"$WOWFS_WORK_ROOT/envs/tectonic-0.17.0/tectonic" \
  -Z "search-path=$WOWFS_WORK_ROOT/external/AISTATS2027PaperPack/AISTATS2027PaperPack" \
  -Z "search-path=$WOWFS_FC_ARTIFACT/figures" \
  -Z "search-path=$WOWFS_FC_ARTIFACT/paper" \
  -Z paper-size=letter --keep-logs --keep-intermediates --outdir "$WOWFS_FC_BUILD" \
  "$WOWFS_SOURCE_ROOT/paper/fc_main.tex" > "$WOWFS_WORK_ROOT/logs/final-completion-capacity/paper-build.log" 2>&1
cp "$WOWFS_FC_BUILD/fc_main.pdf" "$WOWFS_FC_ARTIFACT/paper/fc_main.pdf"
printf '%s\n' "$WOWFS_FC_ARTIFACT/paper/fc_main.pdf"
