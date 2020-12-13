"""
LUNOS Ventilation Fan Control for Home Assistant
https://github.com/rsnodgrass/hass-lunos
"""
import logging
import os

import yaml

from .const import CFM_TO_CMH, LUNOS_DOMAIN

LOG = logging.getLogger(__name__)

# read the configuration that describes each of the LUNOS controller coding settings
LUNOS_CODING_CONFIG = {}
config_path = os.path.dirname(__file__)
config_file = rf"{config_path}/lunos-codings.yaml"
try:
    with open(config_file) as file:
        LUNOS_CODING_CONFIG = yaml.full_load(file)
except:
    LOG.error(f"Failed to load LUNOS config {config_file}")


async def async_setup(hass, config):
    LOG.info(f"LUNOS controller codings supported: {LUNOS_CODING_CONFIG.keys()}")
    return True
