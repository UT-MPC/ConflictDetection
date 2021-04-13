import logging
import re

DATA_ROOT = "data"
UMASS_ROOT = "UMass"

PROCESSED_FILENAME = "processed.json"
PROCESSED_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

PROJ_LOGGING_LEVEL = logging.DEBUG

CATEGORICAL_CTX_SUFFIX = "#CAT"
NUMERIC_CTX_SUFFIX = "#NUM"

TIME_CTX = "sec_of_day" + NUMERIC_CTX_SUFFIX

