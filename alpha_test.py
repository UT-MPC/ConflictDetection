import json
import os
import numpy as np
import math
from typing import Dict, List, Tuple
import copy

from datetime import timedelta
from config import *
from utils import *
from main import *
from GtConflictFinder import GtConflictFinder
from ConflictDetector import ConflictDetector

import plotly.graph_objects as go
from plotly.subplots import make_subplots

test_projects = [
    "HomeA/2016",
    "HomeB/2016",
    "HomeC/2016",
    "HomeD/2016",
    "HomeF/2016",
    "HomeG/2016",
]

capacity = {
    "Range" : 2,
    "Microwave": 1,
    "LivingLights": 0,
    "HomeOffice": 1,
    "WashingMachine": 1,
}

def compute_auc(xs, ys):
    # xs must be monotonical
    auc = 0
    for i, x in enumerate(xs):
        if i == len(xs) - 1:
            break
        auc += (ys[i] + ys[i+1]) * abs(xs[i+1] - x) / 2 
    return auc

def compute_box_area(boxes):
    return sum([compute_area(box) for box in boxes])

def test_auc(alpha=20e-6, ctx_info = None):
    habit_groups = {}
    for p in test_projects:
        habit_groups[p], _ = test_umass(test_project=p, ctx_info=ctx_info,train_ratio=0.7, ccp_alpha=alpha)

    c_detector = ConflictDetector(ctx_info, capacity)
    final_conflicts = c_detector.predict_conflict_scenarios(habit_groups)
    # print({x:len(final_conflicts[x]) for x in final_conflicts})

    # probs = [(x["box"],x["prob"]) for x in final_conflicts["Microwave"]]
    # probs_i = [(x["prob"], i) for i, x in enumerate(final_conflicts["Microwave"])]
    # print(sorted(probs_i))

    # Make ground truth:
    device_events = {}
    for p in test_projects:
        ctx_evts, device_evts = load_processed(p)
        device_events[p] = device_evts

    gtconflict_cfg = {
        "context_info": ctx_info,
        "capacity": capacity
    }

    conflict_finder = GtConflictFinder(gtconflict_cfg)
    conflicts = conflict_finder.get_Gt_conflict(ctx_evts, device_events)

    import plotly.express as px

    conflict_time = [x['cur_time'] for x in conflicts]
    end_time = max(conflict_time)
    start_time = min(conflict_time)
    total_time_range = end_time - start_time
    test_start = end_time - total_time_range * TEST_RATIO

    conflict_device = {
        d:[]
        for d in capacity
    }
    for c in conflicts:
        if c["cur_time"] > test_start:
            conflict_device[c["device"]].append(c)
    # print({d:len(c) for d,c in conflict_device.items()})


    missed_gt_conflicts = {d:[] for d in conflict_device}
    hit_gt_conflicts = {d:{} for d in conflict_device}
    for d in final_conflicts:
        hit_gt_conflicts[d] = {i:0 for i in range(len(final_conflicts[d]))}
    for d, conflicts in conflict_device.items():
        for c in conflicts:
            coor = ctx_info.get_coor_by_ctx(c["ctx"])
            flag = False
            for idx,c_predict in enumerate(final_conflicts[d]):
                if does_contain_point(c_predict["box"], coor):
                    flag = True
                    hit_gt_conflicts[d][idx] += 1
                    break
            if not flag:
                missed_gt_conflicts[d].append(c)
    # print({d:len(missed_gt_conflicts[d]) for d in missed_gt_conflicts})
    hit_count = {d:[0,0] for d in hit_gt_conflicts}
    for d,hit_c in hit_gt_conflicts.items():
        for i,h in hit_c.items():
            if h == 0:
                hit_count[d][0] += 1
            else:
                hit_count[d][1] += 1
    # print(hit_gt_conflicts["Microwave"])
    # print(final_conflicts["Microwave"][14])
    # print(hit_count)

    hit_miss_rate = [[],[]]
    step_size = 0.001
    all_space_area = ctx_info.get_space_area()
    for prob_threshold in np.arange(0.0, 1.0, 0.001):
        test_conflict = {
            d: [x for x in final_conflicts[d] if x["prob"] > prob_threshold]
            for d in final_conflicts
        }

        missed_gt_conflicts = {d:[] for d in conflict_device}
        hit_gt_conflicts = {d:{} for d in conflict_device}
        for d in test_conflict:
            hit_gt_conflicts[d] = {i:0 for i in range(len(test_conflict[d]))}
        for d, conflicts in conflict_device.items():
            for c in conflicts:
                coor = ctx_info.get_coor_by_ctx(c["ctx"])
                flag = False
                for idx,c_predict in enumerate(test_conflict[d]):
                    if does_contain_point(c_predict["box"], coor):
                        flag = True
                        hit_gt_conflicts[d][idx] += 1
                        break
                if not flag:
                    missed_gt_conflicts[d].append(c)
        all_missed_gt_conflicts = sum([len(x) for d,x in missed_gt_conflicts.items()])
        all_gt_conflicts = sum([len(x) for d,x in conflict_device.items()])

        hit_miss_rate[0].append(1.0 - float(all_missed_gt_conflicts) / all_gt_conflicts)
        # print({d:len(missed_gt_conflicts[d]) for d in missed_gt_conflicts})

        # all_pred_conflicts = sum([len(test_conflict[d]) for d in test_conflict])
        # if  all_pred_conflicts == 0:
        #     break
        # all_missed_pred_conflicts = 0
        # hit_count = {d:[0,0] for d in hit_gt_conflicts}
        # for d,hit_c in hit_gt_conflicts.items():
        #     for i,h in hit_c.items():
        #         if h == 0:
        #             all_missed_pred_conflicts += 1
        #             hit_count[d][0] += 1
        #         else:
        #             hit_count[d][1] += 1
        # hit_miss_rate[1].append(1.0 - float(all_missed_pred_conflicts) / all_pred_conflicts)
        # print(hit_count)
        conflict_area = 0.
        for d in test_conflict:
            conflict_area += compute_box_area([c["box"] for c in test_conflict[d]])
        hit_miss_rate[1].append(1-conflict_area / len(test_conflict) / all_space_area)
 

    # print(hit_miss_rate)
    auc = compute_auc(hit_miss_rate[0], hit_miss_rate[1])
    return auc, hit_miss_rate


logging.basicConfig(level=logging.INFO)

# print(test_auc())