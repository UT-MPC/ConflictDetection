import sys
sys.path.append("..")

import json
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
from GridPatternBuilder import build_habit_groups

root_folder = os.path.join(DATA_ROOT, THERMO_ROOT)

test_projects = [
    "HS3301",
    "HS3309",
    "HS5309",
]

setpoint_mapping = {
    "thermostat": thermo_state
}
time_step = 1
ctx_info = ContextAccessor({
        TIME_CTX: {
            "range" : (0, 24*60),
            "interval" : 60,
        },
        "OutTemp#NUM": {
            "range": (-25, 35),
            "interval": 5,
        },
        THERMO_MODE_CTX: {},
        # WEEKDAY_CTX: {
        #     "range": (0, 6),
        #     "interval": 1,
        # },
})
gt_ctx_info = ContextAccessor({
        TIME_CTX: {
            "range" : (0, 24*60),
            "interval" : 60,
        },
        "OutTemp#NUM": {
            "range": (-25, 35),
            "interval": 5,
        },
        THERMO_MODE_CTX: {},
        # WEEKDAY_CTX: {
        #     "range": (0, 6),
        #     "interval": 1,
        # },
})

ccp_alpha = 5e-5  # Prob.
capacity = {
    "thermostat":0
}
BOOL_SIM = False
BOOL_UMASS= False

def full_test():
    test_dates = generate_test_date(root_folder, test_projects, test_ratio = 0.4, true_random=False, is_sim=BOOL_SIM, is_umass=BOOL_UMASS)
    grid_pattern_cfg = {
        # "time_delta" : timedelta(minutes=10),
        "context_info" : ctx_info,
        "alpha": ccp_alpha,
        "test_dates": test_dates,
        "device_state_map": setpoint_mapping,
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
        habit_groups[p] = build_habit_groups(grid_data[p], ccp_alpha)
    c_detector = ConflictDetector(ctx_info, capacity)
    final_conflicts = c_detector.predict_conflict_scenarios(habit_groups)
    # print("Final predicted conflicts" + str({x:len(final_conflicts[x]) for x in final_conflicts}))


    #Compute groundtruth

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

    all_users = test_projects
    all_devices = capacity.keys()
    user_pairs = list(combinations(all_users, 2))
    conflict_predicator = ConflictPredicator(ctx_info, final_conflicts)
    exp_cnt = 0
    exp_gt_c = 0
    exp_result = {
        d: {
            frozenset(u_pair): [0,0,0,0,0] 
            for u_pair in user_pairs
        }
        for d in all_devices}
    max_p = 0
    all_state_cnt = 0
    gt_probs = []
    o_static = [[0,0], [0,0]]
    for d in all_devices:
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

                    gt_prob =  float(conflict_state_device[d][state][frozenset(u_pair)]) / count
                gt_ctx_snapshot = gt_ctx_info.coor_to_snapshot(state)

                pred_prob = conflict_predicator.get_prob_conflict(ctx_info.get_coor_by_ctx(gt_ctx_snapshot), u_pair, d)
                exp_cnt += 1
                gt_probs.append(gt_prob)
                if gt_prob > 0:
                    # if gt_prob > 0.5:
                    #     print(gt_ctx_info.coor_to_snapshot(state).values(), gt_prob, pred_prob, u_pair)
                    exp_gt_c += 1
                    exp_result[d][u_pair_set][0] += abs(pred_prob - gt_prob)
                    exp_result[d][u_pair_set][1] += 1
                    exp_result[d][u_pair_set][4] += gt_prob
                    if gt_prob > 1:
                        print(gt_prob, pred_prob, d, u_pair)
                    # if abs(gt_prob - pred_prob) > 0.2:
                    # print(pred_prob, gt_prob, gt_ctx_snapshot, count, u_pair)
                    max_p = max(gt_prob, max_p)

                else:
                    exp_result[d][u_pair_set][2] += pred_prob - gt_prob
                    exp_result[d][u_pair_set][3] += 1
                    # print(pred_prob, gt_prob, gt_ctx_snapshot, count, u_pair)
            avg_gt = sum(gt_probs) / len(gt_probs)
            errors = [abs(x-avg_gt) for x in gt_probs]
            for i, e in enumerate(errors):
                if gt_probs[i] > 0.:
                    o_static[0][0] += e
                    o_static[0][1] += 1
                else:
                    o_static[1][0] += e
                    o_static[1][1] += 1
            avg_error = str(sum(errors) / len(errors))
            gt_probs = []
            print("Optimal single prediction for users: {} is : {}".format(u_pair, str(sum(errors) / len(errors))))


    o_acc = [[0., 0.], [0., 0.]]
    o_zero = 0.
    for d, result in exp_result.items():
        for u_pair in user_pairs:
            u_pair_set = frozenset(u_pair)
            r= result[u_pair_set]

            o_acc[0][0] += r[0]   #total conflict
            o_acc[1][0] += r[2]   #total non-conflict
            o_acc[0][1] += r[1]   #total conflict no.
            o_acc[1][1] += r[3]   #total non-conflict no.
            o_zero += r[4]     #total zero prediction

            # if r[1] > 0:
            #     r.append((r[0] + r[2]) / (r[1] + r[3]))
            # if r[1] > 0:
            #     r[0] = r[0] / r[1]
            #     r[4] = r[4] / r[1]
            # if r[3] > 0:
            #     r[2] = r[2] / r[3]
            # print(u_pair, r[0], r[2])
        
    print("The no. conf {}, no. non-conf {}".format(o_acc[0][1], o_acc[1][1]))
    print("The overall accuracy for conf is {}".format(o_acc[0][0] / o_acc[0][1]))
    print("The overall accuracy for non-conf is {}".format(o_acc[1][0] / o_acc[1][1]))
    print("The overall acc is {}".format((o_acc[0][0] + o_acc[1][0])/(o_acc[0][1] + o_acc[1][1])))
    
    print("The overall zero for conf is {}".format(o_zero / o_acc[0][1]))
    print("The overall zero for all is {}".format(o_zero / (o_acc[0][1] + o_acc[1][1])))

    print("The no. conf {}, no. non-conf {}".format(o_static[0][1], o_static[1][1]))
    print("Baseline, optimal single prediction for conf is {}".format(o_static[0][0] / o_static[0][1]))
    print("Baseline, optimal single prediction for non-conf is {}".format(o_static[1][0] / o_static[1][1]))
    print("The overall baseline is {}".format((o_static[0][0] + o_static[1][0])/(o_static[0][1] + o_static[1][1])))

        # print("Baseline approach, optimal single prediction: " + str(sum(errors) / len(errors)))


    # print("Baseline approach, optimal single prediction: " + str(sum(errors) / len(errors)))