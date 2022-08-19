from homeassistant.const import STATE_OFF, STATE_ON

LUNOS_DOMAIN = "lunos"
DEFAULT_LUNOS_NAME = "LUNOS Ventilation"

SPEED_TURBO = 'turbo'
SPEED_HIGH = 'high'
SPEED_MEDIUM = 'medium'
SPEED_LOW = 'low'
SPEED_OFF = 'off'

SPEED_MAX = 'max' # logical speed that is the lowest speed the fan can run
SPEED_MIN = 'min' # logical speed that is the fastest speed the fan can run

SPEED_LIST = [ SPEED_OFF, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH ]
DEFAULT_SPEED = SPEED_MEDIUM

PRESET_ECO = 'eco'
PRESET_SUMMER_VENT = 'summer' # also known as night mode
PRESET_EXHAUST_ONLY = 'exhaust'
PRESET_LOW = SPEED_LOW
PRESET_MEDIUM = SPEED_MEDIUM
PRESET_HIGH = SPEED_HIGH
PRESET_TURBO = 'turbo'
PRESET_OFF = SPEED_OFF

# configuration of switch states to active LUNOS speeds
SPEED_SWITCH_STATES = {
    SPEED_OFF:    [ STATE_OFF, STATE_OFF ],
    SPEED_LOW:    [ STATE_ON,  STATE_OFF ],
    SPEED_MEDIUM: [ STATE_OFF, STATE_ON ],
    SPEED_HIGH:   [ STATE_ON,  STATE_ON ]
}

# set_percentage

# delay all speed changes to > 3 seconds since the last relay switch change to avoid side effects
SPEED_CHANGE_DELAY_SECONDS = 4

ATTR_CFM = "cfm"  # note: even when off some LUNOS fans still circulate air
ATTR_CMHR = "cmh"
ATTR_DB = "dB"
ATTR_MODEL_NAME = "model"
ATTR_WATTS = "watts"
ATTR_SPEED = "speed"
ATTR_VENTILATION_MODE = "ventilation"  # [ normal, summer, exhaust-only ]
UNKNOWN = "Unknown"

SERVICE_CLEAR_FILTER_REMINDER = "lunos_clear_filter_reminder"
SERVICE_TURN_ON_SUMMER_VENTILATION = "lunos_turn_on_summer_ventilation"
SERVICE_TURN_OFF_SUMMER_VENTILATION = "lunos_turn_off_summer_ventilation"

CONF_CONTROLLER_CODING = "controller_coding"
CONF_RELAY_W1 = "relay_w1"
CONF_RELAY_W2 = "relay_w2"
CONF_DEFAULT_SPEED = "default_speed"
CONF_DEFAULT_FAN_COUNT = "default_fan_count"
CONF_FAN_COUNT = "fan_count"

CFM_TO_CMH = 1.69901  # 1 cubic feet/minute = 1.69901 cubic meters/hour
