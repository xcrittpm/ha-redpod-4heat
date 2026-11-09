"""Diagnostics for the Red-Pod 4Heat (local) integration."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import FourHeatConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: FourHeatConfigEntry
) -> dict[str, Any]:
    """Return every code the module reports (no secrets: the protocol has none)."""
    coordinator = entry.runtime_data
    return {
        "readings": {
            code: {"marker": reading.marker, "value": reading.value}
            for code, reading in sorted((coordinator.data or {}).items())
        },
        "last_update_success": coordinator.last_update_success,
    }
