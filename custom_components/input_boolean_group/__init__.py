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
    ATTR_ENTITY_IDS,
    CONF_ALL_MODE,
    CONF_ENTITIES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Initialize the Input Boolean Group component."""
    component = EntityComponent[InputBooleanGroup](_LOGGER, DOMAIN, hass)
    hass.data[DOMAIN] = component

    # Register standard switch-like services on the entity
    component.async_register_entity_service(SERVICE_TURN_ON, {}, "async_turn_on")
    component.async_register_entity_service(SERVICE_TURN_OFF, {}, "async_turn_off")
    component.async_register_entity_service(SERVICE_TOGGLE, {}, "async_toggle")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up an Input Boolean Group from a config entry."""
    component: EntityComponent[InputBooleanGroup] = hass.data[DOMAIN]

    entities = entry.options.get(CONF_ENTITIES, entry.data.get(CONF_ENTITIES, []))
    all_mode = entry.options.get(CONF_ALL_MODE, entry.data.get(CONF_ALL_MODE, False))

    entity = InputBooleanGroup(
        unique_id=entry.entry_id,
        name=entry.data["name"],
        entity_ids=entities,
        icon=entry.data.get("icon"),
        all_mode=all_mode,
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
        entity_ids: list[str],
        icon: str | None,
        all_mode: bool,
    ) -> None:
        """Initialize the group."""
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._attr_icon = icon or "mdi:toggle-switch-outline"
        self._entity_ids = entity_ids
        self._all_mode = all_mode
        self._is_on = False
        self._unsub_state_changed: callback | None = None

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

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
        """Expose member entity IDs and mode."""
        return {
            ATTR_ENTITY_IDS: self._entity_ids,
            ATTR_ALL_MODE: self._all_mode,
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_added_to_hass(self) -> None:
        """Subscribe to member state changes when added to hass."""
        await super().async_added_to_hass()

        # Restore previous state on HA restart
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._is_on = last_state.state == STATE_ON

        # Listen for state changes on all member entities
        self._async_start_tracking()

        # Compute the initial state from current member states
        self._async_update_group_state()

    @callback
    def _async_start_tracking(self) -> None:
        """Start tracking state changes for all member entities."""

        @callback
        def _async_state_changed(event: Event) -> None:
            """Handle a member entity state change."""
            self._async_update_group_state()
            self.async_write_ha_state()

        self._unsub_state_changed = async_track_state_change_event(
            self.hass, self._entity_ids, _async_state_changed
        )

    @callback
    def _async_update_group_state(self) -> None:
        """Re-compute the group on/off state from member states."""
        states = []
        for eid in self._entity_ids:
            state = self.hass.states.get(eid)
            if state is not None and state.state not in (
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ):
                states.append(state.state == STATE_ON)

        if not states:
            # All members are unavailable / unknown → group is off
            self._is_on = False
            return

        if self._all_mode:
            self._is_on = all(states)
        else:
            self._is_on = any(states)

    async def async_will_remove_from_hass(self) -> None:
        """Clean up state tracking on removal."""
        if self._unsub_state_changed is not None:
            self._unsub_state_changed()
            self._unsub_state_changed = None

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on all member input_boolean entities."""
        await self.hass.services.async_call(
            "input_boolean",
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: self._entity_ids},
            blocking=True,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off all member input_boolean entities."""
        await self.hass.services.async_call(
            "input_boolean",
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: self._entity_ids},
            blocking=True,
        )

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle all member input_boolean entities."""
        await self.hass.services.async_call(
            "input_boolean",
            SERVICE_TOGGLE,
            {ATTR_ENTITY_ID: self._entity_ids},
            blocking=True,
        )
