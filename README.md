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
- 🔀 **Any / All mode**: Group is `on` when *any* member is on (default), or only when *all* are on
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
3. Enter a name, select your `input_boolean` entities, and choose the aggregation mode
4. The group entity appears as `input_boolean_group.<name>`

### Aggregation Modes

| Mode | Group is ON when… |
|------|-------------------|
| **Any** (default) | At least one member is `on` |
| **All** | All members are `on` |

### Services

| Service | Description |
|---------|-------------|
| `input_boolean_group.turn_on` | Turns on all members |
| `input_boolean_group.turn_off` | Turns off all members |
| `input_boolean_group.toggle` | Toggles all members |

### Editing

Click the group entity → gear icon → **Configure** to change members or mode.

## License

MIT