#!/usr/bin/env bash
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"
export WOWFS_SOURCE_ROOT
export PATH="$WOWFS_WORK_ROOT/envs/r2-go/go/bin:$WOWFS_WORK_ROOT/envs/r2-go/protoc/bin:$WOWFS_WORK_ROOT/cache/r2-discovery/go-path/bin:$PATH"
export GOPATH="$WOWFS_WORK_ROOT/cache/r3-gold/go-path"
export GOCACHE="$WOWFS_WORK_ROOT/cache/r3-gold/go-build"
export GOMODCACHE="$WOWFS_WORK_ROOT/cache/r2-discovery/go-mod"
export GOTOOLCHAIN=local
export WOWFS_R3_ENGINE_ROOT="$WOWFS_WORK_ROOT/external/mythicsim-forever-engine-r3-variants"
expected=17d75ccc8c67d027ae0088243ea3ee806d406847
if [ ! -d "$WOWFS_R3_ENGINE_ROOT" ]; then
  git -C "$WOWFS_WORK_ROOT/external/mythicsim-forever-engine-r2" worktree add --detach "$WOWFS_R3_ENGINE_ROOT" "$expected"
fi
test "$(git -C "$WOWFS_R3_ENGINE_ROOT" rev-parse HEAD)" = "$expected"
mkdir -p "$WOWFS_R3_ENGINE_ROOT/cmd/wowfs-r3" "$WOWFS_WORK_ROOT/envs/r3-go" "$WOWFS_WORK_ROOT/logs/r3-gold"
cp "$WOWFS_SOURCE_ROOT/src/wowfs/simulator/native_ablation.go" "$WOWFS_R3_ENGINE_ROOT/sim/core/wowfs_r2_ablation.go"
cp "$WOWFS_SOURCE_ROOT/src/wowfs/simulator/r3_variants.go" "$WOWFS_R3_ENGINE_ROOT/sim/core/wowfs_r3_variants.go"
cp "$WOWFS_SOURCE_ROOT/src/wowfs/simulator/r3_variants_test.go" "$WOWFS_R3_ENGINE_ROOT/sim/core/wowfs_r3_variants_test.go"
python - <<'PY'
from pathlib import Path
import os, subprocess
source=Path(os.environ['WOWFS_SOURCE_ROOT']);engine=Path(os.environ['WOWFS_R3_ENGINE_ROOT'])
def pristine(path):return subprocess.check_output(['git','-C',str(engine),'show','HEAD:'+path],text=True)
def replace_once(text,old,new):
 assert text.count(old)==1,(old,text.count(old))
 return text.replace(old,new)
helpers=pristine('sim/common/itemhelpers/weaponprocs.go')
old='character.AutoAttacks.NewPPMManager(ppm, procMask)'
assert helpers.count(old)==3
helpers=helpers.replace(old,'character.AutoAttacks.NewPPMManager(core.R3EffectValue(itemId, "proc_ppm", ppm), procMask)')
start='\tcore.NewItemEffect(itemId, func(agent core.Agent) {\n\t\tcharacter := agent.GetCharacter()\n\n\t\tsc := core.SpellConfig{'
replacement='\tcore.NewItemEffect(itemId, func(agent core.Agent) {\n\t\tcharacter := agent.GetCharacter()\n\t\tnativeMin, nativeRange := dmgMin, dmgRange\n\t\tdmgMin, dmgRange := nativeMin, nativeRange\n\t\tif core.R3HasEffectOverride(itemId, "proc_damage_min") || core.R3HasEffectOverride(itemId, "proc_damage_max") {\n\t\t\tdmgMin = core.R3EffectValue(itemId, "proc_damage_min", nativeMin)\n\t\t\tdmgRange = core.R3EffectValue(itemId, "proc_damage_max", nativeMin + nativeRange) - dmgMin\n\t\t}\n\n\t\tsc := core.SpellConfig{'
helpers=replace_once(helpers,start,replacement)
(engine/'sim/common/itemhelpers/weaponprocs.go').write_text(helpers)
effects=pristine('sim/common/item_effects.go')
start=effects.index('\titemhelpers.CreateWeaponProcSpell(BloodTalon,')
end=effects.index('\n\t// https://',start)
blood=effects[start:end]
blood=replace_once(blood,'NumberOfTicks: 10,','NumberOfTicks: int32(core.R3EffectValue(BloodTalon, "number_of_ticks", 10)),')
blood=replace_once(blood,'TickLength:    time.Second * 3,','TickLength: time.Duration(core.R3EffectValue(BloodTalon, "tick_interval_seconds", 3) * float64(time.Second)),')
blood=replace_once(blood,'target, 10, dot.OutcomeTick','target, core.R3EffectValue(BloodTalon, "periodic_damage_per_tick", 10), dot.OutcomeTick')
effects=effects[:start]+blood+effects[end:]
start=effects.index('\tcore.NewItemEffect(Thunderfury,')
end=effects.index('\n\t// https://',start)
thunder=effects[start:end]
thunder=replace_once(thunder,'NewPPMManager(6.0, procMask)','NewPPMManager(core.R3EffectValue(Thunderfury, "proc_ppm", 6.0), procMask)')
thunder=replace_once(thunder,'target, 300, spell.OutcomeMagicHitAndCrit','target, core.R3EffectValue(Thunderfury, "proc_damage", 300), spell.OutcomeMagicHitAndCrit')
thunder=replace_once(thunder,'stats.NatureResistance, -25','stats.NatureResistance, -core.R3EffectValue(Thunderfury, "nature_resistance_reduction", 25)')
thunder=replace_once(thunder,'stats.NatureResistance, 25','stats.NatureResistance, core.R3EffectValue(Thunderfury, "nature_resistance_reduction", 25)')
effects=effects[:start]+thunder+effects[end:]
(engine/'sim/common/item_effects.go').write_text(effects)
main=(source/'src/wowfs/simulator/native_main.go').read_text()
main=replace_once(main,'"encoding/json"','"encoding/json"\n\t"bytes"')
main=replace_once(main,'type inputEnvelope struct {','type inputEnvelope struct {\n\tResearchVariants []core.R3Variant `json:"research_variants"`')
main=replace_once(main,'if err = json.Unmarshal(data, &input); err != nil {','decoder := json.NewDecoder(bytes.NewReader(data))\n\tdecoder.DisallowUnknownFields()\n\tif err = decoder.Decode(&input); err != nil {')
main=replace_once(main,'for _, id := range input.DisableItemEffects {','appliedVariants, err := core.R3ConfigureVariants(input.ResearchVariants)\n\tif err != nil { fail(err) }\n\tfor _, id := range input.DisableItemEffects {')
main=replace_once(main,'write(*outfile, output)','var enriched map[string]json.RawMessage\n\tif err = json.Unmarshal(output, &enriched); err != nil { fail(err) }\n\tvariantMetadata, err := json.Marshal(appliedVariants); if err != nil { fail(err) }\n\tenriched["wowfsResearchVariants"] = variantMetadata\n\toutput, err = json.Marshal(enriched); if err != nil { fail(err) }\n\twrite(*outfile, output)')
main=main.replace('R2 runner requires explicit RulesetForever','R3 runner requires explicit RulesetForever')
(engine/'cmd/wowfs-r3/main.go').write_text(main)
PY
cd "$WOWFS_R3_ENGINE_ROOT"
gofmt -w sim/core/wowfs_r3_variants.go sim/common/itemhelpers/weaponprocs.go sim/common/item_effects.go cmd/wowfs-r3/main.go
protoc -I=./proto --go_out=./sim/core ./proto/*.proto
go build -tags=with_db -o "$WOWFS_WORK_ROOT/envs/r3-go/wowfs-native-variants" ./cmd/wowfs-r3
printf '%s\n' "$WOWFS_WORK_ROOT/envs/r3-go/wowfs-native-variants"
