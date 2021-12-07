import sys
import json
import logging
import re
import random
import os
from datetime import timedelta

from config import *
from utils import *
from GridPatternBuilder import GridPatternBuilder, build_habit_groups
from ConflictDetector import ConflictDetector
from ContextAccessor import ContextAccessor



# Device Type -> Regex to match for the device, the corresponding operations
device_set = {
    "Light": [r'L+[0-9]+', {"ON, OFF"}]
}
def compile_casas_device():
    for key, val in device_set.items():
        # Compile the regex for future use
        val[0] = re.compile(val[0])

def load_processed(root_folder, project, is_sim = False, is_umass=True):
    if is_umass:
        project_path = os.path.join(root_folder, project)
        if is_sim:
            input_file = os.path.join(project_path, SIM_FILENAME)
        else:
            input_file = os.path.join(project_path, PROCESSED_FILENAME)
    else:
        input_file = os.path.join(root_folder, "processed",  project + ".json")
    
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

def generate_test_date(root_folder, test_projects, test_ratio = TEST_RATIO, true_random = True, is_sim = False, is_umass=True):
    start_time = []
    end_time = []
    for project in test_projects:
        ctx_evts, device_evts = load_processed(root_folder, project, is_sim, is_umass)
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

def test_umass(root_folder = "", test_project="HomeF/2016", ctx_info=None, grid_cfg=None, train_ratio=1-TEST_RATIO, 
                is_sim = False, is_umass=True):
    ctx_evts, device_evts = load_processed(root_folder, test_project, is_sim, is_umass)
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
    if grid_cfg is None:
        grid_cfg = {
            "context_info" : ctx_info,
            "test_dates": set(),
            "device_state_map": device_state_map,
        }
    p_builder = GridPatternBuilder(grid_cfg)
    return p_builder.mine_patterns(ctx_evts, device_evts)


def example_run():
    root_folder = os.path.join(DATA_ROOT, REFIT_ROOT)
    test_projects = [
        "House3",
        "House4",
    ]
    time_step = 1
    ctx_info = ContextAccessor({
                TIME_CTX: {
                    "range" : (0, 24*60),
                    "interval" : 60,
                },
                "weatherDesc#CAT": {},
                WEEKDAY_CTX: {
                    "range": (0, 6),
                    "interval": 1,
                },
            })
    capacity = {
        "TV":1,
        "WashingMachine":1,
        "PC": 1,
    }
    capacity = {
        "TV":1,
        "WashingMachine":1,
        "PC": 1,
    }
    BOOL_SIM = False
    BOOL_UMASS= False
    ccp_alpha = 4e-4
    grid_pattern_cfg = {
        "context_info" : ctx_info,
        "alpha": ccp_alpha,
        "test_dates": set(),
        "device_state_map": device_state_map,
        "time_delta": timedelta(minutes=time_step),
    }
    habit_groups = {}
    grid_data = {}

    # Generate habit patterns 
    for p in test_projects:
        grid_data[p] = test_umass(
                    root_folder = root_folder, 
                    test_project=p, 
                    ctx_info=ctx_info, 
                    grid_cfg = grid_pattern_cfg,
                    is_sim=BOOL_SIM, 
                    is_umass=BOOL_UMASS)
    for p in test_projects:
        habit_groups[p] = build_habit_groups(grid_data[p], 1e-4)

    # Predict conflict from mined habit patterns
    c_detector = ConflictDetector(ctx_info, capacity)
    final_conflicts = c_detector.predict_conflict_scenarios(habit_groups)
    print("The number of conflicts we found for the devices are:")
    print({x:len(final_conflicts[x]) for x in final_conflicts})

    # Outputing 5 example conflict scenarios with the highest probability for TV
    probs_i = [(x["prob"], i) for i, x in enumerate(final_conflicts["TV"])]
    for x in sorted(probs_i, reverse=True)[0:10]:
        c = final_conflicts["TV"][x[1]]
        ctx_str = ctx_info.coor_box_to_range(c["box"])
        p = c["prob"]
        us = list(c["users"])
        users = us[0][0] + " and " + us[1][0]
        print("{} have {:.2f}% to have conflicts over TV at {}".format(users, p*100, ctx_str))        

def main():
    logging.basicConfig(level=PROJ_LOGGING_LEVEL)

    example_run()

if __name__ == "__main__":
    main()

