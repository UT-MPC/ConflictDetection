import os

from UmassProcessor import UmassProccessor

data_root = "data"
umass_root = "UMass"

def prepare_data():
    test_project = "HomeD/2016"
    project_path = os.path.join(data_root, umass_root, test_project)
    context_list = {}
    device_list = {"HomeD-meter1_2016.csv": ["WashingMachine [kW]"]}
    umass_processor = UmassProccessor(project_path, context_list, device_list)
    umass_processor.preprocess()

if __name__ == "__main__":
    prepare_data()
