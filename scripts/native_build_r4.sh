#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"
export WOWFS_SOURCE_ROOT
export PATH="$WOWFS_WORK_ROOT/envs/r2-go/go/bin:$WOWFS_WORK_ROOT/envs/r2-go/protoc/bin:$WOWFS_WORK_ROOT/cache/r2-discovery/go-path/bin:$PATH"
export GOPATH="$WOWFS_WORK_ROOT/cache/r4-foundational-discovery/go-path"
export GOCACHE="$WOWFS_WORK_ROOT/cache/r4-foundational-discovery/go-build"
export GOMODCACHE="$WOWFS_WORK_ROOT/cache/r2-discovery/go-mod"
export GOTOOLCHAIN=local
export WOWFS_R4_ENGINE_ROOT="$WOWFS_WORK_ROOT/external/mythicsim-forever-engine-r4-worlds"
expected=17d75ccc8c67d027ae0088243ea3ee806d406847
if [ ! -d "$WOWFS_R4_ENGINE_ROOT" ]; then
 git -C "$WOWFS_WORK_ROOT/external/mythicsim-forever-engine-r2" worktree add --detach "$WOWFS_R4_ENGINE_ROOT" "$expected"
fi
test "$(git -C "$WOWFS_R4_ENGINE_ROOT" rev-parse HEAD)" = "$expected"
mkdir -p "$WOWFS_R4_ENGINE_ROOT/cmd/wowfs-r4" "$WOWFS_WORK_ROOT/envs/r4-go" "$WOWFS_WORK_ROOT/logs/r4-foundational-discovery"
cp "$WOWFS_SOURCE_ROOT/src/wowfs/simulator/native_ablation.go" "$WOWFS_R4_ENGINE_ROOT/sim/core/wowfs_r2_ablation.go"
cp "$WOWFS_SOURCE_ROOT/src/wowfs/simulator/r4_worlds.go" "$WOWFS_R4_ENGINE_ROOT/sim/core/wowfs_r4_worlds.go"
python - <<'PY'
from pathlib import Path
import os,subprocess
source=Path(os.environ['WOWFS_SOURCE_ROOT']);engine=Path(os.environ['WOWFS_R4_ENGINE_ROOT'])
def pristine(path):return subprocess.check_output(['git','-C',str(engine),'show','HEAD:'+path],text=True)
def once(text,old,new):
 assert text.count(old)==1,(old,text.count(old));return text.replace(old,new)
character=pristine('sim/core/character.go')
needle='func (character *Character) GetOffensiveTrinketCD() *Timer {\n'
character=once(character,needle,needle+'\tif R4ActiveWorld.IndependentOffensiveCooldowns { return R4IndependentOffensiveTimer(character) }\n')
(engine/'sim/core/character.go').write_text(character)
spell=pristine('sim/core/spell.go')
needle='func (unit *Unit) RegisterSpell(config SpellConfig) *Spell {\n'
spell=once(spell,needle,needle+'\tR4ConfigureSpellSharedResource(unit, &config)\n')
(engine/'sim/core/spell.go').write_text(spell)
attack=pristine('sim/core/attack.go')
for name in ['ExtraMHAttack','StoreExtraMHAttack']:
 needle=f'func (aa *AutoAttacks) {name}(sim *Simulation, attacks int32, actionID ActionID, triggerAction ActionID) {{\n\tif attacks == 0 {{\n\t\treturn\n\t}}\n'
 attack=once(attack,needle,needle+'\tif !R4AllowExtraAttackBatch(aa, sim, attacks, actionID, triggerAction) { return }\n')
(engine/'sim/core/attack.go').write_text(attack)
helpers=pristine('sim/core/aura_helpers.go')
helpers=once(helpers,'type ProcTrigger struct {','type ProcTrigger struct {\n\tWOWFSHeroismExtraFilter bool')
needle='\t\tif config.Harmful && result.Damage == 0 {\n\t\t\treturn\n\t\t}\n'
helpers=once(helpers,needle,needle+'\t\tif config.WOWFSHeroismExtraFilter && !R4AllowHeroismProcEvent(sim,spell) { return }\n')
(engine/'sim/core/aura_helpers.go').write_text(helpers)
sets=pristine('sim/warrior/item_sets_pve.go')
needle='\t\t\t\tName:     "Warrior\'s Resolve",'
sets=once(sets,needle,needle+'\n\t\t\t\tWOWFSHeroismExtraFilter: true,')
(engine/'sim/warrior/item_sets_pve.go').write_text(sets)
main=(source/'src/wowfs/simulator/native_main.go').read_text()
main=once(main,'"encoding/json"','"encoding/json"\n\t"bytes"')
main=once(main,'type inputEnvelope struct {','type inputEnvelope struct {\n\tResearchWorld core.R4World `json:"research_world"`')
main=once(main,'if err = json.Unmarshal(data, &input); err != nil {','decoder := json.NewDecoder(bytes.NewReader(data)); decoder.DisallowUnknownFields()\n\tif err = decoder.Decode(&input); err != nil {')
main=once(main,'for _, id := range input.DisableItemEffects {','if err = core.R4ConfigureWorld(input.ResearchWorld); err != nil { fail(err) }\n\tfor _, id := range input.DisableItemEffects {')
main=once(main,'write(*outfile, output)','var enriched map[string]json.RawMessage\n\tif err = json.Unmarshal(output, &enriched); err != nil { fail(err) }\n\tmetadata, err := json.Marshal(core.R4GetWorldTelemetry()); if err != nil { fail(err) }\n\tenriched["wowfsResearchWorld"] = metadata\n\toutput, err = json.Marshal(enriched); if err != nil { fail(err) }\n\twrite(*outfile, output)')
(engine/'cmd/wowfs-r4/main.go').write_text(main)
PY
cd "$WOWFS_R4_ENGINE_ROOT"
gofmt -w sim/core/wowfs_r4_worlds.go sim/core/character.go sim/core/spell.go sim/core/attack.go sim/core/aura_helpers.go sim/warrior/item_sets_pve.go cmd/wowfs-r4/main.go
protoc -I=./proto --go_out=./sim/core ./proto/*.proto
go build -tags=with_db -o "$WOWFS_WORK_ROOT/envs/r4-go/wowfs-native-worlds" ./cmd/wowfs-r4
printf '%s\n' "$WOWFS_WORK_ROOT/envs/r4-go/wowfs-native-worlds"
