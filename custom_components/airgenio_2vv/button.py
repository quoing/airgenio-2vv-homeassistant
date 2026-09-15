"""Button platform for the 2VV AirGENIO integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import REG_FILTER_RESET
from .coordinator import Airgenio2vvConfigEntry, AirgenioCoordinator
from .entity import AirgenioEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Airgenio2vvConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the button entities."""
    async_add_entities([AirgenioFilterResetButton(entry.runtime_data)])


class AirgenioFilterResetButton(AirgenioEntity, ButtonEntity):
    """Reset the filter timer after a filter change (register 21016)."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AirgenioCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator, "filter_reset")

    async def async_press(self) -> None:
        """Write the reset command (self-clearing, no read-back verify)."""
        await self._write_and_refresh(REG_FILTER_RESET, 1)
