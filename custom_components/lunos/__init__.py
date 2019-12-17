"""
LUNOS Ventilation Fan Control for Home Assistant
https://github.com/rsnodgrass/hass-lunos
"""
import logging

from homeassistant.helpers import discovery
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'lunos'

CFM_TO_CMHR = 1.69901 # 1 cubic feet/minute = 1.69901 cubic meters/hour

# NOTE: for four-speed LUNOS controller settings, adding a 120V switch that turns off the LUNOS
# transformer entirely would add a Off setting in addition to the four-speeds.
LUNOS_SETTINGS = {
    'e2': {
        'name': 'LUNOS e2 (non-USA)',
        'controller_setting': '3',
        'cfm': {
            SPEED_LOW:    15 / CFM_TO_CMHR,
            SPEED_MEDIUM: 30 / CFM_TO_CMHR,
            SPEED_HIGH:   38 / CFM_TO_CMHR
        },
        'summer_vent': false,
        'cycle_seconds': 70
    },
    'e2-4speed': {
        'name': 'LUNOS e2 (4-speed)',
        'controller_setting': '4',
        'cfm': {
            SPEED_OFF:    15 / CFM_TO_CMHR,
            SPEED_LOW:    20 / CFM_TO_CMHR,
            SPEED_MEDIUM: 30 / CFM_TO_CMHR,
            SPEED_HIGH:   38 / CFM_TO_CMHR
        },
        'four_speed': true,
        'summer_vent': true,
        'cycle_seconds': 70
    },
    'e2-short': {
        'name': 'LUNOS e2 Short (non-USA)',
        'controller_setting': '5',
        'cfm': {
            SPEED_LOW:    15 / CFM_TO_CMHR,
            SPEED_MEDIUM: 30 / CFM_TO_CMHR,
            SPEED_HIGH:   38 / CFM_TO_CMHR
        },
        'summer_vent': true,
        'cycle_seconds': 55
    },
    'e2-usa': {
        'name': 'LUNOS e2 (USA)',
        'controller_setting': '6',
        'cfm': {
            SPEED_LOW:    10, # 17   / CFM_TO_CMHR
            SPEED_MEDIUM: 15, # 25.5 / CFM_TO_CMHR
            SPEED_HIGH:   20  # 34   / CFM_TO_CMHR
        },
        'summer_vent': true,
        'cycle_seconds': 70
    },
    'e2-short-usa': {
        'name': 'LUNOS e2 Short (USA)',
        'controller_setting': '7',
        'cfm': {                # STRANGE: different sources specific different CFM
            SPEED_LOW:    9,  # 17   / CFM_TO_CMHR
            SPEED_MEDIUM: 18, # 25.5 / CFM_TO_CMHR
            SPEED_HIGH:   22  # 34   / CFM_TO_CMHR
        },
        'summer_vent': true,
        'cycle_seconds': 55
    },
    'ego': {
        'name': 'LUNOS eGO',
        'controller_setting': '9',
        'cfm': {
            SPEED_LOW:     5 / CFM_TO_CMHR,  # 3 CFM
            SPEED_MEDIUM: 10 / CFM_TO_CMHR,  # 6 CFM
            SPEED_HIGH:   20 / CFM_TO_CMHR   # 12 CFM
        },
        'summer_vent': true,
        'cycle_seconds': 50
    },
    'ego-4speed': {
        'name': 'LUNOS eGO (4-speed)',
        'controller_setting': 'A',
        'cfm': {
            SPEED_OFF:    5  / CFM_TO_CMHR,
            SPEED_LOW:    10 / CFM_TO_CMHR,
            SPEED_MEDIUM: 15 / CFM_TO_CMHR,
            SPEED_HIGH:   20 / CFM_TO_CMHR
            # SPEED_TURBO: flip W2 on/off < 3 seconds = 60 m3/h
        },
        'four_speed': true,
        'summer_vent': true,
        'turbo_mode': true,
        'cycle_seconds': 50
    },
    'ego-exhaust-4speed': {
        'name': 'LUNOS eGO (high=exhaust-only, 4-speed)',
        'controller_setting': 'B',
        'cfm': {
            SPEED_OFF:    5  / CFM_TO_CMHR,
            SPEED_LOW:    10 / CFM_TO_CMHR,
            SPEED_MEDIUM: 20 / CFM_TO_CMHR,
            SPEED_HIGH:   45 / CFM_TO_CMHR # exhaust only
        },
        'four_speed': true,
        'high_exhaust_only': true,
        'summer_vent': true,
        'cycle_seconds': 50
    },
    'ego-exhaust': {
        'name': 'LUNOS eGO (high=exhaust-only)',
        'controller_setting': 'C',
        'cfm': {
            SPEED_LOW:     5 / CFM_TO_CMHR,
            SPEED_MEDIUM: 10 / CFM_TO_CMHR,
            SPEED_HIGH:   45 / CFM_TO_CMHR # exhaust only
        },
        'four_speed': true,
        'high_exhaust_only': true,
        'summer_vent': true,
        'cycle_seconds': 50
    },
    'ra-15-60': {
        'name': 'LUNOS RA 15-60',
        'controller_setting': '0',
        'cfm': {
            SPEED_LOW:    15 / CFM_TO_CMHR, # 9 CFM
            SPEED_MEDIUM: 30 / CFM_TO_CMHR, # 18 CFM
            SPEED_HIGH:   45 / CFM_TO_CMHR  # 27 CFM
            # SPEED_TURBO: flip W2 on/off < 3 seconds = 60 m3/h (35 CFM)
        },
        'summer_vent': false,
        'turbo_mode': true, # flip W2 on/off < 3 seconds = 60 m3/h
        'exhaust_only': true # not a HRV
    },
    'ra-15-60-high': {
        'name': 'LUNOS RA 15-60 (Extra High)',
        'controller_setting': '1',
        'cfm': {
            SPEED_LOW:    15 / CFM_TO_CMHR, # 9 CFM
            SPEED_MEDIUM: 30 / CFM_TO_CMHR, # 18 CFM
            SPEED_HIGH:   60 / CFM_TO_CMHR  # 35 CFM
        },
        'summer_vent': false,
        'exhaust_only': true # not a HRV
    },
    'ra-15-60-4speed': {
        'name': 'LUNOS RA 15-60 (4-speed)',
        'controller_setting': '2',
        'cfm': {
            SPEED_OFF:    15 / CFM_TO_CMHR, # 9 CFM
            SPEED_LOW:    30 / CFM_TO_CMHR, # 18 CFM
            SPEED_MEDIUM: 45 / CFM_TO_CMHR, # 27 CFM
            SPEED_HIGH:   60 / CFM_TO_CMHR  # 35 CFM
        },
        'summer_vent': false,
        'exhaust_only': true # not a HRV
    }
}

def setup(hass, config):
    """Set up the LUNOS fan controllers"""
    conf = config[DOMAIN]

    # FIXME: iterate through the config!
#    for component in conf['controllers']:
#        discovery.load_platform(hass, component, LUNOS_DOMAIN, conf, config)
    return True
