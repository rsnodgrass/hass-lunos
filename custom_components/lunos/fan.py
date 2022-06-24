"""LUNOS Heat Recovery Ventilation Fan Control (e2/eGO)"""
# FIXME: can we subscribe to updates from the w1/w2 entities to avoid polling?

import asyncio
import logging
import time

import voluptuous as vol
from homeassistant.components.fan import (
    ENTITY_ID_FORMAT,
    PLATFORM_SCHEMA,
    ATTR_PRESET_MODES,
    FanEntity,
    FanEntityFeature
)
from homeassistant.const import (
    CONF_ENTITY_ID,
    CONF_NAME,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_track_state_change_event

from . import LUNOS_CODING_CONFIG
from .const import *

LOG = logging.getLogger(__name__)

# delay all speed changes to > 3 seconds since the last relay switch change to avoid side effects
SPEED_CHANGE_DELAY_SECONDS = 4
DELAY_BETWEEN_FLIPS = 0.100
MINIMUM_DELAY_BETWEEN_STATE_CHANGES = 15.0

# FIXME: support enabling exhaust-only mode
VENTILATION_NORMAL = "normal"
VENTILATION_SUMMER = "summer"
VENTILATION_EXHAUST = "exhaust-only"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(
            CONF_NAME
        ): cv.string,  # NOTE: we default the name later based on logic
        vol.Optional(CONF_RELAY_W1): cv.string,  # cv.entity_id
        vol.Optional(CONF_RELAY_W2): cv.string,  # cv.entity_id
        vol.Optional(CONF_DEFAULT_SPEED, default=DEFAULT_SPEED): vol.In(SPEED_LIST),
        #        vol.Optional(CONF_CONTROLLER_CODING, default='e2-usa'): cv.string,
        vol.Optional(CONF_CONTROLLER_CODING, default="e2-usa"): vol.In(
            LUNOS_CODING_CONFIG.keys()
        ),
        vol.Optional(CONF_FAN_COUNT): vol.In(
            [1, 2, 3, 4]
        ),  # default is based on how controller is coded (see below)
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

    LOG.info(
        f"LUNOS fan controller '{name}' using relays W1={relay_w1}, W2={relay_w2}'"
    )

    fan = LUNOSFan(hass, config, name, relay_w1, relay_w2, default_speed)
    async_add_entities([fan], update_before_add=True)

    # expose service call APIs
    # FIXME: how are these tied to a specific LUNOS fan instance?
    component = EntityComponent(LOG, LUNOS_DOMAIN, hass)
    component.async_register_entity_service(
        SERVICE_CLEAR_FILTER_REMINDER, {}, "async_clear_filter_reminder"
    )
    component.async_register_entity_service(
        SERVICE_TURN_ON_SUMMER_VENTILATION, {}, "async_turn_on_summer_ventilation"
    )
    component.async_register_entity_service(
        SERVICE_TURN_OFF_SUMMER_VENTILATION, {}, "async_turn_off_summer_ventilation"
    )

    return True


class LUNOSFan(FanEntity):
    """Representation of a LUNOS fan."""

    def __init__(
        self, hass, conf, name, relay_w1, relay_w2, default_preset: str = PRESET_ECO
    ):
        """Init this sensor."""

        self.hass = hass
        self._name = name
        self.entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, name, hass=hass)
        super().__init__()

        self._attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE

        self._speed = None
        self._last_state_change = None

        # specify W1/W2 relays to use
        self._relay_w1 = relay_w1
        self._relay_w2 = relay_w2

        coding = conf.get(CONF_CONTROLLER_CODING)
        model_config = LUNOS_CODING_CONFIG[coding]
        self._model_config = model_config

        # default fan count differs depending on controller mode (e2 = 2 fans, eGO = 1 fan)
        self._fan_count = conf.get(CONF_FAN_COUNT, model_config[CONF_DEFAULT_FAN_COUNT])

        self._attributes = {
            ATTR_MODEL_NAME: model_config["name"],
            CONF_CONTROLLER_CODING: coding,
            CONF_FAN_COUNT: self._fan_count,
            ATTR_VENTILATION_MODE: VENTILATION_NORMAL,
            ATTR_DB: UNKNOWN,
            CONF_RELAY_W1: relay_w1,
            CONF_RELAY_W2: relay_w2,
        }

        self._default_preset = default_preset
        self._preset_mode = self._default_preset
        self._preset_modes = [ PRESET_ECO ]

        # enable various preset modes depending on the fan configuration
        if model_config.get('supports_summer_vent'):
            self._preset_modes += PRESET_SUMMER_VENT
        if model_config.get('supports_exhaust_only'):
            self._preset_modes += PRESET_EXHAUST_ONLY
        if model_config.get('supports_turbo_mode'):
            self._preset_modes += PRESET_TURBO

        # since the HASS fan API no longer has speed names, each speed name becomes a preset
        for speed in model_config.get('speeds'):
            self._preset_modes += speed

        self._attributes[ATTR_PRESET_MODES] = self._preset_modes

        # copy select fields from the model config into the attributes
        for attribute in [
            "cycle_seconds",
            "supports_filter_reminder",
        ]:
            if attribute in model_config:
                self._attributes[attribute] = model_config[attribute]

        # determine the current speed of the fans
        current_speed = self._determine_current_speed()
        self._update_speed(current_speed)

        LOG.info(
            f"Created LUNOS fan controller '{self._name}': W1={relay_w1}; W2={relay_w2}; presets={self.preset_modes}"
        )

    async def async_added_to_hass(self) -> None:
        """Once entity has been added to HASS, subscribe to state changes."""
        await super().async_added_to_hass()

        # setup listeners to track changes to the W1/W2 relays
        async_track_state_change_event(
            self.hass, [self._relay_w1, self._relay_w2], self._relay_state_changed
        )

    @callback
    def _schedule_immediate_update(self):
        self.async_schedule_update_ha_state(True)

    @callback
    def _relay_state_changed(self, event):
        """Whenever W1 or W2 relays change state, the fan speed needs to be updated"""
        entity = event.data.get("entity_id")
        to_state = event.data["new_state"].state

        # sometimes there is no from_state
        old_state = event.data.get("old_state")
        from_state = old_state.state if old_state else None

        if not from_state or to_state != from_state:
            LOG.info(
                f"{entity} changed from {from_state} to {to_state}, updating '{self._name}'"
            )
            self.schedule_update_ha_state()

    def update_attributes(self):
        """Calculate the current CFM based on the current fan speed as well as the
        number of fans configured by the user."""
        #self._attributes[ATTR_PRESET_MODE] = self._preset_mode

        if self._speed is not None:
            coding = self._attributes[CONF_CONTROLLER_CODING]
            controller_config = LUNOS_CODING_CONFIG[coding]

            fan_multiplier = self._fan_count / controller_config[CONF_DEFAULT_FAN_COUNT]

            # load the behaviors of the fan for the current speed setting
            behavior_config = controller_config.get("behavior")
            if not behavior_config:
                LOG.error(
                    f"Missing behavior config for coding {coding}: {controller_config}"
                )
            behavior = behavior_config.get(self._speed, {})

            # determine the air flow rates based on fan behavior at the current speed
            cfm = cmh = None
            if "cfm" in behavior:
                cfm_for_mode = behavior["cfm"]
                cfm = cfm_for_mode * fan_multiplier
                cmh = cfm * CFM_TO_CMH
            elif "chm" in behavior:
                chm_for_mode = behavior["chm"]
                cmh = chm_for_mode * fan_multiplier
                cfm = cmh / CFM_TO_CMH

            self._attributes[ATTR_CFM] = cfm
            self._attributes[ATTR_CMHR] = cmh

            # if sound level (dB) is defined for the speed, include it in attributes
            self._attributes[ATTR_DB] = behavior.get(ATTR_DB, None)
            self._attributes["watts"] = behavior.get("watts", None)

            LOG.debug(
                f"Updated '{self._name}': speed={self._speed}; attributes {self._attributes}; controller config {controller_config}"
            )
            
    @property
    def name(self):
        """Return the name of the fan."""
        return self._name
    
    @property
    def percentage(self):
        if self._speed is None:
            return None
        return self.percentage_for_speed(self._speed)

    def speed_for_percentage(self, percentage: int) -> str:
        # FIXME: what about max? turbo?
        if percentage is None:
            return None
        elif percentage == 0:
            return SPEED_OFF
        elif percentage <= 33:
            return SPEED_LOW
        elif percentage <= 67:
            return SPEED_MEDIUM
        else:
            return SPEED_HIGH

    def percentage_for_speed(self, speed: str) -> int:
        # FIXME: this should actually be in YAML to dictate percentages (and whether 0 is allowed)
        if speed is None:
            return None
        elif speed == SPEED_OFF:
            return 0
        elif speed == SPEED_LOW:
            return 33
        elif speed == SPEED_MEDIUM:
            return 67
        else:
            return 100

    async def async_set_percentage(self, percentage: int) -> None:        
        speed = self.speed_for_percentage(percentage)

        # convert speed back to a percentage to get scaled value
        scaled_percentage = self.percentage_for_speed(speed)

        # FIXME: what about for fans that cannot be turned off?
        # FIXME: for those that don't support off...what is the speed? (minimum cfm / max cfm?)
        if self._speed != speed:
            LOG.info(f"Manual speed change to {percentage}%: changing to {speed} ({scaled_percentage}%) from {self._speed}")

        self._update_speed(speed)

        if self._preset_mode != PRESET_ECO:
            LOG.info(f"Manual speed change triggered preset reset to {PRESET_ECO}")
            self._preset_mode = PRESET_ECO

    @property
    def speed(self) -> str:
        """Return the current speed."""
        return self._speed

    @property
    def is_on(self) -> bool:
        """Return true if entity is on."""
        if self._speed is None:
            return False

        # NOTE: for some 4-speed fan settings, there is never a true "OFF" setting
        if not self._model_config.get('supports_off'):
            return False

        return self._speed != SPEED_OFF

    @property
    def preset_modes(self) -> list:
        """Get the list of available preset modes."""
        return self._preset_modes

    async def async_set_preset_mode(self, mode: str) -> None:
        """Set the fan speed"""
        if mode not in self.preset_modes:
            LOG.warning(f"LUNOS preset mode '{mode}' is not valid: {self.preset_modes}")
            return

        if mode == PRESET_OFF:
            await self.turn_off()

        elif mode == PRESET_ECO:
            # FIXME: reset
            self._preset_mode = PRESET_ECO

        elif mode == PRESET_SUMMER_VENT:
            await self.async_turn_on_summer_ventilation()

        else:
            LOG.warning(f"LUNOS preset mode '{mode}' is NOT YET IMPLEMENTED!")
            self._preset_mode = PRESET_ECO

    @property
    def extra_state_attributes(self):
        """Return state attributes."""
        return self._attributes

    def _determine_current_speed(self):
        """Probe the two relays to determine current state and find the matching speed switch state"""
        w1 = self.hass.states.get(self._relay_w1)
        if not w1:
            LOG.warning(f"W1 entity {self._relay_w1} not found, cannot determine {self._name} LUNOS fan speed.")
            return

        w2 = self.hass.states.get(self._relay_w2)
        if not w2:
            LOG.warning(
                f"W2 entity {self._relay_w2} not found, cannot determine {self._name} LUNOS fan speed."
            )
            return

        # determine the current speed based on relay W1/W2 state
        current_state = [ w1.state, w2.state ]
        for speed, speed_state in SPEED_SWITCH_STATES.items():
            if current_state == speed_state:
                LOG.info(
                    f"LUNOS speed for '{self._name}' = {speed} (W1/W2={current_state})"
                )
                return speed
        return None

    def _update_speed(self, speed):
        """Update the speed along with any dependent attributes"""
        self._speed = speed
        self._last_state_change = time.time()
        self.update_attributes()

        # FIXME: percentage 0 means OFF for those that support off!
        # FIXME: for those that don't support off...what is the speed? (minimum cfm / max cfm?)

    async def _throttle_state_changes(self, required_delay):
        time_passed = time.time() - self._last_state_change
        if time_passed < required_delay:
            delay = max(0, required_delay - time_passed)
            LOG.warning(
                f"To avoid LUNOS '{self._name}' controller race conditions, sleeping {delay} seconds before changing relay."
            )
            await asyncio.sleep(delay)
            return True
        return False

    async def async_set_speed(self, speed: str) -> None:
        """Set the fan speed"""
        switch_states = SPEED_SWITCH_STATES[speed]
        if not switch_states:
            LOG.warning(
                f"LUNOS fan '{self._name}' DOES NOT support speed '{speed}'; ignoring speed change."
            )
            return

        # flipping W1 or W2 within 3 seconds instructs the LUNOS controller to either clear the
        # filter warning light (W1) or turn on the summer/night ventilation mode (W2), thus
        # delay all state changes to be > 3 seconds since the last switch change
        await self._throttle_state_changes(SPEED_CHANGE_DELAY_SECONDS)

        LOG.info(
            f"Changing LUNOS fan '{self._name}' speed from {self._speed} to {speed}"
        )
        await self.set_relay_switch_state(self._relay_w1, switch_states[0])
        await self.set_relay_switch_state(self._relay_w2, switch_states[1])

        # update to the new speed and update any dependent attributes
        self._update_speed(speed)

    async def async_update(self):
        """Attempt to retrieve current state of the fan by inspecting the switch state."""

        # delay reading allow any pending switch changes to be applied
        await asyncio.sleep(1.0)

        current_speed = self._determine_current_speed()
        if current_speed != self._speed:
            self._update_speed(current_speed)

    async def async_turn_on(self,
                            percentage: int = None,
                            preset: str = None,
                            **kwargs) -> None:
        """Turn the fan on."""

        # FIXME: should this turn on to the default speed, or the last speed before turning off?

        if preset is None:
            preset = self._default_preset
            await self.async_set_preset_mode(preset)

        if percentage:
            await self.async_set_percentage(percentage)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the fan off."""
        await self.async_set_precentage(0)

    async def call_switch_service(self, method, relay_entity_id):
        LOG.info(f"Calling switch {method} for {relay_entity_id}")
        await self.hass.services.async_call(
            "switch", method, {"entity_id": relay_entity_id}, False
        )
        self._last_state_change = time.time()

    async def set_relay_switch_state(self, relay_entity_id, state):
        LOG.info(f"Setting relay {relay_entity_id} to {state}")

        method = SERVICE_TURN_ON if state == STATE_ON else SERVICE_TURN_OFF
        await self.call_switch_service(method, relay_entity_id)

    async def toggle_relay_to_set_lunos_mode(self, entity_id):
        saved_speed = self._speed

        # LUNOS requires flipping switches on/off 3 times to set mode
        toggle_methods = [
            SERVICE_TURN_OFF,
            SERVICE_TURN_ON,
            SERVICE_TURN_OFF,
            SERVICE_TURN_ON,
            SERVICE_TURN_OFF,
            SERVICE_TURN_ON,
        ]
        for method in toggle_methods:
            await self.call_switch_service(method, entity_id)
            await asyncio.sleep(DELAY_BETWEEN_FLIPS)

        # restore speed state back to the previous state before toggling relay
        await self.async_set_speed(saved_speed)

    # flipping W1 within 3 seconds instructs the LUNOS controller to clear the filter warning light
    async def async_clear_filter_reminder(self):
        LOG.info(f"Clearing the filter change reminder light for LUNOS '{self._name}'")
        self.toggle_relay_to_set_lunos_mode(self._relay_w1)

    # In summer ventilation mode, the reversing time of the fan is extended to one hour, i.e. the fan will run
    # for one hour in the supply air mode and the following hour in the exhaust air mode etc. for max. 8 hours
    def supports_summer_ventilation(self):
        return PRESET_SUMMER_VENT in self.preset_modes

    # flipping W2 within 3 seconds instructs the LUNOS controller to turn on summer ventilation mode
    async def async_turn_on_summer_ventilation(self):
        if not self.supports_summer_ventilation():
            LOG.warning(
                f"LUNOS controller '{self._name}' DOES NOT support summer ventilation"
            )
            return

        LOG.info(f"Enabling summer ventilation mode for LUNOS '{self._name}'")
        await self.toggle_relay_to_set_lunos_mode(self._relay_w2)

        self._preset_mode = PRESET_SUMMER_VENT
        self._attributes[ATTR_VENTILATION_MODE] = VENTILATION_SUMMER

    async def async_turn_off_summer_ventilation(self):
        if not self.supports_summer_ventilation():
            return

        # LUNOS requires waiting for a while after the last time W2 was flipped before turning off ventilation
        await self._throttle_state_changes(MINIMUM_DELAY_BETWEEN_STATE_CHANGES)

        LOG.info(f"Disabling summer ventilation mode for LUNOS '{self._name}'")

        # toggle the switch back and forth once (thus restoring existing state) to clear summer ventilation mode
        await self.call_switch_service(SERVICE_TOGGLE, self._relay_w2)
        await asyncio.sleep(DELAY_BETWEEN_FLIPS)
        await self.call_switch_service(SERVICE_TOGGLE, self._relay_w2)

        self._preset_mode = PRESET_ECO
        self._attributes[ATTR_VENTILATION_MODE] = VENTILATION_NORMAL
