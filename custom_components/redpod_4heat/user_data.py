"""Data the module does not report, kept by Home Assistant.

- The pellet level and total use. They are worked out from the estimated
  pellet use: every poll adds the current use (kg/h) times the time since the
  last poll. The level is only known after the user says how much is in the
  tank (the "Tank filled" button or the level number).
- The stove's model and serial number, typed in by the user.
"""

from __future__ import annotations

from collections.abc import Callable
import time
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .const import DEFAULT_TANK_KG, DOMAIN

STORAGE_VERSION = 1
SAVE_DELAY_S = 60
# Ignore gaps longer than this (e.g. Home Assistant was stopped) instead of
# assuming the stove kept burning at the same rate the whole time.
MAX_GAP_S = 600


class UserData:
    """Keep the pellet figures and stove details, saved across restarts."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}"
        )
        self.capacity: float = DEFAULT_TANK_KG
        self.level: float | None = None
        self.consumed: float = 0.0
        self.model: str = ""
        self.serial: str = ""
        self.rate: float | None = None
        self._last_time: float | None = None
        self._listeners: list[Callable[[], None]] = []

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.capacity = float(data.get("capacity", DEFAULT_TANK_KG))
        level = data.get("level")
        self.level = None if level is None else float(level)
        self.consumed = float(data.get("consumed", 0.0))
        self.model = str(data.get("model", ""))
        self.serial = str(data.get("serial", ""))

    # Pellets

    @property
    def percent(self) -> float | None:
        if self.level is None or self.capacity <= 0:
            return None
        return round(min(self.level / self.capacity, 1) * 100)

    @property
    def hours_left(self) -> float | None:
        """Hours until the tank is empty at the current use."""
        if self.level is None or not self.rate:
            return None
        return round(self.level / self.rate, 1)

    @callback
    def sample(self, rate: float | None) -> None:
        """Add the use since the last poll, then remember the current rate."""
        now = time.monotonic()
        if self.rate and self._last_time is not None:
            elapsed = now - self._last_time
            if 0 < elapsed <= MAX_GAP_S:
                used = self.rate * elapsed / 3600
                self.consumed += used
                if self.level is not None:
                    self.level = max(self.level - used, 0.0)
                self._save()
        self.rate = rate
        self._last_time = now if rate is not None else None
        self._notify()

    @callback
    def set_capacity(self, capacity: float) -> None:
        self.capacity = capacity
        if self.level is not None:
            self.level = min(self.level, capacity)
        self._changed()

    @callback
    def set_level(self, level: float) -> None:
        self.level = max(min(level, self.capacity), 0.0)
        self._changed()

    @callback
    def fill(self) -> None:
        self.set_level(self.capacity)

    # Stove details

    @callback
    def set_model(self, model: str) -> None:
        self.model = model.strip()
        self._changed()

    @callback
    def set_serial(self, serial: str) -> None:
        self.serial = serial.strip()
        self._changed()

    # Listeners and saving

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> CALLBACK_TYPE:
        self._listeners.append(listener)

        @callback
        def remove() -> None:
            self._listeners.remove(listener)

        return remove

    def _changed(self) -> None:
        self._save()
        self._notify()

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    def _as_dict(self) -> dict[str, Any]:
        return {
            "capacity": self.capacity,
            "level": self.level,
            "consumed": self.consumed,
            "model": self.model,
            "serial": self.serial,
        }

    def _save(self) -> None:
        self._store.async_delay_save(self._as_dict, SAVE_DELAY_S)

    async def async_save_now(self) -> None:
        await self._store.async_save(self._as_dict())
