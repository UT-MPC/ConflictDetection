from datetime import timedelta
import logging
import os

from config import *
from UmassProcessor import UmassProccessor

logging.basicConfig(level=PROJ_LOGGING_LEVEL)

def prepare_data():
    test_project = "HomeF/2016"
    project_path = os.path.join(DATA_ROOT, UMASS_ROOT, test_project)
    """
        The device dictionary consists of the informaiton of the deivces that will be used in this experiment. 
        For each table of UMass dataset, we have a list of device consisting of the name of the column in the table, the threshold 
        in kW to indicate that the device is turned on, and the minimal time that we use to remove noise. 
    """
    device_list = {"HomeF-meter2_2016.csv": [
                        {"name": "Microwave [kW]", "onThreshold": 0.01, "minStateTime": timedelta(minutes= 0)},
                        {"name": "Washing_Machine [kW]", "onThreshold": 0.01, "minStateTime": timedelta(minutes= 10)},
                    ]
    }

    context_list = {
        "weather-homeF2016.csv": [
            {"name": "apparentTemperature"},
            {"name": "humidity"},
            {"name": "summary"},
        ]
    }
    umass_processor = UmassProccessor(project_path, context_list, device_list)
    ctx_evts, device_evts = umass_processor.preprocess(output_file=PROCESSED_FILENAME)



if __name__ == "__main__":
    prepare_data()
