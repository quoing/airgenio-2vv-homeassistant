"""DataUpdateCoordinator for the 2VV AirGENIO integration."""

from __future__ import annotations

import logging
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONFIG_REGISTERS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    REG_AUTO_FAN_CONTROL,
    REG_AUTO_TEMP_CONTROL,
    REG_BMS_OUTSIDE_ENABLE,
    REG_TEMP_SENSOR_SELECTION,
    REG_VENTILATION_MODE,
    SHARE_BLOCK_COUNT,
    SHARE_BLOCK_START,
    SLOW_SCAN_INTERVAL,
    STATUS_BLOCK_COUNT,
    STATUS_BLOCK_START,
)
from .data import AirgenioData, decode_temperature
from .modbus_client import (
    AirgenioConnectionError,
    AirgenioModbusClient,
    AirgenioModbusError,
)

_LOGGER = logging.getLogger(__name__)

type Airgenio2vvConfigEntry = ConfigEntry[AirgenioCoordinator]


class AirgenioCoordinator(DataUpdateCoordinator[AirgenioData]):
    """Polls the unit and decodes register blocks into AirgenioData."""

    config_entry: Airgenio2vvConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: Airgenio2vvConfigEntry,
        client: AirgenioModbusClient,
    ) -> None:
        """Initialize the coordinator."""
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self._unsupported_registers: set[int] = set()
        self._config: dict[int, int | None] = {}
        self._last_config_update = 0.0
        self._force_config_refresh = False

    async def async_refresh_config(self) -> None:
        """Refresh runtime and slow configuration registers now."""
        self._force_config_refresh = True
        await self.async_refresh()

    async def _async_update_data(self) -> AirgenioData:
        """Read all register blocks and decode them."""
        try:
            status = await self.client.read_input(
                STATUS_BLOCK_START, STATUS_BLOCK_COUNT
            )
            share = await self.client.read_holding(SHARE_BLOCK_START, SHARE_BLOCK_COUNT)
            now = time.monotonic()
            if (
                not self._config
                or self._force_config_refresh
                or now - self._last_config_update >= SLOW_SCAN_INTERVAL
            ):
                await self._async_update_config()
                self._last_config_update = now
            self._force_config_refresh = False
        except AirgenioModbusError as err:
            raise UpdateFailed(str(err)) from err

        def status_reg(doc_address: int) -> int:
            return status[doc_address - STATUS_BLOCK_START]

        def share_reg(doc_address: int) -> int:
            return share[doc_address - SHARE_BLOCK_START]

        # Local import names kept short; doc addresses per ground-truth.md.
        return AirgenioData(
            status_bits=status_reg(18000),
            error_bits=status_reg(18001),
            sensor_status_bits=status_reg(18003),
            output_bits=status_reg(18005),
            fan_actual_permille=status_reg(18006),
            temp_outside=decode_temperature(status_reg(18007)),
            temp_supply=decode_temperature(status_reg(18008)),
            temp_extract=decode_temperature(status_reg(18009)),
            temp_water_return=decode_temperature(status_reg(18010)),
            temp_room=decode_temperature(status_reg(18011)),
            preheater_power=status_reg(18013),
            bms_outside_readback=decode_temperature(status_reg(18014)),
            bms_room_readback=decode_temperature(status_reg(18015)),
            filter_percent=status_reg(18016),
            switch_on=bool(share_reg(21001)),
            airflow_target_permille=share_reg(21002),
            temp_setpoint=share_reg(21003),
            day_night=bool(share_reg(21009)),
            bms_outside_enable=_opt_bool(self._config[REG_BMS_OUTSIDE_ENABLE]),
            ventilation_mode_raw=self._config[REG_VENTILATION_MODE],
            temp_sensor_selection=self._config[REG_TEMP_SENSOR_SELECTION],
            auto_temp_control=_opt_bool(self._config[REG_AUTO_TEMP_CONTROL]),
            auto_fan_control=_opt_bool(self._config[REG_AUTO_FAN_CONTROL]),
        )

    async def _async_update_config(self) -> None:
        """Read slow-changing configuration registers."""
        for register in CONFIG_REGISTERS:
            if register in self._unsupported_registers:
                self._config[register] = None
                continue
            try:
                self._config[register] = (
                    await self.client.read_holding(register, 1)
                )[0]
            except AirgenioConnectionError:
                raise
            except AirgenioModbusError:
                _LOGGER.warning(
                    "Documentation register %s (raw %s) is unsupported; related "
                    "entity will be unavailable",
                    register,
                    register - 1,
                )
                self._unsupported_registers.add(register)
                self._config[register] = None


def _opt_bool(raw: int | None) -> bool | None:
    """Decode an optional 0/1 register."""
    return None if raw is None else bool(raw)
