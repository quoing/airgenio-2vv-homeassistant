"""Select platform for the 2VV AirGENIO integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import REG_TEMP_SENSOR_SELECTION, TEMP_SENSOR_OPTIONS
from .coordinator import Airgenio2vvConfigEntry, AirgenioCoordinator
from .entity import AirgenioEntity

PARALLEL_UPDATES = 0

_OPTION_TO_VALUE = {option: value for value, option in TEMP_SENSOR_OPTIONS.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Airgenio2vvConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the select entities."""
    async_add_entities([AirgenioTempSensorSelect(entry.runtime_data)])


class AirgenioTempSensorSelect(AirgenioEntity, SelectEntity):
    """Which temperature sensor the unit's control loop uses (25009)."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AirgenioCoordinator) -> None:
        """Initialize the select."""
        super().__init__(coordinator, "temperature_sensor_source")
        self._attr_options = list(TEMP_SENSOR_OPTIONS.values())

    @property
    def current_option(self) -> str | None:
        """Return the currently selected sensor source."""
        selection = self.coordinator.data.temp_sensor_selection
        if selection is None:
            return None
        return TEMP_SENSOR_OPTIONS.get(selection)

    @property
    def available(self) -> bool:
        """Unavailable when the unit does not support the register."""
        return (
            super().available
            and self.coordinator.data.temp_sensor_selection is not None
        )

    async def async_select_option(self, option: str) -> None:
        """Select a sensor source."""
        await self._write_and_refresh(
            REG_TEMP_SENSOR_SELECTION,
            _OPTION_TO_VALUE[option],
            lambda data: data.temp_sensor_selection,
            refresh_config=True,
        )
