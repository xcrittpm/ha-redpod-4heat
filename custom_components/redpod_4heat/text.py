"""Stove model and serial number, typed in by the user.

The module does not report them. They are also shown on the device page.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.text import TextEntity, TextEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEFAULT_MODEL, DOMAIN
from .coordinator import FourHeatConfigEntry, FourHeatCoordinator
from .entity import FourHeatEntity
from .user_data import UserData


@dataclass(frozen=True, kw_only=True)
class FourHeatTextDescription(TextEntityDescription):
    """Describes a stove detail."""

    get: Callable[[UserData], str]
    set: Callable[[UserData, str], None]


TEXTS: tuple[FourHeatTextDescription, ...] = (
    FourHeatTextDescription(
        key="model",
        translation_key="model",
        entity_category=EntityCategory.CONFIG,
        native_max=100,
        get=lambda data: data.model,
        set=lambda data, value: data.set_model(value),
    ),
    FourHeatTextDescription(
        key="serial_number",
        translation_key="serial_number",
        entity_category=EntityCategory.CONFIG,
        native_max=100,
        get=lambda data: data.serial,
        set=lambda data, value: data.set_serial(value),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FourHeatConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(FourHeatText(coordinator, description) for description in TEXTS)


def update_device_details(hass: HomeAssistant, coordinator: FourHeatCoordinator) -> None:
    """Show the typed-in model and serial number on the device page."""
    registry = dr.async_get(hass)
    device = registry.async_get_device(
        identifiers={(DOMAIN, coordinator.config_entry.entry_id)}
    )
    if device is None:
        return
    data = coordinator.user
    registry.async_update_device(
        device.id,
        model=data.model or DEFAULT_MODEL,
        serial_number=data.serial or None,
    )


class FourHeatText(FourHeatEntity, TextEntity):
    """A stove detail kept by Home Assistant."""

    entity_description: FourHeatTextDescription

    def __init__(
        self, coordinator: FourHeatCoordinator, description: FourHeatTextDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> str:
        return self.entity_description.get(self.coordinator.user)

    async def async_set_value(self, value: str) -> None:
        self.entity_description.set(self.coordinator.user, value)
        update_device_details(self.hass, self.coordinator)
        self.async_write_ha_state()
