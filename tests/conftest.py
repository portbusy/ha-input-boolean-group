"""Run compatibility tests against a real, isolated Home Assistant instance."""

import pytest

from homeassistant import config_entries, loader
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry,
    condition,
    device_registry,
    entity_registry,
    floor_registry,
    frame,
    label_registry,
    restore_state,
)

from custom_components.input_boolean_group import async_setup
from custom_components.input_boolean_group.const import DOMAIN


@pytest.fixture
async def hass(tmp_path):
    """Set up core helpers without booting any external integrations."""
    hass = HomeAssistant(str(tmp_path))
    loader.async_setup(hass)
    frame.async_setup(hass)
    hass.config_entries = config_entries.ConfigEntries(hass, {})
    device_registry.async_setup(hass)
    for registry in (
        floor_registry,
        area_registry,
        label_registry,
        device_registry,
        entity_registry,
        restore_state,
    ):
        await registry.async_load(hass, load_empty=True)
    await condition.async_setup(hass)
    await async_setup(hass, {})
    yield hass
    component = hass.data[DOMAIN]
    for entity in list(component.entities):
        await component.async_remove_entity(entity.entity_id)
    await hass.async_block_till_done()
    await hass.async_stop(force=True)
