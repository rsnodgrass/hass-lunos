"""
LUNOS Fan Control for Home Assistant
https://github.com/rsnodgrass/hass-lunos
"""
import logging

from homeassistant.helpers import discovery
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

LUNOS_DOMAIN = 'lunos'

def setup(hass, config):
    """Set up the LUNOS fan controllers"""
    conf = config[LUNOS_DOMAIN]

    # FIXME: iterate through the config!
#    for component in ['fan']:
#        discovery.load_platform(hass, component, LUNOS_DOMAIN, conf, config)
    return True
