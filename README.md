# Input Boolean Group

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![Home Assistant Community Forum](https://img.shields.io/badge/Community-Forum-blue?logo=home-assistant)](https://community.home-assistant.io/t/input-boolean-groups/996318)

Group `input_boolean` entities into a single helper — configurable entirely from the UI, no YAML required.

Home Assistant's built-in Group helper supports lights, switches, covers and more, but not `input_boolean`. This integration fills that gap.

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=portbusy&repository=ha-input-boolean-group&category=integration)

## Installation

**Via HACS (recommended)**

1. Open HACS and go to *Integrations*
2. Click the menu → *Custom repositories* and add `https://github.com/portbusy/ha-input-boolean-group` as an Integration
3. Search for "Input Boolean Group" and install
4. Restart Home Assistant

**Manual**

Copy `custom_components/input_boolean_group/` into your HA `custom_components/` directory and restart.

## Setup

Go to **Settings → Devices & Services → Helpers → Create Helper → Input Boolean Group**, enter a name and choose a mode. The group appears as `input_boolean_group.<name>`.

To edit later: click the entity → gear icon → *Configure*.

## Modes

| Mode | Group is ON when |
|------|-----------------|
| **Any** (default) | At least one member is `on` |
| **All** | Every member is `on` |
| **Union** | All `entities_on` are `on` AND all `entities_off` are `off` |
| **Conditions** | All configured conditions evaluate to true |

Unavailable entities are skipped in all modes. If every tracked entity is unavailable, the group is `off`.

### Any / All

Standard aggregation over a list of `input_boolean` entities. `turn_on` and `turn_off` propagate to all members.

### Union

Two independent lists: entities that must be ON, and entities that must be OFF. Both must be satisfied simultaneously for the group to be ON.

`turn_on` sets all `entities_on` → `on` and all `entities_off` → `off`. `turn_off` inverts this.

### Conditions

Uses Home Assistant's standard condition editor — the same one available in automations. Supports `and`, `or`, `not`, `state`, `numeric_state`, `template`, and any other HA condition type.

The group state is read-only in this mode; `turn_on`, `turn_off` and `toggle` are no-ops. State is recomputed automatically whenever a referenced entity changes. If a condition cannot be compiled at startup, it is skipped and the remaining conditions still apply.

## Services

| Service | any / all | union | conditions |
|---------|-----------|-------|------------|
| `input_boolean_group.turn_on` | All members → `on` | `entities_on` → `on`, `entities_off` → `off` | no-op |
| `input_boolean_group.turn_off` | All members → `off` | `entities_on` → `off`, `entities_off` → `on` | no-op |
| `input_boolean_group.toggle` | Toggles all members | Same logic as turn_on / turn_off | no-op |

## Attributes

| Attribute | Description |
|-----------|-------------|
| `mode` | `any`, `all`, `union`, or `conditions` |
| `all_mode` | `true` when mode is `all` (legacy) |
| `entity_id` | Tracked entity IDs (any / all / conditions modes) |
| `entities_on` | Entities required to be ON (union mode) |
| `entities_off` | Entities required to be OFF (union mode) |

## License

MIT
