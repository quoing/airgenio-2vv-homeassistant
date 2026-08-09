"""Diagnostics support for the 2VV AirGENIO integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import (
    CONFIG_REGISTERS,
    INFO_BLOCK_COUNT,
    INFO_BLOCK_START,
    SHARE_BLOCK_COUNT,
    SHARE_BLOCK_START,
    STATUS_BLOCK_COUNT,
    STATUS_BLOCK_START,
)
from .coordinator import Airgenio2vvConfigEntry
from .modbus_client import AirgenioModbusError

TO_REDACT = {CONF_HOST}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: Airgenio2vvConfigEntry
) -> dict[str, Any]:
    """Return diagnostics: entry data + decoded snapshot + raw registers."""
    coordinator = entry.runtime_data

    raw: dict[str, Any] = {}
    try:
        raw["status_block_18000"] = await coordinator.client.read_input(
            STATUS_BLOCK_START, STATUS_BLOCK_COUNT
        )
        raw["share_block_21001"] = await coordinator.client.read_holding(
            SHARE_BLOCK_START, SHARE_BLOCK_COUNT
        )
        for register in CONFIG_REGISTERS:
            raw[f"holding_{register}"] = await coordinator.client.read_holding(
                register, 1
            )
        # INFO block contains the unit's IP/MAC - redact address parts.
        info = await coordinator.client.read_input(INFO_BLOCK_START, INFO_BLOCK_COUNT)
        raw["info_block_16008"] = ["REDACTED"] * 14 + info[14:]
    except AirgenioModbusError as err:
        raw["error"] = str(err)

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
            "unique_id_redacted": entry.unique_id is not None,
        },
        "decoded": asdict(coordinator.data) if coordinator.data else None,
        "raw_registers": raw,
    }
