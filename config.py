import logging
import re

DATA_ROOT = "data"
UMASS_ROOT = "UMass"

PROCESSED_FILENAME = "processed.json"
SIM_FILENAME = "sim_processed.json"
PROCESSED_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

PROJ_LOGGING_LEVEL = logging.DEBUG

CATEGORICAL_CTX_SUFFIX = "#CAT"
NUMERIC_CTX_SUFFIX = "#NUM"

TIME_CTX = "min_of_day" + NUMERIC_CTX_SUFFIX
WEEKDAY_CTX = "day_of_week" + NUMERIC_CTX_SUFFIX
TEST_RATIO = 0.3
DEFAULT_TIME_INTERVAL_MIN = 10

DEFAULT_ALPHA = 20e-6
MIN_OBS_GRID = 10

EXP_RANDOM_SEED = 42


on_off_states = {
    "off"   : 0,
    "on"    : 1,
    0       : "off",
    1       : "on",
}

window_state = {
    "off"       : 0,
    "close"     : 1,
    "open_full" : 2,
    0           : "off",
    1           : "close",
    2           : "open_full",  
}

device_state_map = {
    "Range" : on_off_states,
    "Microwave": on_off_states,
    "LivingLights": on_off_states,
    "HomeOffice": on_off_states,
    "WashingMachine": on_off_states,
    "Window": window_state,
}

