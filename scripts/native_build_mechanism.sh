#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"
export WOWFS_SOURCE_ROOT
export PATH="$WOWFS_WORK_ROOT/envs/r2-go/go/bin:$WOWFS_WORK_ROOT/envs/r2-go/protoc/bin:$WOWFS_WORK_ROOT/cache/r2-discovery/go-path/bin:$PATH"
export GOPATH="$WOWFS_WORK_ROOT/cache/r2-discovery/go-path"
export GOCACHE="$WOWFS_WORK_ROOT/cache/r2-discovery/go-build"
export GOMODCACHE="$WOWFS_WORK_ROOT/cache/r2-discovery/go-mod"
export GOTOOLCHAIN=local
base="$WOWFS_WORK_ROOT/external/mythicsim-forever-engine-r2"
export WOWFS_MECHANISM_ENGINE_ROOT="$WOWFS_WORK_ROOT/external/mythicsim-forever-engine-r2-mechanism"
expected=17d75ccc8c67d027ae0088243ea3ee806d406847
if [ ! -d "$WOWFS_MECHANISM_ENGINE_ROOT" ]; then
  git -C "$base" worktree add --detach "$WOWFS_MECHANISM_ENGINE_ROOT" "$expected"
fi
test "$(git -C "$WOWFS_MECHANISM_ENGINE_ROOT" rev-parse HEAD)" = "$expected"
mkdir -p "$WOWFS_MECHANISM_ENGINE_ROOT/cmd/wowfs-r2-mechanism"
cp "$WOWFS_SOURCE_ROOT/src/wowfs/simulator/native_ablation.go" "$WOWFS_MECHANISM_ENGINE_ROOT/sim/core/wowfs_r2_ablation.go"
cp "$WOWFS_SOURCE_ROOT/src/wowfs/simulator/native_mechanism.go" "$WOWFS_MECHANISM_ENGINE_ROOT/sim/core/wowfs_r2_mechanism.go"
cp "$WOWFS_SOURCE_ROOT/src/wowfs/simulator/native_mechanism_test.go" "$WOWFS_MECHANISM_ENGINE_ROOT/sim/core/wowfs_r2_mechanism_test.go"
python - <<'PY'
from pathlib import Path
import os,subprocess
source=Path(os.environ['WOWFS_SOURCE_ROOT']) if 'WOWFS_SOURCE_ROOT' in os.environ else Path.cwd()
engine=Path(os.environ['WOWFS_MECHANISM_ENGINE_ROOT'])
attack=subprocess.check_output(['git','-C',str(engine),'show','HEAD:sim/core/attack.go'],text=True)
reset='func (aa *AutoAttacks) reset(sim *Simulation) {\n'
assert attack.count(reset)==1
attack=attack.replace(reset,reset+'\tWOWFSResetExtraMeleeUnit(aa)\n')
for name in ('ExtraMHAttack','StoreExtraMHAttack'):
 start=f'func (aa *AutoAttacks) {name}(sim *Simulation, attacks int32, actionID ActionID, triggerAction ActionID) {{\n\tif attacks == 0 {{\n\t\treturn\n\t}}\n'
 assert attack.count(start)==1
 attack=attack.replace(start,start+'\tif !WOWFSAdmitExtraMeleeBatch(aa, sim, attacks, actionID) { return }\n')
(engine/'sim/core/attack.go').write_text(attack)
main=(source/'src/wowfs/simulator/native_main.go').read_text()
start='type inputEnvelope struct {\n'
assert main.count(start)==1
main=main.replace(start,start+'\tExtraMeleeCooldownSeconds float64 `json:"extra_melee_cooldown_seconds"`\n')
start='result := core.RunRaidSim(request)'
assert main.count(start)==1
main=main.replace(start,'if err = core.WOWFSConfigureExtraMeleeCooldown(input.ExtraMeleeCooldownSeconds); err != nil { fail(err) }\n\t'+start)
start='write(*outfile, output)'
assert main.count(start)==1
main=main.replace(start,'var enriched map[string]json.RawMessage\n\tif err = json.Unmarshal(output, &enriched); err != nil { fail(err) }\n\ttelemetry, err := json.Marshal(core.WOWFSGetMechanismTelemetry()); if err != nil { fail(err) }\n\tenriched["wowfsMechanism"] = telemetry\n\toutput, err = json.Marshal(enriched); if err != nil { fail(err) }\n\t'+start)
(engine/'cmd/wowfs-r2-mechanism/main.go').write_text(main)
PY
cd "$WOWFS_MECHANISM_ENGINE_ROOT"
gofmt -w sim/core/wowfs_r2_mechanism.go sim/core/attack.go cmd/wowfs-r2-mechanism/main.go
protoc -I=./proto --go_out=./sim/core ./proto/*.proto
go build -tags=with_db -o "$WOWFS_WORK_ROOT/envs/r2-go/wowfs-native-mechanism" ./cmd/wowfs-r2-mechanism
printf '%s\n' "$WOWFS_WORK_ROOT/envs/r2-go/wowfs-native-mechanism"
