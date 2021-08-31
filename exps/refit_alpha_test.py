import sys
sys.path.append("..")

import json
import os
import numpy as np
import math
from typing import Dict, List, Tuple
import copy
from itertools import combinations
from collections import Counter

import logging
from datetime import timedelta
from config import *
from utils import *
from main import *
from GtConflictFinder import GtConflictFinder
from ConflictDetector import ConflictDetector, ConflictPredicator


import plotly.graph_objects as go
from plotly.subplots import make_subplots


# config for refit dataset
# test_projects = [
#     # "House1",
#     "House3",
#     "House4",
#     "House8",
#     "House9",
#     "House15",
#     # "House18",
#     # "House20",
# ]
# capacity = {
#     "TV":1,
#     "WashingMachine":1,
#     "PC": 1,
# }

test_projects = [
    "HS3301",
    "HS3309",
    "HS5309",
]

capacity = {
    "thermostat": 0
}

BOOL_SIM = False
BOOL_UMASS= False

def test_acc_alpha(ctx_info, gt_ctx_info, root_folder, alpha_generator=None, device_mapping=None):
    # First find gt conflict
    device_events = {}
    for p in test_projects:
        ctx_evts, device_evts = load_processed(root_folder, p, is_sim=BOOL_SIM, is_umass=BOOL_UMASS)
        device_events[p] = device_evts

    gtconflict_cfg = {
        "context_info": gt_ctx_info,
        "capacity": capacity
    }
    test_dates = generate_test_date(root_folder, test_projects, test_ratio = 0.4, true_random=False, is_sim=BOOL_SIM, is_umass=BOOL_UMASS)
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
    MIN_TEST_OBS = 19
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

    final_alpha_result = {}
    # Then run prediction
    for ccp_alpha in alpha_generator:
        habit_groups = {}
        for p in test_projects:
            habit_groups[p], grid_data = test_umass(root_folder=root_folder,
                                                    test_project=p, 
                                                    ctx_info=ctx_info, 
                                                    ccp_alpha=ccp_alpha, 
                                                    test_dates=test_dates, 
                                                    is_sim=BOOL_SIM, 
                                                    is_umass=BOOL_UMASS,
                                                    d_mapping=device_mapping)
        
        c_detector = ConflictDetector(ctx_info, capacity)
        final_conflicts = c_detector.predict_conflict_scenarios(habit_groups)


        all_users = test_projects
        all_devices = capacity.keys()
        user_pairs = list(combinations(all_users, 2))
        conflict_predicator = ConflictPredicator(ctx_info, final_conflicts)
        exp_result = {
            d : {"conf": [0,0,0],
                "non_conf": [0,0]}
            for d in all_devices
        }
        all_state_cnt = 0
        d = "thermostat"
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
                    (frozenset(u_pair) in conflict_state_device[d][state]):

                    gt_prob =  float(conflict_state_device[d][state][frozenset(u_pair)]) / count
                gt_ctx_snapshot = gt_ctx_info.coor_to_snapshot(state)

                pred_prob = conflict_predicator.get_prob_conflict(ctx_info.get_coor_by_ctx(gt_ctx_snapshot), u_pair, d)
                if gt_prob > 0:
                    # if gt_prob > 0.5:
                    #     print(gt_ctx_info.coor_to_snapshot(state).values(), gt_prob, pred_prob, u_pair)
                    exp_result[d]["conf"][0] += abs(pred_prob - gt_prob)
                    exp_result[d]["conf"][1] += pred_prob - gt_prob
                    exp_result[d]["conf"][2] += 1

                else:
                    exp_result[d]["non_conf"][0] += abs(pred_prob - gt_prob)
                    exp_result[d]["non_conf"][1] += 1

        con_acc = exp_result[d]["conf"][0] / exp_result[d]["conf"][2]
        if exp_result[d]["non_conf"][1] != 0:
            non_acc = exp_result[d]["non_conf"][0] / exp_result[d]["non_conf"][1]
        else:
            non_acc = 0
        overall_acc = (exp_result[d]["conf"][0] +  exp_result[d]["non_conf"][0]) / \
                        (exp_result[d]["conf"][2] + exp_result[d]["non_conf"][1])
        final_alpha_result[ccp_alpha] = (con_acc, non_acc, overall_acc)
        print("Finish alpha {}, result {}".format(ccp_alpha, final_alpha_result[ccp_alpha]))
    return final_alpha_result
    # for d in exp_result:
    #     # exp_result[d].append((exp_result[d][0] + exp_result[d][2]) / (exp_result[d][1] + exp_result[d][3]))
    #     if exp_result[d][1] > 0:
    #         exp_result[d][0] = exp_result[d][0] / exp_result[d][1]
    #         exp_result[d][4] = exp_result[d][4] / exp_result[d][1]
    #     if exp_result[d][3] > 0:
    #         exp_result[d][2] = exp_result[d][2] / exp_result[d][3]

        