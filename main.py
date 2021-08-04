import sys
sys.path.append("data_prepare")
import json
import logging
import re
import random
import os
from datetime import timedelta

from config import *
from utils import *
from UmassProcessor import UmassProccessor
from GridPatternBuilder import GridPatternBuilder
from ContextAccessor import ContextAccessor



# Device Type -> Regex to match for the device, the corresponding operations
device_set = {
    "Light": [r'L+[0-9]+', {"ON, OFF"}]
}
def compile_casas_device():
    for key, val in device_set.items():
        # Compile the regex for future use
        val[0] = re.compile(val[0])

def load_processed(project, is_sim = False, is_umass=True):
    if is_umass:
        project_path = os.path.join(DATA_ROOT, UMASS_ROOT, project)
        if is_sim:
            input_file = os.path.join(project_path, SIM_FILENAME)
        else:
            input_file = os.path.join(project_path, PROCESSED_FILENAME)
    else:
        input_file = os.path.join(DATA_ROOT, REFIT_ROOT, "p_" + project + ".csv")
    with open(input_file) as f:
        json_str = f.read()
        (ctx_evts, device_evts) = json.loads(json_str, object_hook=json_datetime_hook)
    return ctx_evts, device_evts

def extract_train_data(ctx_evts, device_evts, train_ratio):
    start_time = min([ctx_evts[x][0][1] for x in ctx_evts])
    end_time = max([ctx_evts[x][-1][1] for x in ctx_evts])
    total_time_range = end_time - start_time
    train_end = start_time + total_time_range * train_ratio
    ctx_evts = {
        x: [evt for evt in ctx_evts[x] if evt[1] <= train_end]
        for x in ctx_evts
    }
    device_evts = {
        x: [evt for evt in device_evts[x] if evt[1] <= train_end]
        for x in device_evts
    }
    return ctx_evts, device_evts

def generate_test_date(test_projects, test_ratio = TEST_RATIO, true_random = True, is_sim = False, is_umass=True):
    start_time = []
    end_time = []
    for project in test_projects:
        ctx_evts, device_evts = load_processed(project, is_sim, is_umass)
        if len(ctx_evts) > 0:
            start_time.append(min([ctx_evts[x][0][1] for x in ctx_evts]))
            end_time.append(max([ctx_evts[x][-1][1] for x in ctx_evts]))
        if len(device_evts) > 0:
            start_time.append(min([device_evts[x][0][1] for x in device_evts]))
            end_time.append(max([device_evts[x][-1][1] for x in device_evts]))
    s = max(start_time)
    e = min(end_time)
    logging.info("Time start {}, Time end {}".format(min(start_time), max(end_time)))
    total_time_range = e - s
    days = int(total_time_range.days)
    if not true_random:
        random.seed(EXP_RANDOM_SEED)
    sel = random.sample(range(days), int(days*test_ratio))
    return set([(s + timedelta(days=x)).date() for x in sel])

def test_umass(test_project="HomeF/2016", ctx_info=None, train_ratio=1-TEST_RATIO, 
                ccp_alpha=DEFAULT_ALPHA, test_dates=set(), is_sim = False, is_umass=True):
    ctx_evts, device_evts = load_processed(test_project, is_sim, is_umass)
    logging.debug("The number of device events from processed file: {}".format(
        {x: len(device_evts[x]) for x in device_evts}))
    logging.debug("The number of context events from processed file: {}".format(
            {x: len(ctx_evts[x]) for x in ctx_evts}))
    
    if ctx_info is None:
        ctx_info = ContextAccessor({
            TIME_CTX: {
                "range" : (0, 24*60),
                "interval" : 20,
            },
            # "humidity#NUM" : {
            #     "range" : (0., 1.0),
            #     "interval" : 0.1,
            # },
            WEEKDAY_CTX: {
                "range": (0, 6.1),
                "interval": 1,
            },
        })
    grid_pattern_cfg = {
        "time_delta" : timedelta(minutes=10),
        "context_info" : ctx_info,
        "alpha": ccp_alpha,
        "test_dates": test_dates
    }
    p_builder = GridPatternBuilder(grid_pattern_cfg)
    return p_builder.mine_patterns(ctx_evts, device_evts)


def main():
    logging.basicConfig(level=PROJ_LOGGING_LEVEL)

    test_umass()

if __name__ == "__main__":
    main()

