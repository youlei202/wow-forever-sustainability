// Copied into cmd/wowfs-r2 in the pinned community engine at build time.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"

	"github.com/wowsims/classic/sim"
	"github.com/wowsims/classic/sim/core"
	"github.com/wowsims/classic/sim/core/proto"
	"google.golang.org/protobuf/encoding/protojson"
	googleproto "google.golang.org/protobuf/proto"
)

type setAblation struct {
	Name   string `json:"name"`
	Pieces int32  `json:"pieces"`
}
type inputEnvelope struct {
	Request            json.RawMessage `json:"request"`
	DisableItemEffects []int32         `json:"disable_item_effects"`
	DisableSetBonuses  []setAblation   `json:"disable_set_bonuses"`
}

func fail(err error) { fmt.Fprintln(os.Stderr, err); os.Exit(2) }
func write(path string, data []byte) {
	if path == "" {
		_, err := os.Stdout.Write(data)
		if err != nil {
			fail(err)
		}
		return
	}
	if err := os.WriteFile(path, append(data, '\n'), 0644); err != nil {
		fail(err)
	}
}

func template(root string) *proto.RaidSimRequest {
	b := core.ForeverBuffs
	target := googleproto.Clone(core.NewDefaultTarget()).(*proto.Target)
	target.TankIndex = -1
	return &proto.RaidSimRequest{
		Raid: &proto.Raid{Parties: []*proto.Party{{Players: []*proto.Player{{
			Name: "R2Warrior", Race: proto.Race_RaceOrc, Class: proto.Class_ClassWarrior,
			Equipment:     core.GetGearSet(filepath.Join(root, "ui/warrior/gear_sets"), "p0.bis").GearSet,
			Rotation:      core.GetAplRotation(filepath.Join(root, "ui/warrior/apls"), "dps_reck").Rotation,
			TalentsString: "30305013-050520035150310051", Buffs: b.Player,
			Spec: &proto.Player_Warrior{Warrior: &proto.Warrior{Options: &proto.Warrior_Options{
				StartingRage: 50, Shout: proto.WarriorShout_WarriorShoutBattle,
			}}},
			Consumes: &proto.Consumes{
				AgilityElixir:     proto.AgilityElixir_ElixirOfTheMongoose,
				AttackPowerBuff:   proto.AttackPowerBuff_JujuMight,
				DefaultPotion:     proto.Potions_MightyRagePotion,
				DragonBreathChili: true, Food: proto.Food_FoodSmokedDesertDumpling,
				MainHandImbue: proto.WeaponImbue_Windfury,
				OffHandImbue:  proto.WeaponImbue_ElementalSharpeningStone,
				StrengthBuff:  proto.StrengthBuff_JujuPower,
			},
		}}, Buffs: b.Party}}, Buffs: b.Raid, Debuffs: b.Debuffs},
		Encounter:  &proto.Encounter{Duration: 180, ExecuteProportion_20: 0.2, Targets: []*proto.Target{target}},
		SimOptions: &proto.SimOptions{Iterations: 1, RandomSeed: 27092401, Ruleset: proto.Ruleset_RulesetForever, Debug: true},
	}
}

func main() {
	infile := flag.String("in", "", "JSON envelope input")
	outfile := flag.String("out", "", "native RaidSimResult JSON output")
	templateOut := flag.String("template-out", "", "write native Warrior template envelope and exit")
	engineRoot := flag.String("engine-root", ".", "engine root for preset import")
	flag.Parse()
	sim.RegisterAll()
	if *templateOut != "" {
		request, err := protojson.MarshalOptions{Indent: "  "}.Marshal(template(*engineRoot))
		if err != nil {
			fail(err)
		}
		out, err := json.MarshalIndent(inputEnvelope{Request: request, DisableItemEffects: []int32{}, DisableSetBonuses: []setAblation{}}, "", "  ")
		if err != nil {
			fail(err)
		}
		write(*templateOut, out)
		return
	}
	data, err := os.ReadFile(*infile)
	if err != nil {
		fail(err)
	}
	var input inputEnvelope
	if err = json.Unmarshal(data, &input); err != nil {
		fail(err)
	}
	request := &proto.RaidSimRequest{}
	if err = protojson.Unmarshal(input.Request, request); err != nil {
		fail(err)
	}
	if request.SimOptions == nil || request.SimOptions.Ruleset != proto.Ruleset_RulesetForever {
		fail(fmt.Errorf("R2 runner requires explicit RulesetForever"))
	}
	if request.SimOptions.Iterations < 1 {
		fail(fmt.Errorf("iterations must be positive"))
	}
	for _, id := range input.DisableItemEffects {
		if err = core.WOWFSDisableItemEffect(id); err != nil {
			fail(err)
		}
	}
	for _, set := range input.DisableSetBonuses {
		if err = core.WOWFSDisableSetBonus(set.Name, set.Pieces); err != nil {
			fail(err)
		}
	}
	result := core.RunRaidSim(request)
	output, err := protojson.MarshalOptions{EmitUnpopulated: true}.Marshal(result)
	if err != nil {
		fail(err)
	}
	write(*outfile, output)
	if result.Error != nil && result.Error.Message != "" {
		fail(fmt.Errorf("native engine error: %s", result.Error.Message))
	}
}
