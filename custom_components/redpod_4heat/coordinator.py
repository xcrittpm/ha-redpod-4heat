"""Data coordinator for the Red-Pod 4Heat (local) integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import FourHeatClient, FourHeatError, Reading
from .const import DOMAIN, SCAN_INTERVAL

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
        return merged

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
