"""Config flow for LUNOS Heat Recovery Ventilation integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)
import voluptuous as vol

from .const import (
    CONF_CONTROLLER_CODING,
    CONF_DEFAULT_SPEED,
    CONF_FAN_COUNT,
    CONF_RELAY_W1,
    CONF_RELAY_W2,
    DEFAULT_CONTROLLER_CODING,
    DEFAULT_NAME,
    DEFAULT_SPEED,
    DOMAIN,
    SPEED_HIGH,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_OFF,
    SPEED_SILENT,
)
from .helpers import get_coding_options, load_lunos_codings

LOG = logging.getLogger(__name__)

CONF_NAME = 'name'


def _build_user_schema(
    coding_options: list[str],
    defaults: dict[str, Any] | None = None,
) -> vol.Schema:
    """Build the schema for user configuration step."""
    defaults = defaults or {}

    return vol.Schema(
        {
            vol.Required(
                CONF_NAME,
                default=defaults.get(CONF_NAME, DEFAULT_NAME),
            ): TextSelector(TextSelectorConfig(type='text')),
            vol.Required(
                CONF_RELAY_W1,
                default=defaults.get(CONF_RELAY_W1),
            ): EntitySelector(
                EntitySelectorConfig(domain=['switch', 'light']),
            ),
            vol.Required(
                CONF_RELAY_W2,
                default=defaults.get(CONF_RELAY_W2),
            ): EntitySelector(
                EntitySelectorConfig(domain=['switch', 'light']),
            ),
            vol.Required(
                CONF_CONTROLLER_CODING,
                default=defaults.get(CONF_CONTROLLER_CODING, DEFAULT_CONTROLLER_CODING),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=coding_options,
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key='controller_coding',
                ),
            ),
            vol.Optional(
                CONF_FAN_COUNT,
                default=defaults.get(CONF_FAN_COUNT, 2),
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=4,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                ),
            ),
            vol.Optional(
                CONF_DEFAULT_SPEED,
                default=defaults.get(CONF_DEFAULT_SPEED, DEFAULT_SPEED),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SPEED_OFF,
                        SPEED_SILENT,
                        SPEED_LOW,
                        SPEED_MEDIUM,
                        SPEED_HIGH,
                    ],
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key='fan_speed',
                ),
            ),
        }
    )


class LunosConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LUNOS."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._coding_config: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        # load coding configurations
        if not self._coding_config:
            self._coding_config = await self.hass.async_add_executor_job(load_lunos_codings)

        coding_options = get_coding_options(self._coding_config)

        if user_input is not None:
            # validate relays are different
            if user_input[CONF_RELAY_W1] == user_input[CONF_RELAY_W2]:
                errors['base'] = 'same_relay'
            else:
                # check for unique config entry
                await self.async_set_unique_id(
                    f'{user_input[CONF_RELAY_W1]}_{user_input[CONF_RELAY_W2]}'
                )
                self._abort_if_unique_id_configured()

                # convert fan_count to int (NumberSelector returns float)
                user_input[CONF_FAN_COUNT] = int(user_input.get(CONF_FAN_COUNT, 2))

                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id='user',
            data_schema=_build_user_schema(coding_options),
            errors=errors,
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> FlowResult:
        """Handle import from YAML configuration."""
        # convert old LUNOS_DOMAIN to DOMAIN if needed
        name = import_data.get(CONF_NAME, DEFAULT_NAME)

        # check for unique config entry based on relays
        relay_w1 = import_data.get(CONF_RELAY_W1)
        relay_w2 = import_data.get(CONF_RELAY_W2)

        if not relay_w1 or not relay_w2:
            LOG.error('YAML import requires both relay_w1 and relay_w2')
            return self.async_abort(reason='missing_relays')

        await self.async_set_unique_id(f'{relay_w1}_{relay_w2}')
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=name,
            data={
                CONF_NAME: name,
                CONF_RELAY_W1: relay_w1,
                CONF_RELAY_W2: relay_w2,
                CONF_CONTROLLER_CODING: import_data.get(
                    CONF_CONTROLLER_CODING, DEFAULT_CONTROLLER_CODING
                ),
                CONF_FAN_COUNT: int(import_data.get(CONF_FAN_COUNT, 2)),
                CONF_DEFAULT_SPEED: import_data.get(CONF_DEFAULT_SPEED, DEFAULT_SPEED),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return LunosOptionsFlow(config_entry)


class LunosOptionsFlow(OptionsFlow):
    """Handle LUNOS options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry
        self._coding_config: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        # load coding configurations
        if not self._coding_config:
            self._coding_config = await self.hass.async_add_executor_job(load_lunos_codings)

        coding_options = get_coding_options(self._coding_config)

        if user_input is not None:
            # validate relays are different
            if user_input[CONF_RELAY_W1] == user_input[CONF_RELAY_W2]:
                errors['base'] = 'same_relay'
            else:
                # convert fan_count to int
                user_input[CONF_FAN_COUNT] = int(user_input.get(CONF_FAN_COUNT, 2))

                # update config entry data
                self.hass.config_entries.async_update_entry(
                    self._config_entry,
                    data=user_input,
                )
                return self.async_create_entry(title='', data={})

        # merge current config with defaults
        current_data = dict(self._config_entry.data)

        return self.async_show_form(
            step_id='init',
            data_schema=_build_user_schema(coding_options, current_data),
            errors=errors,
        )
