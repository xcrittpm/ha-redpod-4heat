"""Data coordinator for the Red-Pod 4Heat (local) integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FourHeatClient, FourHeatError, Reading
from .const import (
    AUTO_VALUE,
    CODE_COMBUSTION_PHASE,
    CODE_COMBUSTION_POWER,
    CODE_SERVICE_HOURS_LEFT,
    CODE_STATE,
    DOMAIN,
    HEATING_STATES,
    MAX_HEAT_KW,
    MIN_HEAT_KW,
    SCAN_INTERVAL,
    SERVICE_WARNING_HOURS,
)

_LOGGER = logging.getLogger(__name__)

FourHeatConfigEntry = ConfigEntry["FourHeatCoordinator"]


class FourHeatCoordinator(DataUpdateCoordinator[dict[str, Reading]]):
    """Poll the stove and share its values with the entities."""

    config_entry: FourHeatConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: FourHeatConfigEntry, client: FourHeatClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Reading]:
        try:
            readings = await self.client.read_all()
        except FourHeatError as err:
            raise UpdateFailed(str(err)) from err
        # Keep codes that are missing from this answer (the module
        # sometimes reports a shorter list).
        merged = dict(self.data or {})
        merged.update(readings)
        self._update_service_issue(merged)
        return merged

    def _update_service_issue(self, data: dict[str, Reading]) -> None:
        """Show a repair issue when the service is due soon."""
        issue_id = f"service_due_{self.config_entry.entry_id}"
        hours = data.get(CODE_SERVICE_HOURS_LEFT)
        if hours is not None and hours.value <= SERVICE_WARNING_HOURS:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="service_due",
                translation_placeholders={
                    "name": self.config_entry.title,
                    "hours": str(max(hours.value, 0)),
                },
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)

    def estimated_heat_kw(self) -> float | None:
        """Estimate the heat output from the state and power level.

        While running, code 30011 reports the power level the stove is
        actually burning at (1-5). P1-P5 are spread evenly between minimum
        and nominal power. In modulation the stove burns at minimum. If the
        actual level is not reported, fall back to the power setting (Auto
        burns at full power until the room is 1 °C above the target).
        """
        state = self.value(CODE_STATE)
        if state is None:
            return None
        if state not in HEATING_STATES:
            return 0.0
        actual = self.value(CODE_COMBUSTION_PHASE)
        if actual is not None and 1 <= actual <= 5:
            return self._level_kw(actual)
        if state == 6:  # modulation
            return MIN_HEAT_KW
        level = self.value(CODE_COMBUSTION_POWER)
        if level is None or level == AUTO_VALUE or not 1 <= level <= 5:
            return MAX_HEAT_KW
        return self._level_kw(level)

    @staticmethod
    def _level_kw(level: int) -> float:
        return round(MIN_HEAT_KW + (level - 1) * (MAX_HEAT_KW - MIN_HEAT_KW) / 4, 2)

    def value(self, code: str) -> int | None:
        """Return the current value of a code, or None if unknown."""
        if not self.data or code not in self.data:
            return None
        return self.data[code].value

    async def async_write(self, code: str, value: int) -> None:
        """Write a value and refresh."""
        try:
            await self.client.write(code, value)
        except FourHeatError as err:
            raise HomeAssistantError(f"Stove did not accept {code}={value}: {err}") from err
        await self.async_request_refresh()

    async def async_command(self, code: str) -> None:
        """Send a command and refresh."""
        try:
            await self.client.command(code)
        except FourHeatError as err:
            raise HomeAssistantError(f"Stove did not accept command {code}: {err}") from err
        await self.async_request_refresh()
