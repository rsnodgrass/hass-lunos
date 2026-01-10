"""Diagnostics support for LUNOS Heat Recovery Ventilation integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import LunosConfigEntry
from .const import CONF_RELAY_W1, CONF_RELAY_W2

# keys to redact from diagnostics output
TO_REDACT = {
    # entity IDs could reveal user's naming conventions
    CONF_RELAY_W1,
    CONF_RELAY_W2,
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: LunosConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data.coordinator
    coding_config = entry.runtime_data.coding_config

    # get controller coding used
    controller_coding = entry.data.get('controller_coding', 'unknown')
    model_config = coding_config.get(controller_coding, {})

    # get current coordinator data
    data = coordinator.data
    current_state = {
        'current_speed': data.current_speed if data else None,
        'w1_state': data.w1_state if data else None,
        'w2_state': data.w2_state if data else None,
        'fan_speeds': data.fan_speeds if data else [],
        'vent_modes': data.vent_modes if data else [],
    }

    # get fan entity state
    fan_entity_id = f'fan.{entry.title.lower().replace(" ", "_")}_ventilation_fan'
    fan_state = hass.states.get(fan_entity_id)
    entity_state = None
    if fan_state:
        entity_state = {
            'state': fan_state.state,
            'attributes': dict(fan_state.attributes),
        }

    return {
        'config_entry': {
            'entry_id': entry.entry_id,
            'title': entry.title,
            'data': async_redact_data(dict(entry.data), TO_REDACT),
            'options': async_redact_data(dict(entry.options), TO_REDACT),
        },
        'model_config': {
            'name': model_config.get('name'),
            'model_number': model_config.get('model_number'),
            'controller_coding': model_config.get('controller_coding'),
            'supports_off': model_config.get('supports_off'),
            'supports_summer_vent': model_config.get('supports_summer_vent'),
            'supports_exhaust_only': model_config.get('supports_exhaust_only'),
            'supports_filter_reminder': model_config.get('supports_filter_reminder'),
            'cycle_seconds': model_config.get('cycle_seconds'),
            'default_fan_count': model_config.get('default_fan_count'),
        },
        'coordinator_state': current_state,
        'entity_state': entity_state,
        'available_codings': list(coding_config.keys()),
    }
