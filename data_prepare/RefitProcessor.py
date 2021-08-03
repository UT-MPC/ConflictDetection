from datetime import datetime
from datetime import timedelta
import json
import logging
import os
import pandas as pd
from pytz import timezone
from typing import List, Dict, Tuple

from config import *

class RefitProcessor():
    datetime_temp = "%Y-%m-%d %H:%M:%S"
    datetime_col = "Time"
    weather_time_col = "date_time"
    gap_timedelta = timedelta(minutes=50)
    minimal_evt_duration_default = timedelta(minutes=10)

    # The weather categories in the data set are too many. We need to reduce some of them.
    # For those not in this list will be left unchanged. 
    ctx_category_translate = {
        "weatherDesc": {
            'Mist' : 'Fog',
            'Light snow' : 'Snow',
            'Moderate rain' : 'Rain',
            'Patchy light rain with thunder' : 'Rain',
            'Patchy light snow' : 'Snow',
            'Moderate or heavy snow showers' : 'Rain',
            'Patchy heavy snow' : 'Snow',
            'Patchy light rain' : 'Rain',
            'Blowing snow' : 'HeavySnow',
            'Blizzard' : 'HeavySnow',
            'Moderate snow' : 'Snow',
            'Light sleet' : 'Rain',
            'Heavy snow' : 'HeavySnow',
            'Sunny' : 'Clear',
            'Partly cloudy' : 'Cloudy',
            'Freezing fog' : 'Fog',
            'Heavy rain' : 'HeavyRain',
            'Patchy light drizzle' : 'Rain',
            'Moderate or heavy sleet' : 'Rain',
            'Patchy rain possible' : 'Cloudy',
            'Moderate or heavy snow with thunder' : 'Snow',
            'Light drizzle' : 'Rain',
            'Overcast' : 'Cloudy',
            'Light rain' : 'Rain',
            'Moderate rain at times' : 'Rain',
            'Light rain shower' : 'Rain',
            'Moderate or heavy rain with thunder' : 'HeavyRain',
            'Patchy moderate snow' : 'Snow',
            'Thundery outbreaks possible' : 'Cloudy',
            'Moderate or heavy rain shower' : 'HeavyRain',
        }
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
            evt_filtered[d].append(previous_state)
            for state in states[1:]:
                if evt_filtered[d][-1][0] == DEVICE_SKIP_STATE:
                    evt_filtered[d].append(previous_state)
                elif state[1] - previous_state[1] >= filter_dur[d]:
                    if previous_state[0] != evt_filtered[d][-1][0]:
                        evt_filtered[d].append(previous_state)
                previous_state = state
            if len(evt_filtered[d]) == 0 or previous_state[0] != evt_filtered[d][-1][0]:
                        evt_filtered[d].append(previous_state)
        return evt_filtered

    def device_evt_gen(self, device_data: pd.DataFrame, 
                        devices: Dict) -> Dict[str, List[Tuple[str, datetime]]]:
        device_evts = {d: [] for d in devices.keys()}
        time_series = [
            datetime.strptime(x, self.datetime_temp) 
            for x in device_data[self.datetime_col]
        ]
        for name, d in devices.items():
            vals_col = device_data[name]

            pre_time = time_series[0]
            for i, val in enumerate(vals_col):
                time = time_series[i]
                state = "on" if val > d["onThreshold"] else "off"
                if time - pre_time > self.gap_timedelta:
                    device_evts[name].append((DEVICE_SKIP_STATE, pre_time))
                    device_evts[name].append((state, time))
                elif (i == 0) or (state != device_evts[name][-1][0]):
                    # only append new state if it is different from previous or it is the first one
                    device_evts[name].append((state, time))
                pre_time = time

            
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

    def context_evt_gen(self, ctx_data: pd.DataFrame, 
                        contexts: Dict) -> Dict[str, List[Tuple[str, datetime]]]:
        ctx_evts = {c: [] for c in contexts.keys()}
        for index, row in ctx_data.iterrows():
            time = datetime.strptime(row["date_time"], self.datetime_temp)
            if row.isnull().values.any():
                # Skip this row if some values are Null. In the weather dataset, sometimes there are error in the data
                logging.warning("Empty cell in weather dataset at timestamp {}".format(row[self.weather_time_col]))
                continue
            for name, d in contexts.items():
                state = row[d["name"]]
                # Add optional lambda process
                if "lambda" in d:
                    state = d["lambda"](state)
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

    def search_device(self, raw_data:Dict, d_list:List) -> Dict[str, List[Tuple[str, datetime]]]:
        device_evts = {}
        chosen_devices = {
            d["name"]: d
            for d in d_list
        }
        return self.device_evt_gen(raw_data, chosen_devices)

    # Generate the device interaction event and the context changing 
    # events from the data set and output it to a file for future usage.
    def preprocess(self, output_file: str = "p") -> Tuple[Dict[str, List], Dict[str, List]]:
        raw_data = {}
        for filename in self.ctx_list:
            raw_data[filename] = pd.read_csv(os.path.join(self.project_folder, filename))
            logging.info("Load ctx data file: " + os.path.join(filename))
        ctx_evt = self.get_context(raw_data)
        # Add context type to name
        ctx_evt = { k + (CATEGORICAL_CTX_SUFFIX if k in self.ctx_category_translate else NUMERIC_CTX_SUFFIX) : v for k,v in ctx_evt.items()}

        device_evt = {}
        for filename in self.device_list:
            raw_data = pd.read_csv(os.path.join(self.project_folder, filename))
            logging.info("Load REFIT data file: " + os.path.join(filename))
            device_evt = self.search_device(raw_data, self.device_list[filename])

            with open(os.path.join(self.project_folder, output_file + "_" + filename), 'w') as f:
                f.write(json.dumps((ctx_evt, device_evt), default=str))
        return (ctx_evt, device_evt)



