"""
LUNOS Ventilation Fan Control for Home Assistant
https://github.com/rsnodgrass/hass-lunos
"""

import logging
import os
import yaml

from homeassistant.helpers.discovery import load_platform
from .const import LUNOS_DOMAIN

LOG = logging.getLogger(__name__)

# read the configuration that describes each of the LUNOS controller coding settings
LUNOS_CODING_CONFIG = {}
config_path = os.path.dirname(__file__)
config_file = rf'{config_path}/lunos-codings.yaml'
try:
    with open(config_file) as file:
        LUNOS_CODING_CONFIG = yaml.full_load(file)
except Exception as e:
    LOG.error(f'Failed to load LUNOS config {config_file}: {e}')


async def async_setup(hass, config):
    LOG.info(f"LUNOS controller codings supported: {LUNOS_CODING_CONFIG.keys()}")

    conf = config.get(LUNOS_DOMAIN)
    if conf is None:
        LOG.info("No LUNOS configuration found")
        return True

    load_platform(
        hass,
        "fan",
        LUNOS_DOMAIN,
        None,
        conf,
    )

    return True
