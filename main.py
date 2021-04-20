import json
import logging
import re
import os

from casas_processor import *
from config import *
from utils import *
from UmassProcessor import UmassProccessor
from PatternBuilder import PatternBuilder

logging.basicConfig(level=PROJ_LOGGING_LEVEL)

# Device Type -> Regex to match for the device, the corresponding operations
device_set = {
    "Light": [r'L+[0-9]+', {"ON, OFF"}]
}
def compile_casas_device():
    for key, val in device_set.items():
        # Compile the regex for future use
        val[0] = re.compile(val[0])

def test_umass():
    test_project = "HomeD/2016"
    project_path = os.path.join(DATA_ROOT, UMASS_ROOT, test_project)
    input_file = os.path.join(project_path, PROCESSED_FILENAME)
    with open(input_file) as f:
        json_str = f.read()
        (ctx_evts, device_evts) = json.loads(json_str, object_hook=json_datetime_hook)
    logging.debug("The number of device events from processed file: {}".format(
        {x: len(device_evts[x]) for x in device_evts}))
    logging.debug("The number of context events from processed file: {}".format(
            {x: len(ctx_evts[x]) for x in ctx_evts}))
    
    p_builder = PatternBuilder()
    return p_builder.mine_patterns(ctx_evts, device_evts)


def main():
    test_umass()

if __name__ == "__main__":
    main()

