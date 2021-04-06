from casas_processor import *
from UmassProcessor import UmassProccessor
import re

DATASET = "hh104"
FILENAME = "data/" + DATASET + "/ann.txt"

# Device Type -> Regex to match for the device, the corresponding operations
device_set = {
    "Light": [r'L+[0-9]+', {"ON, OFF"}]
}

def test_umass():
    pass

def main():
    for key, val in device_set.items():
        # Compile the regex for future use
        val[0] = re.compile(val[0])
    test_umass()

if __name__ == "__main__":
    main()

