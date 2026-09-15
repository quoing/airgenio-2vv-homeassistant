"""The 2VV AirGENIO integration."""

from __future__ import annotations

import logging

from homeassistant.components.modbus import async_get_unit
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from modbus_connection import ModbusTcpParams

from .const import (
    CONF_MODEL,
    CONF_UNIT_ID,
    CONFIG_ENTRY_VERSION,
    DEFAULT_MODEL,
    REG_INFO_FW_MODULE_A,
)
from .coordinator import Airgenio2vvConfigEntry, AirgenioCoordinator
from .modbus_client import AirgenioModbusClient, AirgenioModbusError

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.FAN,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: Airgenio2vvConfigEntry) -> bool:
    """Set up 2VV AirGENIO from a config entry."""
    unit = async_get_unit(
        hass,
        entry,
        ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
        entry.data[CONF_UNIT_ID],
    )
    client = AirgenioModbusClient(unit)

    # Best-effort firmware version for the device registry.
    try:
        fw = await client.read_input(REG_INFO_FW_MODULE_A, 1)
    except AirgenioModbusError:
        fw = []
    if fw and entry.data.get("sw_version") != f"0x{fw[0]:04X}":
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, "sw_version": f"0x{fw[0]:04X}"}
        )

    coordinator = AirgenioCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: Airgenio2vvConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate existing VENUS entries to the model-aware schema."""
    if entry.version > CONFIG_ENTRY_VERSION:
        return False
    if entry.version == 1:
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_MODEL: DEFAULT_MODEL},
            version=CONFIG_ENTRY_VERSION,
        )
    return True
