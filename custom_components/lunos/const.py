"""Constants for the LUNOS Heat Recovery Ventilation integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = 'lunos'
DEFAULT_NAME: Final = 'LUNOS Ventilation'
DEFAULT_LUNOS_NAME: Final = DEFAULT_NAME

# Fan speed constants
SPEED_TURBO: Final = 'turbo'
SPEED_HIGH: Final = 'high'
SPEED_MEDIUM: Final = 'medium'
SPEED_LOW: Final = 'low'
SPEED_SILENT: Final = 'silent'  # for 4-speed fans when there is no off
SPEED_OFF: Final = 'off'

SPEED_MAX: Final = 'max'  # logical max speed
SPEED_MIN: Final = 'min'  # logical min speed

SPEED_LIST: Final[list[str]] = [
    SPEED_OFF,
    SPEED_SILENT,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_HIGH,
    SPEED_TURBO,
]
DEFAULT_SPEED: Final = SPEED_MEDIUM

# Preset modes (same as speeds for backward compatibility)
PRESET_SILENT: Final = SPEED_SILENT
PRESET_LOW: Final = SPEED_LOW
PRESET_MEDIUM: Final = SPEED_MEDIUM
PRESET_HIGH: Final = SPEED_HIGH
PRESET_TURBO: Final = SPEED_TURBO

# Timing constants for relay control
# delay all speed changes to > 3 seconds since the last relay switch change
SPEED_CHANGE_DELAY_SECONDS: Final = 4
DELAY_BETWEEN_FLIPS: Final = 0.100
MINIMUM_DELAY_BETWEEN_STATE_CHANGES: Final = 4.0

# Entity attribute keys
ATTR_CFM: Final = 'cfm'  # note: even when off some LUNOS fans still circulate air
ATTR_CMHR: Final = 'cmh'
ATTR_DB: Final = 'dB'
ATTR_MODEL_NAME: Final = 'model'
ATTR_WATTS: Final = 'watts'
ATTR_SPEED: Final = 'speed'
UNKNOWN: Final = 'Unknown'

# Ventilation mode attributes
ATTR_VENT_MODE: Final = 'vent_mode'
VENT_ECO: Final = 'eco'
VENT_SUMMER: Final = 'summer'  # also known as night mode
VENT_EXHAUST_ONLY: Final = 'exhaust'
VENT_MODES: Final[list[str]] = [VENT_ECO, VENT_SUMMER, VENT_EXHAUST_ONLY]
DEFAULT_VENT_MODE: Final = VENT_ECO

# Service names
SERVICE_CLEAR_FILTER_REMINDER: Final = 'clear_filter_reminder'
SERVICE_TURN_ON_SUMMER_VENTILATION: Final = 'turn_on_summer_ventilation'
SERVICE_TURN_OFF_SUMMER_VENTILATION: Final = 'turn_off_summer_ventilation'

# Configuration keys
CONF_CONTROLLER_CODING: Final = 'controller_coding'
CONF_RELAY_W1: Final = 'relay_w1'
CONF_RELAY_W2: Final = 'relay_w2'
CONF_DEFAULT_SPEED: Final = 'default_speed'
CONF_DEFAULT_FAN_COUNT: Final = 'default_fan_count'
CONF_FAN_COUNT: Final = 'fan_count'

# Unit conversion
CFM_TO_CMH: Final = 1.69901  # 1 cubic feet/minute = 1.69901 cubic meters/hour

# Default controller coding
DEFAULT_CONTROLLER_CODING: Final = 'e2-usa'
