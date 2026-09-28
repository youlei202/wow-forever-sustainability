#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "$0")/env.sh"
cd "$WOWFS_SOURCE_ROOT"
python -m wowfs bootstrap
python -m wowfs run --suite exact-small --config configs/development.yaml "$@"
python scripts/verify_theory.py
if [[ -f scripts/verify_statistics.py ]]; then
  python scripts/verify_statistics.py
fi
python -m wowfs report --config configs/development.yaml
bash scripts/build_paper.sh
python -m wowfs package --config configs/development.yaml
