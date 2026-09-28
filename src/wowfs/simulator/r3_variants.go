// Research-only native input interventions, compiled in the separate R3 runner.
package core

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math"
	"sort"

	"github.com/wowsims/classic/sim/core/proto"
)

type R3Variant struct {
	ItemID int32 `json:"item_id"`
	WeaponDamageScale *float64 `json:"weapon_damage_scale,omitempty"`
	WeaponDamageMin *float64 `json:"weapon_damage_min,omitempty"`
	WeaponDamageMax *float64 `json:"weapon_damage_max,omitempty"`
	WeaponSpeedSeconds *float64 `json:"weapon_speed_seconds,omitempty"`
	SpeedMode string `json:"speed_mode,omitempty"`
	Stats map[string]float64 `json:"stats,omitempty"`
	ProcPPM *float64 `json:"proc_ppm,omitempty"`
	PeriodicDamagePerTick *float64 `json:"periodic_damage_per_tick,omitempty"`
	TickIntervalSeconds *float64 `json:"tick_interval_seconds,omitempty"`
	NumberOfTicks *int32 `json:"number_of_ticks,omitempty"`
	ProcDamage *float64 `json:"proc_damage,omitempty"`
	ProcDamageMin *float64 `json:"proc_damage_min,omitempty"`
	ProcDamageMax *float64 `json:"proc_damage_max,omitempty"`
	NatureResistanceReduction *float64 `json:"nature_resistance_reduction,omitempty"`
}

type R3AppliedVariant struct {
	Specification R3Variant `json:"specification"`
	IdentitySHA256 string `json:"identity_sha256"`
	Before Item `json:"native_item_before"`
	After Item `json:"research_item_after"`
	NativeBaseDPS float64 `json:"native_base_dps"`
	ResearchBaseDPS float64 `json:"research_base_dps"`
	ResolvedEffects map[string]float64 `json:"resolved_effects"`
}

var r3EffectOverrides = map[int32]map[string]float64{}

// Runtime lookup is necessary: weapon effect factories are registered at init,
// before JSON parameters arrive, and are instantiated when characters are made.
func R3EffectValue(id int32, key string, fallback float64) float64 {
	if fields,ok:=r3EffectOverrides[id];ok {if v,ok:=fields[key];ok{return v}}
	return fallback
}

func R3HasEffectOverride(id int32, key string) bool {
	_, ok := r3EffectOverrides[id][key]
	return ok
}

func r3FiniteNonnegative(x float64) bool {return !math.IsNaN(x)&&!math.IsInf(x,0)&&x>=0}
func r3DPS(item Item) float64 {if item.SwingSpeed<=0{return 0};return (item.WeaponDamageMin+item.WeaponDamageMax)/(2*item.SwingSpeed)}

func R3ConfigureVariants(specs []R3Variant) ([]R3AppliedVariant,error) {
	r3EffectOverrides=map[int32]map[string]float64{}
	out:=make([]R3AppliedVariant,0,len(specs))
	seen:=map[int32]bool{}
	sorted:=append([]R3Variant(nil),specs...)
	sort.Slice(sorted,func(i,j int)bool{return sorted[i].ItemID<sorted[j].ItemID})
	for _,v:=range sorted {
		if seen[v.ItemID] {return nil,fmt.Errorf("duplicate variant item %d",v.ItemID)}
		seen[v.ItemID]=true
		original,ok:=ItemsByID[v.ItemID];if !ok{return nil,fmt.Errorf("unknown item %d",v.ItemID)}
		item:=original
		weaponChange:=v.WeaponDamageScale!=nil||v.WeaponDamageMin!=nil||v.WeaponDamageMax!=nil||v.WeaponSpeedSeconds!=nil
		if weaponChange && (item.SwingSpeed<=0||!item.IsWeapon()) {return nil,fmt.Errorf("item %d is not a damage weapon",v.ItemID)}
		if v.WeaponSpeedSeconds!=nil {
			if !r3FiniteNonnegative(*v.WeaponSpeedSeconds)||*v.WeaponSpeedSeconds==0{return nil,fmt.Errorf("weapon speed must be finite and positive")}
			if v.SpeedMode!="hold_base_dps"&&v.SpeedMode!="hold_damage" {return nil,fmt.Errorf("speed change requires explicit speed_mode")}
			if v.SpeedMode=="hold_base_dps" {
				if v.WeaponDamageMin!=nil||v.WeaponDamageMax!=nil{return nil,fmt.Errorf("absolute damage conflicts with hold_base_dps; use weapon_damage_scale for independent DPS axis")}
				ratio:=*v.WeaponSpeedSeconds/item.SwingSpeed
				item.WeaponDamageMin*=ratio;item.WeaponDamageMax*=ratio
			}
			item.SwingSpeed=*v.WeaponSpeedSeconds
		} else if v.SpeedMode!="" {return nil,fmt.Errorf("speed_mode requires weapon_speed_seconds")}
		if v.WeaponDamageScale!=nil {
			if v.WeaponDamageMin!=nil||v.WeaponDamageMax!=nil{return nil,fmt.Errorf("damage scale and absolute damage overrides are mutually exclusive")}
			if !r3FiniteNonnegative(*v.WeaponDamageScale){return nil,fmt.Errorf("invalid weapon damage scale")}
			item.WeaponDamageMin*=*v.WeaponDamageScale;item.WeaponDamageMax*=*v.WeaponDamageScale
		}
		if v.WeaponDamageMin!=nil{item.WeaponDamageMin=*v.WeaponDamageMin}
		if v.WeaponDamageMax!=nil{item.WeaponDamageMax=*v.WeaponDamageMax}
		if !r3FiniteNonnegative(item.WeaponDamageMin)||!r3FiniteNonnegative(item.WeaponDamageMax)||item.WeaponDamageMax<item.WeaponDamageMin{return nil,fmt.Errorf("invalid weapon damage interval")}
		for name,value:=range v.Stats {
			index,ok:=proto.Stat_value[name]
			if !ok||index<0||int(index)>=len(item.Stats)||!r3FiniteNonnegative(value){return nil,fmt.Errorf("invalid stat override %s=%v",name,value)}
			item.Stats[index]=value
		}
		fields:=map[string]float64{}
		if v.ProcPPM!=nil {
			if v.ItemID!=12795&&v.ItemID!=19019&&v.ItemID!=17068{return nil,fmt.Errorf("PPM hook validated only for Blood Talon, Thunderfury, Deathbringer")}
			fields["proc_ppm"]=*v.ProcPPM
		}
		if v.PeriodicDamagePerTick!=nil||v.TickIntervalSeconds!=nil||v.NumberOfTicks!=nil {
			if v.ItemID!=12795{return nil,fmt.Errorf("periodic hook is Blood Talon only")}
			if v.PeriodicDamagePerTick!=nil{fields["periodic_damage_per_tick"]=*v.PeriodicDamagePerTick}
			if v.TickIntervalSeconds!=nil{
				if *v.TickIntervalSeconds<0.001{return nil,fmt.Errorf("tick interval must be at least 0.001 seconds")}
				fields["tick_interval_seconds"]=*v.TickIntervalSeconds
			}
			if v.NumberOfTicks!=nil{
				if *v.NumberOfTicks<1||*v.NumberOfTicks>100000{return nil,fmt.Errorf("number_of_ticks outside [1,100000]")}
				fields["number_of_ticks"]=float64(*v.NumberOfTicks)
			}
		}
		if v.ProcDamage!=nil||v.NatureResistanceReduction!=nil {
			if v.ItemID!=19019{return nil,fmt.Errorf("proc_damage/resistance hook is Thunderfury only")}
			if v.ProcDamage!=nil{fields["proc_damage"]=*v.ProcDamage}
			if v.NatureResistanceReduction!=nil{fields["nature_resistance_reduction"]=*v.NatureResistanceReduction}
		}
		if v.ProcDamageMin!=nil||v.ProcDamageMax!=nil {
			if v.ItemID!=17068{return nil,fmt.Errorf("proc damage interval hook is Deathbringer only")}
			lo,hi:=110.0,140.0
			if v.ProcDamageMin!=nil{lo=*v.ProcDamageMin};if v.ProcDamageMax!=nil{hi=*v.ProcDamageMax}
			if hi<lo{return nil,fmt.Errorf("invalid proc damage interval")}
			fields["proc_damage_min"]=lo;fields["proc_damage_max"]=hi
		}
		for key,value:=range fields{if !r3FiniteNonnegative(value){return nil,fmt.Errorf("invalid effect parameter %s=%v",key,value)}}
		r3EffectOverrides[v.ItemID]=fields
		resolved:=map[string]float64{}
		switch v.ItemID {
		case 12795:resolved=map[string]float64{"proc_ppm":1,"periodic_damage_per_tick":10,"tick_interval_seconds":3,"number_of_ticks":10}
		case 19019:resolved=map[string]float64{"proc_ppm":6,"proc_damage":300,"nature_resistance_reduction":25}
		case 17068:resolved=map[string]float64{"proc_ppm":1,"proc_damage_min":110,"proc_damage_max":140}
		}
		for key,value:=range fields{resolved[key]=value}
		data,err:=json.Marshal(v);if err!=nil{return nil,err};digest:=sha256.Sum256(data)
		ItemsByID[v.ItemID]=item
		out=append(out,R3AppliedVariant{v,hex.EncodeToString(digest[:]),original,item,r3DPS(original),r3DPS(item),resolved})
	}
	return out,nil
}
