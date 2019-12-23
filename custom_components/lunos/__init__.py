"""
LUNOS Ventilation Fan Control for Home Assistant
https://github.com/rsnodgrass/hass-lunos
"""
import logging
import yaml
import os

from homeassistant.helpers import config_validation as cv, discovery
from homeassistant.helpers.entity import Entity
from homeassistant.components.fan import (
    SPEED_OFF,
    SPEED_LOW,
    SPEED_MEDIUM,
    SPEED_HIGH,
)

LOG = logging.getLogger(__name__)

LUNOS_DOMAIN = 'lunos'

CFM_TO_CMHR = 1.69901 # 1 cubic feet/minute = 1.69901 cubic meters/hour

# read the configuration that describes each of the LUNOS controller coding settings
with open(r'custom_components/lunos/lunos-codings.yaml') as file:
    LUNOS_CODING_CONFIG = yaml.full_load(file)
 
async def async_setup(hass, config):
    LOG.info(f"LUNOS controller codings supported: {LUNOS_CODING_CONFIG.keys()}")
    return True