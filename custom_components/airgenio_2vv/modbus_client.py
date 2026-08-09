"""Async Modbus TCP client wrapper for 2VV AirGENIO units.

Responsibilities:
- translate DOC addresses (PLC BASE1, as printed in the 2VV manual) to
  on-wire 0-based addresses — the only place in the code base that does so,
- serialize all transactions behind one lock (the unit is a small PLC),
- reconnect with exponential backoff,
- raise typed exceptions with function/address context.
"""

from __future__ import annotations

import asyncio
import logging
import time

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

_LOGGER = logging.getLogger(__name__)

# Pause between transactions; the unit misbehaves when hammered.
_INTER_FRAME_DELAY_S = 0.03
_TIMEOUT_S = 5.0
_BACKOFF_START_S = 1.0
_BACKOFF_MAX_S = 60.0


class AirgenioModbusError(Exception):
    """A Modbus transaction with the unit failed."""


class AirgenioConnectionError(AirgenioModbusError):
    """The unit is not reachable."""


class AirgenioWriteMismatchError(AirgenioModbusError):
    """A written value did not read back as expected."""


class AirgenioModbusClient:
    """Thin async wrapper around AsyncModbusTcpClient."""

    def __init__(self, host: str, port: int, unit_id: int) -> None:
        """Initialize the client (no I/O)."""
        self._host = host
        self._port = port
        self._unit_id = unit_id
        self._client = AsyncModbusTcpClient(host, port=port, timeout=_TIMEOUT_S)
        self._lock = asyncio.Lock()
        self._backoff = _BACKOFF_START_S
        self._next_connect_attempt = 0.0

    @property
    def host(self) -> str:
        """Return the configured host."""
        return self._host

    async def close(self) -> None:
        """Close the underlying connection."""
        async with self._lock:
            self._client.close()

    async def _ensure_connected(self) -> None:
        """Connect if needed, honoring the reconnect backoff."""
        if self._client.connected:
            return
        now = time.monotonic()
        if now < self._next_connect_attempt:
            raise AirgenioConnectionError(
                f"Not connected to {self._host}:{self._port} "
                f"(retrying in {self._next_connect_attempt - now:.0f} s)"
            )
        connected = await self._client.connect()
        if not connected:
            self._next_connect_attempt = now + self._backoff
            self._backoff = min(self._backoff * 2, _BACKOFF_MAX_S)
            raise AirgenioConnectionError(
                f"Cannot connect to {self._host}:{self._port}"
            )
        self._backoff = _BACKOFF_START_S
        self._next_connect_attempt = 0.0

    async def read_input(self, doc_address: int, count: int = 1) -> list[int]:
        """Read input registers (FC04) at a DOC address."""
        return await self._read(doc_address, count, input_registers=True)

    async def read_holding(self, doc_address: int, count: int = 1) -> list[int]:
        """Read holding registers (FC03) at a DOC address."""
        return await self._read(doc_address, count, input_registers=False)

    async def _read(
        self, doc_address: int, count: int, *, input_registers: bool
    ) -> list[int]:
        kind = "input" if input_registers else "holding"
        async with self._lock:
            await self._ensure_connected()
            try:
                if input_registers:
                    result = await self._client.read_input_registers(
                        doc_address - 1, count=count, device_id=self._unit_id
                    )
                else:
                    result = await self._client.read_holding_registers(
                        doc_address - 1, count=count, device_id=self._unit_id
                    )
            except ModbusException as err:
                self._client.close()
                raise AirgenioConnectionError(
                    f"Read of {count} {kind} register(s) at {doc_address} failed: {err}"
                ) from err
            if result.isError():
                raise AirgenioModbusError(
                    f"Unit rejected read of {count} {kind} register(s) "
                    f"at {doc_address}: {result}"
                )
            await asyncio.sleep(_INTER_FRAME_DELAY_S)
            return list(result.registers)

    async def write_register(self, doc_address: int, value: int) -> None:
        """Write a single holding register (FC06) at a DOC address."""
        async with self._lock:
            await self._ensure_connected()
            try:
                result = await self._client.write_register(
                    doc_address - 1, value, device_id=self._unit_id
                )
            except ModbusException as err:
                self._client.close()
                raise AirgenioConnectionError(
                    f"Write of {value} to register {doc_address} failed: {err}"
                ) from err
            if result.isError():
                raise AirgenioModbusError(
                    f"Unit rejected write of {value} to register {doc_address}: "
                    f"{result}"
                )
            await asyncio.sleep(_INTER_FRAME_DELAY_S)

    async def write_verified(self, doc_address: int, value: int) -> None:
        """Write a holding register and verify it by reading it back."""
        await self.write_register(doc_address, value)
        readback = (await self.read_holding(doc_address, 1))[0]
        if readback != value:
            _LOGGER.warning(
                "Register %s read back %s after writing %s",
                doc_address,
                readback,
                value,
            )
            raise AirgenioWriteMismatchError(
                f"Register {doc_address} reads back {readback} after writing {value}"
            )
