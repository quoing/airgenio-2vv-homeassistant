"""Binary sensor platform for the 2VV AirGENIO integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ERROR_BIT_FAN,
    ERROR_BIT_FAN1,
    ERROR_BIT_FILTER_ERROR,
    ERROR_BIT_FILTER_WARNING,
    ERROR_BIT_GLOBAL,
    STATUS_BIT_NIGHT_REDUCTION,
    STATUS_BIT_SUMMER,
)
from .coordinator import Airgenio2vvConfigEntry, AirgenioCoordinator
from .data import AirgenioData
from .entity import AirgenioEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class AirgenioBinarySensorDescription(BinarySensorEntityDescription):
    """Binary sensor description with a value extractor."""

    value_fn: Callable[[AirgenioData], bool]


BINARY_SENSORS: tuple[AirgenioBinarySensorDescription, ...] = (
    AirgenioBinarySensorDescription(
        key="global_error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: d.error_bit(ERROR_BIT_GLOBAL),
    ),
    AirgenioBinarySensorDescription(
        key="fan_error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.error_bit(ERROR_BIT_FAN) or d.error_bit(ERROR_BIT_FAN1),
    ),
    AirgenioBinarySensorDescription(
        key="filter_warning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda d: (
            d.error_bit(ERROR_BIT_FILTER_ERROR) or d.error_bit(ERROR_BIT_FILTER_WARNING)
        ),
    ),
    AirgenioBinarySensorDescription(
        key="preheater_active",
        device_class=BinarySensorDeviceClass.HEAT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.preheater_power > 0,
    ),
    AirgenioBinarySensorDescription(
        key="summer_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.status_bit(STATUS_BIT_SUMMER),
    ),
    AirgenioBinarySensorDescription(
        key="night_reduction",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.status_bit(STATUS_BIT_NIGHT_REDUCTION),
    ),
    AirgenioBinarySensorDescription(
        key="sensor_fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.sensor_fault,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Airgenio2vvConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensor entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        AirgenioBinarySensor(coordinator, description) for description in BINARY_SENSORS
    )


class AirgenioBinarySensor(AirgenioEntity, BinarySensorEntity):
    """A binary sensor backed by decoded status bits."""

    entity_description: AirgenioBinarySensorDescription

    def __init__(
        self,
        coordinator: AirgenioCoordinator,
        description: AirgenioBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        """Return the decoded bit."""
        return self.entity_description.value_fn(self.coordinator.data)
