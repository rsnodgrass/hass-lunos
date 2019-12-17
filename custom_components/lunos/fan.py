"""LUNOS Heat Recovery Ventilation Fan Control (e2/eGO)"""
import time
import logging
import voluptuous as vol

from homeassistant.const import CONF_NAME, CONF_ENTITY_ID
from homeassistant.components.fan import (
    PLATFORM_SCHEMA,
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
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import LUNOS_SETTINGS

LOG = logging.getLogger(__name__)

LUNOS_DOMAIN = 'lunos'

SPEED_TURBO = 'turbo' # FUTURE: support the special W2 extra-high mode
SPEED_LIST = [
    SPEED_OFF,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_HIGH
#    SPEED_ON  # FIXME: remove?  is this really a speed....
]
DEFAULT_SPEED = SPEED_MEDIUM

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

ATTR_CFM = 'cfm' # note: even when off some LUNOS fans still circulate air
ATTR_MODEL_NAME = 'model'
ATTR_VENTILATION_MODE = 'ventilation'  # [ normal, summer, exhaust-only ]

SERVICE_CLEAR_FILTER_REMINDER = 'lunos_clear_filter_reminder'
SERVICE_TURN_ON_SUMMER_VENTILATION = 'lunos_turn_on_summer_ventilation'
SERVICE_TURN_OFF_SUMMER_VENTILATION = 'lunos_turn_off_summer_ventilation'

CONF_RELAY_W1 = 'relay_w1'
CONF_RELAY_W2 = 'relay_w2'
CONF_DEFAULT_SPEED = 'default_speed'

CONF_CONTROLLER_CODING = 'controller_coding'
CONF_FAN_COUNT = 'fan_count'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_RELAY_W1): cv.string,  # cv.entity_id
        vol.Optional(CONF_RELAY_W2): cv.string,  # cv.entity_id
        vol.Optional(CONF_DEFAULT_SPEED, default=DEFAULT_SPEED): vol.In(SPEED_LIST),
        vol.Optional(CONF_CONTROLLER_CODING, default='e2-usa'): vol.In(LUNOS_SETTINGS.keys()),
        vol.Optional(CONF_FAN_COUNT, default='2'): vol.In( [ '1', '2', '3', '4' ]), # NOTE: should be controller_type defined
        vol.Optional(CONF_ENTITY_ID): cv.entity_id
    }
)

# pylint: disable=unused-argument
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Initialize the LUNOS fans from config."""
    name = config.get(CONF_NAME)
    relay_w1 = config.get(CONF_RELAY_W1)
    relay_w2 = config.get(CONF_RELAY_W2)
    default_speed = config.get(CONF_DEFAULT_SPEED)

    LOG.info(f"Found configuration for LUNOS fan controller '{name} setup with relays W1={relay_w1}, W2={relay_w2}'")

    fan = LUNOSFan(config, name, relay_w1, relay_w2, default_speed)
    async_add_entities([fan], update_before_add=True)

    #component.async_register_entity_service(SERVICE_CLEAR_FILTER_REMINDER:, {}, "async_clear_filter_reminder")
    #component.async_register_entity_service(SERVICE_TURN_ON_SUMMER_VENTILATION:, {}, "async_turn_on_summer_ventilation")
    #component.async_register_entity_service(SERVICE_TURN_OFF_SUMMER_VENTILATION:, {}, "async_turn_off_summer_ventilation")

    return True

class LUNOSFan(FanEntity):
    """Representation of a LUNOS fan."""

    def __init__(self, conf, name, relay_w1, relay_w2, default_speed: str = DEFAULT_SPEED):
        """Init this sensor."""
        self._name = name
        self._relay_w1 = relay_w1
        self._relay_w2 = relay_w2
        self._default_speed = default_speed

        coding = conf.get(CONF_CONTROLLER_CODING )
        model_config = LUNOS_SETTINGS[coding]

        # default fan count differs depending on what fans are attached to the controller (e2 = 2 fans, eGO = 1 fan)
        fan_count = conf.get(CONF_FAN_COUNT)
        if fan_count == None:
            fan_count = LUNOS_SETTINGS['default_fan_count']
        self._fan_count = fan_count

        self._state_attrs = {
            ATTR_MODEL_NAME: model_config['name'],
            CONF_CONTROLLER_CODING: coding,
            CONF_FAN_COUNT: fan_count,
            ATTR_CFM: 'Unknown',
            ATTR_VENTILATION_MODE: 'normal'  # TODO: support summer and exhaust-only
        }

        # FUTURE: pull effective CFM values from setting and number of configured fans
        # the current cfm expected based on fan speed should be an attribute
        #self._state_attrs[ATTR_CFM] = 10

         # FIXME: determine current state!
        self._last_state_change = time.time()

        LOG.info(f"Created LUNOS fan controller {name} (W1={relay_w1} / W2={relay_w2} / default_speed={default_speed})")

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

    def set_relay_state(self, relay, state):
        if state == STATE_OFF:
            relay.turn_off()
        else:
            relay.turn_on()
        
    async def async_set_speed(self, speed: str) -> None:
        """Set the speed of the fan."""
        switch_states = SPEED_SWITCH_STATES[speed]
        if switch_states == None:
            LOG.error(f"LUNOS fan '{self._name}' does not support speed '{speed}'; ignoring request to change speed.")
            return

        # flipping W1 or W2 within 3 seconds instructs the LUNOS controller to either clear the
        # filter warning light (W1) or turn on the summer/night ventilation mode (W2), thus
        # delay all state changes to be > 3 seconds since the last switch change
        # STATE_CHANGE_DELAY_SECONDS = 4

        self.set_relay_state(self._relay_w1, switch_states[0])
        self.set_relay_state(self._relay_w2, switch_states[1])
        self.async_set_state(speed)

    async def async_update(self):
        """Attempt to retrieve current state of the fan by inspecting the switch state."""

        LOG.error("Updating of LUNOS ventilation fan state update not yet supported!")
#        if self._fan_channel:
#            state = await self._fan_channel.get_attribute_value("fan_mode")
#            if state is not None:
#                self._state = VALUE_TO_SPEED.get(state, self._state)

    async def async_clear_filter_reminder(self):
        LOG.warn(f"Clearing the LUNOS filter reminder light is not currently supported")
        # flipping relay W1 within 3 seconds instructs the LUNOS controller to
        # clear the filter warning light

    async def async_turn_on_summer_ventilation(self):
        LOG.error(f"LUNOS summer/night ventilation mode not yet supported")
        # flipping relay W2 within 3 seconds instructs the LUNOS controller to
        # turn on summer ventilation mode

    async def async_turn_off_summer_ventilation(self):
        LOG.error(f"LUNOS summer/night ventilation mode not yet supported")
        # flipping relay W2 within 3 seconds instructs the LUNOS controller to
        # turn on summer ventilation mode
