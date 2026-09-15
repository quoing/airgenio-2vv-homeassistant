"""Fan platform for the 2VV AirGENIO integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import REG_AIRFLOW_MANUAL, REG_SWITCH_ON
from .coordinator import Airgenio2vvConfigEntry
from .entity import AirgenioEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: Airgenio2vvConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the fan entity."""
    async_add_entities([AirgenioFan(entry.runtime_data)])


class AirgenioFan(AirgenioEntity, FanEntity):
    """The ventilation unit as a fan: on/off + airflow percentage."""

    _attr_name = None  # main feature entity carries the device name
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_speed_count = 100

    def __init__(self, coordinator: Any) -> None:
        """Initialize the fan entity."""
        super().__init__(coordinator, "fan")

    @property
    def is_on(self) -> bool:
        """Return True when the unit is switched on."""
        return self.coordinator.data.switch_on

    @property
    def percentage(self) -> int:
        """Return the target airflow in percent (register is in per mille)."""
        return round(self.coordinator.data.airflow_target_permille / 10)

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        """Expose the actual (measured) fan power next to the target."""
        return {"actual_power": round(self.coordinator.data.fan_actual_permille / 10)}

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the airflow; 0 % turns the unit off."""
        percentage = max(0, min(100, percentage))
        if percentage == 0:
            await self.async_turn_off()
            return
        await self._write_only(REG_AIRFLOW_MANUAL, percentage * 10)
        if not self.coordinator.data.switch_on:
            await self._write_only(REG_SWITCH_ON, 1)
        await self.coordinator.async_refresh()
        self._verify_fan_state(percentage, expected_on=True)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the unit on, optionally at a given airflow."""
        if percentage is not None and percentage > 0:
            percentage = min(100, percentage)
            await self._write_only(REG_AIRFLOW_MANUAL, percentage * 10)
        await self._write_only(REG_SWITCH_ON, 1)
        await self.coordinator.async_refresh()
        self._verify_fan_state(percentage, expected_on=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the unit off."""
        await self._write_and_refresh(
            REG_SWITCH_ON, 0, lambda data: data.switch_on
        )

    def _verify_fan_state(
        self, percentage: int | None, *, expected_on: bool
    ) -> None:
        """Verify refreshed power and percentage state."""
        if not self.coordinator.last_update_success:
            raise HomeAssistantError(
                "Fan command was written, but refreshing its state failed"
            )
        data = self.coordinator.data
        if data.switch_on is not expected_on:
            raise HomeAssistantError("Fan power state did not accept the command")
        if percentage is None:
            return
        observed = round(data.airflow_target_permille / 10)
        if observed != percentage:
            raise HomeAssistantError(
                f"Fan target reads back {observed}% after writing {percentage}%. "
                "Automatic fan control may own the airflow setpoint."
            )
