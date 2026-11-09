"""Constants for the Red-Pod 4Heat (local) integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "redpod_4heat"

DEFAULT_PORT: Final = 80
DEFAULT_NAME: Final = "Estufa de pellets"
SCAN_INTERVAL: Final = timedelta(seconds=30)

# Read-only codes ("J" marker)
CODE_STATE: Final = "30001"
CODE_ERROR: Final = "30002"
CODE_EXHAUST_TEMP: Final = "30005"
CODE_ROOM_TEMP: Final = "30006"
CODE_SETPOINT_READ: Final = "30138"
CODE_SERVICE_HOURS_LEFT: Final = "20119"
CODE_COMBUSTION_PHASE: Final = "30011"  # meaning only partly known

# Writable codes ("B" marker)
CODE_SETPOINT_WRITE: Final = "20493"
CODE_COMBUSTION_POWER: Final = "20364"  # 1-5 manual, 6 = auto
CODE_ROOM_FAN: Final = "20575"  # 1-5, 6 = auto
CODE_DUCTED_FAN: Final = "20614"  # 1-5, 6 = auto

# Commands ("J" marker, value 1)
CMD_ON: Final = "30253"
CMD_OFF: Final = "30254"
CMD_RESET_ERROR: Final = "30255"

AUTO_VALUE: Final = 6

MIN_SETPOINT: Final = 5
MAX_SETPOINT: Final = 40

# Heat output from the Red-Pod P0147 manual (minimum and nominal power).
MIN_HEAT_KW: Final = 4.1
MAX_HEAT_KW: Final = 8.3

# Show a repair issue when this many hours or fewer are left until service.
SERVICE_WARNING_HOURS: Final = 50

# Stove states (code 30001)
STATE_NAMES: Final[dict[int, str]] = {
    0: "off",
    1: "check_up",
    2: "ignition",
    3: "stabilization",
    4: "ignition",
    5: "run",
    6: "modulation",
    7: "extinguishing",
    8: "safety",
    9: "block",
    10: "recover_ignition",
    11: "standby",
    13: "run",
    30: "ignition",
    31: "ignition",
    32: "ignition",
    33: "ignition",
    34: "ignition",
}

# States where the stove is not burning and not trying to burn.
OFF_STATES: Final = frozenset({0, 7, 8, 9})
IGNITION_STATES: Final = frozenset({1, 2, 3, 4, 10, 30, 31, 32, 33, 34})
HEATING_STATES: Final = frozenset({5, 6, 13})
IDLE_STATES: Final = frozenset({11})

# Combustion phase (code 30011). Only the values seen together with a known
# stove state are named; anything else is reported as "unknown".
COMBUSTION_PHASE_NAMES: Final[dict[int, str]] = {
    -1: "ignition",
    0: "stabilization",
    7: "off",
    9: "modulation",
}

# Error codes (code 30002), as shown on the display (ErXX)
ERROR_NAMES: Final[dict[int, str]] = {
    0: "none",
    1: "safety_thermostat",
    2: "pressure_switch",
    3: "flame_out",
    4: "water_overtemperature",
    5: "exhaust_overtemperature",
    7: "encoder_no_signal",
    8: "encoder_regulation",
    9: "low_water_pressure",
    10: "high_water_pressure",
    11: "clock_error",
    12: "ignition_failure",
    15: "power_failure",
    16: "display_link",
    18: "power_failure",
    39: "pressure_sensor",
    44: "door_open",
}
