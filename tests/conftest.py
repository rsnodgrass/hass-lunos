"""Fixtures for LUNOS tests."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import patch

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
import pytest

from custom_components.lunos.const import (
    CONF_CONTROLLER_CODING,
    CONF_DEFAULT_SPEED,
    CONF_FAN_COUNT,
    CONF_RELAY_W1,
    CONF_RELAY_W2,
    DEFAULT_CONTROLLER_CODING,
    DEFAULT_SPEED,
)


@pytest.fixture
def mock_config_entry_data() -> dict[str, Any]:
    """Return mock config entry data."""
    return {
        'name': 'Test LUNOS Fan',
        CONF_RELAY_W1: 'switch.lunos_w1',
        CONF_RELAY_W2: 'switch.lunos_w2',
        CONF_CONTROLLER_CODING: DEFAULT_CONTROLLER_CODING,
        CONF_FAN_COUNT: 2,
        CONF_DEFAULT_SPEED: DEFAULT_SPEED,
    }


@pytest.fixture
def mock_lunos_codings() -> dict[str, Any]:
    """Return mock LUNOS coding configurations."""
    return {
        'e2-usa': {
            'name': 'LUNOS e2 (USA)',
            'model_number': 'e2',
            'controller_coding': 6,
            'default_fan_count': 2,
            'supports_filter_reminder': True,
            'cycle_seconds': 70,
            'supports_summer_vent': True,
            'supports_off': True,
            'summer_vent_cycle_seconds': 3600,
            'behavior': {
                'off': {'decibel': 0, 'cfm': 0, 'watts': 0},
                'low': {'cfm': 10, 'decibel': 16.5},
                'medium': {'cfm': 15, 'decibel': 19.5},
                'high': {'cfm': 20, 'decibel': 26.0},
            },
        },
        'ego': {
            'name': 'LUNOS eGO',
            'model_number': 'eGO',
            'controller_coding': 9,
            'default_fan_count': 1,
            'supports_filter_reminder': True,
            'cycle_seconds': 50,
            'supports_summer_vent': True,
            'supports_off': True,
            'summer_vent_cycle_seconds': 3600,
            'behavior': {
                'off': {'decibel': 0, 'cfm': 0, 'watts': 0},
                'low': {'cfm': 3, 'cmh': 5},
                'medium': {'cmh': 10},
                'high': {'cmh': 20},
            },
        },
        'e2-4speed': {
            'name': 'LUNOS e2 (4-speed)',
            'model_number': 'e2',
            'controller_coding': 4,
            'default_fan_count': 2,
            'supports_filter_reminder': True,
            'supports_summer_vent': True,
            'supports_off': False,  # 4-speed has no OFF
            'cycle_seconds': 70,
            'behavior': {
                'off': {'cmh': 15},
                'low': {'cmh': 20},
                'medium': {'cmh': 30},
                'high': {'cmh': 38},
            },
        },
    }


@pytest.fixture
def mock_load_lunos_codings(mock_lunos_codings: dict[str, Any]) -> Generator:
    """Mock the load_lunos_codings function."""
    with patch(
        'custom_components.lunos.helpers.load_lunos_codings',
        return_value=mock_lunos_codings,
    ) as mock:
        yield mock


@pytest.fixture
def mock_relay_states(hass: HomeAssistant) -> None:
    """Set up mock relay states."""
    hass.states.async_set('switch.lunos_w1', STATE_OFF)
    hass.states.async_set('switch.lunos_w2', STATE_OFF)


@pytest.fixture
def mock_relay_states_on(hass: HomeAssistant) -> None:
    """Set up mock relay states in ON state."""
    hass.states.async_set('switch.lunos_w1', STATE_ON)
    hass.states.async_set('switch.lunos_w2', STATE_ON)
