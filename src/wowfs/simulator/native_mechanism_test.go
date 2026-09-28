package core

import (
	"math"
	"testing"
	"time"
)

func TestWOWFSSharedExtraMeleeCooldown(t *testing.T) {
	if err := WOWFSConfigureExtraMeleeCooldown(2); err != nil {
		t.Fatal(err)
	}
	aa := &AutoAttacks{mh: WeaponAttack{unit: &Unit{Label: "first"}}}
	other := &AutoAttacks{mh: WeaponAttack{unit: &Unit{Label: "second"}}}
	sim := &Simulation{}
	id := ActionID{SpellID: 15494}
	if !WOWFSAdmitExtraMeleeBatch(aa, sim, 2, id) {
		t.Fatal("first two-attack batch must be accepted whole")
	}
	if WOWFSAdmitExtraMeleeBatch(aa, sim, 1, ActionID{SpellID: 15600}) {
		t.Fatal("different source must share the unit's cooldown")
	}
	sim.CurrentTime = 2*time.Second - time.Nanosecond
	if WOWFSAdmitExtraMeleeBatch(aa, sim, 1, id) {
		t.Fatal("cooldown opened before its boundary")
	}
	sim.CurrentTime = 2 * time.Second
	if !WOWFSAdmitExtraMeleeBatch(aa, sim, 1, id) {
		t.Fatal("cooldown must open at exact boundary")
	}
	sim.CurrentTime = 0
	if !WOWFSAdmitExtraMeleeBatch(other, sim, 1, id) {
		t.Fatal("different units must have independent resources")
	}
	WOWFSResetExtraMeleeUnit(aa)
	if !WOWFSAdmitExtraMeleeBatch(aa, sim, 3, id) {
		t.Fatal("new iteration must reset unit resource")
	}
	got := WOWFSGetMechanismTelemetry()
	want := WOWFSBatchCounts{AcceptedBatches: 4, SuppressedBatches: 2, AcceptedRequestedAttacks: 7, SuppressedRequestedAttacks: 2}
	if got.Totals != want {
		t.Fatalf("counts = %+v, want %+v", got.Totals, want)
	}
	if got.MaxRequestedBatchSize != 3 {
		t.Fatalf("lost explicit batch-size limit: %d", got.MaxRequestedBatchSize)
	}
	if got.ByWindow[0] == nil || *got.ByWindow[0] != want {
		t.Fatal("request-time window counts disagree")
	}
}

func TestWOWFSZeroAndInvalidCooldown(t *testing.T) {
	for _, x := range []float64{-1, math.NaN(), math.Inf(1)} {
		if WOWFSConfigureExtraMeleeCooldown(x) == nil {
			t.Fatalf("accepted invalid cooldown %v", x)
		}
	}
	if err := WOWFSConfigureExtraMeleeCooldown(0); err != nil {
		t.Fatal(err)
	}
	aa := &AutoAttacks{mh: WeaponAttack{unit: &Unit{Label: "native"}}}
	for i := 0; i < 3; i++ {
		if !WOWFSAdmitExtraMeleeBatch(aa, &Simulation{}, 2, ActionID{SpellID: 15494}) {
			t.Fatal("zero cooldown suppressed a native request")
		}
	}
	if WOWFSGetMechanismTelemetry().Totals.SuppressedBatches != 0 {
		t.Fatal("zero cooldown suppression counter nonzero")
	}
}
