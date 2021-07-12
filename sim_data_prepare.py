from datetime import datetime
from datetime import timedelta
import numpy as np
import math
from typing import Dict, List, Tuple
import random
import json
import os

from config import *
from utils import *

import json

sim_device_a = {
    "Window": {
        "rule_set": [
            {
                "ctx_box": {
                    TIME_CTX: [420, 780],
                    "summary" + CATEGORICAL_CTX_SUFFIX: {
                        "Breezy", "Clear", "Cloudy"
                    },
                    WEEKDAY_CTX: [0,5]
                },
                "state": "open_full",
                "prob": 1.,
            },
            {
                "ctx_box": {
                    TIME_CTX: [780, 840],
                    WEEKDAY_CTX: [0,5]
                },
                "state": "close",
                "prob": 1.,
            },
            {
                "ctx_box": {
                    TIME_CTX: [840, 1020],
                    "summary" + CATEGORICAL_CTX_SUFFIX: {
                        "Breezy", "Clear", "Cloudy"
                    },
                    WEEKDAY_CTX: [0,5]
                },
                "state": "open_full",
                "prob": 1.,
            },
            {
                "ctx_box": {
                    TIME_CTX: [600, 1020],
                    "summary" + CATEGORICAL_CTX_SUFFIX: {
                        "Breezy", "Clear", "Cloudy"
                    },
                    WEEKDAY_CTX: [5,7]
                },
                "state": "open_full",
                "prob": 1.,
            }
        ],
        "default_state": "close"
    },
}

sim_device_b = {
    "Window": {
        "rule_set": [
            {
                "ctx_box": {
                    TIME_CTX: [540, 1020],
                    "summary" + CATEGORICAL_CTX_SUFFIX: {
                        "Breezy", "Clear", "Cloudy"
                    },
                },
                "state": "open_full",
                "prob": 1.,
            }
        ],
        "default_state": "close"
    },
}


sim_time_min_delta = timedelta(minutes=1)
def match_ctx_box(ctx_snapshot, ctx_box):
    for ctx, val in ctx_snapshot.items():
        if ctx not in ctx_box:
            continue
        if CATEGORICAL_CTX_SUFFIX in ctx:
            if val not in ctx_box[ctx]:
                return False
        else:
            if val < ctx_box[ctx][0] or val >= ctx_box[ctx][1]:
                return False
    return True

def get_state_from_ctx(ctx_snapshot, device_rules):
    rule_set = device_rules["rule_set"]
    for rule in rule_set:
        if match_ctx_box(ctx_snapshot, rule["ctx_box"]):
            if random.uniform(0, 1.) <= rule["prob"]:
                return rule["state"]

    return device_rules["default_state"]


def generate_sim_data(ctx_evts, ctx_accessor, target_folder, device_info):
    cur_time = max([x[0][1] for c, x in ctx_evts.items()])
    end_time = min([x[-1][1] for c, x in ctx_evts.items()])
    ctx_snapshot = {
        c: ctx_evts.get(c, [[0]])[0][0]
        for c in ctx_accessor.get_all_ctx_ordered()
    }
    ctx_idx = {
        c: 0
        for c in ctx_evts
    }
    device_state = {
        d : device_info[d]["default_state"]
        for d in device_info
    }
    device_evts = {
        d: [[device_state[d], cur_time]]
        for d in device_info
    }

    while cur_time < end_time:
        ctx_accessor.update_time_ctx(ctx_snapshot, cur_time)

        for d in device_state:
            state = get_state_from_ctx(ctx_snapshot, device_info[d])
            if state != device_state[d]:
                device_evts[d].append([state, cur_time])
            device_state[d] = state
        
        next_t = datetime.max
        next_c = []
        for c in ctx_evts:
            if ctx_idx[c] + 1 < len(ctx_evts[c]):
                if ctx_evts[c][ctx_idx[c] + 1][1] < next_t:
                    next_c = [c]
                    next_t = ctx_evts[c][ctx_idx[c] + 1][1]
                elif ctx_evts[c][ctx_idx[c] + 1][1] == next_t:
                    next_c.append(c)
        if next_t <= cur_time + sim_time_min_delta:
            cur_time = next_t
            for c in next_c:
                ctx_idx[c] += 1
                ctx_snapshot[c] = ctx_evts[c][ctx_idx[c]][0]
        else:
            cur_time += sim_time_min_delta
    with open(os.path.join(target_folder, SIM_FILENAME), 'w') as f:
        f.write(json.dumps((ctx_evts, device_evts), default=str))




        

    