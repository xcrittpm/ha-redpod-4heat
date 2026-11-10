"""Pellet tank size and level, set by the user."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfMass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import FourHeatConfigEntry, FourHeatCoordinator
from .entity import FourHeatEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FourHeatConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [FourHeatTankCapacity(coordinator), FourHeatPelletLevel(coordinator)]
    )


class FourHeatPelletNumber(FourHeatEntity, NumberEntity):
    """Base for the pellet numbers: refresh when the pellet data changes."""

    _attr_device_class = NumberDeviceClass.WEIGHT
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_mode = NumberMode.BOX

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.user.async_add_listener(self.async_write_ha_state)
        )


class FourHeatTankCapacity(FourHeatPelletNumber):
    """How many kg of pellets fit in the tank (15 kg on the Red-Pod inserts)."""

    _attr_translation_key = "tank_capacity"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 1
    _attr_native_max_value = 200
    _attr_native_step = 0.5

    def __init__(self, coordinator: FourHeatCoordinator) -> None:
        super().__init__(coordinator, "tank_capacity")

    @property
    def native_value(self) -> float:
        return self.coordinator.user.capacity

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.user.set_capacity(value)


class FourHeatPelletLevel(FourHeatPelletNumber):
    """Pellets left in the tank (estimated). Can be corrected by hand."""

    _attr_translation_key = "pellet_level"
    _attr_native_min_value = 0
    _attr_native_step = 0.1

    def __init__(self, coordinator: FourHeatCoordinator) -> None:
        super().__init__(coordinator, "pellet_level")

    @property
    def native_max_value(self) -> float:
        return self.coordinator.user.capacity

    @property
    def native_value(self) -> float | None:
        level = self.coordinator.user.level
        return None if level is None else round(level, 1)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.user.set_level(value)
