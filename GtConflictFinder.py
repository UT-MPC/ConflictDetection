import copy
from datetime import datetime
from datetime import timedelta
import numpy as np
import math
from typing import Dict, List, Tuple
from sklearn.tree import DecisionTreeRegressor

from config import *
from utils import *
from itertools import combinations

class GtConflictFinder():
    # Find GroundTruth conflicts from the original data sequence

    # The default step size to sample the event sequence
    default_time_delta = timedelta(minutes=DEFAULT_TIME_INTERVAL_MIN)

    # To avoid runtime error, we have a default context interval of 1
    default_ctx_interval = 1

    def __init__(self, cfg:Dict):
        super().__init__()
        self.cfg = cfg
        self.ctx_accessor = self.cfg["context_info"]
        self.capacity = self.cfg["capacity"]
        self.conflicts = []

    def time_delta(self):
        return self.cfg.get("time_delta", self.default_time_delta)
    

    def find_conflict(self, ctx_snapshot, device_states, capacity, cur_time, device):
        # Check device_state_conflict
        unique_state = set()
        count = 0
        for u, s in device_states.items():
            if s == "off":
                continue
            count += 1
            unique_state.add(s)
        if len(unique_state) > 1:
            # Found at least two users with different states
            self.conflicts.append({
                "type": "state_diff",
                "device_states": copy.deepcopy(device_states),
                "ctx": copy.deepcopy(ctx_snapshot),
                "cur_time": cur_time,
                "device": device,
            })
            return
        
        # Check capacity conflict
        if count > capacity and capacity > 0:
            # Found at least two users with different states
            self.conflicts.append({
                "type": "capacity",
                "device_states": copy.deepcopy(device_states),
                "ctx": copy.deepcopy(ctx_snapshot),
                "cur_time": cur_time,
                "device": device,
            })

    def find_conflict_pairwise(self, ctx_snapshot, device_states, capacity, cur_time, device):
        # Check device_state_conflict
        com = combinations(device_states.keys(), 2)

        for c in com:
            if device_states[c[1]] == "off" or device_states[c[0]] == "off":
                continue

            if device_states[c[1]] == DEVICE_SKIP_STATE or device_states[c[0]] == DEVICE_SKIP_STATE:
                continue
            if device_states[c[0]] != device_states[c[1]]:
                self.conflicts.append({
                    "type": "state_diff",
                    "device_states": {c[0]:device_states[c[0]], c[1]:device_states[c[1]]},
                    "ctx": copy.deepcopy(ctx_snapshot),
                    "cur_time": cur_time,
                    "device": device,
                })
            elif capacity == 1:
                # Unshareable devices
                self.conflicts.append({
                    "type": "capacity",
                    "device_states": {c[0]:device_states[c[0]], c[1]:device_states[c[1]]},
                    "ctx": copy.deepcopy(ctx_snapshot),
                    "cur_time": cur_time,
                    "device": device,
                })

    def get_Gt_conflict(self, ctx_evts: Dict, 
                        device_evts: Dict, test_dates=set()):
        for d, cap in self.capacity.items():
            device_states = {}
            cur_time = datetime.min
            end_time = datetime.min
            c_evt_idx = {c: 0 for c in ctx_evts}
            ctx_snapshot = {
                c: ctx_evts.get(c, [[0]])[0][0]
                for c in self.ctx_accessor.get_all_ctx_ordered()
            }

            d_evt_idx_per_u = {}
            for u, d_evts in device_evts.items():
                if d in d_evts:
                    d_evt_idx_per_u[u] = 0
                    device_states[u] = d_evts[d][0][0]
                    cur_time = max(d_evts[d][0][1], cur_time)
                    end_time = max(d_evts[d][-1][1], end_time)
            for u in d_evt_idx_per_u:
                evt_lst = device_evts[u][d]
                while evt_lst[d_evt_idx_per_u[u] + 1][1] <= cur_time:
                    device_states[u] = evt_lst[d_evt_idx_per_u[u] + 1][0]
                    d_evt_idx_per_u[u] += 1

            state_cnt = np.zeros(list(self.ctx_accessor.get_ctx_space_shape()))

            while cur_time < end_time:
                if cur_time.date() in test_dates:
                    for c, c_evts in ctx_evts.items():
                        if not self.ctx_accessor.have_ctx(c):
                            continue
                        while c_evt_idx[c] < len(c_evts) and c_evts[c_evt_idx[c]][1] <= cur_time:
                            ctx_snapshot[c] = c_evts[c_evt_idx[c]][0]
                            c_evt_idx[c] += 1
                    self.ctx_accessor.update_time_ctx(ctx_snapshot, cur_time)

                    coor = self.ctx_accessor.get_coor_by_ctx(ctx_snapshot)
                    state_cnt[coor] += 1
                    self.find_conflict_pairwise(ctx_snapshot, device_states, cap, cur_time, d)
                # Find the next device state change event
                min_evt_t = datetime.max
                min_evt_u = []
                for u in d_evt_idx_per_u:
                    evt_lst = device_evts[u][d]
                    if d_evt_idx_per_u[u] + 1 < len(evt_lst):
                        if evt_lst[d_evt_idx_per_u[u] + 1][1] < min_evt_t:
                            min_evt_t = evt_lst[d_evt_idx_per_u[u] + 1][1]
                            min_evt_u = [u]
                        elif evt_lst[d_evt_idx_per_u[u] + 1][1] == min_evt_t:
                            min_evt_u.append(u)

                if min_evt_u == 0:
                    break
                else:
                    if min_evt_t <= cur_time + self.time_delta():
                        cur_time = min_evt_t
                        for u in min_evt_u:
                            d_evt_idx_per_u[u] += 1
                            device_states[u] = device_evts[u][d][d_evt_idx_per_u[u]][0]
                    else:
                        cur_time += self.time_delta()
        return self.conflicts, state_cnt


 

