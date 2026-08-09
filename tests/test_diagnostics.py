"""Tests for the diagnostics endpoint."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.airgenio_2vv.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics(hass: HomeAssistant, init_integration) -> None:
    """Diagnostics include decoded data and redact the host + INFO block."""
    result = await async_get_config_entry_diagnostics(hass, init_integration)

    assert result["entry"]["data"]["host"] == "**REDACTED**"
    assert result["decoded"]["fan_actual_permille"] == 200
    assert result["raw_registers"]["status_block_18000"][7] == 253
    # First 14 INFO registers (IP/mask/gateway/DHCP/port/MAC) are redacted.
    assert result["raw_registers"]["info_block_16008"][0] == "REDACTED"
