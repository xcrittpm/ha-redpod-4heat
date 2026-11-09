"""Async client for the 4Heat WiFi module (local TCP protocol).

The module listens on TCP port 80 but does not speak HTTP. Each exchange opens
a socket, sends one JSON-like array and reads one JSON-like array back:

    -> ["SEL","0"]
    <- ["SEL","22","J30001000000000007","B20364000000000006", ...]

Each item is: one marker letter + 5-digit code + 12-character value.
Marker "J" means read-only, "B" means writable. A write is acknowledged with
the marker "A".

This module has no Home Assistant imports so it can be tested on its own.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import suppress
from dataclasses import dataclass

_LOGGER = logging.getLogger(__name__)

READ_QUERY = '["SEL","0"]'
ERROR_QUERY = '["SEC","3","I30001000000000000","I30002000000000000","I30017000000000000"]'


class FourHeatError(Exception):
    """Base error for the 4Heat client."""


class FourHeatConnectionError(FourHeatError):
    """The module could not be reached or did not answer."""


class FourHeatCommandError(FourHeatError):
    """The module answered but did not accept a command."""


@dataclass(frozen=True, slots=True)
class Reading:
    """One value reported by the stove."""

    marker: str
    value: int

    @property
    def writable(self) -> bool:
        """Return True if the stove allows writing this code."""
        return self.marker == "B"


def parse_item(item: str) -> tuple[str, Reading] | None:
    """Parse one item like 'J30001000000000007' into (code, Reading)."""
    if len(item) < 7 or not item[0].isalpha() or not item[1:6].isdigit():
        return None
    raw = item[6:]
    negative = "-" in raw
    digits = raw.replace("-", "")
    if not digits.isdigit():
        return None
    value = int(digits)
    return item[1:6], Reading(item[0], -value if negative else value)


def parse_response(text: str) -> list[str]:
    """Turn the raw answer into a list of strings."""
    text = text.strip()
    try:
        data = json.loads(text)
    except ValueError:
        data = [part.strip().strip('"') for part in text.strip("[]").split(",")]
    return [str(part) for part in data]


class FourHeatClient:
    """Talk to one 4Heat module."""

    def __init__(self, host: str, port: int = 80, timeout: float = 10.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        # The module handles one connection at a time.
        self._lock = asyncio.Lock()

    async def _exchange(self, payload: str) -> list[str]:
        async with self._lock:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port), self.timeout
                )
            except (OSError, asyncio.TimeoutError) as err:
                raise FourHeatConnectionError(
                    f"Cannot connect to {self.host}:{self.port}: {err}"
                ) from err

            data = b""
            try:
                writer.write(payload.encode("ascii"))
                await writer.drain()
                while True:
                    # Wait longer for the first bytes than for the rest.
                    wait = self.timeout if not data else 1.0
                    try:
                        chunk = await asyncio.wait_for(reader.read(4096), wait)
                    except asyncio.TimeoutError:
                        break
                    if not chunk:
                        break
                    data += chunk
                    if data.rstrip().endswith(b"]"):
                        break
            except OSError as err:
                raise FourHeatConnectionError(str(err)) from err
            finally:
                writer.close()
                with suppress(OSError, asyncio.TimeoutError):
                    await asyncio.wait_for(writer.wait_closed(), 2)

        if not data:
            raise FourHeatConnectionError(f"No answer from {self.host}")
        text = data.decode("ascii", errors="replace")
        _LOGGER.debug("4Heat %s -> %s", payload, text)
        return parse_response(text)

    async def read_all(self) -> dict[str, Reading]:
        """Read every value the module reports."""
        items = await self._exchange(READ_QUERY)
        if items and items[0] == "ERR":
            items = await self._exchange(ERROR_QUERY)
        readings: dict[str, Reading] = {}
        for item in items[2:]:
            parsed = parse_item(item)
            if parsed:
                readings[parsed[0]] = parsed[1]
        if not readings:
            raise FourHeatConnectionError(f"Unexpected answer: {items}")
        return readings

    async def write(self, code: str, value: int) -> None:
        """Write a value to a writable ("B") code."""
        if not (code.isdigit() and len(code) == 5) or not 0 <= value < 10**12:
            raise ValueError(f"Invalid code/value: {code}={value}")
        item = f"B{code}{value:012d}"
        await self._expect_ack(f'["SEC","1","{item}"]', code)

    async def command(self, code: str) -> None:
        """Send a command (on, off, reset error)."""
        await self._expect_ack(f'["SEC","1","J{code}000000000001"]', code)

    async def _expect_ack(self, payload: str, code: str) -> None:
        items = await self._exchange(payload)
        for item in items[2:]:
            parsed = parse_item(item)
            if parsed and parsed[0] == code:
                return
        raise FourHeatCommandError(f"Command not acknowledged: {payload} -> {items}")
