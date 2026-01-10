"""DataUpdateCoordinator for LUNOS Heat Recovery Ventilation integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_CONTROLLER_CODING,
    CONF_DEFAULT_FAN_COUNT,
    CONF_FAN_COUNT,
    CONF_RELAY_W1,
    CONF_RELAY_W2,
    DEFAULT_CONTROLLER_CODING,
    SPEED_HIGH,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_OFF,
    SPEED_SILENT,
)

if TYPE_CHECKING:
    from homeassistant.core import Event

LOG = logging.getLogger(__name__)


@dataclass
class LunosData:
    """Data class for LUNOS coordinator state."""

    current_speed: str | None = None
    w1_state: str | None = None
    w2_state: str | None = None
    model_config: dict[str, Any] = field(default_factory=dict)
    relay_state_map: dict[str, list[str]] = field(default_factory=dict)
    fan_speeds: list[str] = field(default_factory=list)
    vent_modes: list[str] = field(default_factory=list)


class LunosCoordinator(DataUpdateCoordinator[LunosData]):
    """Coordinator for LUNOS fan data updates.

    This coordinator monitors the W1/W2 relay states and determines the
    current fan speed based on their states. Since the LUNOS controller
    is managed by physical relays, we use push-based updates by listening
    to state changes on the relay entities.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coding_config: dict[str, Any],
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOG,
            name=f'LUNOS {entry.title}',
            # no update_interval since we use push updates from relay state changes
        )
        self.entry = entry
        self.coding_config = coding_config

        # extract config values
        self._relay_w1: str = entry.data[CONF_RELAY_W1]
        self._relay_w2: str = entry.data[CONF_RELAY_W2]
        self._controller_coding: str = entry.data.get(
            CONF_CONTROLLER_CODING, DEFAULT_CONTROLLER_CODING
        )

        # get model configuration
        self._model_config = coding_config.get(self._controller_coding, {})
        self._fan_count: int = entry.data.get(
            CONF_FAN_COUNT,
            self._model_config.get(CONF_DEFAULT_FAN_COUNT, 2),
        )

        # build relay state map
        self._relay_state_map = self._build_relay_state_map()
        self._fan_speeds = list(self._relay_state_map.keys())

        # initialize unsub callback
        self._unsub_state_change: callback | None = None

    def _build_relay_state_map(self) -> dict[str, list[str]]:
        """Build the mapping from speed names to W1/W2 relay states."""
        supports_off = self._model_config.get('supports_off', True)

        if supports_off:
            return {
                SPEED_OFF: [STATE_OFF, STATE_OFF],
                SPEED_LOW: [STATE_ON, STATE_OFF],
                SPEED_MEDIUM: [STATE_OFF, STATE_ON],
                SPEED_HIGH: [STATE_ON, STATE_ON],
            }
        else:
            # 4-speed fans that cannot be fully turned off
            return {
                SPEED_SILENT: [STATE_OFF, STATE_OFF],
                SPEED_LOW: [STATE_ON, STATE_OFF],
                SPEED_MEDIUM: [STATE_OFF, STATE_ON],
                SPEED_HIGH: [STATE_ON, STATE_ON],
            }

    async def _async_update_data(self) -> LunosData:
        """Fetch data from relays and determine current state."""
        w1_state = self._get_relay_state(self._relay_w1)
        w2_state = self._get_relay_state(self._relay_w2)
        current_speed = self._determine_speed_from_states(w1_state, w2_state)

        return LunosData(
            current_speed=current_speed,
            w1_state=w1_state,
            w2_state=w2_state,
            model_config=self._model_config,
            relay_state_map=self._relay_state_map,
            fan_speeds=self._fan_speeds,
            vent_modes=self._get_vent_modes(),
        )

    def _get_relay_state(self, entity_id: str) -> str | None:
        """Get the current state of a relay entity."""
        state = self.hass.states.get(entity_id)
        if state is None:
            LOG.warning('Relay entity %s not found', entity_id)
            return None
        return state.state

    def _determine_speed_from_states(
        self, w1_state: str | None, w2_state: str | None
    ) -> str | None:
        """Determine the fan speed based on W1/W2 relay states."""
        if w1_state is None or w2_state is None:
            return None

        current_state = [w1_state, w2_state]
        for speed, relay_states in self._relay_state_map.items():
            if current_state == relay_states:
                LOG.debug('Determined LUNOS speed=%s from W1/W2=%s', speed, current_state)
                return speed

        LOG.warning(
            'Could not determine speed from relay states: W1=%s, W2=%s',
            w1_state,
            w2_state,
        )
        return None

    def _get_vent_modes(self) -> list[str]:
        """Get available ventilation modes based on model configuration."""
        from .const import VENT_ECO, VENT_EXHAUST_ONLY, VENT_SUMMER

        modes = [VENT_ECO]
        if self._model_config.get('supports_summer_vent'):
            modes.append(VENT_SUMMER)
        if self._model_config.get('supports_exhaust_only'):
            modes.append(VENT_EXHAUST_ONLY)
        return modes

    async def async_added_to_hass(self) -> None:
        """Set up state change listeners when added to hass."""
        self._unsub_state_change = async_track_state_change_event(
            self.hass,
            [self._relay_w1, self._relay_w2],
            self._handle_relay_state_change,
        )

    @callback
    def _handle_relay_state_change(self, event: Event) -> None:
        """Handle state changes in W1/W2 relays."""
        entity_id = event.data.get('entity_id')
        new_state = event.data.get('new_state')
        old_state = event.data.get('old_state')

        if new_state is None:
            return

        from_state = old_state.state if old_state else None
        to_state = new_state.state

        if from_state != to_state:
            LOG.info(
                'Relay %s changed: %s -> %s, refreshing LUNOS state',
                entity_id,
                from_state,
                to_state,
            )
            self.hass.async_create_task(self.async_request_refresh())

    @property
    def relay_w1(self) -> str:
        """Return the W1 relay entity ID."""
        return self._relay_w1

    @property
    def relay_w2(self) -> str:
        """Return the W2 relay entity ID."""
        return self._relay_w2

    @property
    def model_config(self) -> dict[str, Any]:
        """Return the model configuration."""
        return self._model_config

    @property
    def fan_count(self) -> int:
        """Return the number of fans."""
        return self._fan_count

    @property
    def controller_coding(self) -> str:
        """Return the controller coding."""
        return self._controller_coding
