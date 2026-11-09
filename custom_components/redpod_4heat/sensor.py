"""Sensors for the stove."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CODE_COMBUSTION_PHASE,
    CODE_ERROR,
    COMBUSTION_PHASE_NAMES,
    CODE_EXHAUST_TEMP,
    CODE_ROOM_TEMP,
    CODE_SERVICE_HOURS_LEFT,
    CODE_STATE,
    ERROR_NAMES,
    STATE_NAMES,
)
from .coordinator import FourHeatConfigEntry, FourHeatCoordinator
from .entity import FourHeatEntity


def _named(names: dict[int, str]) -> Callable[[int | None], str | None]:
    def convert(value: int | None) -> str | None:
        if value is None:
            return None
        return names.get(value, "unknown")

    return convert


@dataclass(frozen=True, kw_only=True)
class FourHeatSensorDescription(SensorEntityDescription):
    """Describes a stove sensor."""

    code: str
    convert: Callable[[int | None], Any] = lambda value: value


SENSORS: tuple[FourHeatSensorDescription, ...] = (
    FourHeatSensorDescription(
        key="state",
        translation_key="state",
        code=CODE_STATE,
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(STATE_NAMES.values()) | {"unknown"}),
        convert=_named(STATE_NAMES),
    ),
    FourHeatSensorDescription(
        key="error",
        translation_key="error",
        code=CODE_ERROR,
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(ERROR_NAMES.values()) | {"unknown"}),
        convert=_named(ERROR_NAMES),
    ),
    FourHeatSensorDescription(
        key="combustion_phase",
        translation_key="combustion_phase",
        code=CODE_COMBUSTION_PHASE,
        device_class=SensorDeviceClass.ENUM,
        options=sorted(set(COMBUSTION_PHASE_NAMES.values()) | {"unknown"}),
        convert=_named(COMBUSTION_PHASE_NAMES),
    ),
    FourHeatSensorDescription(
        key="exhaust_temperature",
        translation_key="exhaust_temperature",
        code=CODE_EXHAUST_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    FourHeatSensorDescription(
        key="room_temperature",
        translation_key="room_temperature",
        code=CODE_ROOM_TEMP,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    FourHeatSensorDescription(
        key="service_hours_left",
        translation_key="service_hours_left",
        code=CODE_SERVICE_HOURS_LEFT,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FourHeatConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        FourHeatSensor(coordinator, description)
        for description in SENSORS
        if description.code in (coordinator.data or {})
    ]
    entities.append(FourHeatRawSensor(coordinator))
    async_add_entities(entities)


class FourHeatSensor(FourHeatEntity, SensorEntity):
    """A value read from the stove."""

    entity_description: FourHeatSensorDescription

    def __init__(
        self, coordinator: FourHeatCoordinator, description: FourHeatSensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        description = self.entity_description
        return description.convert(self.coordinator.value(description.code))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key in ("state", "error", "combustion_phase"):
            return {"code": self.coordinator.value(self.entity_description.code)}
        return None


class FourHeatRawSensor(FourHeatEntity, SensorEntity):
    """Every code the module reports, for finding out what unknown codes mean."""

    _attr_translation_key = "raw_data"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: FourHeatCoordinator) -> None:
        super().__init__(coordinator, "raw_data")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            f"{reading.marker}{code}": reading.value
            for code, reading in sorted((self.coordinator.data or {}).items())
        }
