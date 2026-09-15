"""Switch platform for the 2VV AirGENIO integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_MODEL,
    CONFIG_REGISTERS,
    DEFAULT_MODEL,
    MODEL_DAPHNE,
    REG_AUTO_FAN_CONTROL,
    REG_AUTO_TEMP_CONTROL,
    REG_BMS_OUTSIDE_ENABLE,
    REG_DAY_NIGHT,
)
from .coordinator import Airgenio2vvConfigEntry, AirgenioCoordinator
from .data import AirgenioData
from .entity import AirgenioEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class AirgenioSwitchDescription(SwitchEntityDescription):
    """Switch description with register mapping."""

    register: int
    value_fn: Callable[[AirgenioData], bool | None]


DAY_NIGHT_SWITCH = AirgenioSwitchDescription(
    key="day_night_mode",
    register=REG_DAY_NIGHT,
    value_fn=lambda d: d.day_night,
)

SWITCHES: tuple[AirgenioSwitchDescription, ...] = (
    DAY_NIGHT_SWITCH,
    AirgenioSwitchDescription(
        key="automatic_temperature_control",
        entity_category=EntityCategory.CONFIG,
        register=REG_AUTO_TEMP_CONTROL,
        value_fn=lambda d: d.auto_temp_control,
    ),
    AirgenioSwitchDescription(
        key="automatic_fan_control",
        entity_category=EntityCategory.CONFIG,
        register=REG_AUTO_FAN_CONTROL,
        value_fn=lambda d: d.auto_fan_control,
    ),
    AirgenioSwitchDescription(
        key="bms_outside_enable",
        entity_category=EntityCategory.CONFIG,
        register=REG_BMS_OUTSIDE_ENABLE,
        value_fn=lambda d: d.bms_outside_enable,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Airgenio2vvConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the switch entities."""
    coordinator = entry.runtime_data
    switches = SWITCHES
    if entry.data.get(CONF_MODEL, DEFAULT_MODEL) == MODEL_DAPHNE:
        switches = (replace(DAY_NIGHT_SWITCH, translation_key="boost"), *SWITCHES[1:])
    async_add_entities(
        AirgenioSwitch(coordinator, description) for description in switches
    )


class AirgenioSwitch(AirgenioEntity, SwitchEntity):
    """A 0/1 holding register exposed as a switch."""

    entity_description: AirgenioSwitchDescription

    def __init__(
        self,
        coordinator: AirgenioCoordinator,
        description: AirgenioSwitchDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_translation_key = description.translation_key or description.key

    @property
    def is_on(self) -> bool | None:
        """Return the register state."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Unavailable when the unit does not support the register."""
        return super().available and self.is_on is not None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Write 1 to the register."""
        await self._write_and_refresh(
            self.entity_description.register,
            1,
            self.entity_description.value_fn,
            refresh_config=self.entity_description.register in CONFIG_REGISTERS,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Write 0 to the register."""
        await self._write_and_refresh(
            self.entity_description.register,
            0,
            self.entity_description.value_fn,
            refresh_config=self.entity_description.register in CONFIG_REGISTERS,
        )
