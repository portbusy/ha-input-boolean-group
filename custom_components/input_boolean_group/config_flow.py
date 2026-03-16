"""Config flow for the Input Boolean Group integration."""
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_ALL_MODE, CONF_ENTITIES, DOMAIN


class InputBooleanGroupConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Input Boolean Group."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial creation step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entities = user_input.get(CONF_ENTITIES, [])

            if not entities:
                errors["base"] = "no_entities"
            else:
                return self.async_create_entry(
                    title=user_input["name"], data=user_input
                )

        schema = vol.Schema(
            {
                vol.Required("name"): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                ),
                vol.Optional("icon"): selector.IconSelector(),
                vol.Required(CONF_ENTITIES): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="input_boolean",
                        multiple=True,
                    )
                ),
                vol.Optional(CONF_ALL_MODE, default=False): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
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

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the group options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entities = user_input.get(CONF_ENTITIES, [])

            if not entities:
                errors["base"] = "no_entities"
            else:
                return self.async_create_entry(title="", data=user_input)

        current_entities = self.config_entry.options.get(
            CONF_ENTITIES, self.config_entry.data.get(CONF_ENTITIES, [])
        )
        current_all_mode = self.config_entry.options.get(
            CONF_ALL_MODE, self.config_entry.data.get(CONF_ALL_MODE, False)
        )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_ENTITIES, default=current_entities
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain="input_boolean",
                        multiple=True,
                    )
                ),
                vol.Optional(
                    CONF_ALL_MODE, default=current_all_mode
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )
