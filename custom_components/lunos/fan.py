"""LUNOS Heat Recovery Ventilation Fan Control (e2/eGO)"""
#
# FUTURE:
#   - add switches (instead of presets) for the ventilation modes?
#     the docs recommend this https://developers.home-assistant.io/docs/core/entity/fan/
#     since the presets are sticky even if you change speed on the fan
#   "Manually setting a speed must disable any set preset mode. If it is possible to set a percentage speed manually without disabling the preset mode, create a switch or service to represent the mode."

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

from homeassistant.util.percentage import ordered_list_item_to_percentage, percentage_to_ordered_list_item

from . import LUNOS_CODING_CONFIG
from .const import *

LOG = logging.getLogger(__name__)

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
    name = config.get(CONF_NAME, DEFAULT_LUNOS_NAME)

    relay_w1 = config.get(CONF_RELAY_W1)
    relay_w2 = config.get(CONF_RELAY_W2)
    default_speed = config.get(CONF_DEFAULT_SPEED)

    LOG.info(f"LUNOS fan '{name}' using relays W1={relay_w1}, W2={relay_w2}'")

    fan = LUNOSFan(hass, config, name, relay_w1, relay_w2, default_speed)
    async_add_entities([ fan ], update_before_add=True)

    # expose service APIs
    component = EntityComponent(LOG, LUNOS_DOMAIN, hass)
    for service, method in {
        SERVICE_CLEAR_FILTER_REMINDER:       "async_clear_filter_reminder",
        SERVICE_TURN_ON_SUMMER_VENTILATION:  "async_turn_on_summer_ventilation",
        SERVICE_TURN_OFF_SUMMER_VENTILATION: "async_turn_off_summer_ventilation"
    }.items():
        component.async_register_entity_service(service, {}, method)

    return True


class LUNOSFan(FanEntity):
    """Representation of a LUNOS fan."""

    def __init__(
        self, hass, conf, name, relay_w1, relay_w2, default_preset: str = DEFAULT_VENT_MODE
    ):
        """Init this sensor."""

        self.hass = hass
        self._name = name
        self.entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, name, hass=hass)
        super().__init__()

        LOG.warning(f"Creating entity {self.entity_id}")
        
        self._current_speed = None
        self._last_relay_change = None

        # hardware W1/W2 relays used to determine and control LUNOS fan speed
        self._relay_w1 = relay_w1
        self._relay_w2 = relay_w2

        self._pending_relay_w1 = None
        self._pending_relay_w2 = None

        coding = conf.get(CONF_CONTROLLER_CODING)
        model_config = LUNOS_CODING_CONFIG[coding]
        self._model_config = model_config

        # fan count differs depending on controller mode (e2 = 2 fans, eGO = 1 fan)
        self._fan_count = conf.get(CONF_FAN_COUNT, model_config[CONF_DEFAULT_FAN_COUNT])

        self._attributes = {
            ATTR_MODEL_NAME: model_config["name"],
            CONF_CONTROLLER_CODING: coding,
            CONF_FAN_COUNT: self._fan_count,
            CONF_RELAY_W1: relay_w1,
            CONF_RELAY_W2: relay_w2,
        }

        # copy select fields from the model config into the attributes
        for attribute in [
            "cycle_seconds",
            "supports_filter_reminder",
        ]:
            if attribute in model_config:
                self._attributes[attribute] = model_config[attribute]

        self._init_fan_speeds(model_config)
        self._init_vent_modes(model_config)
        self._init_presets(model_config, default_preset)

        # attempt to determine the current speed of the fans (this can fail on startup
        # if the W1/W2 relays have not yet been initialized by Home Assistant)
        current_speed = self._determine_current_relay_speed()
        self._update_speed(current_speed)

        LOG.info(
            f"Created LUNOS fan '{self._name}': W1={relay_w1}; W2={relay_w2}; presets={self.preset_modes}"
        )

    def _init_fan_speeds(self, model_config):
        self._relay_state_map = {}

        # If the model configuration indicates this LUNOS fan supports OFF then the
        # fan is configured via the LUNOS hardware controller with only three speeds total.
        if model_config.get('supports_off'):
            self._relay_state_map = {
                SPEED_OFF:    [ STATE_OFF, STATE_OFF ],
                SPEED_LOW:    [ STATE_ON,  STATE_OFF ],
                SPEED_MEDIUM: [ STATE_OFF, STATE_ON ],
                SPEED_HIGH:   [ STATE_ON,  STATE_ON ]
            }

        # If the hardware LUNOS controller is set to NOT support OFF,
        # the fan has 4 speeds (and NO OFF).
        else:
            self._relay_state_map = {
                SPEED_SILENT: [ STATE_OFF, STATE_OFF ],
                SPEED_LOW:    [ STATE_ON,  STATE_OFF ],
                SPEED_MEDIUM: [ STATE_OFF, STATE_ON ],
                SPEED_HIGH:   [ STATE_ON,  STATE_ON ]
            }

        self._fan_speeds = []
        for speed in self._relay_state_map:
            self._fan_speeds.append(speed)

        self._attributes |= {
            'fan_speeds': self._fan_speeds
        }

    def _init_vent_modes(self, model_config):
        # ventilation modes have nothing to do with speed, they refer to how
        # air is circulated through the fan (eco, exhaust-only, summer-vent)
        self._vent_mode = VENT_ECO
        self._vent_modes = [ VENT_ECO ]

        # enable various preset modes depending on the fan configuration
        if model_config.get('supports_summer_vent'):
            self._vent_modes.append(VENT_SUMMER)
        if model_config.get('supports_exhaust_only'):
            self._vent_modes.append(VENT_EXHAUST_ONLY)

        self._attributes |= {
            ATTR_VENT_MODE: DEFAULT_VENT_MODE,
            'vent_modes': self._vent_modes
        }

    def _init_presets(self, model_config, default_preset):
        self._preset_modes = [ VENT_ECO ] # eco vent mode

        if model_config.get('supports_turbo_mode'):
            self._preset_modes.append(PRESET_TURBO)

        # since the HASS fan API no longer has speed names, each speed name becomes a preset
        #for speed in model_config.get('speeds'):
        #    self._preset_modes.append(speed)

        # add all fan speeds and ventilation modes as presets
        for key in self._fan_speeds + self._vent_modes:
            if key not in self._preset_modes:
                self._preset_modes.append(key)
                
        # off is not a preset...remove it from the list (use turn_off instead)
        self._preset_modes.remove('off')

        self._attributes[ATTR_PRESET_MODES] = self._preset_modes

        if default_preset not in self._preset_modes:
            LOG.warning(f"Default preset {default_preset} is not valid: {self._preset_modes}")
            default_preset = DEFAULT_VENT_MODE

        self._default_preset = default_preset
        self._preset_mode = self._default_preset

    async def async_added_to_hass(self) -> None:
        """Once entity has been added to HASS, subscribe to state changes."""
        await super().async_added_to_hass()

        # setup listeners to track changes to the W1/W2 relays
        async_track_state_change_event(
            self.hass, [self._relay_w1, self._relay_w2], self._detected_relay_state_change
        )

    @callback
    def _trigger_entity_update(self):
        update_before_ha_records_new_value = True
        self.async_schedule_update_ha_state(update_before_ha_records_new_value)

    @property
    def should_poll(self):
        return False # if this is True, callbacks won't work

    @callback
    def _detected_relay_state_change(self, event):
        """Whenever W1 or W2 relays change state, the fan speed needs to be updated"""
        # ensure there is a delay if any additional state change occurs to
        # avoid confusing the LUNOS hardware controller
        self._record_relay_state_change()
        
        entity = event.data.get("entity_id")
        to_state = event.data["new_state"].state

        # old_state is optional in the event
        old_state = event.data.get("old_state")
        from_state = old_state.state if old_state else None

        if to_state != from_state:
            LOG.info(f"{entity} changed: {from_state} -> {to_state}, updating '{self._name}'")
            self._trigger_entity_update()

    def _update_speed_attributes(self):
        """Update any speed/state based attributes"""
        self._attributes[ATTR_SPEED] = self._current_speed
        if self._current_speed is None:
            return

        coding = self._attributes[CONF_CONTROLLER_CODING]
        controller_config = LUNOS_CODING_CONFIG[coding]
        if not controller_config:
            LOG.error(f"Missing control config for {coding}!")
            return

        fan_multiplier = self._fan_count / controller_config[CONF_DEFAULT_FAN_COUNT]

        # load the behaviors of the fan for the current speed setting
        behavior_config = controller_config.get("behavior")
        if not behavior_config:
            LOG.error(f"Missing behavior config for {coding}: {controller_config}")
            return

        behavior = behavior_config.get(self._current_speed, {})

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
        self._attributes[ATTR_WATTS] = behavior.get("watts", None)

        #LOG.debug(f"Updated '{self._name}': speed={self._current_speed}; config {controller_config}: {self._attributes}")

    @property
    def name(self):
        """Return the name of the fan."""
        return self._name

    @property
    def percentage(self):
        if not self._current_speed:
            return None
        return ordered_list_item_to_percentage(self._fan_speeds, self._current_speed)

    @property
    def supported_features(self):
        return FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE
    
    @property
    def speed_count(self) -> int:
        count = len(self._fan_speeds)
        if SPEED_OFF in self._fan_speeds:
            count -= 1
        return count

    async def async_set_percentage(self, percentage: int) -> None:        
        speed = percentage_to_ordered_list_item(self._fan_speeds, percentage)
        LOG.debug(f"Setting {percentage}% -> {speed}")
        await self.async_set_speed(speed)

    @property
    def speed(self) -> str:
        """Return the current speed."""
        return self._current_speed

    @property
    def is_on(self) -> bool:
        """Return true if entity is on."""
        return self._current_speed != SPEED_OFF

    async def async_turn_off(self, **kwargs) -> None:
        if not SPEED_OFF in self._fan_speeds:
            LOG.warning(f"LUNOS '{self._name}' hardware is not configured to support turning off!")
            return
        await self.async_set_percentage(0)

    async def async_turn_on(self, speed = None, percentage = None, preset_mode = None, **kwargs) -> None:
        if speed:
            await self.async_set_preset_mode(speed)
        elif percentage:
            await self.async_set_percentage(percentage)
        elif preset_mode:
            await self.async_set_preset_mode(preset_mode)

    @property
    def preset_mode(self) -> str:
        """Return the current preset_mode."""
        # NOTE: fan speeds are not really presets...the only presets LUNOS has is vent mode
        return self._vent_mode

    @property
    def preset_modes(self) -> list:
        """Get the list of available preset modes."""
        return self._preset_modes

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the fan speed"""
        if preset_mode not in self.preset_modes:
            LOG.warning(f"LUNOS preset '{preset_mode}' is not valid: {self.preset_modes}")
            return

        if preset_mode in self._fan_speeds:
            await self.async_set_speed(preset_mode)

        elif preset_mode in self._vent_modes:
            await self.async_set_ventilation_mode(preset_mode)

        elif preset_mode == PRESET_SUMMER_VENT:
            await self.async_turn_on_summer_ventilation()
    
        else:
            LOG.warning(f"LUNOS preset '{preset_mode}' not supported: {self.preset_modes}")

    async def async_set_ventilation_mode(self, vent_mode: str) -> None:
        """Reset ventilation to LUNOS normal operation"""

        # if summer vent was known to previously be on, turn it off
        if self._vent_mode == PRESET_SUMMER_VENT:
            await self.async_turn_off_summer_ventilation()

        if vent_mode == VENT_SUMMER:
            await self.async_turn_on_summer_ventilation()
        elif vent_mode == VENT_ECO:
            LOG.warning("Reset to eco mode not implemented")
            # FIXME: reset ventilation
        elif vent_mode == VENT_EXHAUST_ONLY:
            LOG.warning("Exhaust-only ventilation mode NOT IMPLEMENTED!")
        else:
            LOG.error("Ventilation mode '{vent_mode}' not supported: {self._vent_modes}")
            return

        self._vent_mode = vent_mode
        
            
    @property
    def extra_state_attributes(self):
        """Return state attributes."""
        return self._attributes

    def _determine_current_relay_speed(self):
        """Probe W1/W2 relays for current states and then match to a speed"""
        w1 = self.hass.states.get(self._relay_w1)
        if not w1:
            LOG.warning(
                f"W1 entity {self._relay_w1} not found, cannot determine {self._name} LUNOS speed.")
            return None

        w2 = self.hass.states.get(self._relay_w2)
        if not w2:
            LOG.warning(
                f"W2 entity {self._relay_w2} not found, cannot determine {self._name} LUNOS speed.")
            return None

        # determine the current speed based on relay W1/W2 states
        current_state = [ w1.state, w2.state ]
        for speed, switch_state in self._relay_state_map.items():
            if current_state == switch_state:
                LOG.info(f"LUNOS '{self._name}' speed={speed} (W1/W2={current_state})")
                return speed

        LOG.info(f"Could not determine current speed from W1/W2 relays: {current_state}")
        return None

    def _update_speed(self, speed):
        """Update the current speed (+ refresh any dependent attributes)"""
        if speed == None:
            return
        if speed == self._current_speed:
            return

        self._current_speed = speed
        self._update_speed_attributes()
        LOG.info(f"Updated LUNOS {self._name}: {self.percentage}% {self._current_speed}")

    def _record_relay_state_change(self):
        now = time.time()
        self._last_relay_change = now
        #self._attributes['last_relay_change'] = time.localtime().strftime('%Y-%m-%d %H:%M:%S')

    async def _throttle_state_changes(self, required_delay):
        time_passed = time.time() - self._last_relay_change
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
        switch_states = self._relay_state_map.get(speed)
        if not switch_states:
            LOG.warning(
                f"LUNOS '{self._name}' DOES NOT support speed '{speed}'; ignoring speed change."
            )
            return

        # save the pending relay states (in case multiple changes are queued up in
        # event loop only the most recent should "win")
        self._pending_relay_w1 = switch_states[0]
        self._pending_relay_w2 = switch_states[1]
        
        # wait after any relay was last changed to avoid LUNOS controller misinterpreting toggles
        #
        # FIXME: there really should be a queue of changes with a delay between each before application
        # instead of this (and clearing out of old changes IF any are queued up). This existing
        # implementation here does not work if someone starts clicking changes again and again
        await self._throttle_state_changes(MINIMUM_DELAY_BETWEEN_STATE_CHANGES)

        if self._pending_relay_w1 is not None:
            LOG.info(f"Changing LUNOS '{self._name}' speed: {self._current_speed} -> {speed}")
            await self.set_relay_switch_state(self._relay_w1, self._pending_relay_w1)
            await self.set_relay_switch_state(self._relay_w2, self._pending_relay_w2)
            self._pending_relay_w1 = self._pending_relay_w2 = None            

        # update our internal state immediately (instead of waiting for callback relays have changed)
        self._update_speed(speed)

    async def async_update(self):
        """Determine current state of the fan by inspecting relay states."""
        LOG.debug(f"{self._name} async_update() called")

        # delay reading allow any pending switch changes to be applied
        await asyncio.sleep(1.0)

        actual_speed = self._determine_current_relay_speed()
        LOG.debug(f"{self._name} async_update() = {actual_speed}")
        self._update_speed(actual_speed)

    async def async_turn_on(self,
                            percentage: int = None,
                            preset: str = None,
                            **kwargs) -> None:
        """Turn the fan on."""

        # FIXME: should this turn on to the default speed, or the last speed before turning off?

        if preset is None:
            preset = self._default_preset
            await self.async_set_preset_mode(preset)

        if percentage is not None:
            await self.async_set_percentage(percentage)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the fan off."""
        await self.async_set_percentage(0)

    async def async_call_switch_service(self, method, relay_entity_id):
        LOG.info(f"Calling switch {method} for {relay_entity_id}")
        await self.hass.services.async_call(
            "switch", method, {"entity_id": relay_entity_id}, False
        )
        self._record_relay_state_change()

    async def set_relay_switch_state(self, relay_entity_id, state):
        method = SERVICE_TURN_ON if state == STATE_ON else SERVICE_TURN_OFF
        await self.async_call_switch_service(method, relay_entity_id)

    async def toggle_relay_to_set_lunos_mode(self, entity_id):
        saved_speed = self._current_speed

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
            await self.async_call_switch_service(method, entity_id)
            await asyncio.sleep(DELAY_BETWEEN_FLIPS)

        # restore speed state back to the previous state before toggling relay
        await self.async_set_speed(saved_speed)

    
    async def async_clear_filter_reminder(self):
        LOG.info(f"Clearing the filter change reminder light for LUNOS '{self._name}'")

        # toggling W1 many times within 3 seconds instructs the LUNOS controller
        # to clear the filter warning light
        self.toggle_relay_to_set_lunos_mode(self._relay_w1)

    # In LUNOS summer vent mode, the reversing time for the fans is extended to 1 hour.
    # The fan will run for 1 hour in the supply air mode and the following hour in
    # the exhaust air mode (resets after 8 hours). This is typically used during summer
    # nighttime to allow cooler air into the house.
    def supports_summer_ventilation(self):
        return PRESET_SUMMER_VENT in self._vent_modes
    
    async def async_turn_on_summer_ventilation(self):
        if not self.supports_summer_ventilation():
            LOG.warning(f"LUNOS '{self._name}' DOES NOT support summer vent")
            return

        LOG.info(f"Enabling summer vent mode for LUNOS '{self._name}'")
        # toggling W2 many times within 3 seconds instructs the LUNOS controller
        # to turn on summer ventilation mode
        await self.toggle_relay_to_set_lunos_mode(self._relay_w2)

        self._preset_mode = PRESET_SUMMER_VENT
        self._attributes[ATTR_VENT_MODE] = VENT_SUMMER

    async def async_turn_off_summer_ventilation(self):
        if not self.supports_summer_ventilation():
            return

        # wait after any relay was last changed to avoid LUNOS controller misinterpreting toggles
        await self._throttle_state_changes(MINIMUM_DELAY_BETWEEN_STATE_CHANGES)
        
        LOG.info(f"Disabling summer vent mode for LUNOS '{self._name}'")

        # toggle W2 relay once to clear summer ventilation (and return to previous speed)
        await self.async_call_switch_service(SERVICE_TOGGLE, self._relay_w2)
        await asyncio.sleep(DELAY_BETWEEN_FLIPS)
        await self.async_call_switch_service(SERVICE_TOGGLE, self._relay_w2)

        self._preset_mode = DEFAULT_VENT_MODE
        self._attributes[ATTR_VENT_MODE] = DEFAULT_VENT_MODE
