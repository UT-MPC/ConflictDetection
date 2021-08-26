from datetime import datetime
import math
from typing import List, Dict, Tuple
import holidays

from config import  *
from utils import datetime_to_mins, check_HS_thermo_mode
all_ctx = {
    "weather" : {},
    "temperature" : {},
    "humidity" : {}
}
CAT_CTX_ORDER = {
    "summary#CAT": ["Clear", "Breezy", "Cloudy", "Rain", "Snow", "Foggy"],
    "weatherDesc#CAT": ["Clear", "Fog", "Cloudy", "Rain", "HeavyRain", "Snow", "HeavySnow"],
    THERMO_MODE_CTX: ["cooling", "heating"],
}
UK_HOLIDAYS = holidays.UK()


class ContextAccessor():
    def __init__(self, ctx_info = all_ctx):
        super().__init__()
        self.ctx_info = ctx_info
        
    def get_ctx_interval(self, ctx_name:str):
        if CATEGORICAL_CTX_SUFFIX in ctx_name:
            return 1
        return self.ctx_info[ctx_name]["interval"]

    def get_ctx_range(self, ctx_name:str):
        if CATEGORICAL_CTX_SUFFIX in ctx_name:
            return [0, len(CAT_CTX_ORDER[ctx_name])]
        return self.ctx_info[ctx_name]["range"]

    def get_all_ctx_ordered(self) -> List[str]:
        return list(self.ctx_info.keys())

    def have_ctx(self, ctx_name: str):
        return ctx_name in self.ctx_info

    def get_ctx_space_shape(self) -> Tuple[int]:
        space_shape = []
        for k in self.ctx_info:
            r = self.get_ctx_range(k)
            space_shape.append(1+math.ceil((r[1] - r[0]) / self.get_ctx_interval(k)))
        return tuple(space_shape)

    def get_ctx_idx(self, ctx_name, ctx_val) -> int:
        if CATEGORICAL_CTX_SUFFIX in ctx_name:
            return CAT_CTX_ORDER[ctx_name].index(ctx_val)
        r = self.get_ctx_range(ctx_name)
        return int((ctx_val - r[0]) / self. get_ctx_interval(ctx_name))

    def get_coor_by_ctx(self, ctx_val: Dict) -> Tuple[int]:
        cell_idx = tuple([
            self.get_ctx_idx(k, ctx_val[k])
            for k in self.ctx_info
        ])
        return cell_idx
    
    def update_time_ctx(self, ctx_snapshot: Dict, cur_time: datetime):
        if self.have_ctx(TIME_CTX):
            ctx_snapshot[TIME_CTX] = datetime_to_mins(cur_time)
        if self.have_ctx(WEEKDAY_CTX):
            ctx_snapshot[WEEKDAY_CTX] = cur_time.date().weekday() 
        if self.have_ctx(HOLIDAY_CTX):
            ctx_snapshot[HOLIDAY_CTX] = 1 if cur_time.date() in UK_HOLIDAYS else 0
        if self.have_ctx(THERMO_MODE_CTX):
            ctx_snapshot[THERMO_MODE_CTX] = check_HS_thermo_mode(cur_time)

    def get_space_area(self):
        shape = self.get_ctx_space_shape()
        area = 1
        for s in shape:
            area *= s
        return area

    def coor_to_snapshot(self, point):
        p_str = {}
        for idx, ctx in enumerate(self.get_all_ctx_ordered()):
            r = self.get_ctx_range(ctx)
            interval = self.get_ctx_interval(ctx)
            if  ctx in CAT_CTX_ORDER:
                p_str[ctx] = CAT_CTX_ORDER[ctx][point[idx]]
            else:
                p_str[ctx] = r[0] + point[idx] * interval
        return p_str

    def coor_box_to_range(self, box):
        box_str = {}
        ctx_len = len(self.get_all_ctx_ordered())
        # box should follow the format of [min, min,..., max, max]
        for idx, ctx in enumerate(self.get_all_ctx_ordered()):
            r = self.get_ctx_range(ctx)
            interval = self.get_ctx_interval(ctx)
            if  ctx in CAT_CTX_ORDER:
                box_str[ctx] = {
                    CAT_CTX_ORDER[ctx][x]
                    for x in range(int(box[idx]), int(box[ctx_len + idx]))
                }
            else:
                box_str[ctx] = [r[0] + box[idx] * interval, r[0] + box[ctx_len + idx] * interval]
        return box_str
