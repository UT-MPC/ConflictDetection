import logging
from typing import Dict, List, Tuple

from config import *
from utils import datetime_to_mins

class PatternBuilder():
    def __init__(self):
        super().__init__()

    def preprocess_ctx(self, ctx_evts: Dict) -> Dict:
        return ctx_evts

    """Generate device state change events with the corresponding context at that moement.
    The return is a complex dictionary of all devices. 
    The first key is the name of the device.
    The second key is the name of the state change action (i.e., "on", "off").
    The third key is the name of the context. 
    And the value is a list of value of that context at the moment of each event
    """
    def tag_device_evts(self, ctx_evts: Dict, device_evts: Dict) -> Dict[str, Dict[str, Dict[str, List]]]:
        device_evts_c = {}
        # Initialize the structure of device events with context
        for d, evts in device_evts.items():
            act = set([x[0] for x in evts])
            device_evts_c[d] = {
                a : {
                    c : []
                    for c in ctx_evts
                }
                for a in act
            }
            # Add additional contextes
            for a in act:
                device_evts_c[d][a][TIME_CTX] = []
                device_evts_c[d][a][WEEKDAY_CTX] = []

        ctx_evts = self.preprocess_ctx(ctx_evts)

        for c, c_evts in ctx_evts.items():
            pre = c_evts[0]
            d_evt_idx = {d: 0 for d in device_evts}
            for c_evt in c_evts[1:]:
                for d, d_evts in device_evts.items():
                    while d_evt_idx[d] < len(d_evts) and d_evts[d_evt_idx[d]][1] <= c_evt[1]:
                        d_evt = d_evts[d_evt_idx[d]]
                        device_evts_c[d][d_evt[0]][c].append(pre[0])
                        d_evt_idx[d] += 1
                pre = c_evt
            for d, d_evts in device_evts.items():
                while d_evt_idx[d] < len(d_evts):
                    d_evt = d_evts[d_evt_idx[d]]
                    device_evts_c[d][d_evt[0]][c].append(pre[0])
                    d_evt_idx[d] += 1
        for d, d_evts in device_evts.items():
            for d_evt in d_evts:
                device_evts_c[d][d_evt[0]][TIME_CTX].append(datetime_to_mins(d_evt[1]))
                device_evts_c[d][d_evt[0]][WEEKDAY_CTX].append(d_evt[1].date().weekday())

        return device_evts_c

    def mine_patterns(self, ctx_evts: Dict, device_evts: Dict):
        device_evts_c = self.tag_device_evts(ctx_evts, device_evts)

        logging.debug("Verifying the length of the events for each context matches")
        for d,v in device_evts_c.items():
            for a, c_evts in v.items():
                lengths = set([len(e) for c, e in c_evts.items()])
                if len(lengths) != 1:
                    logging.error("Miss match in the length of events for device {}, action {}!!!".format(d, a))
        return device_evts_c