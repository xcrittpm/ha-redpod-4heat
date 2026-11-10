"""Buttons for the stove: reset error and tank filled."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CMD_RESET_ERROR
from .coordinator import FourHeatConfigEntry
from .entity import FourHeatEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FourHeatConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            FourHeatResetErrorButton(coordinator, "reset_error"),
            FourHeatTankFilledButton(coordinator, "tank_filled"),
        ]
    )


class FourHeatResetErrorButton(FourHeatEntity, ButtonEntity):
    """Clear the stove's error.

    The stove only clears it if the cause is gone (for example the door is
    closed again).
    """

    _attr_translation_key = "reset_error"

    async def async_press(self) -> None:
        await self.coordinator.async_command(CMD_RESET_ERROR)


class FourHeatTankFilledButton(FourHeatEntity, ButtonEntity):
    """Tell Home Assistant the pellet tank was filled to the top."""

    _attr_translation_key = "tank_filled"

    async def async_press(self) -> None:
        self.coordinator.user.fill()
