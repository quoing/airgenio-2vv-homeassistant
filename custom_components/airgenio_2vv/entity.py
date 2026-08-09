"""Base entity for the 2VV AirGENIO integration."""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import AirgenioCoordinator
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
            model=MODEL,
            name=entry.title,
            sw_version=entry.data.get("sw_version"),
        )

    async def _write_verified(self, doc_address: int, value: int) -> None:
        """Write a register with read-back verification and refresh."""
        try:
            await self.coordinator.client.write_verified(doc_address, value)
        except AirgenioModbusError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={
                    "register": str(doc_address),
                    "error": str(err),
                },
            ) from err
        await self.coordinator.async_request_refresh()
