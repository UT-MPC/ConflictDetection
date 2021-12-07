from datetime import datetime
from datetime import timedelta
import numpy as np
import math
from typing import Dict, List, Tuple
from sklearn.tree import DecisionTreeRegressor
import copy
from collections import Counter
from rtree import index

from config import *
from utils import *

def build_habit_groups(deivce_patterns: List, alpha=DEFAULT_ALPHA) -> Dict[str, List]:
    habit_group = {}
    for device, data in deivce_patterns.items():
        if len(data) == 0:
            continue
        reg_x = []
        reg_y = []
        weight = []
        for dis in data:
            # Weigh the samples based on the number of occurance in this unit
            mode = GRID_MODE.get(device, GRID_MODE["default"])
            # create sample
            distribution = dis["distribution"]
            cnt = sum(distribution[0:-2])
            weight.append(cnt)
            reg_x.append(dis["coor"])
            y = [
                x / cnt
                for x in distribution[1:-2]
            ]
            y.extend(distribution[-2:])
            reg_y.append(y)
            # if mode == "All":
            #     cnt = sum(dis["distribution"])
            #     weight.append(cnt)
            #     reg_x.append(dis["coor"])
            #     # The data that we want to learn by Decision Tree is the prob. distribution of the states
            #     reg_y.append([
            #         x / cnt
            #         for x in dis["distribution"][1:]
            #     ])
            # else:
            #     distribution = dis["distribution"]
            #     cnt = distribution[0:-2]
            #     weight.append(cnt)
            #     reg_x.append(dis["coor"])
            #     y = [
            #         x / cnt
            #         for x in dis["distribution"][1:]
            #     ]
            #     reg_y.append([
            #         distribution[-2], distribution[-1]
            #     ])
        # TODO: we need to find a better value for ccp_alpha
        regressor = DecisionTreeRegressor(ccp_alpha=alpha)

        # Train the Decision Tree Regressor model
        regressor.fit(reg_x, reg_y, sample_weight = weight)

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
        
        # Crazy test
        # boxes = []
        # for i, x in enumerate(reg_x):
        #     b = {
        #         "box": bounding_box([x]),
        #         "dis": reg_y[i]
        #     }
        #     boxes.append(b)
        # These habit boxes are the mined habit pattern for each users
        habit_group[device] = boxes
    return habit_group

class GridPatternBuilder():

    # The default step size to sample the event sequence
    default_time_delta = timedelta(minutes=60)

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
        for d, evts in device_evts.items():
            val_range = device_nonfunctional_range.get(d, [0,1])
            mode = GRID_MODE.get(d, GRID_MODE["default"])
            if mode == "All":
                continue
            for e in evts:
                if e[0] == DEVICE_SKIP_STATE:
                    continue
                e[2] = normalize(e[2], val_range[0], val_range[1])
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

    def process_snapshot(self, space_mat, cur_time, ctx_snapshot, d_state, device, d_val_rec):
        cell_idx = self.ctx_accessor.get_coor_by_ctx(ctx_snapshot)
        mode = GRID_MODE.get(device, GRID_MODE["default"])
        if mode == "All":
            d_coor = self.device_state_mapping[device][get_d_state_str(d_state)]
        else:
            d_coor = self.device_state_mapping[device][d_state[0]]
            if cell_idx not in d_val_rec:
                d_val_rec[cell_idx] = []
            d_val_rec[cell_idx].append(d_state[2])   
        space_mat[cell_idx][d_coor] += 1

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

            d_state = d_evts[0]
            tmp = list(self.ctx_accessor.get_ctx_space_shape())
            tmp.append(int(len(self.device_state_mapping[d])/2))
            space_mat= np.zeros(tmp)
            device_val_rec = {}
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
                    if d_state[0] != DEVICE_SKIP_STATE:
                        cell = self.process_snapshot(space_mat, 
                                                    cur_time, 
                                                    ctx_snapshot, 
                                                    d_state, 
                                                    d, 
                                                    device_val_rec)  
                        if cell:
                            cell_to_process.append(cell)
                
                # Proceed to the next timestamp
                if d_evts[cur_evt_idx + 1][1] <= cur_time + self.time_delta():
                    cur_time = d_evts[cur_evt_idx + 1][1]
                    cur_evt_idx += 1
                    d_state = d_evts[cur_evt_idx]
                else:
                    cur_time += self.time_delta()
            for cell in cell_to_process:
                mode = GRID_MODE.get(d, GRID_MODE["default"])
                if mode == "All":
                    dis = list(space_mat[cell])
                    dis.append(0)
                    dis.append(0)
                    device_patterns[d].append(
                        {"coor": cell,
                        "distribution": dis}
                    )
                else:
                    var = np.var(device_val_rec[cell])
                    mean = sum(device_val_rec[cell]) / len(device_val_rec[cell])
                    dis = list(space_mat[cell])
                    dis.append(mean)
                    dis.append(var)
                    device_patterns[d].append(
                        {"coor": cell,
                        "distribution": dis}
                    )
        return device_patterns


    def build_device_pattern_range(self, ctx_evts:Dict, device_evts:Dict):
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

            d_state = d_evts[0]
            # p = index.Property()
            # p.dimension = len(self.ctx_accessor.get_all_ctx_ordered())
            # r_tree = index.Index(properties=p)
            state_set = {}
            total_points = 0
            d_mode = GRID_MODE.get(d, GRID_MODE["default"])

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
                    if d_state[0] != DEVICE_SKIP_STATE:
                        coor_f = self.ctx_accessor.get_coor_float(ctx_snapshot)
                        coor_i = self.ctx_accessor.get_coor_by_ctx(ctx_snapshot)
                        if coor_i not in state_set:
                            state_set[coor_i] = []

                        if d_mode == "All":
                            d_coor = self.device_state_mapping[d][get_d_state_str(d_state)]
                            d_val = 0
                        else:
                            d_coor = self.device_state_mapping[d][d_state[0]]
                            d_val = d_state[2]
                        
                        state_set[coor_i].append([coor_f, d_coor, d_val])
                        total_points += 1
                        # r_tree.insert(id=total_points, coordinates=coor*2, obj=d_state)
                
                # Proceed to the next timestamp
                if d_evts[cur_evt_idx + 1][1] <= cur_time + self.time_delta():
                    cur_time = d_evts[cur_evt_idx + 1][1]
                    cur_evt_idx += 1
                    d_state = d_evts[cur_evt_idx]
                else:
                    cur_time += self.time_delta()

            neighbors = []
            tot_slots = 0
            for coor_i, close_set in state_set.items():
                coor_pool = get_coor_neighbor(coor_i, set(self.ctx_accessor.get_cate_ctx_idx()))
                flag = False
                for p_i in close_set:
                    d_cnt= np.zeros(int(len(self.device_state_mapping[d])/2))
                    d_vals = []
                    num_neighbors = 0
                    for coor_j in coor_pool:
                        for p_j in state_set.get(coor_j, []):
                            if euclidean_dist(p_i[0], p_j[0]) < 1:
                                num_neighbors += 1 
                                d_cnt[p_j[1]] += 1
                                d_vals.append(p_j[2])
                    if num_neighbors > 20:
                        flag = True
                        if d_mode == "All":
                            device_patterns[d].append(
                                {"coor": p_i[0],
                                "distribution": d_cnt}
                            )
                        else:
                            var = np.var(d_vals)
                            mean = sum(d_vals) / len(d_vals)
                            dis = list(d_cnt)
                            dis.append(mean)
                            dis.append(var)
                            device_patterns[d].append(
                                {"coor": p_i[0],
                                "distribution": dis}
                            )
                    # d_cnt[p_i[1]] += 1
                    # device_patterns[d].append(
                    #     {"coor": p_i[0],
                    #     "distribution": d_cnt}
                    # )
                if flag:
                    tot_slots += 1
        # print(total_points)
        # print(tot_slots)
        return device_patterns

    def mine_patterns(self, ctx_evts: Dict, device_evts: Dict):
        self.preprocess(ctx_evts, device_evts)
        device_patterns = self.build_device_pattern_mat(ctx_evts, device_evts)
        # print("Mined pattern" + str({x: len(device_patterns[x]) for x in device_patterns}))
        # Move pattern mining to a separate function to have better efficiency when doing experiments
        # habit_groups =  build_habit_groups(device_patterns, self.cfg.get("alpha", DEFAULT_ALPHA))

        return device_patterns