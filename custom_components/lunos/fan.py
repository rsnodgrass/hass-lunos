"""LUNOS Heat Recovery Ventilation Fan Control (e2/eGO)"""
import time
import logging
import voluptuous as vol

from homeassistant.const import (
    CONF_NAME, CONF_ENTITY_ID,
    STATE_ON, STATE_OFF,
    SERVICE_TURN_ON, SERVICE_TURN_OFF, SERVICE_TOGGLE
)
from homeassistant.components.fan import (
    PLATFORM_SCHEMA,
    SUPPORT_SET_SPEED,
    SPEED_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH,
    FanEntity
)

import homeassistant.remote as rem
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_component import EntityComponent

from . import LUNOS_CODING_CONFIG

LOG = logging.getLogger(__name__)

LUNOS_DOMAIN = 'lunos'

SPEED_TURBO = 'turbo' # FUTURE: support the special W2 extra-high mode
SPEED_LIST = [
    SPEED_OFF,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_HIGH
]
DEFAULT_SPEED = SPEED_MEDIUM

# configuration of switch states to active LUNOS speedsy
SPEED_SWITCH_STATES = {
    SPEED_OFF:    [ STATE_OFF, STATE_OFF ],
    SPEED_LOW:    [ STATE_ON,  STATE_OFF ],
    SPEED_MEDIUM: [ STATE_OFF, STATE_ON  ],
    SPEED_HIGH:   [ STATE_ON,  STATE_ON  ]
}

# delay all speed changes to > 3 seconds since the last relay switch change to avoid side effects
SPEED_CHANGE_DELAY_SECONDS = 4

ATTR_CFM = 'cfm' # note: even when off some LUNOS fans still circulate air
ATTR_CMHR = 'cmh'
ATTR_DBA = 'dB'
ATTR_MODEL_NAME = 'model'
ATTR_VENTILATION_MODE = 'ventilation'  # [ normal, summer, exhaust-only ]

SERVICE_CLEAR_FILTER_REMINDER = 'lunos_clear_filter_reminder'
SERVICE_TURN_ON_SUMMER_VENTILATION = 'lunos_turn_on_summer_ventilation'
SERVICE_TURN_OFF_SUMMER_VENTILATION = 'lunos_turn_off_summer_ventilation'

CONF_CONTROLLER_CODING = 'controller_coding'
CONF_RELAY_W1 = 'relay_w1'
CONF_RELAY_W2 = 'relay_w2'
CONF_DEFAULT_SPEED = 'default_speed'
CONF_DEFAULT_FAN_COUNT = 'default_fan_count'
CONF_FAN_COUNT = 'fan_count'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_RELAY_W1): cv.string,  # cv.entity_id
        vol.Optional(CONF_RELAY_W2): cv.string,  # cv.entity_id
        vol.Optional(CONF_DEFAULT_SPEED, default=DEFAULT_SPEED): vol.In(SPEED_LIST),
        vol.Optional(CONF_CONTROLLER_CODING, default='e2-usa'): cv.string,
#        vol.Optional(CONF_CONTROLLER_CODING, default='e2-usa'): vol.In(LUNOS_CODING_CONFIG.keys()),
        vol.Optional(CONF_FAN_COUNT): vol.In( [ '1', '2', '3', '4' ]), # default is based on how controller is coded (see below)
        vol.Optional(CONF_ENTITY_ID): cv.entity_id
    }
)

CFM_TO_CMH = 1.69901 # 1 cubic feet/minute = 1.69901 cubic meters/hour

# pylint: disable=unused-argument
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Initialize the LUNOS fans from config."""
    name = config.get(CONF_NAME)
    relay_w1 = config.get(CONF_RELAY_W1)
    relay_w2 = config.get(CONF_RELAY_W2)
    default_speed = config.get(CONF_DEFAULT_SPEED)

    LOG.info(f"Coding supported {LUNOS_CODING_CONFIG.keys()}")

    LOG.info(f"Found configuration for LUNOS fan controller '{name}' setup with relays W1={relay_w1}, W2={relay_w2}'")

    fan = LUNOSFan(hass, config, name, relay_w1, relay_w2, default_speed)
    async_add_entities([fan], update_before_add=True)

    # expose service call APIs
    component = EntityComponent(LOG, LUNOS_DOMAIN, hass)
    component.async_register_entity_service(SERVICE_CLEAR_FILTER_REMINDER, {}, "async_clear_filter_reminder")
    component.async_register_entity_service(SERVICE_TURN_ON_SUMMER_VENTILATION, {}, "async_turn_on_summer_ventilation")
    component.async_register_entity_service(SERVICE_TURN_OFF_SUMMER_VENTILATION, {}, "async_turn_off_summer_ventilation")

    return True

class LUNOSFan(FanEntity):
    """Representation of a LUNOS fan."""

    def __init__(self, hass, conf, name, relay_w1, relay_w2, default_speed: str = DEFAULT_SPEED):
        """Init this sensor."""
        self._hass = hass

        self._name = name
        self._relay_w1 = relay_w1
        self._relay_w2 = relay_w2
        self._default_speed = default_speed

        coding = conf.get(CONF_CONTROLLER_CODING)
        model_config = LUNOS_CODING_CONFIG[coding]

        # default fan count differs depending on what fans are attached to the controller (e2 = 2 fans, eGO = 1 fan)
        fan_count = conf.get(CONF_FAN_COUNT)
        if fan_count == None:
            fan_count = model_config[CONF_DEFAULT_FAN_COUNT]
        self._fan_count = fan_count

        self._state_attrs = {
            ATTR_MODEL_NAME: model_config['name'],
            CONF_CONTROLLER_CODING: coding,
            CONF_FAN_COUNT: fan_count,
            ATTR_VENTILATION_MODE: 'normal',  # TODO: support summer and exhaust-only
            ATTR_DBA: 'Unknown'
        }

        self.update_attributes_based_on_mode()

        state = hass.states.get(self._relay_w1)
        LOG.info(f"State {self._relay_w1} = {state.state)}")
        state = hass.states.get(self._relay_w2)
        LOG.info(f"State {self._relay_w2} = {state.state)}")

         # FIXME: determine current state!
        self._last_state_change = time.time()

        LOG.info(f"Created LUNOS fan controller {name} (W1={relay_w1} / W2={relay_w2} / default_speed={default_speed})")

    # calculate the current CFM based on the current fan speed as well as the
    # number of fans configured by the user
    def update_attributes_based_on_mode(self):
        if self._state != None:
            coding = self._state_attrs[CONF_CONTROLLER_CODING]
            controller_config = LUNOS_SETTINGS[coding]

            cfm_for_mode = controller_config['cfm'][self._state]
            cfm_multiplier = self._fan_count / controller_config[CONF_DEFAULT_FAN_COUNT]
            self._state_attrs[ATTR_CFM] = cfm_for_mode * cfm_multiplier
            self._state_attrs[ATTR_CMHR] = self._state_attrs[ATTR_CFM] * CFM_TO_CMH

            #self._state_attrs[ATTR_DBA] = controller_config['dbA'][self._state]

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
        # NOTE: for 4-speed fans, there is never a true "OFF" setting
        return self._state != SPEED_OFF

    # TOOD: last updated? controller type? cfm?
    @property
    def device_state_attributes(self):
        """Return state attributes."""
        return self.state_attributes

    async def _async_set_state(self, speed):
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

    def determine_current_speed_setting(self):
        # FIXME: probe the two relays to determine current state and match to the SPEED_SWITCH_STATES table
        # self._state = speed
        return

    async def set_relay_switch_state(self, relay_entity_id, state):
        if state == STATE_OFF:
            self.switch_service_call('turn_off', relay_entity_id)
        else:
            self.switch_service_call('turn_on', relay_entity_id)
        
    def switch_service_call(self, method, relay_entity_id):
        self._hass.services.call('switch', method, { 'entity_id': relay }, False)
        self._last_state_change = time.time()

    async def async_set_speed(self, speed: str) -> None:
        """Set the speed of the fan."""
        switch_states = SPEED_SWITCH_STATES[speed]
        if switch_states == None:
            LOG.error(f"LUNOS fan '{self._name}' DOES NOT support speed '{speed}'; ignoring request to change speed.")
            return

        # flipping W1 or W2 within 3 seconds instructs the LUNOS controller to either clear the
        # filter warning light (W1) or turn on the summer/night ventilation mode (W2), thus
        # delay all state changes to be > 3 seconds since the last switch change
        now = time.time()
        if now < self._last_state_change + SPEED_CHANGE_DELAY_SECONDS:
            LOG.error("LUNOS currently DOES NOT delay switch toggles by at least 3 seconds to avoid confusing LUNOS controller")
            # FIXME: register a callback to fire after the required delay

        self.set_relay_switch_state(self._relay_w1, switch_states[0])
        self.set_relay_switch_state(self._relay_w2, switch_states[1])

        self._async_set_state(speed)

    async def async_update(self):
        """Attempt to retrieve current state of the fan by inspecting the switch state."""

        LOG.error("Updating of LUNOS ventilation fan state update not yet supported!")

    # flipping W1 within 3 seconds instructs the LUNOS controller to clear the filter warning light
    async def async_clear_filter_reminder(self):
        LOG.info(f"Clearing the change filter reminder light for LUNOS controller '{self._name}'")
        save_speed = self._state

        # flip W1 on off at least 2 times to clear reminder
        for i in range(3):
            self.switch_service_call(SERVICE_TURN_OFF, self._relay_w1)
            self.switch_service_call(SERVICE_TURN_ON, self._relay_w1)

        # reset back to the speed prior to toggling W1
        self.async_set_speed(save_speed)

    def supports_summer_ventilation(self):
        coding = self._state_attrs[CONF_CONTROLLER_CODING]
        controller_config = LUNOS_CODING_CONFIG[coding]
        return controller_config['supports_summer_vent'] == True

    # flipping W2 within 3 seconds instructs the LUNOS controller to turn on summer ventilation mode
    async def async_turn_on_summer_ventilation(self):
        if not self.supports_summer_ventilation():
            LOG.info(f"LUNOS controller '{self._name}' is coded and DOES NOT support summer ventilation")
            return

        LOG.info(f"Turning summer ventilation mode ON for LUNOS controller '{self._name}'")
        save_speed = self._state

        # flip W2 on off at least 2 times to enable summer ventilation
        for i in range(3):
            self.switch_service_call(SERVICE_TURN_OFF, self._relay_w2)
            self.switch_service_call(SERVICE_TURN_ON, self._relay_w2)

        # reset back to the speed prior to toggling W2
        self.async_set_speed(save_speed)

    async def async_turn_off_summer_ventilation(self):
        if not self.supports_summer_ventilation():
            return # silently ignore as it is already off

        # FIXME: must wait 10 seconds since the last time W2 was flipped before turning off ventilation will work
        LOG.info(f"Turning summer ventilation mode OFF for LUNOS controller '{self._name}'")

        # toggle the switch back and forth once (thus restoring existing state) to clear summer ventilation mode
        self.switch_service_call(SERVICE_TOGGLE, self._relay_w2)
        self.switch_service_call(SERVICE_TOGGLE, self._relay_w2)
