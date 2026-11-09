"""Thermostat entity for the stove."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CMD_OFF,
    CMD_ON,
    CODE_ROOM_TEMP,
    CODE_SETPOINT_READ,
    CODE_SETPOINT_WRITE,
    CODE_STATE,
    HEATING_STATES,
    IDLE_STATES,
    IGNITION_STATES,
    MAX_SETPOINT,
    MIN_SETPOINT,
    OFF_STATES,
)
from .coordinator import FourHeatConfigEntry
from .entity import FourHeatEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FourHeatConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([FourHeatClimate(entry.runtime_data, "climate")])


class FourHeatClimate(FourHeatEntity, ClimateEntity):
    """On/off and target temperature of the stove."""

    _attr_name = None
    _attr_translation_key = "stove"
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.OFF]
    _attr_min_temp = MIN_SETPOINT
    _attr_max_temp = MAX_SETPOINT
    _attr_target_temperature_step = 1
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    @property
    def current_temperature(self) -> float | None:
        return self.coordinator.value(CODE_ROOM_TEMP)

    @property
    def target_temperature(self) -> float | None:
        return self.coordinator.value(CODE_SETPOINT_READ)

    @property
    def hvac_mode(self) -> HVACMode | None:
        state = self.coordinator.value(CODE_STATE)
        if state is None:
            return None
        return HVACMode.OFF if state in OFF_STATES else HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction | None:
        state = self.coordinator.value(CODE_STATE)
        if state is None:
            return None
        if state in IGNITION_STATES:
            return HVACAction.PREHEATING
        if state in HEATING_STATES:
            return HVACAction.HEATING
        if state in IDLE_STATES:
            return HVACAction.IDLE
        return HVACAction.OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        value = int(round(min(max(temperature, MIN_SETPOINT), MAX_SETPOINT)))
        await self.coordinator.async_write(CODE_SETPOINT_WRITE, value)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.HEAT:
            await self.async_turn_on()
        elif hvac_mode == HVACMode.OFF:
            await self.async_turn_off()

    async def async_turn_on(self) -> None:
        await self.coordinator.async_command(CMD_ON)

    async def async_turn_off(self) -> None:
        await self.coordinator.async_command(CMD_OFF)
