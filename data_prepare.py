from datetime import timedelta
import logging
import os

from UmassProcessor import UmassProccessor

data_root = "data"
umass_root = "UMass"
logging.basicConfig(level=logging.DEBUG)

def prepare_data():
    test_project = "HomeD/2016"
    project_path = os.path.join(data_root, umass_root, test_project)
    """
        The device dictionary consists of the informaiton of the deivces that will be used in this experiment. 
        For each table of UMass dataset, we have a list of device consisting of the name of the column in the table, the threshold 
        in kW to indicate that the device is turned on, and the minimal time that we use to remove noise. 
    """
    device_list = {"HomeD-meter1_2016.csv": [
                        {"name": "Microwave [kW]", "onThreshold": 0.01, "minStateTime": timedelta(minutes= 2)},
                    ]
    }

    context_list = {
        "weather-homeD2016.csv": [
            {"name": "apparentTemperature"},
            {"name": "humidity"},
            {"name": "summary"},
        ]
    }
    umass_processor = UmassProccessor(project_path, context_list, device_list)
    umass_processor.preprocess()

if __name__ == "__main__":
    prepare_data()