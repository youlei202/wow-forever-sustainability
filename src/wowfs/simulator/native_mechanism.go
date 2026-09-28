// Optional research intervention, compiled only in wowfs-native-mechanism.
package core

import (
	"fmt"
	"math"
	"time"
)

type WOWFSBatchCounts struct {
	AcceptedBatches int64 `json:"accepted_batches"`
	SuppressedBatches int64 `json:"suppressed_batches"`
	AcceptedRequestedAttacks int64 `json:"accepted_requested_attacks"`
	SuppressedRequestedAttacks int64 `json:"suppressed_requested_attacks"`
}

type WOWFSMechanismTelemetry struct {
	Policy string `json:"policy"`
	CooldownSeconds float64 `json:"cooldown_seconds"`
	WindowSeconds float64 `json:"window_seconds"`
	MaxRequestedBatchSize int32 `json:"max_requested_batch_size"`
	Totals WOWFSBatchCounts `json:"totals"`
	BySource map[string]*WOWFSBatchCounts `json:"by_source"`
	ByWindow map[int64]*WOWFSBatchCounts `json:"by_request_time_window"`
	ByUnit map[string]*WOWFSBatchCounts `json:"by_unit"`
}

var wowfsExtraMeleeCooldown time.Duration
var wowfsNextExtraMelee = map[*AutoAttacks]time.Duration{}
var wowfsMechanismTelemetry WOWFSMechanismTelemetry

func WOWFSConfigureExtraMeleeCooldown(seconds float64) error {
	if seconds < 0 || math.IsNaN(seconds) || math.IsInf(seconds,0) || seconds > 1e6 {
		return fmt.Errorf("extra-melee cooldown must be finite in [0,1e6] seconds")
	}
	wowfsExtraMeleeCooldown = time.Duration(seconds*float64(time.Second))
	wowfsNextExtraMelee = map[*AutoAttacks]time.Duration{}
	wowfsMechanismTelemetry = WOWFSMechanismTelemetry{
		Policy:"per-unit shared cooldown; entire extra-main-hand generation-request batch; no item-ID list",
		CooldownSeconds:seconds,WindowSeconds:10,
		BySource:map[string]*WOWFSBatchCounts{},ByWindow:map[int64]*WOWFSBatchCounts{},ByUnit:map[string]*WOWFSBatchCounts{},
	}
	return nil
}

func WOWFSResetExtraMeleeUnit(aa *AutoAttacks) { delete(wowfsNextExtraMelee,aa) }

func WOWFSAdmitExtraMeleeBatch(aa *AutoAttacks,sim *Simulation,attacks int32,actionID ActionID) bool {
	next,alreadyAccepted:=wowfsNextExtraMelee[aa]
	accepted:=wowfsExtraMeleeCooldown==0 || !alreadyAccepted || sim.CurrentTime>=next
	if accepted && wowfsExtraMeleeCooldown>0 { wowfsNextExtraMelee[aa]=sim.CurrentTime+wowfsExtraMeleeCooldown }
	t:=&wowfsMechanismTelemetry
	if attacks>t.MaxRequestedBatchSize { t.MaxRequestedBatchSize=attacks }
	source:=actionID.String()
	unit:=aa.mh.unit.LogLabel()
	window:=int64(math.Floor(sim.CurrentTime.Seconds()/t.WindowSeconds))
	if t.BySource[source]==nil { t.BySource[source]=&WOWFSBatchCounts{} }
	if t.ByUnit[unit]==nil { t.ByUnit[unit]=&WOWFSBatchCounts{} }
	if t.ByWindow[window]==nil { t.ByWindow[window]=&WOWFSBatchCounts{} }
	for _,count:=range []*WOWFSBatchCounts{&t.Totals,t.BySource[source],t.ByWindow[window],t.ByUnit[unit]} {
		if accepted { count.AcceptedBatches++;count.AcceptedRequestedAttacks+=int64(attacks)
		} else { count.SuppressedBatches++;count.SuppressedRequestedAttacks+=int64(attacks) }
	}
	if sim.Log!=nil && wowfsExtraMeleeCooldown>0 {
		aa.mh.unit.Log(sim,"WOWFS extra-MH batch accepted=%t attacks=%d source=%s shared_cooldown_seconds=%.6f",accepted,attacks,actionID,wowfsExtraMeleeCooldown.Seconds())
	}
	return accepted
}

func WOWFSGetMechanismTelemetry() WOWFSMechanismTelemetry { return wowfsMechanismTelemetry }
