package core

import (
	"math"
	"reflect"
	"testing"
)

func TestR3WeaponAxesPreserveOtherItemFields(t *testing.T) {
	original:=ItemsByID[12795]
	defer func(){ItemsByID[12795]=original}()
	speed,scale:=2.2,0.8
	rows,err:=R3ConfigureVariants([]R3Variant{{ItemID:12795,WeaponSpeedSeconds:&speed,SpeedMode:"hold_base_dps",WeaponDamageScale:&scale}})
	if err!=nil{t.Fatal(err)}
	after:=rows[0].After
	if math.Abs(r3DPS(after)-0.8*r3DPS(original))>1e-12{t.Fatal("independent DPS axis did not preserve requested scaling")}
	if after.SwingSpeed!=speed{t.Fatal("speed override not applied")}
	comparison:=after;comparison.SwingSpeed=original.SwingSpeed;comparison.WeaponDamageMin=original.WeaponDamageMin;comparison.WeaponDamageMax=original.WeaponDamageMax
	if !reflect.DeepEqual(comparison,original){t.Fatal("weapon axis changed other native item fields")}
	ItemsByID[12795]=original
	rows,err=R3ConfigureVariants([]R3Variant{{ItemID:12795,WeaponSpeedSeconds:&speed,SpeedMode:"hold_damage"}})
	if err!=nil{t.Fatal(err)}
	if rows[0].After.WeaponDamageMin!=original.WeaponDamageMin||rows[0].After.WeaponDamageMax!=original.WeaponDamageMax{t.Fatal("hold_damage changed min/max")}
}

func TestR3EffectKnobsLeaveStaticItemIntact(t *testing.T) {
	original:=ItemsByID[12795];defer func(){ItemsByID[12795]=original}()
	ppm,damage,interval:=3.0,0.0,1.5;ticks:=int32(20)
	rows,err:=R3ConfigureVariants([]R3Variant{{ItemID:12795,ProcPPM:&ppm,PeriodicDamagePerTick:&damage,TickIntervalSeconds:&interval,NumberOfTicks:&ticks}})
	if err!=nil{t.Fatal(err)}
	if !reflect.DeepEqual(rows[0].After,original){t.Fatal("effect-only variation modified native static attributes")}
	if R3EffectValue(12795,"periodic_damage_per_tick",10)!=0{t.Fatal("explicit zero damage lost")}
	if R3EffectValue(12795,"proc_ppm",1)!=3||R3EffectValue(12795,"number_of_ticks",10)!=20{t.Fatal("effect parameter lookup failed")}
	if R3EffectValue(19019,"proc_damage",300)!=300{t.Fatal("variant leaked into another item")}
}

func TestR3InvalidAndAmbiguousVariantsRejected(t *testing.T) {
	speed,damage:=2.0,10.0
	cases:=[]R3Variant{
		{ItemID:12795,WeaponSpeedSeconds:&speed},
		{ItemID:12795,WeaponSpeedSeconds:&speed,SpeedMode:"hold_base_dps",WeaponDamageMin:&damage},
		{ItemID:19019,PeriodicDamagePerTick:&damage},
		{ItemID:12795,Stats:map[string]float64{"InventedStat":1}},
	}
	for _,v:=range cases{if _,err:=R3ConfigureVariants([]R3Variant{v});err==nil{t.Fatalf("accepted unsupported/ambiguous variant: %+v",v)}}
}
