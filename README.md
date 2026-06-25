# Input Boolean Group

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

[![Home Assistant Community Forum](https://img.shields.io/badge/Home%20Assistant-Community%20Forum-blue?logo=home-assistant&style=for-the-badge)](https://community.home-assistant.io/t/input-boolean-groups/996318)

A custom Home Assistant integration that lets you **group `input_boolean` entities** into a single controllable entity — directly from the UI.

Home Assistant's built-in Group helper supports lights, switches, binary sensors, covers, fans, and more — but **not `input_boolean`**. This integration fills that gap.

<br>

[![Open Input Boolean Group on Home Assistant Community Store (HACS).](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=portbusy&repository=ha-input-boolean-group&category=integration)



## Features

- 🎛️ **UI-configurable**: Create and edit groups via *Settings → Helpers → Create Helper*
- ⚡ **Live state tracking**: Group state updates instantly when any member changes
- 🔁 **Command forwarding**: `turn_on` / `turn_off` / `toggle` propagates to all members
- 🔀 **Any / All mode**: Group is `on` when *any* member is on, or only when *all* are on
- 🔗 **Union mode**: Specify which entities must be ON and which must be OFF simultaneously
- 🧠 **Conditions mode**: Full OR/AND/NOT logic — same condition editor as automations
- 💾 **State restore**: Survives HA restarts
- 📦 **HACS-compatible**: Easy install via custom repository

## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click the **⋮** menu → **Custom repositories**
3. Add `https://github.com/portbusy/ha-input-boolean-group` as an **Integration**
4. Search for "Input Boolean Group" → Install
5. Restart Home Assistant

### Manual

1. Copy `custom_components/input_boolean_group/` to your HA `custom_components/` directory
2. Restart Home Assistant

## Usage

1. Go to **Settings → Devices & Services → Helpers**
2. Click **Create Helper** → **Input Boolean Group**
3. Enter a name, select your mode, configure the entities
4. The group entity appears as `input_boolean_group.<name>`

### Aggregation Modes

| Mode | Group is ON when… |
|------|-------------------|
| **Any** (default) | At least one member is `on` |
| **All** | Every member is `on` |
| **Union** | All `entities_on` are `on` AND all `entities_off` are `off` |
| **Conditions** | All configured HA conditions evaluate to true |

#### Any / All

Standard aggregation. Select one or more `input_boolean` entities — the group state is computed from all of them.

Unavailable entities are **ignored** in the computation; the group reflects the state of the remaining available members. If all members are unavailable, the group is `off`.

#### Union

Lets you specify two independent lists:

- **Entities ON** — must all be `on` for the group to be `on`
- **Entities OFF** — must all be `off` for the group to be `on`

Both conditions must hold simultaneously. At least one list must be non-empty.

Unavailable entities in either list are **ignored** (same behaviour as Any/All). If all tracked entities are unavailable, the group is `off`.

`turn_on` sets all `entities_on` → `on` and all `entities_off` → `off`.
`turn_off` inverts the above: all `entities_on` → `off` and all `entities_off` → `on`.

#### Conditions

Uses Home Assistant's standard condition editor (the same one available in automations and scripts). You can combine `and`, `or`, `not`, `state`, `numeric_state`, `template`, and any other HA condition type.

The group state is **read-only** in this mode — `turn_on`, `turn_off`, and `toggle` are no-ops. The state is recomputed automatically whenever a referenced entity changes.

If a condition fails to compile at startup, it is **skipped** and an error is logged — the remaining valid conditions still evaluate normally.

### Services

| Service | any/all mode | union mode | conditions mode |
|---------|-------------|------------|----------------|
| `input_boolean_group.turn_on` | All members → `on` | `entities_on` → `on`, `entities_off` → `off` | no-op |
| `input_boolean_group.turn_off` | All members → `off` | `entities_on` → `off`, `entities_off` → `on` | no-op |
| `input_boolean_group.toggle` | Toggles based on current state | Same logic as turn_on/turn_off | no-op |

### State Attributes

The group entity exposes these attributes:

| Attribute | Description |
|-----------|-------------|
| `mode` | Current mode: `any`, `all`, `union`, or `conditions` |
| `all_mode` | `true` if mode is `all` (legacy compatibility) |
| `entity_id` | Tracked entity IDs (any/all/conditions modes) |
| `entities_on` | Entities required to be ON (union mode only) |
| `entities_off` | Entities required to be OFF (union mode only) |

### Editing

Click the group entity → gear icon → **Configure** to change members or mode.

## License

MIT
