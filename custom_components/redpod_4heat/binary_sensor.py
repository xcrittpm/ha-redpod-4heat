"""Problem sensor for the stove."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CODE_ERROR
from .coordinator import FourHeatConfigEntry
from .entity import FourHeatEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FourHeatConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([FourHeatProblemSensor(entry.runtime_data, "problem")])


class FourHeatProblemSensor(FourHeatEntity, BinarySensorEntity):
    """On when the stove reports an error."""

    _attr_translation_key = "problem"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool | None:
        error = self.coordinator.value(CODE_ERROR)
        return None if error is None else error != 0
