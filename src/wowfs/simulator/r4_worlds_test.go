package core

import (
 "testing"
 "time"
 "github.com/wowsims/classic/sim/core/proto"
)

func TestR4DefaultAndIndependentTimer(t *testing.T) {
 if err:=R4ConfigureWorld(R4World{});err!=nil {t.Fatal(err)}
 c:=&Character{}
 if c.GetOffensiveTrinketCD()!=c.GetOffensiveTrinketCD(){t.Fatal("native timer sharing changed")}
 if err:=R4ConfigureWorld(R4World{IndependentOffensiveCooldowns:true});err!=nil {t.Fatal(err)}
 if c.GetOffensiveTrinketCD()==c.GetOffensiveTrinketCD(){t.Fatal("independent registrations still share")}
}

func TestR4UnifiedEquipmentResource(t *testing.T) {
 if err:=R4ConfigureWorld(R4World{AllOffensiveSharedSeconds:60});err!=nil {t.Fatal(err)}
 unit:=&Unit{};other:=&Unit{}
 a:=SpellConfig{Flags:SpellFlagOffensiveEquipment};b:=a;c:=a;ordinary:=SpellConfig{}
 R4ConfigureSpellSharedResource(unit,&a);R4ConfigureSpellSharedResource(unit,&b);R4ConfigureSpellSharedResource(other,&c);R4ConfigureSpellSharedResource(unit,&ordinary)
 if a.Cast.SharedCD.Timer==nil || a.Cast.SharedCD.Timer!=b.Cast.SharedCD.Timer || a.Cast.SharedCD.Timer==c.Cast.SharedCD.Timer {t.Fatal("incorrect per-unit shared resource")}
 if a.Cast.SharedCD.Duration!=60*time.Second || ordinary.Cast.SharedCD.Timer!=nil {t.Fatal("incorrect scope or duration")}
 if err:=R4ConfigureWorld(R4World{AllOffensiveSharedSeconds:60,IndependentOffensiveCooldowns:true});err==nil {t.Fatal("ambiguous worlds accepted")}
}

func TestR4SemanticExtraEventFilters(t *testing.T) {
 extra:=ActionID{OtherID:proto.OtherAction_OtherActionAttack,Tag:3}
 ordinary:=ActionID{OtherID:proto.OtherAction_OtherActionAttack,Tag:1}
 special:=ActionID{SpellID:25286,Tag:3}
 if !R4TaggedExtraAttack(extra)||R4TaggedExtraAttack(ordinary)||R4TaggedExtraAttack(special){t.Fatal("extra event identity too broad")}
 sim:=&Simulation{};unit:=&Unit{}
 R4ConfigureWorld(R4World{HeroismExcludesExtraAttacks:true,BlockExtraAttackReentry:true})
 if R4AllowHeroismProcEvent(sim,&Spell{ActionID:extra,Unit:unit})||!R4AllowHeroismProcEvent(sim,&Spell{ActionID:ordinary,Unit:unit}){t.Fatal("Heroism filter scope")}
 aa:=&AutoAttacks{}
 if R4AllowExtraAttackBatch(aa,sim,2,ActionID{ItemID:11684},extra)||!R4AllowExtraAttackBatch(aa,sim,2,ActionID{ItemID:11684},ordinary){t.Fatal("reentry filter scope")}
 totals:=R4GetWorldTelemetry().Totals
 if totals.SuppressedHeroismExtraEvents!=1||totals.SuppressedReentrantBatches!=1||totals.SuppressedReentrantRequestedCount!=2 {t.Fatal("telemetry counts incorrect",totals)}
}
