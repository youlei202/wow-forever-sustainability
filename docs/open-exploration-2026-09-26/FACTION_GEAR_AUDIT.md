# Faction equipment audit — 2026-09-26

The frozen broad-v1 inputs have **8 of 96 worlds with a conflicting database faction tag**, plus **10 of 96 worlds with faction-named PvP items whose database faction field is unspecified**. These are two different findings. Neither changes the actual recorded combat outputs. The same counts hold for broad-v2; the then-present refine-v1 inputs contain 3 strict-tag worlds and 6 PvP-source-question worlds. The catalog-v1 inputs have neither flagged issue.

`FACTION_GEAR_AUDIT.json` and `.csv` in the campaign artifact root enumerate each world, slot, item, role, tag, batch and replacement recommendation. The JSON hashes every scanned frozen JOBS file and the relevant engine source. No original input or result was changed.

## What the engine field means

The pinned engine's `proto/ui.proto:85` puts `FactionRestriction` in **UIItem**, with 0 unspecified, 1 Alliance only, 2 Horde only. `proto/common.proto:858` defines the execution **SimItem** without that field. `sim/core/database.go:46` similarly omits it from `Item`; `NewItem` and `EquipItem` do not validate faction. Therefore this native executable accepts the affected configurations; these are not simulation failures.

`ui/core/player.ts:1212` applies a user-selected faction filter to item search. It does not automatically prohibit a player of a different race from passing that item to simulation. The database field has mixed provenance: `tools/database/wowhead_db.go:352` derives it from a race mask, `tools/database/wago_db.go:27` from item flags, and `tools/database/atlasloot.go:250` from faction-specific acquisition records. Consequently the available field is not sufficient to classify every tagged item as a physical equip ban, a trade ban, or only a source-access limitation in the live Forever server. That live distinction remains unverified.

## Concrete cases

- **12543, Songstone of Ironforge:** explicit Alliance tag and quest source 4363, “The Princess's Surprise.” It appears on Tauren Druid's fixed `finger1` in mana_regen/spell_hit (both strata) and Orc Warlock's fixed `finger2` in onuse_shared_cd/policy_resource (both strata). None is a numerical-override base. This is a definite metadata/acquisition inconsistency for a faction-realistic claim, while remaining valid engine-domain exploratory physics.
- **23258, Champion's Leather Shoulders; 22879, Legionnaire's Leather Chestpiece:** Rogue class allowlist, unspecified faction field, vendor 12792 Lady Palanseer. The Human Rogue worlds use both as fixed preset pieces. Their names and source warrant an acquisition check; names alone do not establish an enforced physical restriction. These are retained as `faction_named_pvp_source_unresolved`, separately from strict tag mismatches.

## Consequence for claims and challenges

Retain the original observations as executed research worlds. Do not present their equipment as verified faction-obtainable loadouts. A separate neutral-equipment robustness challenge can replace 12543 with 19147, 23258 with 16708, and 22879 with 16721, preserving the candidate set, other overrides, thresholds and declared policies. These substitutions alter real stats and sometimes set bonuses, so they are new measured worlds, not cosmetic corrections. Revalidate the full physical cross and use new seeds. If a future replacement involves an overridden ID, record all unaffected base-stat changes as well as preserving the explicit override coordinates.

The actual-catalog generator applies a conservative database-tag filter. Passing that filter means compatible with available metadata, not independent proof of live acquisition or all omitted restrictions.
