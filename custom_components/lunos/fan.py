"""LUNOS Heat Recovery Ventilation Fan Control (e2/eGO)."""

#
# FUTURE:
#   - add switches (instead of presets) for the ventilation modes?
#     the docs recommend this https://developers.home-assistant.io/docs/core/entity/fan/
#     since the presets are sticky even if you change speed on the fan
#   "Manually setting a speed must disable any set preset mode. If it is possible to set a
#    percentage speed manually without disabling the preset mode, create a switch or service
#    to represent the mode."

from __future__ import annotations

import logging
import asyncio
import time
from typing import TYPE_CHECKING, Any

from homeassistant.components.fan import (
    ATTR_PRESET_MODES,
    FanEntity,
    FanEntityFeature,
)
from homeassistant.const import (
    CONF_NAME,
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import Event, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import (
    AddEntitiesCallback,
    async_get_current_platform,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .const import (
    ATTR_CFM,
    ATTR_CMHR,
    ATTR_DB,
    ATTR_MODEL_NAME,
    ATTR_SPEED,
    ATTR_VENT_MODE,
    ATTR_WATTS,
    CFM_TO_CMH,
    CONF_CONTROLLER_CODING,
    CONF_DEFAULT_FAN_COUNT,
    CONF_DEFAULT_SPEED,
    CONF_FAN_COUNT,
    CONF_RELAY_W1,
    CONF_RELAY_W2,
    DEFAULT_NAME,
    DEFAULT_SPEED,
    DEFAULT_VENT_MODE,
    DELAY_BETWEEN_FLIPS,
    DOMAIN,
    MINIMUM_DELAY_BETWEEN_STATE_CHANGES,
    SERVICE_CLEAR_FILTER_REMINDER,
    SERVICE_TURN_OFF_SUMMER_VENTILATION,
    SERVICE_TURN_ON_SUMMER_VENTILATION,
    SPEED_HIGH,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_OFF,
    SPEED_SILENT,
    VENT_ECO,
    VENT_EXHAUST_ONLY,
    VENT_SUMMER,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import LunosConfigEntry
    from .coordinator import LunosCoordinator

LOG = logging.getLogger(__name__)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: LunosConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up LUNOS fan entities from a config entry."""
    coordinator = entry.runtime_data.coordinator
    coding_config = entry.runtime_data.coding_config

    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    relay_w1 = entry.data[CONF_RELAY_W1]
    relay_w2 = entry.data[CONF_RELAY_W2]
    default_speed = entry.data.get(CONF_DEFAULT_SPEED, DEFAULT_SPEED)

    LOG.info("LUNOS fan '%s' using relays W1=%s, W2=%s", name, relay_w1, relay_w2)

    fan = LUNOSFan(
        coordinator=coordinator,
        entry=entry,
        coding_config=coding_config,
        name=name,
        relay_w1=relay_w1,
        relay_w2=relay_w2,
        default_speed=default_speed,
    )
    async_add_entities([fan], update_before_add=True)

    # register entity services
    platform = async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_CLEAR_FILTER_REMINDER,
        {},
        'async_clear_filter_reminder',
    )
    platform.async_register_entity_service(
        SERVICE_TURN_ON_SUMMER_VENTILATION,
        {},
        'async_turn_on_summer_ventilation',
    )
    platform.async_register_entity_service(
        SERVICE_TURN_OFF_SUMMER_VENTILATION,
        {},
        'async_turn_off_summer_ventilation',
    )


class LUNOSFan(FanEntity):
    """Representation of a LUNOS fan."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LunosCoordinator,
        entry: LunosConfigEntry,
        coding_config: dict[str, Any],
        name: str,
        relay_w1: str,
        relay_w2: str,
        default_speed: str = DEFAULT_SPEED,
    ) -> None:
        """Initialize this fan entity."""
        self._coordinator = coordinator
        self._entry = entry
        self._coding_config = coding_config
        self._name = name

        # unique id based on relay entity ids
        self._attr_unique_id = f'{relay_w1}_{relay_w2}'

        LOG.info('Creating LUNOS fan entity: %s', self._attr_unique_id)

        self._current_speed: str | None = None
        self._last_non_off_speed: str | None = None
        self._last_relay_change: float | None = None

        # hardware W1/W2 relays used to determine and control LUNOS fan speed
        self._relay_w1 = relay_w1
        self._relay_w2 = relay_w2

        self._pending_relay_w1: str | None = None
        self._pending_relay_w2: str | None = None

        coding = entry.data.get(CONF_CONTROLLER_CODING, 'e2-usa')
        model_config = coding_config.get(coding, {})
        self._model_config: dict[str, Any] = model_config

        # fan count differs depending on controller mode (e2 = 2 fans, eGO = 1 fan)
        self._fan_count: int = entry.data.get(
            CONF_FAN_COUNT, model_config.get(CONF_DEFAULT_FAN_COUNT, 2)
        )

        self._attributes: dict[str, Any] = {
            ATTR_MODEL_NAME: model_config.get('name', 'Unknown'),
            CONF_CONTROLLER_CODING: coding,
            CONF_FAN_COUNT: self._fan_count,
            CONF_RELAY_W1: relay_w1,
            CONF_RELAY_W2: relay_w2,
        }

        # copy select fields from the model config into the attributes
        for attribute in (
            'cycle_seconds',
            'supports_filter_reminder',
        ):
            if attribute in model_config:
                self._attributes[attribute] = model_config[attribute]

        self._fan_speeds: list[str] = []
        self._relay_state_map: dict[str, list[str]] = {}
        self._init_fan_speeds(model_config)

        self._vent_mode: str = VENT_ECO
        self._vent_modes: list[str] = []
        self._init_vent_modes(model_config)

        self._default_speed = (
            default_speed if default_speed in self._fan_speeds else DEFAULT_SPEED
        )

        self._preset_modes: list[str] = []
        self._preset_mode: str | None = None
        self._init_presets()

        LOG.info(
            "Created LUNOS fan '%s': W1=%s; W2=%s; presets=%s",
            self._name,
            relay_w1,
            relay_w2,
            self.preset_modes,
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this LUNOS fan."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=self._name,
            manufacturer='LUNOS',
            model=self._model_config.get('name', 'Unknown'),
        )

    def _init_fan_speeds(self, model_config: dict[str, Any]) -> None:
        """Initialize fan speed configuration based on model."""
        self._relay_state_map = {}

        # If the model configuration indicates this LUNOS fan supports OFF then the
        # fan is configured via the LUNOS hardware controller with only three speeds total.
        if model_config.get('supports_off'):
            self._relay_state_map = {
                SPEED_OFF: [STATE_OFF, STATE_OFF],
                SPEED_LOW: [STATE_ON, STATE_OFF],
                SPEED_MEDIUM: [STATE_OFF, STATE_ON],
                SPEED_HIGH: [STATE_ON, STATE_ON],
            }

        # If the hardware LUNOS controller is set to NOT support OFF,
        # the fan has 4 speeds (and NO OFF).
        else:
            self._relay_state_map = {
                SPEED_SILENT: [STATE_OFF, STATE_OFF],
                SPEED_LOW: [STATE_ON, STATE_OFF],
                SPEED_MEDIUM: [STATE_OFF, STATE_ON],
                SPEED_HIGH: [STATE_ON, STATE_ON],
            }

        self._fan_speeds = list(self._relay_state_map.keys())
        self._attributes |= {'fan_speeds': self._fan_speeds}

    def _init_vent_modes(self, model_config: dict[str, Any]) -> None:
        """Initialize ventilation mode configuration."""
        # ventilation modes have nothing to do with speed, they refer to how
        # air is circulated through the fan (eco, exhaust-only, summer-vent)
        self._vent_mode = VENT_ECO
        self._vent_modes = [VENT_ECO]

        # enable various preset modes depending on the fan configuration
        if model_config.get('supports_summer_vent'):
            self._vent_modes.append(VENT_SUMMER)
        if model_config.get('supports_exhaust_only'):
            self._vent_modes.append(VENT_EXHAUST_ONLY)

        self._attributes |= {
            ATTR_VENT_MODE: DEFAULT_VENT_MODE,
            'vent_modes': self._vent_modes,
        }

    def _init_presets(self) -> None:
        """Initialize preset mode configuration."""
        # Fan preset modes should not include manual/named speeds; speeds are represented
        # by percentages. We only expose ventilation-related modes as presets.
        self._preset_modes = list(self._vent_modes)
        self._attributes[ATTR_PRESET_MODES] = self._preset_modes

        # By default the fan is in eco ventilation; percentage changes will clear
        # the preset_mode as required by the FanEntity docs.
        self._preset_mode = DEFAULT_VENT_MODE

    async def async_added_to_hass(self) -> None:
        """Once entity has been added to HASS, subscribe to state changes."""
        await super().async_added_to_hass()

        # setup listeners to track changes to the W1/W2 relays
        async_track_state_change_event(
            self.hass,
            [self._relay_w1, self._relay_w2],
            self._detected_relay_state_change,
        )

        # attempt to determine the current speed of the fans
        current_speed = self._determine_current_relay_speed()
        self._update_speed(current_speed)

    @callback
    def _trigger_entity_update(self) -> None:
        """Schedule entity state update."""
        update_before_ha_records_new_value = True
        self.async_schedule_update_ha_state(update_before_ha_records_new_value)

    @property
    def should_poll(self) -> bool:
        """Return False since we use push-based updates."""
        return False  # if this is True, callbacks won't work

    @callback
    def _detected_relay_state_change(self, event: Event) -> None:
        """Handle W1 or W2 relay state changes to update fan speed."""
        # ensure there is a delay if any additional state change occurs to
        # avoid confusing the LUNOS hardware controller
        self._record_relay_state_change()

        entity = event.data.get('entity_id')
        new_state = event.data.get('new_state')
        if new_state is None:
            return

        to_state = new_state.state

        # old_state is optional in the event
        old_state = event.data.get('old_state')
        from_state = old_state.state if old_state else None

        if to_state != from_state:
            LOG.info(
                "%s changed: %s -> %s, updating '%s'",
                entity,
                from_state,
                to_state,
                self._name,
            )
            self._trigger_entity_update()

    def _update_speed_attributes(self) -> None:
        """Update any speed/state based attributes."""
        self._attributes[ATTR_SPEED] = self._current_speed
        if self._current_speed is None:
            return

        coding = self._attributes[CONF_CONTROLLER_CODING]
        controller_config = self._coding_config.get(coding, {})
        if not controller_config:
            LOG.error('Missing control config for %s!', coding)
            return

        default_fan_count = controller_config.get(CONF_DEFAULT_FAN_COUNT, 2)
        fan_multiplier = self._fan_count / default_fan_count

        # load the behaviors of the fan for the current speed setting
        behavior_config = controller_config.get('behavior')
        if not behavior_config:
            LOG.error('Missing behavior config for %s: %s', coding, controller_config)
            return

        behavior = behavior_config.get(self._current_speed, {})

        # determine the air flow rates based on fan behavior at the current speed
        cfm: float | None = None
        cmh: float | None = None
        if 'cfm' in behavior:
            cfm_for_mode: float = behavior['cfm']
            cfm = cfm_for_mode * fan_multiplier
            cmh = cfm_for_mode * fan_multiplier * CFM_TO_CMH
        elif 'chm' in behavior:
            chm_for_mode: float = behavior['chm']
            cmh = chm_for_mode * fan_multiplier
            cfm = chm_for_mode * fan_multiplier / CFM_TO_CMH

        self._attributes[ATTR_CFM] = cfm
        self._attributes[ATTR_CMHR] = cmh

        # if sound level (dB) is defined for the speed, include it in attributes
        self._attributes[ATTR_DB] = behavior.get(ATTR_DB)
        self._attributes[ATTR_WATTS] = behavior.get('watts')

    @property
    def name(self) -> str:
        """Return the name of the fan."""
        return self._name

    @property
    def percentage(self) -> int | None:
        """Return the current speed as a percentage."""
        if self._current_speed is None:
            return None
        if self._current_speed == SPEED_OFF:
            return 0
        return ordered_list_item_to_percentage(self._percentage_speeds, self._current_speed)

    @property
    def supported_features(self) -> FanEntityFeature:
        """Return the supported features of this fan."""
        features = FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_ON
        if SPEED_OFF in self._fan_speeds:
            features |= FanEntityFeature.TURN_OFF
        if self._preset_modes:
            features |= FanEntityFeature.PRESET_MODE
        return features

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return len(self._percentage_speeds)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan as a percentage."""
        # Manually setting a percentage must disable any set preset mode.
        self._preset_mode = None

        if percentage <= 0:
            if SPEED_OFF in self._fan_speeds:
                await self._async_set_named_speed(SPEED_OFF)
                return
            # Hardware doesn't support off: map 0% to lowest available speed.
            await self._async_set_named_speed(self._percentage_speeds[0])
            return

        speed = percentage_to_ordered_list_item(self._percentage_speeds, percentage)
        LOG.debug('Setting %s%% -> %s', percentage, speed)
        await self._async_set_named_speed(speed)

    @property
    def is_on(self) -> bool:
        """Return true if entity is on."""
        return self._current_speed != SPEED_OFF

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Turn the fan off."""
        if SPEED_OFF not in self._fan_speeds:
            LOG.warning(
                "LUNOS '%s' hardware is not configured to support turning off!",
                self._name,
            )
            return
        await self._async_set_named_speed(SPEED_OFF)

    async def async_turn_on(
        self,
        speed: str | None = None,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **_kwargs: Any,
    ) -> None:
        """Turn the fan on."""
        # `speed` is deprecated by Home Assistant but may be passed by older callers.
        if percentage is not None:
            await self.async_set_percentage(percentage)
        elif preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        elif speed is not None:
            await self.async_set_preset_mode(speed)
        else:
            # No args: restore last non-off speed, or fall back to configured default.
            target_speed = self._last_non_off_speed or self._default_speed
            if target_speed == SPEED_OFF:
                target_speed = self._percentage_speeds[0]
            await self._async_set_named_speed(target_speed)

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset_mode."""
        return self._preset_mode

    @property
    def preset_modes(self) -> list[str]:
        """Get the list of available preset modes."""
        return self._preset_modes

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set a preset mode.

        Note: For backward compatibility, we still accept speed names here, but
        we do not advertise them via preset_modes.
        """
        if preset_mode in self._fan_speeds:
            # Backward compatible: treat speed names as a direct speed request.
            self._preset_mode = None
            await self._async_set_named_speed(preset_mode)
            return

        if preset_mode not in self.preset_modes:
            LOG.warning("LUNOS preset '%s' is not valid: %s", preset_mode, self.preset_modes)
            return

        await self.async_set_ventilation_mode(preset_mode)

    async def async_set_ventilation_mode(self, vent_mode: str) -> None:
        """Set ventilation mode on the LUNOS controller."""
        # if summer vent was known to previously be on, turn it off
        if self._vent_mode == VENT_SUMMER:
            await self.async_turn_off_summer_ventilation()

        if vent_mode == VENT_SUMMER:
            await self.async_turn_on_summer_ventilation()
        elif vent_mode == VENT_ECO:
            LOG.warning('Reset to eco mode not implemented')
            # FIXME: reset ventilation
        elif vent_mode == VENT_EXHAUST_ONLY:
            LOG.warning('Exhaust-only ventilation mode NOT IMPLEMENTED!')
        else:
            LOG.error(
                "Ventilation mode '%s' not supported: %s",
                vent_mode,
                self._vent_modes,
            )
            return

        self._vent_mode = vent_mode
        self._preset_mode = vent_mode
        self._attributes[ATTR_VENT_MODE] = vent_mode

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return state attributes."""
        return self._attributes

    def _determine_current_relay_speed(self) -> str | None:
        """Probe W1/W2 relays for current states and then match to a speed."""
        w1 = self.hass.states.get(self._relay_w1)
        if not w1:
            LOG.warning(
                "W1 entity %s not found, cannot determine %s LUNOS speed.",
                self._relay_w1,
                self._name,
            )
            return None

        w2 = self.hass.states.get(self._relay_w2)
        if not w2:
            LOG.warning(
                "W2 entity %s not found, cannot determine %s LUNOS speed.",
                self._relay_w2,
                self._name,
            )
            return None

        # determine the current speed based on relay W1/W2 states
        current_state = [w1.state, w2.state]
        for speed, switch_state in self._relay_state_map.items():
            if current_state == switch_state:
                LOG.info("LUNOS '%s' speed=%s (W1/W2=%s)", self._name, speed, current_state)
                return speed

        LOG.info(
            'Could not determine current speed from W1/W2 relays: %s',
            current_state,
        )
        return None

    def _update_speed(self, speed: str | None) -> None:
        """Update the current speed (+ refresh any dependent attributes)."""
        if not speed or speed == self._current_speed:
            return

        self._current_speed = speed
        if speed != SPEED_OFF:
            self._last_non_off_speed = speed
        self._update_speed_attributes()
        LOG.info(
            'Updated LUNOS %s: %s%% %s',
            self._name,
            self.percentage,
            self._current_speed,
        )

    @property
    def _percentage_speeds(self) -> list[str]:
        """Return list of speeds excluding OFF for percentage calculations."""
        # ordered_list_item_to_percentage expects OFF to be represented by 0% and
        # not included in the ordered list.
        return [s for s in self._fan_speeds if s != SPEED_OFF]

    def _record_relay_state_change(self) -> None:
        """Record the timestamp of the last relay state change."""
        self._last_relay_change = time.time()

    async def _throttle_state_changes(self, required_delay: float) -> bool:
        """Ensure minimum delay between relay state changes."""
        if self._last_relay_change is None:
            return False

        time_passed = time.time() - self._last_relay_change
        if time_passed < required_delay:
            delay = max(0, required_delay - time_passed)
            LOG.warning(
                "To avoid LUNOS '%s' controller race conditions, "
                "sleeping %s seconds before changing relay.",
                self._name,
                delay,
            )
            await asyncio.sleep(delay)
            return True
        return False

    async def _async_set_named_speed(self, speed: str) -> None:
        """Set the fan speed using the integration's internal named speeds."""
        switch_states = self._relay_state_map.get(speed)
        if not switch_states:
            LOG.warning(
                "LUNOS '%s' DOES NOT support speed '%s'; ignoring speed change.",
                self._name,
                speed,
            )
            return

        # save the pending relay states (in case multiple changes are queued up in
        # event loop only the most recent should "win")
        self._pending_relay_w1 = switch_states[0]
        self._pending_relay_w2 = switch_states[1]

        # wait after any relay was last changed to avoid LUNOS controller
        # misinterpreting toggles
        #
        # FIXME: there really should be a queue of changes with a delay between each
        # before application instead of this (and clearing out of old changes IF any
        # are queued up). This existing
        # implementation here does not work if someone starts clicking changes again and again
        await self._throttle_state_changes(MINIMUM_DELAY_BETWEEN_STATE_CHANGES)

        if self._pending_relay_w1 is not None:
            LOG.info(
                "Changing LUNOS '%s' speed: %s -> %s",
                self._name,
                self._current_speed,
                speed,
            )
            await self.set_relay_switch_state(self._relay_w1, self._pending_relay_w1)
            await self.set_relay_switch_state(self._relay_w2, self._pending_relay_w2)
            self._pending_relay_w1 = self._pending_relay_w2 = None

        # update our internal state immediately (instead of waiting for callback
        # relays have changed)
        self._update_speed(speed)

    async def async_set_speed(self, speed: str) -> None:
        """Backward-compatible speed setter (deprecated by HA)."""
        await self._async_set_named_speed(speed)

    async def async_update(self) -> None:
        """Determine current state of the fan by inspecting relay states."""
        LOG.debug('%s async_update() called', self._name)

        # delay reading allow any pending switch changes to be applied
        await asyncio.sleep(1.0)

        actual_speed = self._determine_current_relay_speed()
        LOG.debug('%s async_update() = %s', self._name, actual_speed)
        self._update_speed(actual_speed)

    async def async_call_switch_service(
        self, method: str, relay_entity_id: str
    ) -> None:
        """Call the appropriate service for the relay entity."""
        domain = relay_entity_id.split('.', 1)[0]
        # Backward-compatible: original versions assumed relays were always switch entities.
        # Many Zigbee relays can also appear as light entities, so we route the service call
        # to the entity's domain when it's one we know.
        if domain not in ('switch', 'light'):
            LOG.warning(
                "Relay entity '%s' is in unsupported domain '%s'; falling back to switch.%s",
                relay_entity_id,
                domain,
                method,
            )
            domain = 'switch'

        LOG.info('Calling %s %s for %s', domain, method, relay_entity_id)
        await self.hass.services.async_call(domain, method, {'entity_id': relay_entity_id}, False)
        self._record_relay_state_change()

    async def set_relay_switch_state(self, relay_entity_id: str, state: str) -> None:
        """Set the relay to the specified state."""
        method = SERVICE_TURN_ON if state == STATE_ON else SERVICE_TURN_OFF
        await self.async_call_switch_service(method, relay_entity_id)

    async def toggle_relay_to_set_lunos_mode(self, entity_id: str) -> None:
        """Toggle relay multiple times to set LUNOS mode."""
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
        if saved_speed is not None:
            await self._async_set_named_speed(saved_speed)

    async def async_clear_filter_reminder(self) -> None:
        """Clear the filter change reminder light."""
        LOG.info("Clearing the filter change reminder light for LUNOS '%s'", self._name)

        # toggling W1 many times within 3 seconds instructs the LUNOS controller
        # to clear the filter warning light
        await self.toggle_relay_to_set_lunos_mode(self._relay_w1)

    # In LUNOS summer vent mode, the reversing time for the fans is extended to 1 hour.
    # The fan will run for 1 hour in the supply air mode and the following hour in
    # the exhaust air mode (resets after 8 hours). This is typically used during summer
    # nighttime to allow cooler air into the house.
    def supports_summer_ventilation(self) -> bool:
        """Return True if this fan supports summer ventilation mode."""
        return VENT_SUMMER in self._vent_modes

    async def async_turn_on_summer_ventilation(self) -> None:
        """Enable summer ventilation mode."""
        if not self.supports_summer_ventilation():
            LOG.warning("LUNOS '%s' DOES NOT support summer vent", self._name)
            return

        LOG.info("Enabling summer vent mode for LUNOS '%s'", self._name)
        # toggling W2 many times within 3 seconds instructs the LUNOS controller
        # to turn on summer ventilation mode
        await self.toggle_relay_to_set_lunos_mode(self._relay_w2)

        self._vent_mode = VENT_SUMMER
        self._preset_mode = VENT_SUMMER
        self._attributes[ATTR_VENT_MODE] = VENT_SUMMER

    async def async_turn_off_summer_ventilation(self) -> None:
        """Disable summer ventilation mode."""
        if not self.supports_summer_ventilation():
            return

        # wait after any relay was last changed to avoid LUNOS controller misinterpreting toggles
        await self._throttle_state_changes(MINIMUM_DELAY_BETWEEN_STATE_CHANGES)

        LOG.info("Disabling summer vent mode for LUNOS '%s'", self._name)

        # toggle W2 relay once to clear summer ventilation (and return to previous speed)
        await self.async_call_switch_service(SERVICE_TOGGLE, self._relay_w2)
        await asyncio.sleep(DELAY_BETWEEN_FLIPS)
        await self.async_call_switch_service(SERVICE_TOGGLE, self._relay_w2)

        self._vent_mode = DEFAULT_VENT_MODE
        self._preset_mode = DEFAULT_VENT_MODE
        self._attributes[ATTR_VENT_MODE] = DEFAULT_VENT_MODE
