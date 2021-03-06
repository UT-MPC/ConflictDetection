import sys
import os
# Add parent folder to path because I did not make a package. 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import timedelta
import logging

from config import *
from UmassProcessor import UmassProccessor
from RefitProcessor import RefitProcessor

logging.basicConfig(level=PROJ_LOGGING_LEVEL)

def prepare_umass_data():
    test_project = "HomeG/2016"
    project_path = os.path.join(DATA_ROOT, UMASS_ROOT, test_project)
    """
        The device dictionary consists of the informaiton of the deivces that will be used in this experiment. 
        For each table of UMass dataset, we have a list of device consisting of the name of the column in the table, the threshold 
        in kW to indicate that the device is turned on, and the minimal time that we use to remove noise. 
    """

    # device_list = {"HomeA-meter3_2016.csv": [
    #                     {"name": "ElectricRange [kW]", 
    #                     "onThreshold": 1.0, 
    #                     "minStateTime": timedelta(minutes= 1),
    #                     "deviceName": "Range"},
    #                 ],
    #                 "HomeA-meter4_2016.csv": [
    #                     {"name": "Microwave [kW]", 
    #                     "onThreshold": 1.0, 
    #                     "minStateTime": timedelta(minutes= 0),
    #                     "deviceName": "Microwave"},
    #                     {"name": "KitchenDenLights [kW]", 
    #                     "onThreshold": 0.05, 
    #                     "minStateTime": timedelta(minutes= 2),
    #                     "deviceName": "LivingLights"},
    #                     {"name": "OfficeLights [kW]", 
    #                     "onThreshold": 0.15, 
    #                     "minStateTime": timedelta(minutes= 10),
    #                     "deviceName": "HomeOffice"},
    #                 ],
    # }

    # device_list = { "HomeB-meter2_2016.csv": [
    #                     {"name": "Living room &amp; Kitchen Lights [kW]", 
    #                     "onThreshold": 0.025, 
    #                     "minStateTime": timedelta(minutes= 2), 
    #                     "deviceName": "LivingLights"},
    #                     {"name": "Microwave [kW]", 
    #                     "onThreshold": 0.25, 
    #                     "minStateTime": timedelta(minutes= 1), 
    #                     "deviceName": "Microwave"},
    #                 ]
    # }

    # device_list = { "HomeC-meter1_2016.csv": [
    #                     {"name": "Home office [kW]", 
    #                     "onThreshold": 0.3, 
    #                     "minStateTime": timedelta(minutes= 10), 
    #                     "deviceName": "HomeOffice"},
    #                     {"name": "Microwave [kW]", 
    #                     "onThreshold": 1.0, 
    #                     "minStateTime": timedelta(minutes= 1), 
    #                     "deviceName": "Microwave"},
    #                     {"name": "Living room [kW]", 
    #                     "onThreshold": 0.1, 
    #                     "minStateTime": timedelta(minutes= 2), 
    #                     "deviceName": "LivingLights"},
    #                 ]
    # }

    device_list = { "HomeD-meter1_2016.csv": [
                        {"name": "Microwave [kW]", 
                        "onThreshold": 0.1, 
                        "minStateTime": timedelta(minutes= 1), 
                        "deviceName": "Microwave"},
                        {"name": "KitchenLighting [kW]", 
                        "onThreshold": 0.01, 
                        "minStateTime": timedelta(minutes= 1), 
                        "deviceName": "LivingLights"},
                        {"name": "WashingMachine [kW]", 
                        "onThreshold": 0.01, 
                        "minStateTime": timedelta(minutes= 2), 
                        "deviceName": "WashingMachine"},
                    ],
                    "HomeD-meter2_2016.csv": [
                        {"name": "Range [kW]", 
                        "onThreshold": 0.1, 
                        "minStateTime": timedelta(minutes= 2), 
                        "deviceName": "Range"},
                    ],
    }

    # device_list = {"HomeF-meter2_2016.csv": [
    #                     {"name": "Microwave [kW]", 
    #                     "onThreshold": 0.5, 
    #                     "minStateTime": timedelta(minutes= 1),
    #                     "deviceName": "Microwave"},
    #                     {"name": "Washing_Machine [kW]", 
    #                     "onThreshold": 0.01, 
    #                     "minStateTime": timedelta(minutes= 10),
    #                     "deviceName": "WashingMachine"},
    #                 ]
    # }

    device_list = { "HomeG-meter1_2016.csv": [
                        {"name": "Wall oven [kW]", 
                        "onThreshold": 0.5, 
                        "minStateTime": timedelta(minutes= 2),
                        "deviceName": "Range"},
                    ],
                    "HomeG-meter2_2016.csv": [
                        {"name": "Dining + foyer lights [kW]", 
                        "onThreshold": 0.02, 
                        "minStateTime": timedelta(minutes= 2),
                        "deviceName": "LivingLights"},
                        {"name": "Office + sewing lights [kW]", 
                        "onThreshold": 0.1, 
                        "minStateTime": timedelta(minutes= 2),
                        "deviceName": "HomeOffice"},
                    ],
                    "HomeG-meter4_2016.csv": [
                        {"name": "Kitchen microwave [kW]", 
                        "onThreshold": 0.2, 
                        "minStateTime": timedelta(minutes= 1),
                        "deviceName": "Microwave"},
                    ]
    }

    context_list = {
        "weather-homeG2016.csv": [
            {"name": "apparentTemperature"},
            {"name": "temperature"},
            {"name": "humidity"},
            {"name": "summary"},
        ]
    }
    umass_processor = UmassProccessor(project_path, context_list, device_list)
    ctx_evts, device_evts = umass_processor.preprocess(output_file=PROCESSED_FILENAME)


def prepare_refit_data():
    test_project = "refit"
    project_path = os.path.join(DATA_ROOT, test_project)

    device_list = {
                    "House1.csv": [
                        {"name": "Appliance7", 
                        "onThreshold": 20, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "PC"},
                        {"name": "Appliance5", 
                        "onThreshold": 0, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "WashingMachine"},
                        {"name": "Appliance8", 
                        "onThreshold": 20, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "TV"},
                    ],
                    "House3.csv": [
                        {"name": "Appliance6", 
                        "onThreshold": 0, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "WashingMachine"},
                        {"name": "Appliance7", 
                        "onThreshold": 20, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "TV"},
                    ],
                    "House4.csv": [
                        {"name": "Appliance5", 
                        "onThreshold": 9, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "PC"},
                        {"name": "Appliance4", 
                        "onThreshold": 5, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "WashingMachine"},
                        {"name": "Appliance7", 
                        "onThreshold": 30, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "TV"},
                    ],
                    "House8.csv": [
                        {"name": "Appliance6", 
                        "onThreshold": 60, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "PC"},
                        {"name": "Appliance4", 
                        "onThreshold": 5, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "WashingMachine"},
                        {"name": "Appliance7", 
                        "onThreshold": 30, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "TV"},
                    ],
                    "House9.csv": [
                        {"name": "Appliance3", 
                        "onThreshold": 1, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "WashingMachine"},
                        {"name": "Appliance5", 
                        "onThreshold": 60, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "TV"},
                    ],
                    "House15.csv": [
                        {"name": "Appliance6", 
                        "onThreshold": 89, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "PC"},
                        {"name": "Appliance3", 
                        "onThreshold": 0, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "WashingMachine"},
                        {"name": "Appliance6", 
                        "onThreshold": 60, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "TV"},
                    ],
                    "House18.csv": [
                        {"name": "Appliance7", 
                        "onThreshold": 50, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "PC"},
                        {"name": "Appliance5", 
                        "onThreshold": 0, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "WashingMachine"},
                        {"name": "Appliance8", 
                        "onThreshold": 50, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "TV"},
                    ],
                    "House20.csv": [
                        {"name": "Appliance6", 
                        "onThreshold": 70, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "PC"},
                        {"name": "Appliance4", 
                        "onThreshold": 0, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "WashingMachine"},
                        {"name": "Appliance7", 
                        "onThreshold": 50, 
                        "minStateTime": timedelta(minutes= 5),
                        "deviceName": "TV"},
                    ],
    }
    context_list = {
        "Weather.csv": [
            {"name": "FeelsLikeC"},
            {"name": "cloudcover"},
            {"name": "humidity"},
            {"name": "weatherDesc", "lambda": lambda x: x.split("'")[-2]},
            {"name": "tempC"},
        ]
    }
    refit_processor = RefitProcessor(project_path, context_list, device_list)
    ctx_evts, device_evts = refit_processor.preprocess(output_folder="processed")


if __name__ == "__main__":
    prepare_refit_data()
