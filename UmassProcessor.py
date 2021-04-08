from datetime import datetime
import os
import pandas as pd
from typing import List, Dict

class UmassProccessor():
    datetime_temp = "%Y-%m-%d %H:%M:%S"
    datetime_col = "Date & Time"

    def __init__(self, project_folder:str, context_list: dict, device_list: dict, output_file: str = "processed"):
        self.project_folder = project_folder
        self.ctx_list = context_list
        self.device_list = device_list
        self.output_file = output_file

    def device_evt_gen(self, device_data: pd.DataFrame, devices: List[Dict]):
        device_evt = {d: [] for d in devices.keys()}
        for index, row in device_data.iterrows():
            time = datetime.strptime(row[self.datetime_col], self.datetime_temp)
            for name, d in devices.items():
                state = "on" if row[d["name"]] > d["onThreshold"] else "off"
                if (len(device_evt[name]) == 0) or (state != device_evt[name][-1][0]):
                    # only append new state if it is different from previous or it is the first one
                    device_evt[name].append((state, time))
        print({x: len(device_evt[x]) for x in device_evt})
        evt_filtered = {}
        for d, states in device_evt.items():
            evt_filtered[d] = []
            previous_state = states[0]
            for state in states[1:]:
                if state[1] - previous_state[1] >= devices[d]["minStateTime"]:
                    if len(evt_filtered[d]) == 0 or previous_state[0] != evt_filtered[d][-1][0]:
                        evt_filtered[d].append(previous_state)
                previous_state = state
            if len(evt_filtered[d]) == 0 or previous_state[0] != evt_filtered[d][-1][0]:
                        evt_filtered[d].append(previous_state)
        print({x: len(evt_filtered[x]) for x in evt_filtered})
        return evt_filtered

    def search_device(self, raw_data:dict):
        for filename, devices in self.device_list.items():
            if filename not in raw_data:
                # No file found
                print("File {} not found!!".format(filename))
                continue
            cols = [self.datetime_col]
            chosen_devices = {}
            for d in devices:
                if d["name"] not in raw_data[filename].columns:
                    # No device found
                    print("The device({}) is not a column in file({})!!".format(d, filename))
                else: 
                    cols.append(d["name"])
                    chosen_devices[d["name"]] = d

            # No device columns found in this table
            if len(cols) < 2:
                continue
            data = raw_data[filename].loc[:, cols]
            self.device_evt_gen(data, chosen_devices)



    def preprocess(self):
        raw_data = {}
        all_csv = [f for f in os.listdir(self.project_folder) if f.endswith(".csv") and (f in self.device_list or f in self.ctx_list)]
        for f in all_csv:
            if f.endswith(".csv"):
                raw_data[f] = pd.read_csv(os.path.join(self.project_folder, f))
                print("Load file: " + os.path.join(f))
        self.search_device(raw_data)        



