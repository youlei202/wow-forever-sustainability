#!/usr/bin/env bash
# Execute inside tmux. Logs and portable replay remain outside the sealed run.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source scripts/env.sh
export GOMAXPROCS=1
mi_run="${1:-$WOWFS_WORK_ROOT/artifacts/minimal-interface-native-audit-2026-09-27}"
mi_extract="${2:-$WOWFS_WORK_ROOT/artifacts/minimal-interface-actual-zip}"
mi_recheck="${3:-$WOWFS_WORK_ROOT/artifacts/minimal-interface-package-recheck}"
python -m wowfs.reporting.mi_report package --run "$mi_run"
python - "$mi_run" "$mi_extract" <<'PY'
from pathlib import Path
import sys
import zipfile
run = Path(sys.argv[1])
destination = Path(sys.argv[2])
if destination.exists():
    raise FileExistsError(destination)
destination.mkdir()
with zipfile.ZipFile(run.parent / 'WOW_MINIMAL_INTERFACE_NATIVE_REVIEW.zip') as archive:
    for info in archive.infolist():
        path = Path(info.filename)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Unsafe output archive member')
    archive.extractall(destination)
PY
mi_package="$mi_extract/$(basename -- "$mi_run")"
export PYTHONPATH="$mi_package/code:$mi_package/tests"
cd -- "$WOWFS_WORK_ROOT/tmp"
python -m pytest -q "$mi_package/tests/test_mi_native.py" "$mi_package/tests/test_mi_druid.py" "$mi_package/tests/test_mi_theory.py"
python "$mi_package/scripts/recheck_minimal_interface_package.py" --package "$mi_package" --output "$mi_recheck"
