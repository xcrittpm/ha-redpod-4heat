"""Sensors for the stove."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import time
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
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
    entities.append(FourHeatHeatPowerSensor(coordinator))
    entities.append(FourHeatHeatEnergySensor(coordinator))
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


class FourHeatHeatPowerSensor(FourHeatEntity, SensorEntity):
    """Estimated heat output right now (see FourHeatCoordinator.estimated_heat_kw)."""

    _attr_translation_key = "heat_power"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT

    def __init__(self, coordinator: FourHeatCoordinator) -> None:
        super().__init__(coordinator, "heat_power")

    @property
    def native_value(self) -> float | None:
        return self.coordinator.estimated_heat_kw()


# Ignore gaps longer than this (e.g. Home Assistant was stopped) instead of
# assuming the stove kept the same output the whole time.
MAX_INTEGRATION_GAP_S = 600


class FourHeatHeatEnergySensor(FourHeatEntity, RestoreSensor):
    """Estimated heat produced, adding up the heat output over time."""

    _attr_translation_key = "heat_energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: FourHeatCoordinator) -> None:
        super().__init__(coordinator, "heat_energy")
        self._total = 0.0
        self._last_kw: float | None = None
        self._last_time: float | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            try:
                self._total = float(last.native_value or 0)
            except (TypeError, ValueError):
                self._total = 0.0
        self._sample()

    @property
    def native_value(self) -> float:
        return round(self._total, 3)

    def _sample(self) -> None:
        now = time.monotonic()
        if self._last_kw is not None and self._last_time is not None:
            elapsed = now - self._last_time
            if 0 < elapsed <= MAX_INTEGRATION_GAP_S:
                self._total += self._last_kw * elapsed / 3600
        self._last_kw = self.coordinator.estimated_heat_kw()
        self._last_time = now

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.last_update_success:
            self._sample()
        else:
            # Do not count time while the stove cannot be read.
            self._last_kw = None
        super()._handle_coordinator_update()


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
