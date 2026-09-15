"""Modbus client adapter for 2VV AirGENIO units.

Home Assistant owns and shares the physical connection. This adapter keeps
AirGENIO's one-based documentation addresses out of transport-facing code and
normalizes backend exceptions for the integration.
"""

from __future__ import annotations

from contextlib import suppress

from modbus_connection import (
    ModbusConnectionError,
    ModbusError,
    ModbusProtocolError,
    ModbusTimeoutError,
    ModbusUnit,
)

from .const import MESSAGE_SPACING


class AirgenioModbusError(Exception):
    """A Modbus transaction with the unit failed."""


class AirgenioConnectionError(AirgenioModbusError):
    """The unit is not reachable."""


class AirgenioModbusClient:
    """Adapt a Home Assistant shared Modbus unit for AirGENIO."""

    def __init__(self, unit: ModbusUnit) -> None:
        """Initialize the adapter without opening another connection."""
        self._unit = unit
        self._unit.set_message_spacing(MESSAGE_SPACING)

    @property
    def connected(self) -> bool:
        """Return whether shared transport is currently connected."""
        return self._unit.connected

    async def read_input(self, doc_address: int, count: int = 1) -> list[int]:
        """Read input registers using a one-based documentation address."""
        try:
            return await self._unit.read_input_registers(doc_address - 1, count)
        except (ModbusConnectionError, ModbusTimeoutError, ModbusProtocolError) as err:
            await self._disconnect()
            raise AirgenioConnectionError(
                f"Read of {count} input register(s) at documentation address "
                f"{doc_address} (raw {doc_address - 1}) failed: {err}"
            ) from err
        except ModbusError as err:
            raise AirgenioModbusError(
                f"Unit rejected read of {count} input register(s) at "
                f"documentation address {doc_address} (raw {doc_address - 1}): {err}"
            ) from err

    async def read_holding(self, doc_address: int, count: int = 1) -> list[int]:
        """Read holding registers using a one-based documentation address."""
        try:
            return await self._unit.read_holding_registers(doc_address - 1, count)
        except (ModbusConnectionError, ModbusTimeoutError, ModbusProtocolError) as err:
            await self._disconnect()
            raise AirgenioConnectionError(
                f"Read of {count} holding register(s) at documentation address "
                f"{doc_address} (raw {doc_address - 1}) failed: {err}"
            ) from err
        except ModbusError as err:
            raise AirgenioModbusError(
                f"Unit rejected read of {count} holding register(s) at "
                f"documentation address {doc_address} (raw {doc_address - 1}): {err}"
            ) from err

    async def write_register(self, doc_address: int, value: int) -> None:
        """Write one holding register using a documentation address."""
        try:
            await self._unit.write_register(doc_address - 1, value)
        except (ModbusConnectionError, ModbusTimeoutError, ModbusProtocolError) as err:
            await self._disconnect()
            raise AirgenioConnectionError(
                f"Write of {value} to documentation address {doc_address} "
                f"(raw {doc_address - 1}) failed: {err}"
            ) from err
        except ModbusError as err:
            raise AirgenioModbusError(
                f"Unit rejected write of {value} to documentation address "
                f"{doc_address} (raw {doc_address - 1}): {err}"
            ) from err

    async def _disconnect(self) -> None:
        """Recycle a failed shared link without releasing connection ownership."""
        with suppress(ModbusError):
            await self._unit.disconnect()
