"""LUNOS Heat Recovery Ventilation Fan Control (e2/eGO)"""
import time
import logging

from homeassistant.components.fan import (
    SPEED_OFF,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_HIGH,
    SUPPORT_SET_SPEED,
    STATE_ON,
    STATE_OFF,
    FanEntity
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_SPEED = SPEED_MEDIUM
SPEED_LIST = [
    SPEED_OFF,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_HIGH
#    SPEED_ON  # FIXME: remove?  is this really a speed....
]

# configuration of switch states to active LUNOS speedsy
SPEED_SWITCH_STATES = {
    SPEED_OFF:    [ STATE_OFF, STATE_OFF ],
    SPEED_LOW:    [ STATE_ON,  STATE_OFF ],
    SPEED_MEDIUM: [ STATE_OFF, STATE_ON  ],
    SPEED_HIGH:   [ STATE_ON,  STATE_ON  ]
}

# flipping W1 or W2 within 3 seconds instructs the LUNOS controller to either clear the
# filter warning light (W1) or turn on the summer/night ventilation mode (W2), thus
# delay all state changes to be > 3 seconds since the last switch change
STATE_CHANGE_DELAY_SECONDS = 4

CONF_RELAY_W1 = 'relay_w1'
CONF_RELAY_W2 = 'relay_w1'
CONF_DEFAULT_SPEED = 'default_speed'

#FAN_SCHEMA = vol.Schema(
#    {
#        vol.Optional(CONF_FRIENDLY_NAME): cv.string,
#        vol.Optional(CONF_DEFAULT_SPEED, default=DEFAULT_SPEED): vol.In(SPEED_LIST),
#        vol.Optional(CONF_RELAY_W1): cv.string,  # cv.entity_id
#        vol.Optional(CONF_RELAY_W2): cv.string,  # cv.entity_id
#        vol.Optional(CONF_ENTITY_ID): cv.entity_id,
#    }
#)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Old way of setting up fans"""
    pass

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Initialize the LUNOS fans from config."""
    pass
#    async def async_discover(discovery_info):
#        await _async_setup_entities(
#            hass, config_entry, async_add_entities, [discovery_info]
#        )

async def _async_setup_entities(
    hass, config_entry, async_add_entities, discovery_infos
):
    """Set up the LUNOS fans."""
    fans = []
#    for discovery_info in discovery_infos:
#        fans.append(LUNOSFan(**discovery_info))
         # FIXME: pass in relay_w1 and relay_w2

    async_add_entities(fans, update_before_add=True)

class LUNOSFan(FanEntity):
    """Representation of a LUNOS fan."""

    def __init__(self, friendly_name, relay_w1, relay_w2, default_speed: str = DEFAULT_SPEED):
        """Init this sensor."""
        super().__init__()

        self._relay_w1 = relay_w1
        self._relay_w2 = relay_w2
        self._default_speed = default_speed

         # FIXME: determine current state!
        self._last_state_change = time.time()

#    async def async_added_to_hass(self):
#        """Run when about to be added to HASS."""
#        await super().async_added_to_hass()

    def determine_current_relay_state(self):
        # FIXME:
        return DEFAULT_SPEED # FIXME

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        return SUPPORT_SET_SPEED

    @property
    def speed_list(self) -> list:
        """Get the list of available speeds."""
        return SPEED_LIST

    @property
    def speed(self) -> str:
        """Return the current speed."""
        return self._state

    @property
    def is_on(self) -> bool:
        """Return true if entity is on."""
        if self._state is None:
            return False
        return self._state != SPEED_OFF

    # TOOD: last updated? controller type? cfm?
    @property
    def device_state_attributes(self):
        """Return state attributes."""
        return self.state_attributes

    def async_set_state(self, speed):
        """Handle state update from fan."""
        self._state = speed
        self.async_schedule_update_ha_state()

    async def async_turn_on(self, speed: str = None, **kwargs) -> None:
        """Turn the fan on."""
        if speed is None:
            speed = self._default_speed

        await self.async_set_speed(speed)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the fan off."""
        await self.async_set_speed(SPEED_OFF)

    def switch_to_state(switch, state):
        if state == STATE_OFF:
            switch.turn_off()
        else:
            switch.turn_on()

        
    async def async_set_speed(self, speed: str) -> None:
        """Set the speed of the fan."""
        switch_states = SPEED_SWITCH_STATES[speed]
        if switch_states == None:
            log.error(f"LUNOS fan '{self._name}' does not support speed '{speed}'; ignoring request to change speed.")
            return

        # flipping W1 or W2 within 3 seconds instructs the LUNOS controller to either clear the
        # filter warning light (W1) or turn on the summer/night ventilation mode (W2), thus
        # delay all state changes to be > 3 seconds since the last switch change
        # STATE_CHANGE_DELAY_SECONDS = 4

        switch_to_state(self._switch_w1, switch_states[0])
        switch_to_state(self._switch_w2, switch_states[1])
        self.async_set_state(speed)

    async def async_update(self):
        """Attempt to retrieve current state of the fan by inspecting the switch state."""
        await super().async_update()

        LOG.warn("LUNOS ventilation fan state update not yet supported!")
#        if self._fan_channel:
#            state = await self._fan_channel.get_attribute_value("fan_mode")
#            if state is not None:
#                self._state = VALUE_TO_SPEED.get(state, self._state)
