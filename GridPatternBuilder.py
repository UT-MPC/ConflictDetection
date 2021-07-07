from datetime import datetime
from datetime import timedelta
import numpy as np
import math
from typing import Dict, List, Tuple
from sklearn.tree import DecisionTreeRegressor

from config import *
from utils import *

class GridPatternBuilder():

    # The default step size to sample the event sequence
    default_time_delta = timedelta(minutes=DEFAULT_TIME_INTERVAL_MIN)

    # To avoid runtime error, we have a default context interval of 1
    default_ctx_interval = 1

    def __init__(self, cfg:Dict):
        super().__init__()
        self.cfg = cfg
        self.ctx_accessor = self.cfg["context_info"]
        self.pattern_space = None
        self.pattern_sparse = []
        self.unit_indices = []
        self.device_state_mapping = self.cfg.get("device_state_map", device_state_map)
        self.test_dates = self.cfg["test_dates"]

    def time_delta(self)-> timedelta:
        return self.cfg.get("time_delta", self.default_time_delta)

    def preprocess(self, ctx_evts: Dict, device_evts:Dict):
        pass

        # Change device state string to a number and create a map to record it. 
        # self.device_state_mapping = {
        #     d : {}
        #     for d in device_evts
        # }
        # for d, d_evts in device_evts.items():
        #     act = set([x[0] for x in d_evts])
        #     if "off" in act:
        #         act.remove("off")
        #         states = ["off"]
        #     else:
        #         states = []
        #     states.extend(list(act))
        #     for i, s in enumerate(states):
        #         # Create a bidirectional mapping of the index of the state and the string of the state
        #         self.device_state_mapping[d][s] = i
        #         self.device_state_mapping[d][i] = s

    def process_snapshot(self, space_mat, cur_time, ctx_snapshot, d_state : int):
        cell_idx = self.ctx_accessor.get_coor_by_ctx(ctx_snapshot)
        space_mat[cell_idx][d_state] += 1

        # If this cell has enough observations, we want to add it to the watch list
        if sum(space_mat[cell_idx]) == self.cfg.get("min_obs", MIN_OBS_GRID):
            return cell_idx
        return None

    def verify_train(self, cur_time):
        return not (cur_time.date() in self.test_dates)

    def build_device_pattern_mat(self, ctx_evts:Dict, device_evts:Dict):
        device_patterns = {
            d : []
            for d in device_evts
        }
        for d, d_evts in device_evts.items():
            cur_time = d_evts[0][1]
            end_time = d_evts[-1][1]
            c_evt_idx = {c: 0 for c in ctx_evts}
            ctx_snapshot = {
                c: ctx_evts.get(c, [[0]])[0][0]
                for c in self.ctx_accessor.get_all_ctx_ordered()
            }
            cur_evt_idx = 0
            d_state = d_evts[0][0]
            tmp = list(self.ctx_accessor.get_ctx_space_shape())
            tmp.append(int(len(self.device_state_mapping[d])/2))
            space_mat= np.zeros(tmp)
            cell_to_process = []
            while cur_time < end_time:
                if self.verify_train(cur_time):
                    # We randomly select some dates as test dates that we need to exclude 
                    # from the training process
                    for c, c_evts in ctx_evts.items():
                        if not self.ctx_accessor.have_ctx(c):
                            continue
                        while c_evt_idx[c] < len(c_evts) and c_evts[c_evt_idx[c]][1] <= cur_time:
                            ctx_snapshot[c] = c_evts[c_evt_idx[c]][0]
                            c_evt_idx[c] += 1
                    # Add additional contextes
                    self.ctx_accessor.update_time_ctx(ctx_snapshot, cur_time)
                    cell = self.process_snapshot(space_mat, 
                                cur_time, ctx_snapshot, 
                                self.device_state_mapping[d][d_state])  
                    if cell:
                        cell_to_process.append(cell)
                
                # Proceed to the next timestamp
                if d_evts[cur_evt_idx + 1][1] <= cur_time + self.time_delta():
                    cur_time = d_evts[cur_evt_idx + 1][1]
                    cur_evt_idx += 1
                    d_state = d_evts[cur_evt_idx][0]
                else:
                    cur_time += self.time_delta()
            for cell in cell_to_process:
                device_patterns[d].append(
                    {"coor": cell,
                     "distribution": space_mat[cell]}
                )
        return device_patterns

    def build_habit_groups(self, deivce_patterns: List) -> Dict[str, List]:
        habit_group = {}
        for device, data in deivce_patterns.items():
            reg_x = []
            reg_y = []
            weight = []
            for dis in data:
                # Weigh the samples based on the number of occurance in this unit
                cnt = sum(dis["distribution"])
                weight.append(cnt)
                reg_x.append(dis["coor"])
                # The data that we want to learn by Decision Tree is the prob. distribution of the states
                reg_y.append([
                    x / cnt
                    for x in dis["distribution"][1:]
                ])

            # TODO: we need to find a better value for ccp_alpha
            regressor = DecisionTreeRegressor(ccp_alpha=self.cfg.get("alpha",DEFAULT_ALPHA))

            # Train the Decision Tree Regressor model
            regressor.fit(reg_x, reg_y, sample_weight=weight)

            # Find the No. of leaf for each input
            leaves = regressor.apply(reg_x)

            groups = {}
            boxes = []

            # Group the input points based on the trained tree model
            for i,l in enumerate(leaves):
                if l not in groups:
                    groups[l] = {"coors": [reg_x[i]], "tot_dis": np.array(reg_y[i]), "cnt": 1}
                else:
                    groups[l]["coors"].append(reg_x[i])
                    groups[l]["tot_dis"] += reg_y[i]
                    groups[l]["cnt"] += 1
            
            # Compute the bounding box of the found groups of points with its prob. distribution
            for g, points in groups.items():
                boxes.append({})
                boxes[-1]["box"] = bounding_box(points["coors"])
                boxes[-1]["dis"] = points["tot_dis"] / points["cnt"] 
            
            # These habit boxes are the mined habit pattern for each users
            habit_group[device] = boxes
        return habit_group


    def mine_patterns(self, ctx_evts: Dict, device_evts: Dict):
        self.preprocess(ctx_evts, device_evts)
        device_patterns = self.build_device_pattern_mat(ctx_evts, device_evts)
        habit_groups =  self.build_habit_groups(device_patterns)

        return habit_groups, device_patterns

