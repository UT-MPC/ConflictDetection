import logging
import re

DATA_ROOT = "data"
UMASS_ROOT = "UMass"

PROCESSED_FILENAME = "processed.json"
PROCESSED_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

PROJ_LOGGING_LEVEL = logging.DEBUG

CATEGORICAL_CTX_SUFFIX = "#CAT"
NUMERIC_CTX_SUFFIX = "#NUM"

TIME_CTX = "min_of_day" + NUMERIC_CTX_SUFFIX
WEEKDAY_CTX = "day_of_week" + "#CAT"

on_off_states = {
    "off"   : 0,
    "on"    : 1,
    0       : "off",
    1       : "on",
}
device_state_map = {
    "Range" : on_off_states,
    "Microwave": on_off_states,
    "LivingLights": on_off_states,
    "HomeOffice": on_off_states,
    "WashingMachine": on_off_states,
}

