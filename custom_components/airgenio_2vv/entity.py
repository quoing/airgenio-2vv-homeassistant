"""Base entity for the 2VV AirGENIO integration."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_MODEL, DEFAULT_MODEL, DOMAIN, MANUFACTURER, MODEL_NAMES
from .coordinator import AirgenioCoordinator
from .data import AirgenioData
from .modbus_client import AirgenioModbusError


class AirgenioEntity(CoordinatorEntity[AirgenioCoordinator]):
    """Common base: device info, naming and unique-id scheme."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AirgenioCoordinator, key: str) -> None:
        """Initialize the entity with a stable per-device unique id."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        entry_unique = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{entry_unique}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_unique)},
            manufacturer=MANUFACTURER,
            model=MODEL_NAMES[entry.data.get(CONF_MODEL, DEFAULT_MODEL)],
            name=entry.title,
            sw_version=entry.data.get("sw_version"),
        )

    async def _write_and_refresh(
        self,
        doc_address: int,
        value: int,
        observed_fn: Callable[[AirgenioData], float | int | bool | None] | None = None,
        *,
        expected_value: float | int | bool | None = None,
        refresh_config: bool = False,
        mismatch_hint: str = "",
    ) -> None:
        """Write once, refresh coordinator data, and optionally verify state."""
        await self._write_only(doc_address, value)
        if refresh_config:
            await self.coordinator.async_refresh_config()
        else:
            await self.coordinator.async_refresh()
        if not self.coordinator.last_update_success:
            raise HomeAssistantError(
                f"Register {doc_address} was written, but refreshing its state failed"
            )
        if observed_fn is None:
            return
        observed = observed_fn(self.coordinator.data)
        expected = value if expected_value is None else expected_value
        if observed != expected:
            hint = f" {mismatch_hint}" if mismatch_hint else ""
            raise HomeAssistantError(
                f"Register {doc_address} reads back {observed} after writing {value}."
                f"{hint}"
            )

    async def _write_only(self, doc_address: int, value: int) -> None:
        """Write one register and translate transport errors for HA."""
        try:
            await self.coordinator.client.write_register(doc_address, value)
        except AirgenioModbusError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={
                    "register": str(doc_address),
                    "error": str(err),
                },
            ) from err
