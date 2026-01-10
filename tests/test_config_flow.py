"""Tests for LUNOS config flow."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.lunos.const import (
    CONF_CONTROLLER_CODING,
    CONF_DEFAULT_SPEED,
    CONF_FAN_COUNT,
    CONF_RELAY_W1,
    CONF_RELAY_W2,
    DEFAULT_CONTROLLER_CODING,
    DEFAULT_SPEED,
    DOMAIN,
)


async def test_user_flow_success(
    hass: HomeAssistant,
    _mock_load_lunos_codings: Any,
    _mock_relay_states: None,
) -> None:
    """Test successful user flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={'source': config_entries.SOURCE_USER}
    )
    assert result['type'] == FlowResultType.FORM
    assert result['step_id'] == 'user'
    assert result['errors'] == {}

    result = await hass.config_entries.flow.async_configure(
        result['flow_id'],
        {
            'name': 'Test LUNOS',
            CONF_RELAY_W1: 'switch.lunos_w1',
            CONF_RELAY_W2: 'switch.lunos_w2',
            CONF_CONTROLLER_CODING: DEFAULT_CONTROLLER_CODING,
            CONF_FAN_COUNT: 2,
            CONF_DEFAULT_SPEED: DEFAULT_SPEED,
        },
    )

    assert result['type'] == FlowResultType.CREATE_ENTRY
    assert result['title'] == 'Test LUNOS'
    assert result['data'] == {
        'name': 'Test LUNOS',
        CONF_RELAY_W1: 'switch.lunos_w1',
        CONF_RELAY_W2: 'switch.lunos_w2',
        CONF_CONTROLLER_CODING: DEFAULT_CONTROLLER_CODING,
        CONF_FAN_COUNT: 2,
        CONF_DEFAULT_SPEED: DEFAULT_SPEED,
    }


async def test_user_flow_same_relay_error(
    hass: HomeAssistant,
    _mock_load_lunos_codings: Any,
    _mock_relay_states: None,
) -> None:
    """Test user flow with same relay for W1 and W2."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={'source': config_entries.SOURCE_USER}
    )
    assert result['type'] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result['flow_id'],
        {
            'name': 'Test LUNOS',
            CONF_RELAY_W1: 'switch.lunos_w1',
            CONF_RELAY_W2: 'switch.lunos_w1',  # same as W1
            CONF_CONTROLLER_CODING: DEFAULT_CONTROLLER_CODING,
            CONF_FAN_COUNT: 2,
            CONF_DEFAULT_SPEED: DEFAULT_SPEED,
        },
    )

    assert result['type'] == FlowResultType.FORM
    assert result['errors'] == {'base': 'same_relay'}


async def test_user_flow_already_configured(
    hass: HomeAssistant,
    _mock_load_lunos_codings: Any,
    _mock_relay_states: None,
) -> None:
    """Test user flow when entry already exists."""
    # first entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={'source': config_entries.SOURCE_USER}
    )
    await hass.config_entries.flow.async_configure(
        result['flow_id'],
        {
            'name': 'Test LUNOS',
            CONF_RELAY_W1: 'switch.lunos_w1',
            CONF_RELAY_W2: 'switch.lunos_w2',
            CONF_CONTROLLER_CODING: DEFAULT_CONTROLLER_CODING,
            CONF_FAN_COUNT: 2,
            CONF_DEFAULT_SPEED: DEFAULT_SPEED,
        },
    )

    # second entry with same relays should abort
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={'source': config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result['flow_id'],
        {
            'name': 'Test LUNOS 2',
            CONF_RELAY_W1: 'switch.lunos_w1',
            CONF_RELAY_W2: 'switch.lunos_w2',
            CONF_CONTROLLER_CODING: DEFAULT_CONTROLLER_CODING,
            CONF_FAN_COUNT: 2,
            CONF_DEFAULT_SPEED: DEFAULT_SPEED,
        },
    )

    assert result['type'] == FlowResultType.ABORT
    assert result['reason'] == 'already_configured'


async def test_import_flow_success(
    hass: HomeAssistant,
    _mock_load_lunos_codings: Any,
    _mock_relay_states: None,
) -> None:
    """Test import flow from YAML."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={'source': config_entries.SOURCE_IMPORT},
        data={
            'name': 'Imported LUNOS',
            CONF_RELAY_W1: 'switch.lunos_w1',
            CONF_RELAY_W2: 'switch.lunos_w2',
            CONF_CONTROLLER_CODING: 'ego',
            CONF_FAN_COUNT: 1,
        },
    )

    assert result['type'] == FlowResultType.CREATE_ENTRY
    assert result['title'] == 'Imported LUNOS'
    assert result['data'][CONF_CONTROLLER_CODING] == 'ego'
    assert result['data'][CONF_FAN_COUNT] == 1


async def test_import_flow_missing_relays(
    hass: HomeAssistant,
    _mock_load_lunos_codings: Any,
) -> None:
    """Test import flow with missing relays."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={'source': config_entries.SOURCE_IMPORT},
        data={
            'name': 'Incomplete LUNOS',
            # missing relay_w1 and relay_w2
        },
    )

    assert result['type'] == FlowResultType.ABORT
    assert result['reason'] == 'missing_relays'
