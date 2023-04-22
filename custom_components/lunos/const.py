LUNOS_DOMAIN = "lunos"
DEFAULT_LUNOS_NAME = "LUNOS Ventilation"

SPEED_TURBO = "turbo"  # not sure what this speed is ;)
SPEED_HIGH = "high"
SPEED_MEDIUM = "medium"
SPEED_LOW = "low"
SPEED_SILENT = "silent"  # for 4-speed fans when there is no off
SPEED_OFF = "off"

SPEED_MAX = "max"  # logical speed that is the lowest speed the fan can run
SPEED_MIN = "min"  # logical speed that is the fastest speed the fan can run

SPEED_LIST = [SPEED_OFF, SPEED_SILENT, SPEED_LOW, SPEED_MEDIUM, SPEED_HIGH, SPEED_TURBO]
DEFAULT_SPEED = SPEED_MEDIUM

PRESET_SILENT = SPEED_SILENT
PRESET_LOW = SPEED_LOW
PRESET_MEDIUM = SPEED_MEDIUM
PRESET_HIGH = SPEED_HIGH
PRESET_TURBO = SPEED_TURBO

# delay all speed changes to > 3 seconds since the last relay switch change to avoid side effects
SPEED_CHANGE_DELAY_SECONDS = 4
DELAY_BETWEEN_FLIPS = 0.100
MINIMUM_DELAY_BETWEEN_STATE_CHANGES = 4.0

ATTR_CFM = "cfm"  # note: even when off some LUNOS fans still circulate air
ATTR_CMHR = "cmh"
ATTR_DB = "dB"
ATTR_MODEL_NAME = "model"
ATTR_WATTS = "watts"
ATTR_SPEED = "speed"
UNKNOWN = "Unknown"

ATTR_VENT_MODE = "vent_mode"
VENT_ECO = "eco"
VENT_SUMMER = "summer"  # also known as night mode
VENT_EXHAUST_ONLY = "exhaust"
VENT_MODES = [VENT_ECO, VENT_SUMMER, VENT_EXHAUST_ONLY]
DEFAULT_VENT_MODE = VENT_ECO

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
