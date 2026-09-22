"""Regression coverage for Home Assistant's current condition API."""

from copy import deepcopy
from datetime import timedelta
from unittest.mock import patch

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers import area_registry as ar, condition as cond_helper
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.input_boolean_group import (
    InputBooleanGroup,
    _normalize_conditions,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.input_boolean_group.config_flow import (
    InputBooleanGroupConfigFlow,
    InputBooleanGroupOptionsFlowHandler,
)
from custom_components.input_boolean_group.const import DOMAIN


def state_condition(entity_id="input_boolean.a", state="on", **kwargs):
    return {"condition": "state", "entity_id": entity_id, "state": state, **kwargs}


async def add_group(hass, conditions=None, *, mode="conditions", **kwargs):
    group = InputBooleanGroup(
        unique_id="test_group",
        name="Test group",
        icon=None,
        mode=mode,
        entity_ids=kwargs.get("entity_ids", []),
        entities_on=kwargs.get("entities_on", []),
        entities_off=kwargs.get("entities_off", []),
        conditions=_normalize_conditions(conditions or []),
    )
    await hass.data[DOMAIN].async_add_entities([group])
    await hass.async_block_till_done()
    assert hass.states.get(group.entity_id) is not None
    return group


@pytest.mark.parametrize("behavior,expected", [("any", "on"), ("all", "off")])
async def test_native_switch_behavior(hass, behavior, expected):
    """The condition editor's any/all option must survive normalization."""
    hass.states.async_set("input_boolean.a", "on")
    hass.states.async_set("input_boolean.b", "off")
    raw = {
        "condition": "switch.is_on",
        "target": {"entity_id": ["input_boolean.a", "input_boolean.b"]},
        "options": {"behavior": behavior, "for": "00:00:00"},
    }
    original = deepcopy(raw)
    group = await add_group(hass, [raw])
    assert hass.states.get(group.entity_id).state == expected
    assert raw == original

    hass.states.async_set("input_boolean.b", "on")
    await hass.async_block_till_done()
    assert hass.states.get(group.entity_id).state == "on"


async def test_native_condition_preserves_mixed_target_and_metadata(hass):
    """Saving must preserve area selection, aliases and disabled state."""
    raw = {
        "condition": "switch.is_off",
        "alias": "Evening switches",
        "enabled": False,
        "target": {"entity_id": "input_boolean.a", "area_id": "living_room"},
        "options": {"behavior": "any", "for": {"minutes": 2}},
    }
    assert _normalize_conditions([raw]) == [raw]


@pytest.mark.parametrize(
    "conditions",
    [
        [state_condition(enabled=False), state_condition(state="off")],
        [{"condition": "and", "conditions": [state_condition(enabled=False), state_condition(state="off")]}],
        [{"condition": "or", "conditions": [state_condition(enabled=False), state_condition(state="off")]}],
        [{"condition": "not", "conditions": [state_condition(enabled=False), state_condition()]}],
        [{"condition": "and", "enabled": False, "conditions": [state_condition()]}],
        [{"condition": "switch.is_on", "enabled": False, "target": {"entity_id": "input_boolean.a"}, "options": {"behavior": "any"}}],
    ],
)
async def test_disabled_conditions_follow_ha_semantics(hass, conditions):
    """A disabled condition is ignored, including inside logical blocks."""
    hass.states.async_set("input_boolean.a", "off")
    group = await add_group(hass, conditions)
    assert hass.states.get(group.entity_id).state == "on"


@pytest.mark.parametrize("nested", [False, True])
async def test_condition_checkers_unload_when_group_is_removed(hass, nested):
    """Removal releases every checker, including resources held by nested leaves."""
    hass.states.async_set("input_boolean.a", "on")
    raw = state_condition()
    if nested:
        raw = {"condition": "and", "conditions": [{"condition": "or", "conditions": [raw]}]}
    with patch.object(cond_helper, "async_from_config", wraps=cond_helper.async_from_config) as compile_check:
        group = await add_group(hass, [raw])
        assert compile_check.await_count == 1
    checker = group._condition_checks[0]
    # A native leaf has an unload method; logical closures own their leaves
    # through the removal callbacks registered on the entity.
    with patch.object(cond_helper.LegacyConditionChecker, "_async_unload") as unload:
        await hass.data[DOMAIN].async_remove_entity(group.entity_id)
        assert unload.call_count == 1
    if not nested:
        assert checker._unloaded


async def test_legacy_callable_without_unload_remains_supported(hass):
    """Older Home Assistant versions return ordinary condition functions."""
    with patch.object(cond_helper, "async_from_config", return_value=lambda h, v: True):
        group = await add_group(hass, [state_condition()])
    assert hass.states.get(group.entity_id).state == "on"
    await hass.data[DOMAIN].async_remove_entity(group.entity_id)


async def test_invalid_nested_condition_is_still_skipped(hass, caplog):
    hass.states.async_set("input_boolean.a", "on")
    group = await add_group(hass, [{
        "condition": "and",
        "conditions": [state_condition(), {"condition": "switch.nonexistent"}],
    }])
    assert hass.states.get(group.entity_id).state == "on"
    assert "condition skipped (compile error)" in caplog.text


@pytest.mark.parametrize("mode,expected", [("any", "on"), ("all", "off"), ("union", "on")])
async def test_base_modes_and_member_updates(hass, mode, expected):
    hass.states.async_set("input_boolean.a", "on")
    hass.states.async_set("input_boolean.b", "off")
    group = await add_group(
        hass,
        mode=mode,
        entity_ids=["input_boolean.a", "input_boolean.b"],
        entities_on=["input_boolean.a"],
        entities_off=["input_boolean.b"],
    )
    assert hass.states.get(group.entity_id).state == expected
    hass.states.async_set("input_boolean.a", "off")
    await hass.async_block_till_done()
    assert hass.states.get(group.entity_id).state == "off"


async def test_template_condition(hass):
    hass.states.async_set("input_boolean.a", "off")
    group = await add_group(hass, [{
        "condition": "template",
        "value_template": {"template": "{{ is_state('input_boolean.a', 'on') }}"},
    }])
    assert hass.states.get(group.entity_id).state == "off"
    hass.states.async_set("input_boolean.a", "on")
    await hass.async_block_till_done()
    assert hass.states.get(group.entity_id).state == "on"


async def add_entry(hass, data):
    entry = ConfigEntry(
        domain=DOMAIN,
        title="Configured group",
        data=data,
        options={},
        source="user",
        version=1,
        minor_version=1,
        unique_id=None,
        discovery_keys={},
        subentries_data=[],
    )
    # Store a real config entry without bootstrapping unrelated integrations.
    with patch.object(hass.config_entries, "async_setup", return_value=True):
        await hass.config_entries.async_add(entry)
    return entry


async def test_area_condition_tracks_child_devices(hass):
    """HA 2026.9 child devices inherit their parent's area."""
    entry = await add_entry(hass, {})
    area = ar.async_get(hass).async_create("Living room")
    devices = dr.async_get(hass)
    parent = devices.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "parent")},
    )
    devices.async_update_device(parent.id, area_id=area.id)
    child = devices.async_get_or_create_child(
        config_entry_id=entry.entry_id,
        parent_device_id=parent.id,
        identifiers={(DOMAIN, "child")},
    )
    member = er.async_get(hass).async_get_or_create(
        "input_boolean", DOMAIN, "child_switch",
        config_entry=entry, device_id=child.id,
    )
    hass.states.async_set(member.entity_id, "off")
    group = await add_group(hass, [{
        "condition": "switch.is_on",
        "target": {"area_id": area.id},
        "options": {"behavior": "any"},
    }])
    assert member.entity_id in group.extra_state_attributes["entity_id"]
    assert hass.states.get(group.entity_id).state == "off"
    hass.states.async_set(member.entity_id, "on")
    await hass.async_block_till_done()
    assert hass.states.get(group.entity_id).state == "on"


@pytest.mark.parametrize("nested", [False, True])
async def test_duration_listeners_released_on_removal(hass, nested):
    """A native condition with active duration tracking must release listeners."""
    hass.states.async_set("climate.room", "heat")
    raw = {
        "condition": "climate.is_hvac_mode",
        "target": {"entity_id": "climate.room"},
        "options": {"behavior": "any", "hvac_mode": ["heat", "cool"], "for": {"minutes": 5}},
    }
    if nested:
        raw = {"condition": "and", "conditions": [raw]}
    checkers = []
    original_compile = cond_helper.async_from_config

    async def capture_checker(*args, **kwargs):
        checker = await original_compile(*args, **kwargs)
        checkers.append(checker)
        return checker

    with patch.object(cond_helper, "async_from_config", side_effect=capture_checker):
        group = await add_group(hass, [raw])
    assert len(checkers) == 1
    checker = checkers[0]
    assert checker._on_unload
    assert "climate.room" in checker._valid_since
    await hass.data[DOMAIN].async_remove_entity(group.entity_id)
    assert checker._unloaded
    assert not checker._on_unload
    hass.states.async_set("climate.room", "off")
    await hass.async_block_till_done()
    assert "climate.room" in checker._valid_since


async def test_legacy_native_condition_compiles_as_state(hass):
    """The older API still works for input_booleans without enabling Labs."""
    hass.states.async_set("input_boolean.a", "on")
    hass.states.async_set("input_boolean.b", "off")
    raw = {
        "condition": "switch.is_on",
        "target": {"entity_id": ["input_boolean.a", "input_boolean.b"]},
        "options": {"behavior": "any", "for": "00:00:00"},
    }
    with (
        patch.object(cond_helper.Condition, "async_get_checker", create=True),
        patch.object(cond_helper, "async_from_config", wraps=cond_helper.async_from_config) as compile_check,
    ):
        group = await add_group(hass, [raw])
    compiled_config = compile_check.call_args.args[1]
    assert compiled_config["condition"] == "state"
    assert compiled_config["match"] == "any"
    assert compiled_config["for"] == timedelta(0)
    assert group._conditions == [raw]
    assert hass.states.get(group.entity_id).state == "on"


async def test_config_entry_and_options_flow(hass):
    """Creating, configuring and unloading a helper use supported HA APIs."""
    hass.states.async_set("input_boolean.a", "on")
    flow = InputBooleanGroupConfigFlow()
    flow.hass = hass
    form = await flow.async_step_user({"name": "Configured group", "mode": "conditions"})
    assert form["step_id"] == "conditions"
    raw = {"condition": "switch.is_on", "target": {"entity_id": "input_boolean.a"}, "options": {"behavior": "any"}}
    selected = form["data_schema"]({"conditions": [raw]})
    result = await flow.async_step_conditions(selected)
    entry = await add_entry(hass, result["data"])
    assert await async_setup_entry(hass, entry)
    group = next(iter(hass.data[DOMAIN].entities))
    assert er.async_get(hass).async_get(group.entity_id).config_entry_id == entry.entry_id
    assert hass.states.get(group.entity_id).state == "on"

    options = InputBooleanGroupOptionsFlowHandler()
    options.hass = hass
    options.handler = entry.entry_id
    form = await options.async_step_init({"mode": "conditions"})
    assert form["step_id"] == "conditions"
    updated = await options.async_step_conditions({"conditions": [raw]})
    assert updated["data"]["conditions"] == [raw]
    assert await async_unload_entry(hass, entry)
    assert not list(hass.data[DOMAIN].entities)


async def test_group_services_use_real_service_registry(hass):
    """Registered group services still propagate to their members."""
    hass.states.async_set("input_boolean.a", "off")

    @callback
    def member_service(call):
        for entity_id in call.data["entity_id"]:
            hass.states.async_set(entity_id, "on" if call.service == "turn_on" else "off")

    for service in ("turn_on", "turn_off"):
        hass.services.async_register("input_boolean", service, member_service)
    group = await add_group(hass, mode="any", entity_ids=["input_boolean.a"])
    for service, expected in (("turn_on", "on"), ("toggle", "off")):
        await hass.services.async_call(DOMAIN, service, {"entity_id": group.entity_id}, blocking=True)
        await hass.async_block_till_done()
        assert hass.states.get("input_boolean.a").state == expected
        assert hass.states.get(group.entity_id).state == expected
