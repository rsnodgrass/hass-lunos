"""Tests for LUNOS fan entity."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
import pytest

from custom_components.lunos.const import (
    DEFAULT_SPEED,
    DOMAIN,
    SPEED_HIGH,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_OFF,
)
from custom_components.lunos.coordinator import LunosCoordinator, LunosData
from custom_components.lunos.fan import LUNOSFan


@pytest.fixture
def mock_coordinator(
    hass: HomeAssistant,
    mock_lunos_codings: dict[str, Any],
) -> MagicMock:
    """Create a mock coordinator."""
    coordinator = MagicMock(spec=LunosCoordinator)
    coordinator.hass = hass
    coordinator.data = LunosData(
        current_speed=SPEED_OFF,
        w1_state=STATE_OFF,
        w2_state=STATE_OFF,
        model_config=mock_lunos_codings['e2-usa'],
        relay_state_map={
            SPEED_OFF: [STATE_OFF, STATE_OFF],
            SPEED_LOW: [STATE_ON, STATE_OFF],
            SPEED_MEDIUM: [STATE_OFF, STATE_ON],
            SPEED_HIGH: [STATE_ON, STATE_ON],
        },
        fan_speeds=[SPEED_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH],
        vent_modes=['eco', 'summer'],
    )
    return coordinator


@pytest.fixture
def mock_entry(mock_config_entry_data: dict[str, Any]) -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock()
    entry.data = mock_config_entry_data
    entry.entry_id = 'test_entry_id'
    entry.title = 'Test LUNOS'
    return entry


async def test_fan_creation(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    mock_entry: MagicMock,
    mock_lunos_codings: dict[str, Any],
    _mock_relay_states: None,
) -> None:
    """Test fan entity creation."""
    fan = LUNOSFan(
        coordinator=mock_coordinator,
        entry=mock_entry,
        coding_config=mock_lunos_codings,
        name='Test LUNOS Fan',
        relay_w1='switch.lunos_w1',
        relay_w2='switch.lunos_w2',
        default_speed=DEFAULT_SPEED,
    )
    fan.hass = hass

    assert fan.unique_id == 'switch.lunos_w1_switch.lunos_w2'
    assert fan.speed_count == 3  # low, medium, high (not counting off)
    assert SPEED_OFF in fan._fan_speeds
    assert fan.preset_modes == ['eco', 'summer']


async def test_fan_is_on(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    mock_entry: MagicMock,
    mock_lunos_codings: dict[str, Any],
    _mock_relay_states: None,
) -> None:
    """Test fan is_on property."""
    fan = LUNOSFan(
        coordinator=mock_coordinator,
        entry=mock_entry,
        coding_config=mock_lunos_codings,
        name='Test LUNOS Fan',
        relay_w1='switch.lunos_w1',
        relay_w2='switch.lunos_w2',
        default_speed=DEFAULT_SPEED,
    )
    fan.hass = hass

    # initially off
    assert fan.is_on is False

    # simulate turning on
    fan._current_speed = SPEED_MEDIUM
    assert fan.is_on is True


async def test_fan_percentage(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    mock_entry: MagicMock,
    mock_lunos_codings: dict[str, Any],
    _mock_relay_states: None,
) -> None:
    """Test fan percentage calculation."""
    fan = LUNOSFan(
        coordinator=mock_coordinator,
        entry=mock_entry,
        coding_config=mock_lunos_codings,
        name='Test LUNOS Fan',
        relay_w1='switch.lunos_w1',
        relay_w2='switch.lunos_w2',
        default_speed=DEFAULT_SPEED,
    )
    fan.hass = hass

    # off = 0%
    fan._current_speed = SPEED_OFF
    assert fan.percentage == 0

    # low = 33%
    fan._current_speed = SPEED_LOW
    assert fan.percentage == 33

    # medium = 66%
    fan._current_speed = SPEED_MEDIUM
    assert fan.percentage == 66

    # high = 100%
    fan._current_speed = SPEED_HIGH
    assert fan.percentage == 100


async def test_fan_supported_features(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    mock_entry: MagicMock,
    mock_lunos_codings: dict[str, Any],
    _mock_relay_states: None,
) -> None:
    """Test fan supported features."""
    from homeassistant.components.fan import FanEntityFeature

    fan = LUNOSFan(
        coordinator=mock_coordinator,
        entry=mock_entry,
        coding_config=mock_lunos_codings,
        name='Test LUNOS Fan',
        relay_w1='switch.lunos_w1',
        relay_w2='switch.lunos_w2',
        default_speed=DEFAULT_SPEED,
    )
    fan.hass = hass

    features = fan.supported_features

    assert features & FanEntityFeature.SET_SPEED
    assert features & FanEntityFeature.TURN_ON
    assert features & FanEntityFeature.TURN_OFF
    assert features & FanEntityFeature.PRESET_MODE


async def test_fan_extra_attributes(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    mock_entry: MagicMock,
    mock_lunos_codings: dict[str, Any],
    _mock_relay_states: None,
) -> None:
    """Test fan extra state attributes."""
    fan = LUNOSFan(
        coordinator=mock_coordinator,
        entry=mock_entry,
        coding_config=mock_lunos_codings,
        name='Test LUNOS Fan',
        relay_w1='switch.lunos_w1',
        relay_w2='switch.lunos_w2',
        default_speed=DEFAULT_SPEED,
    )
    fan.hass = hass

    attrs = fan.extra_state_attributes

    assert 'model' in attrs
    assert 'controller_coding' in attrs
    assert 'fan_count' in attrs
    assert 'relay_w1' in attrs
    assert 'relay_w2' in attrs
    assert 'fan_speeds' in attrs
    assert 'vent_modes' in attrs
    assert attrs['fan_count'] == 2


async def test_fan_device_info(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    mock_entry: MagicMock,
    mock_lunos_codings: dict[str, Any],
    _mock_relay_states: None,
) -> None:
    """Test fan device info."""
    fan = LUNOSFan(
        coordinator=mock_coordinator,
        entry=mock_entry,
        coding_config=mock_lunos_codings,
        name='Test LUNOS Fan',
        relay_w1='switch.lunos_w1',
        relay_w2='switch.lunos_w2',
        default_speed=DEFAULT_SPEED,
    )
    fan.hass = hass

    device_info = fan.device_info

    assert device_info['identifiers'] == {(DOMAIN, 'switch.lunos_w1_switch.lunos_w2')}
    assert device_info['manufacturer'] == 'LUNOS'
    assert 'name' in device_info


async def test_fan_supports_summer_ventilation(
    hass: HomeAssistant,
    mock_coordinator: MagicMock,
    mock_entry: MagicMock,
    mock_lunos_codings: dict[str, Any],
    _mock_relay_states: None,
) -> None:
    """Test summer ventilation support detection."""
    fan = LUNOSFan(
        coordinator=mock_coordinator,
        entry=mock_entry,
        coding_config=mock_lunos_codings,
        name='Test LUNOS Fan',
        relay_w1='switch.lunos_w1',
        relay_w2='switch.lunos_w2',
        default_speed=DEFAULT_SPEED,
    )
    fan.hass = hass

    # e2-usa supports summer vent
    assert fan.supports_summer_ventilation() is True
