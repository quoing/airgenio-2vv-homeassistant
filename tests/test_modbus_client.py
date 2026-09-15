"""Tests for shared Modbus unit adapter and address conversion."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from modbus_connection import IllegalDataAddressError, ModbusTimeoutError

from custom_components.airgenio_2vv.const import MESSAGE_SPACING
from custom_components.airgenio_2vv.modbus_client import (
    AirgenioConnectionError,
    AirgenioModbusClient,
    AirgenioModbusError,
)


@pytest.fixture
def unit():
    """Return a shared Modbus unit mock."""
    mock = MagicMock()
    mock.connected = True
    mock.read_input_registers = AsyncMock(return_value=[253])
    mock.read_holding_registers = AsyncMock(return_value=[600])
    mock.write_register = AsyncMock()
    mock.disconnect = AsyncMock()
    return mock


def test_configures_message_spacing(unit) -> None:
    """Fragile AirGENIO server receives paced requests."""
    AirgenioModbusClient(unit)
    unit.set_message_spacing.assert_called_once_with(MESSAGE_SPACING)


async def test_read_input_applies_doc_offset(unit) -> None:
    """Documentation address 18007 must hit raw address 18006."""
    client = AirgenioModbusClient(unit)
    assert await client.read_input(18007, 1) == [253]
    unit.read_input_registers.assert_awaited_once_with(18006, 1)


async def test_read_holding_applies_doc_offset(unit) -> None:
    """Documentation address 21002 must hit raw address 21001."""
    client = AirgenioModbusClient(unit)
    assert await client.read_holding(21002, 1) == [600]
    unit.read_holding_registers.assert_awaited_once_with(21001, 1)


async def test_write_applies_doc_offset(unit) -> None:
    """Fan target documentation address must hit Daphne raw address."""
    client = AirgenioModbusClient(unit)
    await client.write_register(21002, 600)
    unit.write_register.assert_awaited_once_with(21001, 600)


async def test_boost_write_applies_doc_offset(unit) -> None:
    """Boost documentation address must hit Daphne raw address 21008."""
    client = AirgenioModbusClient(unit)
    await client.write_register(21009, 1)
    unit.write_register.assert_awaited_once_with(21008, 1)


async def test_connection_failure_disconnects(unit) -> None:
    """Timeout recycles stale shared connection before next request."""
    unit.read_input_registers.side_effect = ModbusTimeoutError("timed out")
    client = AirgenioModbusClient(unit)
    with pytest.raises(AirgenioConnectionError, match="raw 17999"):
        await client.read_input(18000, 1)
    unit.disconnect.assert_awaited_once()


async def test_device_exception_does_not_disconnect(unit) -> None:
    """Illegal register response does not imply a broken TCP connection."""
    unit.read_holding_registers.side_effect = IllegalDataAddressError()
    client = AirgenioModbusClient(unit)
    with pytest.raises(AirgenioModbusError, match="raw 25076"):
        await client.read_holding(25077, 1)
    unit.disconnect.assert_not_awaited()
