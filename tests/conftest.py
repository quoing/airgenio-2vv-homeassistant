"""Shared fixtures for airgenio_2vv tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.airgenio_2vv.const import (
    CONF_MODEL,
    CONF_UNIT_ID,
    DOMAIN,
    MODEL_VENUS,
)
from custom_components.airgenio_2vv.modbus_client import (
    AirgenioModbusError,
)

pytest_plugins = "pytest_homeassistant_custom_component"

# Live-unit sample from 2026-08-09 (fan 20 %, outside 25.3 °C, extract
# 25.7 °C, filter 19 %, BMS readbacks 17.0 / 32.5 °C, room sensor absent).
STATUS_BLOCK = {
    18000: 0b0000000100000001,  # ON + summer
    18001: 0,
    18002: 0,
    18003: 0,
    18004: 0,
    18005: 0,
    18006: 200,
    18007: 253,
    18008: 253,
    18009: 257,
    18010: 65097,  # water return sensor absent -> sentinel
    18011: 65097,  # room sensor absent -> sentinel
    18012: 0,
    18013: 0,
    18014: 170,
    18015: 325,
    18016: 19,
}
HOLDING_REGS = {
    21001: 1,
    21002: 200,
    21003: 22,
    21004: 0,
    21005: 0,
    21006: 0,
    21007: 0,
    21008: 0,
    21009: 0,
    20044: 1,
    25000: 0,
    25009: 4,
    25033: 1,
    25077: 1,
    23000: 325,
    23002: 170,
}
INFO_REGS = {16029: 0x0203}


class FakeModbusClient:
    """In-memory stand-in for AirgenioModbusClient."""

    def __init__(self, host: str, port: int, unit_id: int) -> None:
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.input_regs = {**STATUS_BLOCK, **INFO_REGS}
        self.holding_regs = dict(HOLDING_REGS)
        self.writes: list[tuple[int, int]] = []
        self.input_reads: list[tuple[int, int]] = []
        self.holding_reads: list[tuple[int, int]] = []
        self.fail_reads = False
        self.fail_writes = False
        self.unsupported: set[int] = set()
        self.closed = False

    async def close(self) -> None:
        self.closed = True

    async def read_input(self, doc_address: int, count: int = 1) -> list[int]:
        self.input_reads.append((doc_address, count))
        if self.fail_reads:
            raise AirgenioModbusError("read failed (test)")
        return [self.input_regs.get(doc_address + i, 0) for i in range(count)]

    async def read_holding(self, doc_address: int, count: int = 1) -> list[int]:
        self.holding_reads.append((doc_address, count))
        if self.fail_reads:
            raise AirgenioModbusError("read failed (test)")
        if doc_address in self.unsupported:
            raise AirgenioModbusError(
                f"Unit rejected read at {doc_address} (test: IllegalDataAddress)"
            )
        return [self.holding_regs.get(doc_address + i, 0) for i in range(count)]

    async def write_register(self, doc_address: int, value: int) -> None:
        if self.fail_writes:
            raise AirgenioModbusError("write failed (test)")
        self.holding_regs[doc_address] = value
        self.writes.append((doc_address, value))

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading custom integrations in all tests."""
    return


@pytest.fixture
def mock_client() -> FakeModbusClient:
    """Return a fake Modbus client preloaded with live-unit sample data."""
    return FakeModbusClient("192.168.1.100", 502, 1)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry for the fake unit."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="AirGENIO 192.168.1.100",
        unique_id="192.168.1.100:502:1",
        data={
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 502,
            CONF_UNIT_ID: 1,
            CONF_MODEL: MODEL_VENUS,
        },
        version=2,
    )


@pytest.fixture
async def init_integration(hass, mock_config_entry, mock_client):
    """Set up the integration with the fake client."""
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.airgenio_2vv.AirgenioModbusClient",
        return_value=mock_client,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    return mock_config_entry
