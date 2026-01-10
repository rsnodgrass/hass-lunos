"""LUNOS Heat Recovery Ventilation Fan Control for Home Assistant.

https://github.com/rsnodgrass/hass-lunos
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .helpers import load_lunos_codings

if TYPE_CHECKING:
    from .coordinator import LunosCoordinator

LOG = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.FAN]


@dataclass
class LunosRuntimeData:
    """Runtime data for a LUNOS config entry."""

    coordinator: LunosCoordinator
    coding_config: dict[str, Any]


type LunosConfigEntry = ConfigEntry[LunosRuntimeData]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up LUNOS from YAML configuration (deprecated)."""
    # YAML configuration is deprecated, but we still support import
    if DOMAIN in config:
        LOG.warning(
            'YAML configuration for LUNOS is deprecated. '
            'Please migrate to the UI-based configuration.'
        )
        # import each fan configuration
        for fan_config in config[DOMAIN] if isinstance(config[DOMAIN], list) else [config[DOMAIN]]:
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={'source': 'import'},
                    data=fan_config,
                )
            )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: LunosConfigEntry) -> bool:
    """Set up LUNOS from a config entry."""
    from .coordinator import LunosCoordinator

    # load coding configurations
    coding_config = await hass.async_add_executor_job(load_lunos_codings)
    LOG.info('LUNOS controller codings supported: %s', list(coding_config.keys()))

    # create coordinator
    coordinator = LunosCoordinator(hass, entry, coding_config)
    await coordinator.async_config_entry_first_refresh()

    # store runtime data
    entry.runtime_data = LunosRuntimeData(
        coordinator=coordinator,
        coding_config=coding_config,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: LunosConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
