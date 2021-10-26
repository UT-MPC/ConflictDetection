import sys
sys.path.append("..")


import json
import numpy as np
import math
from typing import Dict, List, Tuple
import copy
from itertools import combinations
from collections import Counter
from statistics import median

import logging
from datetime import timedelta
from config import *
from utils import *
from main import *
from GtConflictFinder import GtConflictFinder
from ConflictDetector import ConflictDetector, ConflictPredicator
from GridPatternBuilder import build_habit_groups

import plotly.graph_objects as go
from plotly.subplots import make_subplots
root_folder = os.path.join(DATA_ROOT, REFIT_ROOT)


test_projects = [
    # "House1",
    "House3",
    "House4",
    "House8",
    "House9",
    "House15",
    # "House18",
    # "House20",
]
time_step = 1
default_train_ctx = ContextAccessor({
            TIME_CTX: {
                "range" : (0, 24*60),
                "interval" : 60,
            },
            # "humidity#NUM" : {
            #     "range" : (0, 100),
            #     "interval" : 10,
            # },
            # "FeelsLikeC#NUM" : {
            #     "range" : (-10., 40),
            #     "interval" : 5,
            # },
            # "tempC#NUM" : {
            #     "range" : (-10., 40),
            #     "interval" : 5,
            # },
            # "weatherDesc#CAT": {},
            # WEEKDAY_CTX: {
            #     "range": (0, 6),
            #     "interval": 1,
            # },
            # HOLIDAY_CTX: {
            #     "range": (0,1),
            #     "interval": 1,
            # }
        })

gt_ctx_info = ContextAccessor({
            TIME_CTX: {
                "range" : (0, 24*60),
                "interval" : 60,
            },
            # "humidity#NUM" : {
            #     "range" : (0, 100),
            #     "interval" : 10,
            # },
            # "FeelsLikeC#NUM" : {
            #     "range" : (-10., 40),
            #     "interval" : 5,
            # },
            # "tempC#NUM" : {
            #     "range" : (-10., 40),
            #     "interval" : 5,
            # },
            "weatherDesc#CAT": {},
            WEEKDAY_CTX: {
                "range": (0, 6),
                "interval": 1,
            },
            # HOLIDAY_CTX: {
            #     "range": (0,1),
            #     "interval": 1,
            # },
        })
capacity = {
    "TV":1,
    "WashingMachine":1,
    "PC": 1,
}
BOOL_SIM = False
BOOL_UMASS= False
ccp_alpha = 9e-5    # Normal
# ccp_alpha = 0.0003  # Det.

def full_test(ctx_info = default_train_ctx):
    test_dates = generate_test_date(root_folder, test_projects, test_ratio = 0.4, true_random=False, is_sim=BOOL_SIM, is_umass=BOOL_UMASS)
    grid_pattern_cfg = {
        # "time_delta" : timedelta(minutes=10),
        "context_info" : ctx_info,
        "alpha": ccp_alpha,
        "test_dates": test_dates,
        "device_state_map": device_state_map,
        "time_delta": timedelta(minutes=time_step),
    }
    habit_groups = {}
    grid_data = {}
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

    c_detector = ConflictDetector(ctx_info, capacity)
    final_conflicts = c_detector.predict_conflict_scenarios(habit_groups)

    # Make ground truth:
    device_events = {}
    for p in test_projects:
        ctx_evts, device_evts = load_processed(root_folder, p, is_sim=BOOL_SIM, is_umass=BOOL_UMASS)
        device_events[p] = device_evts

    gtconflict_cfg = {
        "context_info": gt_ctx_info,
        "capacity": capacity
    }
    # test_dates = {}

    conflict_finder = GtConflictFinder(gtconflict_cfg)
    gt_conflicts, test_state_cnt = conflict_finder.get_Gt_conflict(ctx_evts, device_events, test_dates)


    conflict_device = {
        d:[]
        for d in capacity
    }

    conflict_state_device = {
        d:{}
        for d in capacity
    }
    MIN_TEST_OBS = 20
    cnts = []
    for c in gt_conflicts:
        d = c["device"]
        conflict_device[d].append(c)
        s = gt_ctx_info.get_coor_by_ctx(c["ctx"])
        users = frozenset(c["device_states"].keys())
        cnts.append(test_state_cnt[d][users][s])
        if test_state_cnt[d][users][s] < MIN_TEST_OBS:
            continue
        if s not in conflict_state_device[d]:
            conflict_state_device[d][s] = {}
        conflict_state_device[d][s][users] = conflict_state_device[d][s].get(users, 0) + 1

        # if conflict_state_device[d][s][users] > test_state_cnt[d][s]:
        #     print(conflict_state_device[d][s][users], test_state_cnt[d][s])
        #     print(users, d, c["cur_time"], s)
        

    all_users = test_projects
    all_devices = capacity.keys()
    user_pairs = list(combinations(all_users, 2))
    conflict_predicator = ConflictPredicator(ctx_info, final_conflicts)
    exp_cnt = 0
    exp_gt_c = 0
    exp_result = {d:[0,0,0,0,0] for d in all_devices}
    max_p = 0
    all_state_cnt = 0
    final_res = {}
    for d in all_devices:
        gt_probs = []
        o_static = [[0,0], [0,0]]
        for u_pair in user_pairs:
            u_pair_set = frozenset(u_pair)
            it = np.nditer(test_state_cnt[d][u_pair_set], flags=['multi_index'])
            for count in it:
                all_state_cnt += count
                if count < MIN_TEST_OBS:
                    continue
                state = it.multi_index
                gt_prob = 0.
                if (d in conflict_state_device) and \
                    (state in conflict_state_device[d]) and \
                    (u_pair_set in conflict_state_device[d][state]):

                    gt_prob =  float(conflict_state_device[d][state][u_pair_set]) / count
                gt_ctx_snapshot = gt_ctx_info.coor_to_snapshot(state)

                pred_prob = conflict_predicator.get_prob_conflict(ctx_info.get_coor_by_ctx(gt_ctx_snapshot), u_pair, d)
                exp_cnt += 1
                gt_probs.append(gt_prob)
                if gt_prob > 0:
                    # if gt_prob > 0.5:
                    #     print(gt_ctx_info.coor_to_snapshot(state).values(), gt_prob, pred_prob, u_pair)
                    exp_gt_c += 1
                    exp_result[d][0] += abs(pred_prob - gt_prob)
                    exp_result[d][1] += 1
                    exp_result[d][4] += gt_prob
                    if gt_prob > 1:
                        print(gt_prob, pred_prob, d, u_pair)
                    max_p = max(gt_prob, max_p)

                else:
                    exp_result[d][2] += pred_prob - gt_prob
                    exp_result[d][3] += 1
            if len(gt_probs) == 0:
                continue
            median_gt = median(gt_probs)
            errors = [abs(x-median_gt) for x in gt_probs]
            for i, e in enumerate(errors):
                if gt_probs[i] > 0.:
                    o_static[0][0] += e
                    o_static[0][1] += 1
                else:
                    o_static[1][0] += e
                    o_static[1][1] += 1
            gt_probs = []
        final_res[d] = {
            "static": [o_static[0][0] / o_static[0][1], o_static[1][0] / o_static[1][1], (o_static[0][0] + o_static[1][0])/(o_static[0][1] + o_static[1][1])]
        }
        # print("Baseline for {}".format(d))
        # print("Baseline, optimal single prediction for conf is {}".format(o_static[0][0] / o_static[0][1]))
        # print("Baseline, optimal single prediction for non-conf is {}".format(o_static[1][0] / o_static[1][1]))
        # print("The overall baseline is {}".format((o_static[0][0] + o_static[1][0])/(o_static[0][1] + o_static[1][1])))

    for d in exp_result:
        r = exp_result[d]
        o_acc = [[0., 0.], [0., 0.]]
        o_zero = 0.
        # print("Device!! {}".format(d))
        # print("The no. conf {}, no. non-conf {}".format(r[1], r[3]))
        # print("The overall accuracy for conf is {}".format(r[0] / r[1]))
        # print("The overall accuracy for non-conf is {}".format(r[2] / r[3]))
        # print("The overall acc is {}".format((r[0] + r[2])/(r[1] + r[3])))

        # print("The overall zero for conf is {}".format(r[4] / r[1]))
        # print("The overall zero for all is {}".format(r[4] / (r[1] + r[3])))
        r[1] = max(0.000001, r[1])
        r[3] = max(0.000001, r[3])
        final_res[d].update({
            "conf cont.": [r[1], r[3]],
            "our": [r[0] / r[1], r[2] / r[3], (r[0] + r[2])/(r[1] + r[3])],
            "zero": [r[4] / r[1], r[4] / (r[1] + r[3])], 
        })
        # r.append((r[0] + r[2]) / (r[1] + r[3]))
        # if r[1] > 0:
        #     r[0] = r[0] / r[1]
        #     r[4] = r[4] / r[1]
        # if r[3] > 0:
        #     r[2] = r[2] / r[3]
    return final_res
def context_step_perc():
    # step_perc = [1, 2, 3, 6, 8, 10, 20, 30, 40, 60, 80, 100]
    step_perc = [0.1, 0.2, 0.4, 0.6, 0.8]
    time_range = 24*60
    results = {"time":{}}
    ctx_info = {
            TIME_CTX: {
                "range" : (0, 24*60),
                "interval" : 60,
            },
            "weatherDesc#CAT": {},
            WEEKDAY_CTX: {
                "range": (0, 6),
                "interval": 1,
            },
        }
    for p in step_perc:
        ts = p / 100. * time_range
        ctx_info[TIME_CTX]["interval"] = ts
        r = full_test(ContextAccessor(ctx_info))
        print(p, ts, r["TV"]["our"][-1])
        results["time"][p] = r["TV"]["our"][-1]
    return results


def context_step_exp():
    time_steps = [5,10,30,60,120,240]
    time_range = 24*60
    results = {"time":{}}
    ctx_info = {
            TIME_CTX: {
                "range" : (0, 24*60),
                "interval" : 60,
            },
            "weatherDesc#CAT": {},
            WEEKDAY_CTX: {
                "range": (0, 6),
                "interval": 1,
            },
        }
    for ts in time_steps:
        ctx_info[TIME_CTX]["interval"] = ts
        r = full_test(ContextAccessor(ctx_info))
        print(ts, r["TV"]["our"][-1])
        results["time"][ts] = r["TV"]["our"][-1]
    return results