"""Tests for LUNOS coordinator."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

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
    SPEED_HIGH,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_OFF,
    SPEED_SILENT,
)
from custom_components.lunos.coordinator import LunosCoordinator


@pytest.fixture
def mock_config_entry(mock_config_entry_data: dict[str, Any]) -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock()
    entry.data = mock_config_entry_data
    entry.entry_id = 'test_entry_id'
    entry.title = 'Test LUNOS'
    return entry


async def test_coordinator_init(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_lunos_codings: dict[str, Any],
    _mock_relay_states: None,
) -> None:
    """Test coordinator initialization."""
    coordinator = LunosCoordinator(hass, mock_config_entry, mock_lunos_codings)

    assert coordinator.relay_w1 == 'switch.lunos_w1'
    assert coordinator.relay_w2 == 'switch.lunos_w2'
    assert coordinator.controller_coding == DEFAULT_CONTROLLER_CODING
    assert coordinator.fan_count == 2


async def test_coordinator_speed_detection_off(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_lunos_codings: dict[str, Any],
    _mock_relay_states: None,
) -> None:
    """Test speed detection when both relays are off."""
    coordinator = LunosCoordinator(hass, mock_config_entry, mock_lunos_codings)
    data = await coordinator._async_update_data()

    assert data.current_speed == SPEED_OFF
    assert data.w1_state == STATE_OFF
    assert data.w2_state == STATE_OFF


async def test_coordinator_speed_detection_low(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_lunos_codings: dict[str, Any],
) -> None:
    """Test speed detection for low speed (W1=ON, W2=OFF)."""
    hass.states.async_set('switch.lunos_w1', STATE_ON)
    hass.states.async_set('switch.lunos_w2', STATE_OFF)

    coordinator = LunosCoordinator(hass, mock_config_entry, mock_lunos_codings)
    data = await coordinator._async_update_data()

    assert data.current_speed == SPEED_LOW
    assert data.w1_state == STATE_ON
    assert data.w2_state == STATE_OFF


async def test_coordinator_speed_detection_medium(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_lunos_codings: dict[str, Any],
) -> None:
    """Test speed detection for medium speed (W1=OFF, W2=ON)."""
    hass.states.async_set('switch.lunos_w1', STATE_OFF)
    hass.states.async_set('switch.lunos_w2', STATE_ON)

    coordinator = LunosCoordinator(hass, mock_config_entry, mock_lunos_codings)
    data = await coordinator._async_update_data()

    assert data.current_speed == SPEED_MEDIUM
    assert data.w1_state == STATE_OFF
    assert data.w2_state == STATE_ON


async def test_coordinator_speed_detection_high(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_lunos_codings: dict[str, Any],
    _mock_relay_states_on: None,
) -> None:
    """Test speed detection for high speed (W1=ON, W2=ON)."""
    coordinator = LunosCoordinator(hass, mock_config_entry, mock_lunos_codings)
    data = await coordinator._async_update_data()

    assert data.current_speed == SPEED_HIGH
    assert data.w1_state == STATE_ON
    assert data.w2_state == STATE_ON


async def test_coordinator_4speed_mode(
    hass: HomeAssistant,
    mock_lunos_codings: dict[str, Any],
) -> None:
    """Test coordinator with 4-speed fan that has no OFF state."""
    entry = MagicMock()
    entry.data = {
        'name': 'Test 4-speed',
        CONF_RELAY_W1: 'switch.lunos_w1',
        CONF_RELAY_W2: 'switch.lunos_w2',
        CONF_CONTROLLER_CODING: 'e2-4speed',
        CONF_FAN_COUNT: 2,
        CONF_DEFAULT_SPEED: DEFAULT_SPEED,
    }
    entry.entry_id = 'test_4speed_entry'

    hass.states.async_set('switch.lunos_w1', STATE_OFF)
    hass.states.async_set('switch.lunos_w2', STATE_OFF)

    coordinator = LunosCoordinator(hass, entry, mock_lunos_codings)
    data = await coordinator._async_update_data()

    # 4-speed mode should show SILENT instead of OFF when both relays are off
    assert data.current_speed == SPEED_SILENT
    assert SPEED_OFF not in data.fan_speeds
    assert SPEED_SILENT in data.fan_speeds


async def test_coordinator_vent_modes(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_lunos_codings: dict[str, Any],
    _mock_relay_states: None,
) -> None:
    """Test that coordinator returns correct vent modes."""
    coordinator = LunosCoordinator(hass, mock_config_entry, mock_lunos_codings)
    data = await coordinator._async_update_data()

    # e2-usa supports summer vent but not exhaust only
    assert 'eco' in data.vent_modes
    assert 'summer' in data.vent_modes
    assert 'exhaust' not in data.vent_modes


async def test_coordinator_missing_relay(
    hass: HomeAssistant,
    mock_config_entry: MagicMock,
    mock_lunos_codings: dict[str, Any],
) -> None:
    """Test coordinator behavior when relay entity is missing."""
    # don't set up any relay states
    coordinator = LunosCoordinator(hass, mock_config_entry, mock_lunos_codings)
    data = await coordinator._async_update_data()

    # should return None speed when relays can't be found
    assert data.current_speed is None
    assert data.w1_state is None
