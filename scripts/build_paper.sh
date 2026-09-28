#!/usr/bin/env bash
# Dependencies, cache, logs, and output are external to the source tree.
set -euo pipefail
source "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/env.sh"
WOWFS_TECTONIC="${WOWFS_TECTONIC:-$WOWFS_WORK_ROOT/envs/tectonic-0.17.0/tectonic}"
WOWFS_PAPERPACK="${WOWFS_PAPERPACK:-$WOWFS_WORK_ROOT/external/AISTATS2027PaperPack/AISTATS2027PaperPack}"
WOWFS_PAPER_BUILD="$WOWFS_WORK_ROOT/tmp/paper"
WOWFS_PAPER_DEST="$WOWFS_WORK_ROOT/artifacts/latest/paper"
test -x "$WOWFS_TECTONIC" || { echo 'Tectonic binary missing; see docs/SOURCES.md' >&2; exit 1; }
test -f "$WOWFS_PAPERPACK/aistats2027.sty" || { echo 'Verified AISTATS 2027 template missing' >&2; exit 1; }
mkdir -p "$WOWFS_PAPER_BUILD" "$WOWFS_PAPER_DEST" "$WOWFS_WORK_ROOT/logs"
export SOURCE_DATE_EPOCH=1790208000
"$WOWFS_TECTONIC" -Z "search-path=$WOWFS_PAPERPACK" \
  -Z "search-path=$WOWFS_WORK_ROOT/artifacts/latest/figures" -Z paper-size=letter \
  --keep-logs --keep-intermediates --outdir "$WOWFS_PAPER_BUILD" \
  "$WOWFS_SOURCE_ROOT/paper/main.tex" \
  > "$WOWFS_WORK_ROOT/logs/paper-build.log" 2>&1
cp "$WOWFS_PAPER_BUILD/main.pdf" "$WOWFS_PAPER_DEST/main.pdf"
printf '%s\n' "$WOWFS_PAPER_DEST/main.pdf"
