"""Power and fan level selectors for the stove."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import AUTO_VALUE, CODE_COMBUSTION_POWER, CODE_DUCTED_FAN, CODE_ROOM_FAN
from .coordinator import FourHeatConfigEntry
from .entity import FourHeatEntity

# Option key -> value written to the stove. 1-5 are manual levels, 6 is auto.
LEVEL_OPTIONS: dict[str, int] = {
    "auto": AUTO_VALUE,
    "level_1": 1,
    "level_2": 2,
    "level_3": 3,
    "level_4": 4,
    "level_5": 5,
}


@dataclass(frozen=True, kw_only=True)
class FourHeatSelectDescription(SelectEntityDescription):
    """Describes a level selector."""

    code: str


SELECTS: tuple[FourHeatSelectDescription, ...] = (
    FourHeatSelectDescription(
        key="combustion_power",
        translation_key="combustion_power",
        code=CODE_COMBUSTION_POWER,
        options=list(LEVEL_OPTIONS),
    ),
    FourHeatSelectDescription(
        key="room_fan",
        translation_key="room_fan",
        code=CODE_ROOM_FAN,
        options=list(LEVEL_OPTIONS),
    ),
    FourHeatSelectDescription(
        key="ducted_fan",
        translation_key="ducted_fan",
        code=CODE_DUCTED_FAN,
        options=list(LEVEL_OPTIONS),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FourHeatConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        FourHeatSelect(coordinator, description)
        for description in SELECTS
        # Only create selectors the stove actually reports.
        if description.code in (coordinator.data or {})
    )


class FourHeatSelect(FourHeatEntity, SelectEntity):
    """Choose Auto or a manual level 1-5."""

    entity_description: FourHeatSelectDescription

    def __init__(self, coordinator, description: FourHeatSelectDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def current_option(self) -> str | None:
        value = self.coordinator.value(self.entity_description.code)
        for option, option_value in LEVEL_OPTIONS.items():
            if option_value == value:
                return option
        return None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_write(self.entity_description.code, LEVEL_OPTIONS[option])
