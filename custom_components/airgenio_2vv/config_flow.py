"""Config flow for the 2VV AirGENIO integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from modbus_connection import ModbusTcpParams

from .const import (
    CONF_MODEL,
    CONF_UNIT_ID,
    CONFIG_ENTRY_VERSION,
    DEFAULT_MODEL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UNIT_ID,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    MODEL_NAMES,
    REG_STATUS_GLOBAL,
)
from .modbus_client import (
    AirgenioConnectionError,
    AirgenioModbusClient,
    AirgenioModbusError,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=247)
        ),
        vol.Required(CONF_MODEL, default=DEFAULT_MODEL): vol.In(MODEL_NAMES),
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
        ),
    }
)


async def _validate_connection(
    hass: HomeAssistant, user_input: dict[str, Any]
) -> str | None:
    """Try to reach the unit; return an error key or None on success."""
    try:
        params = ModbusTcpParams(
            host=user_input[CONF_HOST], port=user_input[CONF_PORT]
        )
        async with async_get_temporary_unit(
            hass, params, user_input[CONF_UNIT_ID]
        ) as unit:
            client = AirgenioModbusClient(unit)
            await client.read_input(REG_STATUS_GLOBAL, 1)
    except AirgenioConnectionError:
        return "cannot_connect"
    except AirgenioModbusError:
        return "invalid_response"
    except Exception:
        _LOGGER.exception("Unexpected error validating connection")
        return "unknown"
    return None


class AirgenioConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the UI config flow."""

    VERSION = CONFIG_ENTRY_VERSION

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: Any) -> AirgenioOptionsFlow:
        """Return the options flow handler."""
        return AirgenioOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match(
                {
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_PORT: user_input[CONF_PORT],
                    CONF_UNIT_ID: user_input[CONF_UNIT_ID],
                }
            )
            unique_id = (
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                f":{user_input[CONF_UNIT_ID]}"
            )
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            error = await _validate_connection(self.hass, user_input)
            if error is None:
                return self.async_create_entry(
                    title=f"AirGENIO {user_input[CONF_HOST]}",
                    data=user_input,
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA, user_input
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            error = await _validate_connection(self.hass, user_input)
            if error is None:
                unique_id = (
                    f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                    f":{user_input[CONF_UNIT_ID]}"
                )
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_mismatch(reason="already_configured")
                return self.async_update_reload_and_abort(
                    entry, data_updates=user_input
                )
            errors["base"] = error

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA, user_input or dict(entry.data)
            ),
            errors=errors,
        )


class AirgenioOptionsFlow(OptionsFlowWithReload):
    """Handle the options flow (scan interval)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
