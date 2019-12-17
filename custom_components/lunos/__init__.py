"""
LUNOS Ventilation Fan Control for Home Assistant
https://github.com/rsnodgrass/hass-lunos
"""
import logging
import yaml

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

LUNOS_CODING_CONFIG = {}

#async def async_setup(hass, config):
def setup(hass, config):
    global LUNOS_CODING_CONFIG
    LUNOS_CODING_CONFIG = yaml.load('lunos-codings.yaml', Loader=yaml.FullLoader)
    return True

# NOTE: for four-speed LUNOS controller settings, adding a 120V switch that turns off the LUNOS
# transformer entirely would add a Off setting in addition to the four-speeds.
LUNOS_SETTINGS = {
    'e2': {
        'name': 'LUNOS e2 (non-USA)',
        'controller_setting': '3',
        'default_fan_count': 2,
        'cfm': {
            SPEED_LOW:    15 / CFM_TO_CMHR,
            SPEED_MEDIUM: 30 / CFM_TO_CMHR,
            SPEED_HIGH:   38 / CFM_TO_CMHR
        },
        'summer_vent': False,
        'cycle_seconds': 70
    },
    'e2-4speed': {
        'name': 'LUNOS e2 (4-speed)',
        'controller_setting': '4',
        'default_fan_count': 2,
        'cfm': {
            SPEED_OFF:    15 / CFM_TO_CMHR,
            SPEED_LOW:    20 / CFM_TO_CMHR,
            SPEED_MEDIUM: 30 / CFM_TO_CMHR,
            SPEED_HIGH:   38 / CFM_TO_CMHR
        },
        'four_speed': True,
        'summer_vent': True,
        'cycle_seconds': 70
    },
    'e2-short': {
        'name': 'LUNOS e2 Short (non-USA)',
        'controller_setting': '5',
        'default_fan_count': 2,
        'cfm': {
            SPEED_LOW:    15 / CFM_TO_CMHR,
            SPEED_MEDIUM: 30 / CFM_TO_CMHR,
            SPEED_HIGH:   38 / CFM_TO_CMHR
        },
        'summer_vent': True,
        'cycle_seconds': 55
    },
    'e2-usa': {
        'name': 'LUNOS e2 (USA)',
        'controller_setting': '6',
        'default_fan_count': 2,
        'cfm': {
            SPEED_LOW:    10, # 17   / CFM_TO_CMHR
            SPEED_MEDIUM: 15, # 25.5 / CFM_TO_CMHR
            SPEED_HIGH:   20  # 34   / CFM_TO_CMHR
        },
        'summer_vent': True,
        'cycle_seconds': 70
    },
    'e2-short-usa': {
        'name': 'LUNOS e2 Short (USA)',
        'controller_setting': '7',
        'default_fan_count': 2,
        'cfm': {                # STRANGE: different sources specific different CFM
            SPEED_LOW:    9,  # 17   / CFM_TO_CMHR
            SPEED_MEDIUM: 18, # 25.5 / CFM_TO_CMHR
            SPEED_HIGH:   22  # 34   / CFM_TO_CMHR
        },
        'summer_vent': True,
        'cycle_seconds': 55
    },
    'ego': {
        'name': 'LUNOS eGO',
        'controller_setting': '9',
        'default_fan_count': 1,
        'cfm': {
            SPEED_LOW:     5 / CFM_TO_CMHR,  # 3 CFM
            SPEED_MEDIUM: 10 / CFM_TO_CMHR,  # 6 CFM
            SPEED_HIGH:   20 / CFM_TO_CMHR   # 12 CFM
        },
        'summer_vent': True,
        'cycle_seconds': 50
    },
    'ego-4speed': {
        'name': 'LUNOS eGO (4-speed)',
        'controller_setting': 'A',
        'default_fan_count': 1,
        'cfm': {
            SPEED_OFF:    5  / CFM_TO_CMHR,
            SPEED_LOW:    10 / CFM_TO_CMHR,
            SPEED_MEDIUM: 15 / CFM_TO_CMHR,
            SPEED_HIGH:   20 / CFM_TO_CMHR
            # SPEED_TURBO: flip W2 on/off < 3 seconds = 60 m3/h
        },
        'four_speed': True,
        'summer_vent': True,
        'turbo_mode': True,
        'cycle_seconds': 50
    },
    'ego-exhaust-4speed': {
        'name': 'LUNOS eGO (high=exhaust-only, 4-speed)',
        'controller_setting': 'B',
        'default_fan_count': 1,
        'cfm': {
            SPEED_OFF:    5  / CFM_TO_CMHR,
            SPEED_LOW:    10 / CFM_TO_CMHR,
            SPEED_MEDIUM: 20 / CFM_TO_CMHR,
            SPEED_HIGH:   45 / CFM_TO_CMHR # exhaust only
        },
        # TODO: this behavior model (instead of a cfm entry) seems to work better with features applying to specific modes
        'behavior': {
            SPEED_OFF: {
                'cfm': 5  / CFM_TO_CMHR
            },
            SPEED_LOW: {
                'cfm': 10 / CFM_TO_CMHR  # 3 CFM
            },
            SPEED_MEDIUM: {
                'cfm': 20 / CFM_TO_CMHR  # 6 CFM
            },
            SPEED_HIGH: {
                'cfm': 45 / CFM_TO_CMHR, # 12 CFM
                'exhaust_only': True
            }
        },
        'four_speed': True,
        'summer_vent': True,
        'cycle_seconds': 50
    },
    'ego-exhaust': {
        'name': 'LUNOS eGO (high=exhaust-only)',
        'controller_setting': 'C',
        'default_fan_count': 1,
        'cfm': {
            SPEED_LOW:     5 / CFM_TO_CMHR,
            SPEED_MEDIUM: 10 / CFM_TO_CMHR,
            SPEED_HIGH:   45 / CFM_TO_CMHR # exhaust only
        },
        'four_speed': True,
        'high_exhaust_only': True,
        'summer_vent': True,
        'cycle_seconds': 50
    },
    'ra-15-60': {
        'name': 'LUNOS RA 15-60',
        'controller_setting': '0',
        'default_fan_count': 1,
        'cfm': {
            SPEED_LOW:    15 / CFM_TO_CMHR, # 9 CFM
            SPEED_MEDIUM: 30 / CFM_TO_CMHR, # 18 CFM
            SPEED_HIGH:   45 / CFM_TO_CMHR  # 27 CFM
            # SPEED_TURBO: flip W2 on/off < 3 seconds = 60 m3/h (35 CFM)
        },
        'summer_vent': False,
        'turbo_mode': True, # flip W2 on/off < 3 seconds = 60 m3/h
        'exhaust_only': True # not a HRV
    },
    'ra-15-60-high': {
        'name': 'LUNOS RA 15-60 (Extra High)',
        'controller_setting': '1',
        'default_fan_count': 1,
        'cfm': {
            SPEED_LOW:    15 / CFM_TO_CMHR, # 9 CFM
            SPEED_MEDIUM: 30 / CFM_TO_CMHR, # 18 CFM
            SPEED_HIGH:   60 / CFM_TO_CMHR  # 35 CFM
        },
        'summer_vent': False,
        'exhaust_only': True # not a HRV
    },
    'ra-15-60-4speed': {
        'name': 'LUNOS RA 15-60 (4-speed)',
        'controller_setting': '2',
        'default_fan_count': 1,
        'cfm': {
            SPEED_OFF:    15 / CFM_TO_CMHR, # 9 CFM
            SPEED_LOW:    30 / CFM_TO_CMHR, # 18 CFM
            SPEED_MEDIUM: 45 / CFM_TO_CMHR, # 27 CFM
            SPEED_HIGH:   60 / CFM_TO_CMHR  # 35 CFM
        },
        'summer_vent': False,
        'exhaust_only': True # not a HRV
    }
}