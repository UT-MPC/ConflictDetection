from datetime import datetime
from datetime import timedelta
import json
import logging
import os
import pandas as pd
from pytz import timezone
from typing import List, Dict, Tuple

from config import *

class UmassProccessor():
    datetime_temp = "%Y-%m-%d %H:%M:%S"
    weather_timezone = timezone("US/Eastern")
    datetime_col = "Date & Time"
    weather_time_col = "time"
    minimal_evt_duration_default = timedelta(minutes=10)

    # The weather categories in the data set are too many. We need to reduce some of them.
    # For those not in this list will be left unchanged. 
    ctx_category_translate = {
        "summary": {'Breezy and Mostly Cloudy': 'Breezy',
            'Breezy and Partly Cloudy': 'Breezy',
            'Breezy and Overcast': 'Breezy',
            'Light Rain and Breezy': 'Rain',
            'Rain and Breezy': 'Rain',
            'Humid and Partly Cloudy': 'Cloudy',
            'Drizzle': 'Rain',
            'Drizzle and Breezy': 'Rain',
            'Dry': 'Clear',
            'Flurries': 'Snow',
            'Flurries and Breezy': 'Snow',
            'Heavy Rain': 'Rain',
            'Heavy Snow': 'Snow',
            'Light Rain': 'Rain',
            'Light Snow': 'Snow',
            'Mostly Cloudy': 'Cloudy',
            'Overcast': 'Cloudy',
            'Partly Cloudy': 'Cloudy',}
    }

    def __init__(self, project_folder:str, context_list: Dict, device_list: Dict):
        self.project_folder = project_folder
        self.ctx_list = context_list
        self.device_list = device_list

    def evt_time_filter(self, evts: Dict[str, List], 
                        filter_dur: Dict[str, timedelta]) -> Dict[str, List[Tuple[str, datetime]]]:
        evt_filtered = {}
        for d, states in evts.items():
            evt_filtered[d] = []
            previous_state = states[0]
            for state in states[1:]:
                if state[1] - previous_state[1] >= filter_dur[d]:
                    if len(evt_filtered[d]) == 0 or previous_state[0] != evt_filtered[d][-1][0]:
                        evt_filtered[d].append(previous_state)
                previous_state = state
            if len(evt_filtered[d]) == 0 or previous_state[0] != evt_filtered[d][-1][0]:
                        evt_filtered[d].append(previous_state)
        return evt_filtered

    def device_evt_gen(self, device_data: pd.DataFrame, 
                        devices: Dict) -> Dict[str, List[Tuple[str, datetime]]]:
        device_evts = {d: [] for d in devices.keys()}
        for index, row in device_data.iterrows():
            time = datetime.strptime(row[self.datetime_col], self.datetime_temp)
            for name, d in devices.items():
                state = "on" if row[d["name"]] > d["onThreshold"] else "off"
                if (len(device_evts[name]) == 0) or (state != device_evts[name][-1][0]):
                    # only append new state if it is different from previous or it is the first one
                    device_evts[name].append((state, time))
        logging.debug("The number of device events before filter: {}".format(
            {x: len(device_evts[x]) for x in device_evts}))
        evt_filtered = self.evt_time_filter(device_evts, 
                {d: devices[d].get("minStateTime", self.minimal_evt_duration_default) for d in devices})
        logging.debug("The number of device events after filter: {}".format(
            {x: len(evt_filtered[x]) for x in evt_filtered}))
        evt_filtered = {
            devices[d].get("deviceName", d) : evt_filtered[d]
            for d in devices
        }
        return evt_filtered

    def search_device(self, raw_data:Dict) -> Dict[str, List[Tuple[str, datetime]]]:
        device_evts = {}
        for filename, devices in self.device_list.items():
            if filename not in raw_data:
                # No file found
                logging.error("File {} not found!!".format(filename))
                continue
            cols = [self.datetime_col]
            chosen_devices = {}
            for d in devices:
                if d["name"] not in raw_data[filename].columns:
                    # No device found
                    logging.error("The device({}) is not a column in file({})!!".format(d, filename))
                else: 
                    cols.append(d["name"])
                    chosen_devices[d["name"]] = d

            # No device columns found in this table
            if len(cols) < 2:
                continue
            data = raw_data[filename].loc[:, cols]
            device_evts.update(self.device_evt_gen(data, chosen_devices))
        return device_evts

    def context_evt_gen(self, ctx_data: pd.DataFrame, 
                        contexts: Dict) -> Dict[str, List[Tuple[str, datetime]]]:
        ctx_evts = {c: [] for c in contexts.keys()}
        for index, row in ctx_data.iterrows():
            time = datetime.fromtimestamp(row[self.weather_time_col], self.weather_timezone).replace(tzinfo=None)
            if row.isnull().values.any():
                # Skip this row if some values are Null. In the weather dataset, sometimes there are error in the data
                logging.warning("Empty cell in weather dataset at timestamp {}".format(row[self.weather_time_col]))
                continue
            for name, d in contexts.items():
                state = row[d["name"]]
                # If this is a categorical context, we might need to convert it
                if name in self.ctx_category_translate:
                    state = self.ctx_category_translate[name].get(state, state)
                if (len(ctx_evts[name]) == 0) or (state != ctx_evts[name][-1][0]):
                    # only append new state if it is different from previous or it is the first one
                    ctx_evts[name].append((state, time))
        logging.debug("The number of context events before filter: {}".format(
            {x: len(ctx_evts[x]) for x in ctx_evts}))

        evt_filtered = self.evt_time_filter(ctx_evts, 
                {c: contexts[c].get("minStateTime", self.minimal_evt_duration_default) for c in contexts})
        
        logging.debug("The number of context events after filter: {}".format(
            {x: len(evt_filtered[x]) for x in evt_filtered}))
        return evt_filtered


    def get_context(self, raw_data: Dict):
        ctx_evts = {}
        for filename, ctxs in self.ctx_list.items():
            if filename not in raw_data:
                # No file found
                logging.error("File {} not found!!".format(filename))
                continue
            cols = [self.weather_time_col]
            chosen_ctx = {}
            for c in ctxs:
                if c["name"] not in raw_data[filename].columns:
                    # No device found
                    logging.error("The device({}) is not a column in file({})!!".format(c, filename))
                else: 
                    cols.append(c["name"])
                    chosen_ctx[c["name"]] = c
            # No device columns found in this table
            if len(cols) < 2:
                continue
            data = raw_data[filename].loc[:, cols]
            ctx_evts.update(self.context_evt_gen(data, chosen_ctx))
        return ctx_evts
        
    # Maybe change this function to merge sort
    def merge_ctx_evts(self, ctx_evts):
        all_evts = []
        for c, evts in ctx_evts:
            all_evts.extend([(c, x[0], x[1]) for x in evts])
        # Sort the events based on time
        return sorted(all_evts, key = lambda x : x[2])

    # Generate the device interaction event and the context changing 
    # events from the data set and output it to a file for future usage.
    def preprocess(self, output_file: str = "processed") -> Tuple[Dict[str, List], Dict[str, List]]:
        raw_data = {}
        all_csv = [f for f in os.listdir(self.project_folder) if f.endswith(".csv") and (f in self.device_list or f in self.ctx_list)]
        for f in all_csv:
            if f.endswith(".csv"):
                raw_data[f] = pd.read_csv(os.path.join(self.project_folder, f))
                logging.info("Load UMass data file: " + os.path.join(f))
        
        device_evt = self.search_device(raw_data)   
        ctx_evt = self.get_context(raw_data)

        # Add context type to name
        ctx_evt = { k + (CATEGORICAL_CTX_SUFFIX if k in self.ctx_category_translate else NUMERIC_CTX_SUFFIX) : v for k,v in ctx_evt.items()}

        with open(os.path.join(self.project_folder, output_file), 'w') as f:
            f.write(json.dumps((ctx_evt, device_evt), default=str))
        return (ctx_evt, device_evt)



