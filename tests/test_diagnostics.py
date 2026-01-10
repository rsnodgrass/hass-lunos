"""Tests for LUNOS diagnostics."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
import pytest

from custom_components.lunos.const import CONF_RELAY_W1, CONF_RELAY_W2
from custom_components.lunos.coordinator import LunosData
from custom_components.lunos.diagnostics import async_get_config_entry_diagnostics


@pytest.fixture
def mock_runtime_data(
    mock_lunos_codings: dict[str, Any],
) -> MagicMock:
    """Create mock runtime data."""
    coordinator = MagicMock()
    coordinator.data = LunosData(
        current_speed='medium',
        w1_state='off',
        w2_state='on',
        model_config=mock_lunos_codings['e2-usa'],
        relay_state_map={},
        fan_speeds=['off', 'low', 'medium', 'high'],
        vent_modes=['eco', 'summer'],
    )

    runtime_data = MagicMock()
    runtime_data.coordinator = coordinator
    runtime_data.coding_config = mock_lunos_codings

    return runtime_data


@pytest.fixture
def mock_config_entry_for_diag(
    mock_config_entry_data: dict[str, Any],
    mock_runtime_data: MagicMock,
) -> MagicMock:
    """Create mock config entry for diagnostics."""
    entry = MagicMock()
    entry.entry_id = 'test_entry_id'
    entry.title = 'Test LUNOS'
    entry.data = mock_config_entry_data
    entry.options = {}
    entry.runtime_data = mock_runtime_data
    return entry


async def test_diagnostics_output(
    hass: HomeAssistant,
    mock_config_entry_for_diag: MagicMock,
) -> None:
    """Test diagnostics output structure."""
    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry_for_diag)

    # verify structure
    assert 'config_entry' in diagnostics
    assert 'model_config' in diagnostics
    assert 'coordinator_state' in diagnostics
    assert 'available_codings' in diagnostics


async def test_diagnostics_redaction(
    hass: HomeAssistant,
    mock_config_entry_for_diag: MagicMock,
) -> None:
    """Test that sensitive data is redacted."""
    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry_for_diag)

    # relay entity IDs should be redacted
    config_data = diagnostics['config_entry']['data']
    assert config_data[CONF_RELAY_W1] == '**REDACTED**'
    assert config_data[CONF_RELAY_W2] == '**REDACTED**'


async def test_diagnostics_coordinator_state(
    hass: HomeAssistant,
    mock_config_entry_for_diag: MagicMock,
) -> None:
    """Test coordinator state in diagnostics."""
    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry_for_diag)

    coord_state = diagnostics['coordinator_state']
    assert coord_state['current_speed'] == 'medium'
    assert coord_state['w1_state'] == 'off'
    assert coord_state['w2_state'] == 'on'
    assert 'fan_speeds' in coord_state
    assert 'vent_modes' in coord_state


async def test_diagnostics_model_config(
    hass: HomeAssistant,
    mock_config_entry_for_diag: MagicMock,
) -> None:
    """Test model config in diagnostics."""
    diagnostics = await async_get_config_entry_diagnostics(hass, mock_config_entry_for_diag)

    model_config = diagnostics['model_config']
    assert model_config['name'] == 'LUNOS e2 (USA)'
    assert model_config['supports_off'] is True
    assert model_config['supports_summer_vent'] is True
