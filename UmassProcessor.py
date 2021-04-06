import os
import pandas as pd

class UmassProccessor():
    datetime_temp = "%Y-%m-%d %H:%M:%S"
    datetime_col = "Date & Time"

    def __init__(self, project_folder:str, context_list: dict, device_list: dict, output_file: str = "processed"):
        self.project_folder = project_folder
        self.ctx_list = context_list
        self.device_list = device_list
        self.output_file = output_file

    def filter_device_evt(self, device_data: pd.DataFrame):
        print(device_data.head)        

    def search_device(self, raw_data:dict):
        for filename, devices in self.device_list.items():
            if filename not in raw_data:
                # No file found
                print("File {} not found!!".format(filename))
                continue
            cols = [self.datetime_col]
            for d in devices:
                if d not in raw_data[filename].columns:
                    # No device found
                    print("The device({}) is not a column in file({})!!".format(d, filename))
                else: 
                    cols.append(d)

            # No device columns found in this table
            if len(cols) < 2:
                continue
            data = raw_data[filename].loc[:, cols]
            self.filter_device_evt(data)



    def preprocess(self):
        raw_data = {}
        all_csv = [f for f in os.listdir(self.project_folder) if f.endswith(".csv") and (f in self.device_list or f in self.ctx_list)]
        for f in all_csv:
            if f.endswith(".csv"):
                raw_data[f] = pd.read_csv(os.path.join(self.project_folder, f))
                print("Load file: " + os.path.join(f))
        self.search_device(raw_data)        



