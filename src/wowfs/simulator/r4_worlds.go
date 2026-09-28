// Optional first-party research worlds; native physics is the zero value.
package core

import (
 "math"
 "time"
 "fmt"
 "github.com/wowsims/classic/sim/core/proto"
)

type R4World struct {
 IndependentOffensiveCooldowns bool `json:"independent_offensive_cooldowns"`
 HeroismExcludesExtraAttacks bool `json:"heroism_excludes_extra_attacks"`
 BlockExtraAttackReentry bool `json:"block_extra_attack_reentry"`
 AllOffensiveSharedSeconds float64 `json:"all_offensive_shared_seconds"`
}

type R4EventCounts struct {
 EligibleHeroismExtraEvents int64 `json:"eligible_heroism_extra_events"`
 SuppressedHeroismExtraEvents int64 `json:"suppressed_heroism_extra_events"`
 ExtraAttackRequestBatches int64 `json:"extra_attack_request_batches"`
 ExtraAttackRequestedCount int64 `json:"extra_attack_requested_count"`
 ReentrantRequestBatches int64 `json:"reentrant_request_batches"`
 SuppressedReentrantBatches int64 `json:"suppressed_reentrant_batches"`
 SuppressedReentrantRequestedCount int64 `json:"suppressed_reentrant_requested_count"`
}

type R4WorldTelemetry struct {
 World R4World `json:"world"`
 Totals R4EventCounts `json:"totals"`
 BySource map[string]*R4EventCounts `json:"by_source"`
 ByTimeWindow map[int64]*R4EventCounts `json:"by_request_time_window"`
 WindowSeconds float64 `json:"window_seconds"`
 IndependentOffensiveRegistrations int64 `json:"independent_offensive_registrations"`
 UnifiedOffensiveRegistrations int64 `json:"unified_offensive_registrations"`
}

var R4ActiveWorld R4World
var r4WorldTelemetry R4WorldTelemetry
var r4OffensiveTimers map[*Unit]*Timer

func R4ConfigureWorld(world R4World) error {
 if world.AllOffensiveSharedSeconds<0 || world.AllOffensiveSharedSeconds>600 || math.IsNaN(world.AllOffensiveSharedSeconds) || math.IsInf(world.AllOffensiveSharedSeconds,0) { return fmt.Errorf("all_offensive_shared_seconds must be finite in [0,600]") }
 if world.AllOffensiveSharedSeconds>0 && world.IndependentOffensiveCooldowns { return fmt.Errorf("independent and unified offensive worlds are mutually exclusive") }
 R4ActiveWorld=world
 r4OffensiveTimers=map[*Unit]*Timer{}
 r4WorldTelemetry=R4WorldTelemetry{World:world,BySource:map[string]*R4EventCounts{},ByTimeWindow:map[int64]*R4EventCounts{},WindowSeconds:10}
 return nil
}

func R4ConfigureSpellSharedResource(unit *Unit,config *SpellConfig) {
 if R4ActiveWorld.AllOffensiveSharedSeconds<=0 || !config.Flags.Matches(SpellFlagOffensiveEquipment) {return}
 timer:=r4OffensiveTimers[unit]
 if timer==nil {timer=unit.NewTimer();r4OffensiveTimers[unit]=timer}
 config.Cast.SharedCD=Cooldown{Timer:timer,Duration:time.Duration(R4ActiveWorld.AllOffensiveSharedSeconds*float64(time.Second))}
 r4WorldTelemetry.UnifiedOffensiveRegistrations++
}

func R4TaggedExtraAttack(id ActionID) bool {return id.OtherID==proto.OtherAction_OtherActionAttack && id.Tag==3}

func r4Counters(sim *Simulation,source string) []*R4EventCounts {
 t:=&r4WorldTelemetry;window:=int64(math.Floor(sim.CurrentTime.Seconds()/t.WindowSeconds))
 if t.BySource[source]==nil {t.BySource[source]=&R4EventCounts{}}
 if t.ByTimeWindow[window]==nil {t.ByTimeWindow[window]=&R4EventCounts{}}
 return []*R4EventCounts{&t.Totals,t.BySource[source],t.ByTimeWindow[window]}
}

func R4AllowHeroismProcEvent(sim *Simulation,spell *Spell) bool {
 if !R4TaggedExtraAttack(spell.ActionID) {return true}
 blocked:=R4ActiveWorld.HeroismExcludesExtraAttacks
 for _,count:=range r4Counters(sim,"heroism_extra_event") {
  count.EligibleHeroismExtraEvents++
  if blocked {count.SuppressedHeroismExtraEvents++}
 }
 if blocked && sim.Log!=nil {spell.Unit.Log(sim,"WOWFS R4 excluded tagged extra-auto from Heroism proc eligibility")}
 return !blocked
}

func R4AllowExtraAttackBatch(aa *AutoAttacks,sim *Simulation,attacks int32,source,trigger ActionID) bool {
 reentry:=R4TaggedExtraAttack(trigger);blocked:=R4ActiveWorld.BlockExtraAttackReentry&&reentry
 for _,count:=range r4Counters(sim,source.String()) {
  count.ExtraAttackRequestBatches++;count.ExtraAttackRequestedCount+=int64(attacks)
  if reentry {count.ReentrantRequestBatches++}
  if blocked {count.SuppressedReentrantBatches++;count.SuppressedReentrantRequestedCount+=int64(attacks)}
 }
 if blocked && sim.Log!=nil {aa.mh.unit.Log(sim,"WOWFS R4 blocked extra-MH reentry batch attacks=%d source=%s trigger=%s",attacks,source,trigger)}
 return !blocked
}

func R4IndependentOffensiveTimer(character *Character) *Timer {
 r4WorldTelemetry.IndependentOffensiveRegistrations++
 return character.NewTimer()
}

func R4GetWorldTelemetry() R4WorldTelemetry {return r4WorldTelemetry}
