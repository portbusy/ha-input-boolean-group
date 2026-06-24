"""Config flow for the Input Boolean Group integration."""
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
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

_MODE_OPTIONS = [
    {
        "value": MODE_ANY,
        "label": "Any — ON if at least one entity is ON",
    },
    {
        "value": MODE_ALL,
        "label": "All — ON only when every entity is ON",
    },
    {
        "value": MODE_UNION,
        "label": "Union — specify which entities must be ON and which OFF",
    },
    {
        "value": MODE_CONDITIONS,
        "label": "Conditions — full OR/AND/NOT logic, like automations",
    },
]


def _entity_selector(multiple: bool = True) -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain="input_boolean", multiple=multiple)
    )


def _condition_selector() -> selector.ConditionSelector:
    return selector.ConditionSelector()


class InputBooleanGroupConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Input Boolean Group."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 1 – name, icon and mode selection."""
        if user_input is not None:
            self._data.update(user_input)
            mode = user_input.get(CONF_MODE, MODE_ANY)
            if mode == MODE_UNION:
                return await self.async_step_union()
            if mode == MODE_CONDITIONS:
                return await self.async_step_conditions()
            return await self.async_step_entities()

        schema = vol.Schema(
            {
                vol.Required("name"): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional("icon"): selector.IconSelector(),
                vol.Required(CONF_MODE, default=MODE_ANY): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=_MODE_OPTIONS)
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2 (any/all) – entity list and optional conditions."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_ENTITIES):
                errors["base"] = "no_entities"
            else:
                self._data.update(user_input)
                return self.async_create_entry(
                    title=self._data["name"], data=self._data
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_ENTITIES): _entity_selector(),
                vol.Optional(CONF_CONDITIONS, default=[]): _condition_selector(),
            }
        )

        return self.async_show_form(
            step_id="entities", data_schema=schema, errors=errors
        )

    async def async_step_union(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2 (union) – entities_on, entities_off and optional conditions."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entities_on = user_input.get(CONF_ENTITIES_ON) or []
            entities_off = user_input.get(CONF_ENTITIES_OFF) or []
            if not entities_on and not entities_off:
                errors["base"] = "no_union_entities"
            else:
                self._data.update(user_input)
                return self.async_create_entry(
                    title=self._data["name"], data=self._data
                )

        schema = vol.Schema(
            {
                vol.Optional(CONF_ENTITIES_ON, default=[]): _entity_selector(),
                vol.Optional(CONF_ENTITIES_OFF, default=[]): _entity_selector(),
                vol.Optional(CONF_CONDITIONS, default=[]): _condition_selector(),
            }
        )

        return self.async_show_form(
            step_id="union", data_schema=schema, errors=errors
        )

    async def async_step_conditions(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2 (conditions) – build OR/AND/NOT logic via condition selector."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_CONDITIONS):
                errors["base"] = "no_conditions"
            else:
                self._data.update(user_input)
                return self.async_create_entry(
                    title=self._data["name"], data=self._data
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_CONDITIONS): _condition_selector(),
            }
        )

        return self.async_show_form(
            step_id="conditions", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return InputBooleanGroupOptionsFlowHandler()


class InputBooleanGroupOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Input Boolean Group."""

    def __init__(self) -> None:
        """Initialize the options flow."""
        self._options: dict[str, Any] = {}

    def _get(self, key: str, default: Any = None) -> Any:
        """Read a value from options, falling back to data, then default."""
        return self.config_entry.options.get(
            key, self.config_entry.data.get(key, default)
        )

    def _current_mode(self) -> str:
        """Return the stored mode, migrating from legacy all_mode if needed."""
        if CONF_MODE in self.config_entry.options or CONF_MODE in self.config_entry.data:
            return self._get(CONF_MODE, MODE_ANY)
        return MODE_ALL if self._get(CONF_ALL_MODE, False) else MODE_ANY

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 1 – mode selection."""
        if user_input is not None:
            self._options.update(user_input)
            mode = user_input.get(CONF_MODE, MODE_ANY)
            if mode == MODE_UNION:
                return await self.async_step_union()
            if mode == MODE_CONDITIONS:
                return await self.async_step_conditions()
            return await self.async_step_entities()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_MODE, default=self._current_mode()
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=_MODE_OPTIONS)
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2 (any/all) – entity list and optional conditions."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_ENTITIES):
                errors["base"] = "no_entities"
            else:
                self._options.update(user_input)
                return self.async_create_entry(title="", data=self._options)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ENTITIES, default=self._get(CONF_ENTITIES, [])
                ): _entity_selector(),
                vol.Optional(
                    CONF_CONDITIONS, default=self._get(CONF_CONDITIONS, [])
                ): _condition_selector(),
            }
        )

        return self.async_show_form(
            step_id="entities", data_schema=schema, errors=errors
        )

    async def async_step_union(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2 (union) – entities_on, entities_off and optional conditions."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entities_on = user_input.get(CONF_ENTITIES_ON) or []
            entities_off = user_input.get(CONF_ENTITIES_OFF) or []
            if not entities_on and not entities_off:
                errors["base"] = "no_union_entities"
            else:
                self._options.update(user_input)
                return self.async_create_entry(title="", data=self._options)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ENTITIES_ON, default=self._get(CONF_ENTITIES_ON, [])
                ): _entity_selector(),
                vol.Optional(
                    CONF_ENTITIES_OFF, default=self._get(CONF_ENTITIES_OFF, [])
                ): _entity_selector(),
                vol.Optional(
                    CONF_CONDITIONS, default=self._get(CONF_CONDITIONS, [])
                ): _condition_selector(),
            }
        )

        return self.async_show_form(
            step_id="union", data_schema=schema, errors=errors
        )

    async def async_step_conditions(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2 (conditions) – build OR/AND/NOT logic via condition selector."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_CONDITIONS):
                errors["base"] = "no_conditions"
            else:
                self._options.update(user_input)
                return self.async_create_entry(title="", data=self._options)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_CONDITIONS, default=self._get(CONF_CONDITIONS, [])
                ): _condition_selector(),
            }
        )

        return self.async_show_form(
            step_id="conditions", data_schema=schema, errors=errors
        )
