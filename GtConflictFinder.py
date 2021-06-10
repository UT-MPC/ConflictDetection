from datetime import datetime
from datetime import timedelta
import numpy as np
import math
from typing import Dict, List, Tuple
from sklearn.tree import DecisionTreeRegressor

from config import *
from utils import *

class GtConflictFinder():
    # Find GroundTruth conflicts from the original data sequence

    # The default step size to sample the event sequence
    default_time_delta = timedelta(minutes=10)

    # To avoid runtime error, we have a default context interval of 1
    default_ctx_interval = 1

    def __init__(self, cfg:Dict):
        super().__init__()
        self.cfg = cfg
        self.ctx_accessor = self.cfg["context_info"]
        self.capacity = self.cfg["capacity"]
        self.conflicts = []
    

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
                "ctx": ctx_snapshot,
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
                "ctx": ctx_snapshot,
                "cur_time": cur_time,
                "device": device,
            })


    def get_Gt_conflict(self, ctx_evts: Dict, device_evts: Dict):
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
            while cur_time < end_time:
                for c, c_evts in ctx_evts.items():
                    if not self.ctx_accessor.have_ctx(c):
                        continue
                    while c_evt_idx[c] < len(c_evts) and c_evts[c_evt_idx[c]][1] <= cur_time:
                        ctx_snapshot[c] = c_evts[c_evt_idx[c]][0]
                        c_evt_idx[c] += 1
                self.ctx_accessor.update_time_ctx(ctx_snapshot, cur_time)

                self.find_conflict(ctx_snapshot, device_states, cap, cur_time, d)
                # Find the next device state change event
                min_evt_t = datetime.max
                min_evt_u = 0
                for u in d_evt_idx_per_u:
                    evt_lst = device_evts[u][d]
                    if d_evt_idx_per_u[u] + 1 < len(evt_lst) and evt_lst[d_evt_idx_per_u[u] + 1][1] < min_evt_t:
                        min_evt_t = evt_lst[d_evt_idx_per_u[u] + 1][1]
                        min_evt_u = u
                if min_evt_u == 0:
                    break
                else:
                    cur_time = min_evt_t
                    d_evt_idx_per_u[min_evt_u] += 1
                    device_states[min_evt_u] = device_evts[min_evt_u][d][d_evt_idx_per_u[min_evt_u]][0]
        return self.conflicts


 

