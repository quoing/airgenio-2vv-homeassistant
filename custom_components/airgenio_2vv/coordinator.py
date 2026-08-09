"""DataUpdateCoordinator for the 2VV AirGENIO integration."""

from __future__ import annotations

import logging
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
    STATUS_BLOCK_COUNT,
    STATUS_BLOCK_START,
)
from .data import AirgenioData, decode_temperature
from .modbus_client import AirgenioModbusClient, AirgenioModbusError

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

    async def _async_update_data(self) -> AirgenioData:
        """Read all register blocks and decode them."""
        try:
            status = await self.client.read_input(
                STATUS_BLOCK_START, STATUS_BLOCK_COUNT
            )
            share = await self.client.read_holding(SHARE_BLOCK_START, SHARE_BLOCK_COUNT)
            config: dict[int, int] = {}
            for register in CONFIG_REGISTERS:
                config[register] = (await self.client.read_holding(register, 1))[0]
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
            bms_outside_enable=bool(config[REG_BMS_OUTSIDE_ENABLE]),
            ventilation_mode_raw=config[REG_VENTILATION_MODE],
            temp_sensor_selection=config[REG_TEMP_SENSOR_SELECTION],
            auto_temp_control=bool(config[REG_AUTO_TEMP_CONTROL]),
            auto_fan_control=bool(config[REG_AUTO_FAN_CONTROL]),
        )
