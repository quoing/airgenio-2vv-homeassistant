"""Sensor platform for the 2VV AirGENIO integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import Airgenio2vvConfigEntry, AirgenioCoordinator
from .data import AirgenioData
from .entity import AirgenioEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class AirgenioSensorDescription(SensorEntityDescription):
    """Sensor description with a value extractor."""

    value_fn: Callable[[AirgenioData], float | int | None]


def _temperature(
    key: str,
    value_fn: Callable[[AirgenioData], float | None],
    *,
    category: EntityCategory | None = None,
    enabled: bool = True,
) -> AirgenioSensorDescription:
    return AirgenioSensorDescription(
        key=key,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=category,
        entity_registry_enabled_default=enabled,
        value_fn=value_fn,
    )


SENSORS: tuple[AirgenioSensorDescription, ...] = (
    _temperature("outside_temperature", lambda d: d.temp_outside),
    _temperature("supply_temperature", lambda d: d.temp_supply),
    _temperature("extract_temperature", lambda d: d.temp_extract),
    _temperature("room_temperature", lambda d: d.temp_room),
    _temperature(
        "water_return_temperature",
        lambda d: d.temp_water_return,
        category=EntityCategory.DIAGNOSTIC,
        enabled=False,
    ),
    _temperature(
        "bms_outside_readback",
        lambda d: d.bms_outside_readback,
        category=EntityCategory.DIAGNOSTIC,
        enabled=False,
    ),
    _temperature(
        "bms_room_readback",
        lambda d: d.bms_room_readback,
        category=EntityCategory.DIAGNOSTIC,
        enabled=False,
    ),
    AirgenioSensorDescription(
        key="fan_power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: round(d.fan_actual_permille / 10),
    ),
    AirgenioSensorDescription(
        key="preheater_power",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.preheater_power,
    ),
    AirgenioSensorDescription(
        key="filter_clogging",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.filter_percent,
    ),
    AirgenioSensorDescription(
        key="heat_recovery_efficiency",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda d: d.heat_recovery_efficiency,
    ),
    AirgenioSensorDescription(
        key="ventilation_mode_raw",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.ventilation_mode_raw,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Airgenio2vvConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensor entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        AirgenioSensor(coordinator, description) for description in SENSORS
    )


class AirgenioSensor(AirgenioEntity, SensorEntity):
    """A sensor backed by a decoded coordinator value."""

    entity_description: AirgenioSensorDescription

    def __init__(
        self,
        coordinator: AirgenioCoordinator,
        description: AirgenioSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | None:
        """Return the decoded value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Unavailable when the backing value is missing (e.g. no sensor)."""
        return super().available and self.native_value is not None
