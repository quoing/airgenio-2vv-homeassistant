"""Number platform for the 2VV AirGENIO integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_MODEL,
    DEFAULT_MODEL,
    MODEL_DAPHNE,
    REG_AIRFLOW_MANUAL,
    REG_BMS_OUTSIDE_WRITE,
    REG_BMS_ROOM_WRITE,
    REG_TEMP_SETPOINT,
    SETPOINT_MAX,
    SETPOINT_MIN,
)
from .coordinator import Airgenio2vvConfigEntry, AirgenioCoordinator
from .data import AirgenioData
from .entity import AirgenioEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class AirgenioNumberDescription(NumberEntityDescription):
    """Number description with register mapping."""

    register: int
    value_fn: Callable[[AirgenioData], float | None]
    # Factor from entity value to raw register value.
    write_scale: int = 1


NUMBERS: tuple[AirgenioNumberDescription, ...] = (
    AirgenioNumberDescription(
        key="temperature_setpoint",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=SETPOINT_MIN,
        native_max_value=SETPOINT_MAX,
        native_step=1,
        register=REG_TEMP_SETPOINT,
        value_fn=lambda d: d.temp_setpoint,
    ),
    AirgenioNumberDescription(
        key="bms_outside_temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0.0,
        native_max_value=60.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        register=REG_BMS_OUTSIDE_WRITE,
        value_fn=lambda d: d.bms_outside_readback,
        write_scale=10,
    ),
    AirgenioNumberDescription(
        key="bms_room_temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0.0,
        native_max_value=60.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        register=REG_BMS_ROOM_WRITE,
        value_fn=lambda d: d.bms_room_readback,
        write_scale=10,
    ),
)

DAPHNE_FAN_PERCENTAGE = AirgenioNumberDescription(
    key="fan_percentage",
    native_unit_of_measurement=PERCENTAGE,
    native_min_value=20,
    native_max_value=100,
    native_step=1,
    mode=NumberMode.SLIDER,
    register=REG_AIRFLOW_MANUAL,
    value_fn=lambda d: round(d.airflow_target_permille / 10),
    write_scale=10,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Airgenio2vvConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the number entities."""
    coordinator = entry.runtime_data
    numbers = NUMBERS
    if entry.data.get(CONF_MODEL, DEFAULT_MODEL) == MODEL_DAPHNE:
        numbers = (*NUMBERS, DAPHNE_FAN_PERCENTAGE)
    async_add_entities(
        AirgenioNumber(coordinator, description) for description in numbers
    )


class AirgenioNumber(AirgenioEntity, NumberEntity):
    """A writable register exposed as a number."""

    entity_description: AirgenioNumberDescription

    def __init__(
        self,
        coordinator: AirgenioCoordinator,
        description: AirgenioNumberDescription,
    ) -> None:
        """Initialize the number."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_set_native_value(self, value: float) -> None:
        """Write the value to the unit (with read-back verification)."""
        raw = round(value * self.entity_description.write_scale)
        await self._write_and_refresh(
            self.entity_description.register,
            raw,
            self.entity_description.value_fn,
            expected_value=value,
        )
