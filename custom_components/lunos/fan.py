"""LUNOS e2 and eGO fan control"""
import logging
y
from homeassistant.components.fan import (
    DOMAIN,
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

from . import LUNOS_DOMAIN

_LOGGER = logging.getLogger(__name__)

SPEED_LIST = [
    SPEED_OFF,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_HIGH,
#    SPEED_ON  # FIXME: remove?  is this really a speed....
]

DEFAULT_SPEED = SPEED_MEDIUM

ON  = STATE_
OFF = STATE_OFF

# configuration of switch states to active LUNOS speedsy
SPEED_SWITCH_STATES = {
    SPEED_OFF:    [ OFF, OFF ],
    SPEED_LOW:    [  ON, OFF ],
    SPEED_MEDIUM: [ OFF,  ON ],
    SPEED_HIGH:   [  ON,  ON ]
}

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
    entities = []
#    for discovery_info in discovery_infos:
#        entities.append(LUNOSFan(**discovery_info))

# FIXME: pass in switch_a and switch_b

#    async_add_entities(entities, update_before_add=True)

class LUNOSFan(FanEntity):
    """Representation of a LUNOS fan."""

    def __init__(self, unique_id, fan_device, channels, **kwargs):
        """Init this sensor."""
        super().__init__(unique_id, fan_device, channels, **kwargs)
        # FIXME: confirm the signature
        
        self._default_speed = DEFAULT_SPEED  # FIXME: allow default override?
#        self._switch_a = xxx
#        self._switch_b = xxx

         # FIXME: determine current state!

    async def async_added_to_hass(self):
        """Run when about to be added to HASS."""
        await super().async_added_to_hass()
#       await self.async_accept_signal(
#            self._fan_channel, SIGNAL_ATTR_UPDATED, self.async_set_state
#        )

    def determine_current_switch_state(self):
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

    # FIXME: are there any attributes!?
    @property
    def device_state_attributes(self):
        """Return state attributes."""
        return self.state_attributes

    # FIXME...effectively this should just call async_set_speed since it is the same thing (but with update ha state)
    def async_set_state(self, state):
        """Handle state update from channel."""
        self._state = VALUE_TO_SPEED.get(state, self._state)
        self.async_schedule_update_ha_state()

    async def async_turn_on(self, speed: str = None, **kwargs) -> None:
        """Turn the fan on."""
        if speed is None:
            speed = self._default_speed

        await self.async_set_speed(speed)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the fan off."""
        await self.async_set_speed(SPEED_OFF)

    async def async_set_speed(self, speed: str) -> None:
        """Set the speed of the fan."""
        switch_states = SPEED_SWITCH_STATES[speed]

#        switch1.set(switch_states[0])
#        switch2.set(switch_states[1])
# FIXME
        self._state = speed
        
        self.async_set_state(speed)

    async def async_update(self):
        """Attempt to retrieve on off state from the fan."""
        await super().async_update()
        if self._fan_channel:
            state = await self._fan_channel.get_attribute_value("fan_mode")
            if state is not None:
                self._state = VALUE_TO_SPEED.get(state, self._state)
