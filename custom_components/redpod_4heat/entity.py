"""Base entity for the Red-Pod 4Heat (local) integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FourHeatCoordinator


class FourHeatEntity(CoordinatorEntity[FourHeatCoordinator]):
    """Common parts of every stove entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: FourHeatCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Red-Pod",
            model="Pellet stove with 4Heat WiFi module",
        )
