from datetime import datetime
from datetime import timedelta
import numpy as np
import math
from typing import Dict, List, Tuple

from config import *
from utils import *

class GridPatternBuilder():

    # The default step size to sample the event sequence
    default_time_delta = timedelta(minutes=10)

    # To avoid runtime error, we have a default context interval of 1
    default_ctx_interval = 1

    def __init__(self, cfg:Dict):
        super().__init__()
        self.cfg = cfg
        self.ctx_accessor = self.cfg["context_info"]
        self.pattern_space = None
        self.pattern_sparse = []
        self.unit_indices = []

    def time_delta(self)-> timedelta:
        return self.cfg.get("time_delta", self.default_time_delta)

    def preprocess(self, ctx_evts: Dict, device_evts:Dict):
        # Change device state string to a number and create a map to record it. 
        self.device_state_mapping = {
            d : {}
            for d in device_evts
        }
        for d, d_evts in device_evts.items():
            act = set([x[0] for x in d_evts])
            if "off" in act:
                act.remove("off")
                states = ["off"]
            else:
                states = []
            states.extend(list(act))
            for i, s in enumerate(states):
                # Create a bidirectional mapping of the index of the state and the string of the state
                self.device_state_mapping[d][s] = i
                self.device_state_mapping[d][i] = s

    def process_snapshot(self, space_mat, cur_time, ctx_snapshot, d_state : int):
        cell_idx = self.ctx_accessor.get_coor_by_ctx(ctx_snapshot)
        space_mat[cell_idx][d_state] += 1

        # If this cell has enough observations, we want to add it to the watch list
        if sum(space_mat[cell_idx]) == self.cfg.get("min_obs", 10):
            return cell_idx
        return None

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
                for c, c_evts in ctx_evts.items():
                    if not self.ctx_accessor.have_ctx(c):
                        continue
                    while c_evt_idx[c] < len(c_evts) and c_evts[c_evt_idx[c]][1] <= cur_time:
                        ctx_snapshot[c] = c_evts[c_evt_idx[c]][0]
                        c_evt_idx[c] += 1
                # Add additional contextes
                if self.ctx_accessor.have_ctx(TIME_CTX):
                    ctx_snapshot[TIME_CTX] = datetime_to_mins(cur_time)
                if self.ctx_accessor.have_ctx(WEEKDAY_CTX):
                    ctx_snapshot[WEEKDAY_CTX] = cur_time.date().weekday()  
                cell = self.process_snapshot(space_mat, 
                            cur_time, ctx_snapshot, 
                            self.device_state_mapping[d][d_state])  
                if cell:
                    cell_to_process.append(cell)

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

    def mine_patterns(self, ctx_evts: Dict, device_evts: Dict):
        self.preprocess(ctx_evts, device_evts)
        device_patterns = self.build_device_pattern_mat(ctx_evts, device_evts)
        return device_patterns

