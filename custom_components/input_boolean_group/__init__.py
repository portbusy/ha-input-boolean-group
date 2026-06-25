"""Core logic and entity setup for the Input Boolean Group helper."""
import asyncio
import logging
import re
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_HOMEASSISTANT_STARTED,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import condition as cond_helper
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
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

_UNAVAILABLE_STATES = frozenset({STATE_UNAVAILABLE, STATE_UNKNOWN})


def _normalize_conditions(conditions: list[dict]) -> list[dict]:
    """Normalize raw condition dicts to forms accepted by async_from_config.

    Handles several mismatches between the HA frontend condition editor and
    the backend condition schema:

    - state: entity_id as single-item list → string; redundant match:all removed
    - state: state as single-item list → string
    - or/and/not: spurious `mode` key removed
    - template: value_template as {template: "..."} dict → plain string
    - action conditions (domain.is_on / domain.is_off with target/options):
      converted to equivalent classic `state` conditions; the `for` key is
      kept only when non-zero, and only when it's already a timedelta-compatible
      value (HA passes it as a string '00:00:00' which breaks datetime math).

    Called both from config_flow (before saving) and from async_setup_entry
    (at load time, to fix entries saved before normalization was in place).
    """
    result: list[dict] = []
    for raw in conditions:
        cond: dict[str, Any] = dict(raw)
        cond_type = cond.get("condition", "")

        # Action-condition format: domain.is_on / domain.is_off
        # Example: {'condition': 'switch.is_on', 'target': {'entity_id': '...'}, 'options': {...}}
        if isinstance(cond_type, str) and "." in cond_type and "target" in cond:
            target = cond.get("target") or {}
            entity_id = target.get("entity_id")
            options = cond.get("options") or {}
            state_val = (
                "on" if cond_type.endswith(".is_on")
                else "off" if cond_type.endswith(".is_off")
                else None
            )
            if state_val and entity_id:
                new_cond: dict[str, Any] = {
                    "condition": "state",
                    "entity_id": entity_id,
                    "state": state_val,
                }
                for_val = options.get("for")
                # Keep 'for' only when it is a non-zero, timedelta-compatible value.
                # The frontend often emits '00:00:00' which causes datetime - str errors.
                if for_val and for_val not in ("0", "00:00:00", "0:00:00"):
                    new_cond["for"] = for_val
                cond = new_cond
                cond_type = "state"

        if cond_type == "state":
            entity_id = cond.get("entity_id")
            if isinstance(entity_id, list) and len(entity_id) == 1:
                cond["entity_id"] = entity_id[0]
                cond.pop("match", None)
            state = cond.get("state")
            if isinstance(state, list) and len(state) == 1:
                cond["state"] = state[0]
        elif cond_type in ("or", "and", "not"):
            cond.pop("mode", None)
        elif cond_type == "template":
            vt = cond.get("value_template")
            if isinstance(vt, dict) and "template" in vt:
                cond["value_template"] = vt["template"]

        for nested_key in ("conditions", "sequence"):
            nested = cond.get(nested_key)
            if isinstance(nested, list):
                cond[nested_key] = _normalize_conditions(nested)
        result.append(cond)
    return result


# Matches states("entity.id"), is_state("entity.id", ...), state_attr("entity.id", ...)
_TEMPLATE_ENTITY_RE = re.compile(
    r'(?:states|is_state|state_attr)\s*\(\s*["\']([a-z_]+\.[a-z0-9_]+)["\']'
)


def _extract_entity_ids_from_conditions(conditions: list[dict]) -> list[str]:
    """Recursively collect entity IDs referenced inside a condition list.

    Scans both 'entity_id' (singular) and 'entity_ids' (plural) for explicit
    references, and also extracts entities from value_template strings via
    regex so that template-based conditions trigger re-evaluation when any
    referenced entity changes.
    """
    entity_ids: set[str] = set()

    def _scan(obj: Any) -> None:
        if isinstance(obj, dict):
            for key in ("entity_id", "entity_ids"):
                raw = obj.get(key)
                if isinstance(raw, str):
                    entity_ids.add(raw)
                elif isinstance(raw, list):
                    entity_ids.update(e for e in raw if isinstance(e, str))
            # Extract entities referenced inside template strings.
            for key in ("value_template", "template"):
                tmpl = obj.get(key)
                if isinstance(tmpl, str):
                    entity_ids.update(_TEMPLATE_ENTITY_RE.findall(tmpl))
            for v in obj.values():
                _scan(v)
        elif isinstance(obj, list):
            for item in obj:
                _scan(item)

    _scan(conditions)
    return list(entity_ids)


def _build_tracked_ids(
    mode: str,
    entity_ids: list[str],
    entities_on: list[str],
    entities_off: list[str],
    conditions: list[dict],
) -> list[str]:
    """Return the deduplicated entity IDs to track for this mode."""
    if mode == MODE_CONDITIONS:
        return _extract_entity_ids_from_conditions(conditions)
    sources = (entities_on + entities_off) if mode == MODE_UNION else entity_ids
    seen: set[str] = set()
    result: list[str] = []
    for eid in sources:
        if eid not in seen:
            seen.add(eid)
            result.append(eid)
    return result


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Initialize the Input Boolean Group component."""
    component = EntityComponent[InputBooleanGroup](_LOGGER, DOMAIN, hass)
    hass.data[DOMAIN] = component

    component.async_register_entity_service(SERVICE_TURN_ON, {}, "async_turn_on")
    component.async_register_entity_service(SERVICE_TURN_OFF, {}, "async_turn_off")
    component.async_register_entity_service("toggle", {}, "async_toggle")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up an Input Boolean Group from a config entry."""
    component: EntityComponent[InputBooleanGroup] = hass.data[DOMAIN]

    def _get(key: str, default: Any = None) -> Any:
        return entry.options.get(key, entry.data.get(key, default))

    # Resolve mode, migrating legacy all_mode if needed.
    if CONF_MODE in entry.options or CONF_MODE in entry.data:
        mode = _get(CONF_MODE, MODE_ANY)
    else:
        mode = MODE_ALL if _get(CONF_ALL_MODE, False) else MODE_ANY

    raw_conditions = _get(CONF_CONDITIONS, [])
    conditions = _normalize_conditions(raw_conditions)
    if mode == MODE_CONDITIONS:
        _LOGGER.warning("ibg[%s] normalized: %s", entry.data["name"], conditions)

    entity = InputBooleanGroup(
        unique_id=entry.entry_id,
        name=entry.data["name"],
        icon=entry.data.get("icon"),
        mode=mode,
        entity_ids=_get(CONF_ENTITIES, []),
        entities_on=_get(CONF_ENTITIES_ON, []),
        entities_off=_get(CONF_ENTITIES_OFF, []),
        conditions=conditions,
    )

    await component.async_add_entities([entity])

    # EntityComponent does not auto-link entities to their config entry.
    # Without this, the Helpers UI cannot find the options flow for editing
    # and the integration page shows no entity count.
    ent_reg = er.async_get(hass)
    entity_id = entity.entity_id or ent_reg.async_get_entity_id(DOMAIN, DOMAIN, entry.entry_id)
    if entity_id and (ent_entry := ent_reg.async_get(entity_id)):
        if ent_entry.config_entry_id != entry.entry_id:
            ent_reg.async_update_entity(entity_id, config_entry_id=entry.entry_id)

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
        self._update_task: asyncio.Task | None = None

        # Pre-compiled condition callables; populated in async_added_to_hass.
        self._condition_checks: list[Any] = []

        # Cached once: all inputs are immutable after __init__.
        self._tracked_ids: list[str] = _build_tracked_ids(
            mode, entity_ids, entities_on, entities_off, conditions
        )

        # Derived constant exposed as backward-compat attribute.
        self._attr_all_mode: bool = mode == MODE_ALL

    @property
    def state(self) -> str:
        """Return the group state as on/off."""
        return STATE_ON if self._is_on else STATE_OFF

    @property
    def is_on(self) -> bool:
        """Return True if the group is on."""
        return self._is_on

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose mode-specific member IDs and current mode."""
        attrs: dict[str, Any] = {
            ATTR_MODE: self._mode,
            ATTR_ALL_MODE: self._attr_all_mode,
        }
        if self._mode == MODE_UNION:
            attrs[ATTR_ENTITIES_ON] = self._entities_on
            attrs[ATTR_ENTITIES_OFF] = self._entities_off
        else:
            attrs[ATTR_ENTITY_IDS] = self._tracked_ids
        return attrs

    async def async_added_to_hass(self) -> None:
        """Subscribe to member state changes when added to hass."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._is_on = last_state.state == STATE_ON

        # Compile conditions once at setup time to avoid per-event overhead.
        for cond in self._conditions:
            try:
                self._condition_checks.append(
                    await cond_helper.async_from_config(self.hass, cond)
                )
            except Exception as err:  # noqa: BLE001
                _LOGGER.error(
                    "Failed to compile condition for %s: %s — condition skipped",
                    self.name,
                    err,
                )

        if self._mode == MODE_CONDITIONS:
            _LOGGER.warning(
                "ibg[%s] checks compiled: %d/%d",
                self.name, len(self._condition_checks), len(self._conditions),
            )

        self._async_start_tracking()
        await self._async_update_and_write()

        if self._mode == MODE_CONDITIONS:
            # Re-evaluate once HA has fully started: template-referenced entities
            # (e.g. sensors) may not have their state yet during early setup.
            @callback
            def _on_ha_started(_event: Event) -> None:
                self.hass.async_create_task(self._async_update_and_write())

            self.async_on_remove(
                self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_ha_started)
            )

    @callback
    def _async_start_tracking(self) -> None:
        """Start listening to state changes for tracked member entities."""
        if not self._tracked_ids:
            return

        @callback
        def _async_state_changed(event: Event) -> None:
            # Cancel any pending update so rapid changes collapse into one.
            if self._update_task is not None and not self._update_task.done():
                self._update_task.cancel()
            self._update_task = self.hass.async_create_task(
                self._async_update_and_write()
            )

        self._unsub_state_changed = async_track_state_change_event(
            self.hass, self._tracked_ids, _async_state_changed
        )

    async def _async_update_and_write(self) -> None:
        """Recompute group state then push to HA."""
        if self._mode == MODE_CONDITIONS:
            self._is_on = (
                await self._async_check_conditions()
                if self._condition_checks
                else False
            )
        else:
            self._is_on = self._compute_base_state()
        self.async_write_ha_state()

    def _compute_base_state(self) -> bool:
        """Return ON/OFF from member entity states (no conditions)."""
        if self._mode == MODE_UNION:
            return self._compute_union_state()
        return self._compute_any_all_state()

    def _compute_any_all_state(self) -> bool:
        """Evaluate any/all aggregation over self._entity_ids."""
        states: list[bool] = []
        for eid in self._entity_ids:
            state = self.hass.states.get(eid)
            if state is not None and state.state not in _UNAVAILABLE_STATES:
                states.append(state.state == STATE_ON)
        if not states:
            return False
        return all(states) if self._mode == MODE_ALL else any(states)

    def _compute_union_state(self) -> bool:
        """Return True when entities_on are all ON and entities_off are all OFF.

        Unavailable entities are skipped, consistent with any/all mode.
        If all tracked entities are unavailable, returns False.
        """
        if not self._entities_on and not self._entities_off:
            return False

        on_results: list[bool] = []
        for eid in self._entities_on:
            state = self.hass.states.get(eid)
            if state is not None and state.state not in _UNAVAILABLE_STATES:
                on_results.append(state.state == STATE_ON)

        off_results: list[bool] = []
        for eid in self._entities_off:
            state = self.hass.states.get(eid)
            if state is not None and state.state not in _UNAVAILABLE_STATES:
                off_results.append(state.state != STATE_ON)

        if not on_results and not off_results:
            return False

        return all(on_results) and all(off_results)

    async def _async_check_conditions(self) -> bool:
        """Evaluate pre-compiled HA conditions; returns True if all pass."""
        try:
            for i, check in enumerate(self._condition_checks):
                result = check(self.hass, {})
                _LOGGER.warning("ibg[%s] check[%d]=%s", self.name, i, result)
                if not result:
                    return False
            return True
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Error evaluating conditions for %s: %s", self.name, err)
            return False

    async def async_will_remove_from_hass(self) -> None:
        """Clean up state tracking and any pending update task on removal."""
        if self._unsub_state_changed is not None:
            self._unsub_state_changed()
            self._unsub_state_changed = None
        if self._update_task is not None and not self._update_task.done():
            self._update_task.cancel()
            self._update_task = None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the group.

        union mode: entities_on → ON, entities_off → OFF.
        any/all mode: turn on all member entities.
        conditions mode: no-op (state is read-only, driven by conditions).
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
        elif self._entity_ids:
            await self.hass.services.async_call(
                "input_boolean",
                SERVICE_TURN_ON,
                {ATTR_ENTITY_ID: self._entity_ids},
                blocking=True,
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the group.

        union mode: entities_on → OFF, entities_off → ON (inverts the union condition).
        any/all mode: turn off all member entities.
        conditions mode: no-op (state is read-only, driven by conditions).
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
        elif self._entity_ids:
            await self.hass.services.async_call(
                "input_boolean",
                SERVICE_TURN_OFF,
                {ATTR_ENTITY_ID: self._entity_ids},
                blocking=True,
            )

    async def async_toggle(self, **kwargs: Any) -> None:
        """Toggle the group state (no-op in conditions mode)."""
        if self._is_on:
            await self.async_turn_off()
        else:
            await self.async_turn_on()
