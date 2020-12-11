"""LUNOS Heat Recovery Ventilation Fan Control (e2/eGO)"""
# FIXME: can we subscribe to updates from the w1/w2 entities to avoid polling?

import time
import asyncio
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

from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_component import EntityComponent

from . import LUNOS_CODING_CONFIG
from .const import (
    LUNOS_DOMAIN, DEFAULT_LUNOS_NAME,
    SPEED_TURBO, SPEED_LIST, DEFAULT_SPEED,
    ATTR_CFM, ATTR_CMHR, ATTR_DB, ATTR_MODEL_NAME, ATTR_VENTILATION_MODE,
    CONF_CONTROLLER_CODING, CONF_RELAY_W1, CONF_RELAY_W2, CONF_DEFAULT_SPEED,
    CONF_DEFAULT_FAN_COUNT, CONF_FAN_COUNT,
    UNKNOWN, CFM_TO_CMH,
    SERVICE_CLEAR_FILTER_REMINDER,
    SERVICE_TURN_ON_SUMMER_VENTILATION,
    SERVICE_TURN_OFF_SUMMER_VENTILATION
)

LOG = logging.getLogger(__name__)

DELAY_BETWEEN_FLIPS = 0.100
MINIMUM_DELAY_BETWEEN_STATE_CHANGES = 30.0

# configuration of switch states to active LUNOS speedsy
SPEED_SWITCH_STATES = {
    SPEED_OFF:    [ STATE_OFF, STATE_OFF ],
    SPEED_LOW:    [ STATE_ON,  STATE_OFF ],
    SPEED_MEDIUM: [ STATE_OFF, STATE_ON  ],
    SPEED_HIGH:   [ STATE_ON,  STATE_ON  ]
}

# delay all speed changes to > 3 seconds since the last relay switch change to avoid side effects
SPEED_CHANGE_DELAY_SECONDS = 4

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME): cv.string, # NOTE: we default the name later based on software
        vol.Optional(CONF_RELAY_W1): cv.string,  # cv.entity_id
        vol.Optional(CONF_RELAY_W2): cv.string,  # cv.entity_id
        vol.Optional(CONF_DEFAULT_SPEED, default=DEFAULT_SPEED): vol.In(SPEED_LIST),
#        vol.Optional(CONF_CONTROLLER_CODING, default='e2-usa'): cv.string,
        vol.Optional(CONF_CONTROLLER_CODING, default='e2-usa'): vol.In(LUNOS_CODING_CONFIG.keys()),
        vol.Optional(CONF_FAN_COUNT): vol.In( [ 1, 2, 3, 4 ]) # default is based on how controller is coded (see below)
    }
)

# pylint: disable=unused-argument
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Initialize the LUNOS fans from config."""
    name = config.get(CONF_NAME)
    if not name:
        name = DEFAULT_LUNOS_NAME

    relay_w1 = config.get(CONF_RELAY_W1)
    relay_w2 = config.get(CONF_RELAY_W2)
    default_speed = config.get(CONF_DEFAULT_SPEED)

    LOG.info(f"LUNOS fan controller '{name}' using relays W1={relay_w1}, W2={relay_w2}'")

    fan = LUNOSFan(hass, config, name, relay_w1, relay_w2, default_speed)
    async_add_entities([fan], update_before_add=True)

    # expose service call APIs
    # FIXME: how are these tied to a specific LUNOS fan instance?
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
        self._speed = None

        self._relay_w1 = relay_w1
        self.subscribe_to_state_changes(relay_w1)

        self._relay_w2 = relay_w2
        self.subscribe_to_state_changes(relay_w2)

        self._default_speed = default_speed

        coding = conf.get(CONF_CONTROLLER_CODING)
        model_config = LUNOS_CODING_CONFIG[coding]

        # default fan count differs depending on what fans are attached to the controller (e2 = 2 fans, eGO = 1 fan)
        fan_count = conf.get(CONF_FAN_COUNT)
        if fan_count == None:
            fan_count = model_config[CONF_DEFAULT_FAN_COUNT]
        self._fan_count = fan_count

        self._attributes = {
            ATTR_MODEL_NAME: model_config['name'],
            CONF_CONTROLLER_CODING: coding,
            CONF_FAN_COUNT: fan_count,
            ATTR_VENTILATION_MODE: 'normal',  # TODO: support summer and exhaust-only
            ATTR_DB: UNKNOWN,
            CONF_RELAY_W1: relay_w1,
            CONF_RELAY_W2: relay_w2
        }

        for attribute in [ 'cycle_seconds',
                           'supports_summer_vent',
                           'supports_filter_reminder',
                           'turbo_mode',
                           'exhaust_only' ]: 
            if attribute in model_config:
                self._attributes[attribute] = model_config[attribute]

        # determine the current speed of the fans
        self.determine_current_speed_setting()
        self._last_state_change = time.time()

        super().__init__()
        LOG.info(f"Created LUNOS fan controller '{self._name}' (W1={relay_w1}; W2={relay_w2}; default_speed={default_speed})")

    def relay_state_changed_callback(self, event, data, kwargs):
        """When either W1 or W2 relays change state, the fan speed needs to be updated"""
        old_state = data['old_state']['state']
        new_state = data['new_state']['state']
        LOG.info(f"Detected change in {data['entity_id']} relay from {old_state} to {new_state}, forcing fan update")        
        self.async_schedule_update_ha_state()

    def subscribe_to_state_changes(self, entity_id):
        LOG.info(f"Listening for state changes to entity {entity_id}")
        self._hass.listen_event(self.relay_state_changed_callback, "state_changed", entity_id=entity_id)

    # calculate the current CFM based on the current fan speed as well as the
    # number of fans configured by the user
    def update_attributes(self):
        if self._speed != None:
            coding = self._attributes[CONF_CONTROLLER_CODING]
            controller_config = LUNOS_CODING_CONFIG[coding]
            behavior = controller_config['behavior']

            cfm = cmh = None
            if 'cfm' in behavior:
                cfm_for_mode = behavior['cfm'][self._speed]
                fan_multiplier = self._fan_count / controller_config[CONF_DEFAULT_FAN_COUNT]
                cfm = cfm_for_mode * fan_multiplier
                cmh = cfm * CFM_TO_CMH
            elif 'chm' in behavior:
                chm_for_mode = behavior['chm'][self._speed]
                fan_multiplier = self._fan_count / controller_config[CONF_DEFAULT_FAN_COUNT]
                cmh = chm_for_mode * fan_multiplier
                cfm = cmh / CFM_TO_CMH

            self._attributes[ATTR_CFM] = cfm
            self._attributes[ATTR_CMHR] = cmh

            if ATTR_DB in behavior:
                self._attributes[ATTR_DB] = controller_config[ATTR_DB][self._speed]
            else:
                self._attributes[ATTR_DB] = UNKNOWN

            self._attributes['watts'] = behavior.get('watts')

            LOG.info(f"Updated '{self._name}': speed={self._speed}; attributes {self._attributes}; controller config {controller_config}")

    @property
    def name(self):
        """Return the name of the fan."""
        return self._name

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
        return self._speed

    @property
    def is_on(self) -> bool:
        """Return true if entity is on."""
        if self._speed is None:
            return False
        # NOTE: for 4-speed fans, there is never a true "OFF" setting
        return self._speed != SPEED_OFF

    # TOOD: last updated? controller type? cfm?
    @property
    def device_state_attributes(self):
        """Return state attributes."""
        return self._attributes

    async def _async_set_state(self, speed):
        """Handle state update from fan."""
        LOG.info(f"async changing LUNOS fan '{self._name}' to speed '{self._speed}'")
        self._speed = speed
        self.async_schedule_update_ha_state()

     # probe the two relays to determine current state and find the matching speed switch state
    def determine_current_speed_setting(self):
        w1 = self._hass.states.get(self._relay_w1)
        if not w1:
            LOG.error(f"W1 entity {self._relay_w1} not found, cannot determine LUNOS fan speed.")
            self._speed = UNKNOWN
            return

        w2 = self._hass.states.get(self._relay_w2)
        if not w2:
            LOG.error(f"W2 entity {self._relay_w2} not found, cannot determine LUNOS fan speed.")
            self._speed = UNKNOWN
            return

        # determine the current speed
        current_state = [ w1.state, w2.state ]
        for current_speed, speed_state in SPEED_SWITCH_STATES.items():
            if current_state == speed_state:
                break
 
        # update the speed state, if a change has been detected
        if current_speed != self._speed:
            LOG.info(f"LUNOS speed for '{self._name}' = {current_speed} (W1 {self._relay_w1}={w1.state}, W2 {self._relay_w2}={w2.state})")
            self._speed = current_speed
            self.update_attributes()

        return current_speed

    async def async_set_speed(self, speed: str) -> None:
        """Set the speed of the fan."""
        switch_states = SPEED_SWITCH_STATES[speed]
        if not switch_states:
            LOG.error(f"LUNOS fan '{self._name}' DOES NOT support speed '{speed}'; ignoring speed change.")
            return

        # flipping W1 or W2 within 3 seconds instructs the LUNOS controller to either clear the
        # filter warning light (W1) or turn on the summer/night ventilation mode (W2), thus
        # delay all state changes to be > 3 seconds since the last switch change
        time_passed = time.time() - self._last_state_change
        if time_passed < SPEED_CHANGE_DELAY_SECONDS:
            delay = max(0, SPEED_CHANGE_DELAY_SECONDS - time_passed)
            LOG.error(f"To avoid LUNOS controller confusion, speed changes must >= {SPEED_CHANGE_DELAY_SECONDS} seconds apart; sleeping {delay} seconds")
            await asyncio.sleep(delay)

        # FIXME: can we synchronously change the switches (or at least not have this fan auto-update/detect based on current settings for N seconds)
        LOG.info(f"Changing LUNOS fan '{self._name}' speed from {self._speed} to {speed}")
        await self.set_relay_switch_state(self._relay_w1, switch_states[0])
        await self.set_relay_switch_state(self._relay_w2, switch_states[1])

        # update to the new speed and update any dependent attributes
        self._speed = speed
        self.update_attributes()

    async def async_turn_on(self, speed: str = None, **kwargs) -> None:
        """Turn the fan on."""
        # TODO: should this turn on to the default speed, or the last speed before turning off?
        if speed is None:
            speed = self._default_speed

        await self.async_set_speed(speed)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the fan off."""
        await self.async_set_speed(SPEED_OFF)

    async def call_switch_service(self, method, relay_entity_id):
        LOG.info(f"Calling switch {method} for {relay_entity_id}")
        await self._hass.services.async_call('switch', method, { 'entity_id': relay_entity_id }, False)
        self._last_state_change = time.time()

    async def set_relay_switch_state(self, relay_entity_id, state):
        LOG.info(f"Setting relay {relay_entity_id} to {state}")

        method = SERVICE_TURN_ON if state == STATE_ON else SERVICE_TURN_OFF
        await self.call_switch_service(method, relay_entity_id)

    async def toggle_relay_to_set_lunos_mode(self, entity_id):
        saved_speed = self._speed

        # LUNOS requires flipping switches on/off 3 times to set mode
        toggle_methods = [ SERVICE_TURN_OFF, SERVICE_TURN_ON,
                           SERVICE_TURN_OFF, SERVICE_TURN_ON,
                           SERVICE_TURN_OFF, SERVICE_TURN_ON ] 
        for method in toggle_methods:
            await self.call_switch_service(method, entity_id)
            await asyncio.sleep(DELAY_BETWEEN_FLIPS)

        # restore speed state back to state before toggling relay
        await self.async_set_speed(saved_speed)

    async def async_update(self):
        """Attempt to retrieve current state of the fan by inspecting the switch state."""
        # FIXME: temporary hack...do not update immediately while waiting for relay switch state to change
        required_delay = MINIMUM_DELAY_BETWEEN_STATE_CHANGES
        time_passed = time.time() - self._last_state_change
        if time_passed < required_delay:
            delay = max(0, required_delay - time_passed)
            LOG.error(f"To avoid BUG when relay switch states change, waiting >= {required_delay} sec from last switch change before updating")
            await asyncio.sleep(delay)
            self.determine_current_speed_setting()

    # flipping W1 within 3 seconds instructs the LUNOS controller to clear the filter warning light
    async def async_clear_filter_reminder(self):
        LOG.info(f"Clearing the filter change reminder light for LUNOS '{self._name}'")
        self.toggle_relay_to_set_lunos_mode(self._relay_w1)

    # In summer ventilation mode, the reversing time of the fan is extended to one hour, i.e. the fan will run
    # for one hour in the supply air mode and the following hour in the exhaust air mode etc. for max. 8 hours
    def supports_summer_ventilation(self):
        coding = self._attributes[CONF_CONTROLLER_CODING]
        controller_config = LUNOS_CODING_CONFIG[coding]
        return controller_config['supports_summer_vent'] == True

    # flipping W2 within 3 seconds instructs the LUNOS controller to turn on summer ventilation mode
    async def async_turn_on_summer_ventilation(self):
        if not self.supports_summer_ventilation():
            LOG.info(f"LUNOS controller '{self._name}' is coded and DOES NOT support summer ventilation")
            return

        LOG.info(f"Enabling summer ventilation mode for LUNOS controller '{self._name}'")
        await self.toggle_relay_to_set_lunos_mode(self._relay_w2)

    async def async_turn_off_summer_ventilation(self):
        if not self.supports_summer_ventilation():
            return # silently ignore as it is already off

        # LUNOS requires waiting for a while after the last time W2 was flipped before turning off ventilation
        required_delay = MINIMUM_DELAY_BETWEEN_STATE_CHANGES
        time_passed = time.time() - self._last_state_change
        if time_passed < required_delay:
            delay = max(0, required_delay - time_passed)
            LOG.error(f"To avoid LUNOS controller confusion, summer ventilation changes >= {required_delay} seconds since last relay switch; sleeping {delay} seconds")
            await asyncio.sleep(delay)

        LOG.info(f"Disabling summer ventilation mode for LUNOS controller '{self._name}'")

        # toggle the switch back and forth once (thus restoring existing state) to clear summer ventilation mode
        await self.call_switch_service(SERVICE_TOGGLE, self._relay_w2)
        await asyncio.sleep(DELAY_BETWEEN_FLIPS)
        await self.call_switch_service(SERVICE_TOGGLE, self._relay_w2)
