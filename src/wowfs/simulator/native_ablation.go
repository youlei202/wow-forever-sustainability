// Copied into the pinned engine's sim/core package by scripts/native_build.sh.
// No native rule changes occur unless the caller requests an explicit ablation.
package core

import "fmt"

// WOWFSDisableItemEffect preserves the item and all of its static attributes,
// including its enchant and set membership. Only its registered effect is off.
func WOWFSDisableItemEffect(id int32) error {
	if _, ok := itemEffects[id]; !ok {
		return fmt.Errorf("item %d has no registered effect to disable", id)
	}
	itemEffects[id] = func(Agent) {}
	return nil
}

// WOWFSDisableSetBonus leaves all other thresholds and static item stats intact.
func WOWFSDisableSetBonus(name string, pieces int32) error {
	for _, set := range sets {
		if set.Name == name {
			if _, ok := set.Bonuses[pieces]; !ok {
				return fmt.Errorf("set %q has no %d-piece bonus", name, pieces)
			}
			set.Bonuses[pieces] = func(Agent) {}
			return nil
		}
	}
	return fmt.Errorf("unknown set %q", name)
}
