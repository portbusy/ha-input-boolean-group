"""Core logic and entity setup for the Input Boolean Group helper."""
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_ALL_MODE,
    ATTR_ENTITIES_OFF,
    ATTR_ENTITIES_ON,
    ATTR_ENTITY_IDS,
    ATTR_MODE,
    CONF_ALL_MODE,
    CONF_CONDITIONS,
    CONF_ENTITIES,
    CONF_ENTITIES_OFF,
    CONF_ENTITIES_ON,
    CONF_MODE,
    DOMAIN,
    MODE_ALL,
    MODE_ANY,
    MODE_CONDITIONS,
    MODE_UNION,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def _extract_entity_ids_from_conditions(conditions: list[dict]) -> list[str]:
    """Recursively collect every entity_id referenced inside a condition list."""
    entity_ids: set[str] = set()

    def _scan(obj: Any) -> None:
        if isinstance(obj, dict):
            raw = obj.get("entity_id")
            if isinstance(raw, str):
                entity_ids.add(raw)
            elif isinstance(raw, list):
                entity_ids.update(e for e in raw if isinstance(e, str))
            for v in obj.values():
                _scan(v)
        elif isinstance(obj, list):
            for item in obj:
                _scan(item)

    _scan(conditions)
    return list(entity_ids)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Initialize the Input Boolean Group component."""
    component = EntityComponent[InputBooleanGroup](_LOGGER, DOMAIN, hass)
    hass.data[DOMAIN] = component

    component.async_register_entity_service(SERVICE_TURN_ON, {}, "async_turn_on")
    component.async_register_entity_service(SERVICE_TURN_OFF, {}, "async_turn_off")
    component.async_register_entity_service(SERVICE_TOGGLE, {}, "async_toggle")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up an Input Boolean Group from a config entry."""
    component: EntityComponent[InputBooleanGroup] = hass.data[DOMAIN]

    def _get(key: str, default: Any = None) -> Any:
        return entry.options.get(key, entry.data.get(key, default))

    # Resolve mode, migrating legacy all_mode if needed
    if CONF_MODE in entry.options or CONF_MODE in entry.data:
        mode = _get(CONF_MODE, MODE_ANY)
    else:
        mode = MODE_ALL if _get(CONF_ALL_MODE, False) else MODE_ANY

    entity = InputBooleanGroup(
        unique_id=entry.entry_id,
        name=entry.data["name"],
        icon=entry.data.get("icon"),
        mode=mode,
        entity_ids=_get(CONF_ENTITIES, []),
        entities_on=_get(CONF_ENTITIES_ON, []),
        entities_off=_get(CONF_ENTITIES_OFF, []),
        conditions=_get(CONF_CONDITIONS, []),
    )

    await component.async_add_entities([entity])
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of a config entry."""
    component: EntityComponent[InputBooleanGroup] = hass.data[DOMAIN]

    entity = next(
        (ent for ent in component.entities if ent.unique_id == entry.entry_id), None
    )
    if entity:
        await component.async_remove_entity(entity.entity_id)

    return True


class InputBooleanGroup(RestoreEntity):
    """Representation of a group of input_boolean entities."""

    _attr_should_poll = False

    def __init__(
        self,
        unique_id: str,
        name: str,
        icon: str | None,
        mode: str,
        entity_ids: list[str],
        entities_on: list[str],
        entities_off: list[str],
        conditions: list[dict],
    ) -> None:
        """Initialize the group."""
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._attr_icon = icon or "mdi:toggle-switch-outline"
        self._mode = mode
        self._entity_ids = entity_ids
        self._entities_on = entities_on
        self._entities_off = entities_off
        self._conditions = conditions
        self._is_on = False
        self._unsub_state_changed: callback | None = None

    @property
    def _all_tracked_ids(self) -> list[str]:
        """Deduplicated list of all entity IDs to monitor for state changes."""
        if self._mode == MODE_CONDITIONS:
            # Entities are embedded inside the condition configs
            return _extract_entity_ids_from_conditions(self._conditions)

        seen: set[str] = set()
        result: list[str] = []
        for eid in self._entity_ids + self._entities_on + self._entities_off:
            if eid not in seen:
                seen.add(eid)
                result.append(eid)
        return result

    @property
    def state(self) -> str:
        """Return the group state as on/off."""
        return STATE_ON if self._is_on else "off"

    @property
    def is_on(self) -> bool:
        """Return True if the group is on."""
        return self._is_on

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose mode-specific member IDs and current mode."""
        attrs: dict[str, Any] = {
            ATTR_MODE: self._mode,
            ATTR_ALL_MODE: self._mode == MODE_ALL,  # backward compat
        }
        if self._mode == MODE_UNION:
            attrs[ATTR_ENTITIES_ON] = self._entities_on
            attrs[ATTR_ENTITIES_OFF] = self._entities_off
        elif self._mode == MODE_CONDITIONS:
            attrs[ATTR_ENTITY_IDS] = self._all_tracked_ids
        else:
            attrs[ATTR_ENTITY_IDS] = self._entity_ids
        return attrs

    async def async_added_to_hass(self) -> None:
        """Subscribe to member state changes when added to hass."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._is_on = last_state.state == STATE_ON

        self._async_start_tracking()
        await self._async_update_and_write()

    @callback
    def _async_start_tracking(self) -> None:
        """Start listening to state changes for all tracked member entities."""
        tracked = self._all_tracked_ids
        if not tracked:
            return

        @callback
        def _async_state_changed(event: Event) -> None:
            self.hass.async_create_task(self._async_update_and_write())

        self._unsub_state_changed = async_track_state_change_event(
            self.hass, tracked, _async_state_changed
        )

    async def _async_update_and_write(self) -> None:
        """Recompute group state, evaluate conditions, then push to HA."""
        if self._mode == MODE_CONDITIONS:
            # State is determined entirely by conditions
            self._is_on = await self._async_check_conditions() if self._conditions else False
        else:
            self._async_compute_base_state()
            if self._is_on and self._conditions:
                self._is_on = await self._async_check_conditions()
        self.async_write_ha_state()

    @callback
    def _async_compute_base_state(self) -> None:
        """Compute _is_on from member entity states (sync, no conditions)."""
        if self._mode == MODE_UNION:
            self._is_on = self._compute_union_state()
        else:
            self._compute_any_all_state()

    @callback
    def _compute_any_all_state(self) -> None:
        """Evaluate any/all aggregation over self._entity_ids."""
        states: list[bool] = []
        for eid in self._entity_ids:
            state = self.hass.states.get(eid)
            if state is not None and state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                states.append(state.state == STATE_ON)

        if not states:
            self._is_on = False
            return

        self._is_on = all(states) if self._mode == MODE_ALL else any(states)

    def _compute_union_state(self) -> bool:
        """Return True when entities_on are all ON and entities_off are all OFF."""
        if not self._entities_on and not self._entities_off:
            return False

        for eid in self._entities_on:
            state = self.hass.states.get(eid)
            if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                return False
            if state.state != STATE_ON:
                return False

        for eid in self._entities_off:
            state = self.hass.states.get(eid)
            if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
                return False
            if state.state == STATE_ON:
                return False

        return True

    async def _async_check_conditions(self) -> bool:
        """Evaluate HA automation-style conditions; returns True if all pass."""
        from homeassistant.helpers import condition as cond_helper  # noqa: PLC0415

        try:
            for cond_config in self._conditions:
                check = await cond_helper.async_from_config(self.hass, cond_config)
                if not check(self.hass, None):
                    return False
            return True
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Error evaluating conditions for %s: %s", self.name, err)
            return False

    async def async_will_remove_from_hass(self) -> None:
        """Clean up state tracking on removal."""
        if self._unsub_state_changed is not None:
            self._unsub_state_changed()
            self._unsub_state_changed = None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the group.

        In union mode: set entities_on → ON, entities_off → OFF.
        In any/all mode: turn on all member entities.
        In conditions mode: no-op (state is read-only, driven by conditions).
        """
        if self._mode == MODE_CONDITIONS:
            return
        if self._mode == MODE_UNION:
            if self._entities_on:
                await self.hass.services.async_call(
                    "input_boolean",
                    SERVICE_TURN_ON,
                    {ATTR_ENTITY_ID: self._entities_on},
                    blocking=True,
                )
            if self._entities_off:
                await self.hass.services.async_call(
                    "input_boolean",
                    SERVICE_TURN_OFF,
                    {ATTR_ENTITY_ID: self._entities_off},
                    blocking=True,
                )
        else:
            await self.hass.services.async_call(
                "input_boolean",
                SERVICE_TURN_ON,
                {ATTR_ENTITY_ID: self._entity_ids},
                blocking=True,
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the group.

        In union mode: invert the union condition (entities_on → OFF, entities_off → ON).
        In any/all mode: turn off all member entities.
        In conditions mode: no-op (state is read-only, driven by conditions).
        """
        if self._mode == MODE_CONDITIONS:
            return
        if self._mode == MODE_UNION:
            if self._entities_on:
                await self.hass.services.async_call(
                    "input_boolean",
                    SERVICE_TURN_OFF,
                    {ATTR_ENTITY_ID: self._entities_on},
                    blocking=True,
                )
            if self._entities_off:
                await self.hass.services.async_call(
                    "input_boolean",
                    SERVICE_TURN_ON,
                    {ATTR_ENTITY_ID: self._entities_off},
                    blocking=True,
                )
        else:
            await self.hass.services.async_call(
                "input_boolean",
                SERVICE_TURN_OFF,
                {ATTR_ENTITY_ID: self._entity_ids},
                blocking=True,
            )

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the group state."""
        if self._is_on:
            await self.async_turn_off()
        else:
            await self.async_turn_on()
