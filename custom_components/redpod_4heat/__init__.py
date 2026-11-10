"""The Red-Pod 4Heat (local) integration."""

from __future__ import annotations

from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, callback

from .api import FourHeatClient
from .const import DEFAULT_PORT
from .coordinator import FourHeatConfigEntry, FourHeatCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.TEXT,
]


async def async_setup_entry(hass: HomeAssistant, entry: FourHeatConfigEntry) -> bool:
    """Set up the stove from a config entry."""
    client = FourHeatClient(entry.data[CONF_HOST], entry.data.get(CONF_PORT, DEFAULT_PORT))
    coordinator = FourHeatCoordinator(hass, entry, client)
    await coordinator.user.async_load()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    @callback
    def _count_pellets() -> None:
        if coordinator.last_update_success:
            coordinator.user.sample(coordinator.estimated_pellet_kgh())
        else:
            # Do not count time while the stove cannot be read.
            coordinator.user.sample(None)

    entry.async_on_unload(coordinator.async_add_listener(_count_pellets))
    _count_pellets()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FourHeatConfigEntry) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.user.async_save_now()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
