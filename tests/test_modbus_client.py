"""Unit tests for the Modbus client wrapper (doc->wire offset, errors)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.airgenio_2vv.modbus_client import (
    AirgenioConnectionError,
    AirgenioModbusClient,
    AirgenioModbusError,
    AirgenioWriteMismatchError,
)


def make_result(registers: list[int] | None = None, error: bool = False):
    result = MagicMock()
    result.isError.return_value = error
    result.registers = registers or []
    return result


@pytest.fixture
def pymodbus_mock():
    with patch(
        "custom_components.airgenio_2vv.modbus_client.AsyncModbusTcpClient"
    ) as cls:
        instance = cls.return_value
        instance.connected = True
        instance.connect = AsyncMock(return_value=True)
        instance.close = MagicMock()
        instance.read_input_registers = AsyncMock(return_value=make_result([253]))
        instance.read_holding_registers = AsyncMock(return_value=make_result([600]))
        instance.write_register = AsyncMock(return_value=make_result())
        yield instance


async def test_read_input_applies_doc_offset(pymodbus_mock) -> None:
    """DOC address 18007 must hit wire address 18006."""
    client = AirgenioModbusClient("host", 502, 1)
    registers = await client.read_input(18007, 1)
    assert registers == [253]
    pymodbus_mock.read_input_registers.assert_awaited_once_with(
        18006, count=1, device_id=1
    )


async def test_write_applies_doc_offset(pymodbus_mock) -> None:
    """DOC address 21002 must hit wire address 21001."""
    client = AirgenioModbusClient("host", 502, 1)
    await client.write_register(21002, 600)
    pymodbus_mock.write_register.assert_awaited_once_with(21001, 600, device_id=1)


async def test_write_verified_reads_back(pymodbus_mock) -> None:
    """write_verified re-reads the same register and accepts a match."""
    client = AirgenioModbusClient("host", 502, 1)
    await client.write_verified(21002, 600)
    pymodbus_mock.read_holding_registers.assert_awaited_once_with(
        21001, count=1, device_id=1
    )


async def test_write_verified_mismatch_raises(pymodbus_mock) -> None:
    """A read-back mismatch raises AirgenioWriteMismatchError."""
    pymodbus_mock.read_holding_registers.return_value = make_result([500])
    client = AirgenioModbusClient("host", 502, 1)
    with pytest.raises(AirgenioWriteMismatchError):
        await client.write_verified(21002, 600)


async def test_exception_response_raises_modbus_error(pymodbus_mock) -> None:
    """A Modbus exception response raises AirgenioModbusError."""
    pymodbus_mock.read_input_registers.return_value = make_result(error=True)
    client = AirgenioModbusClient("host", 502, 1)
    with pytest.raises(AirgenioModbusError):
        await client.read_input(18000, 1)


async def test_connect_failure_and_backoff(pymodbus_mock) -> None:
    """A failed connect raises and the immediate retry is throttled."""
    pymodbus_mock.connected = False
    pymodbus_mock.connect = AsyncMock(return_value=False)
    client = AirgenioModbusClient("host", 502, 1)

    with pytest.raises(AirgenioConnectionError):
        await client.read_input(18000, 1)
    assert pymodbus_mock.connect.await_count == 1

    # Second call within the backoff window must not attempt to connect.
    with pytest.raises(AirgenioConnectionError):
        await client.read_input(18000, 1)
    assert pymodbus_mock.connect.await_count == 1
