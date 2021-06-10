from datetime import datetime
import math
from typing import List, Dict, Tuple


from config import TIME_CTX, WEEKDAY_CTX
from utils import datetime_to_mins
all_ctx = {
    "weather" : {

    },
    "temperature" : {

    },
    "humidity" : {
        
    }
}

class ContextAccessor():
    def __init__(self, ctx_info = all_ctx):
        super().__init__()
        self.ctx_info = ctx_info

    def get_ctx_interval(self, ctx_name:str):
        return self.ctx_info[ctx_name]["interval"]

    def get_ctx_range(self, ctx_name:str):
        return self.ctx_info[ctx_name]["range"]

    def get_all_ctx_ordered(self) -> List[str]:
        return list(self.ctx_info.keys())

    def have_ctx(self, ctx_name: str):
        return ctx_name in self.ctx_info

    def get_ctx_space_shape(self) -> Tuple[int]:
        space_shape = []
        for k in self.ctx_info:
            r = self.get_ctx_range(k)
            space_shape.append(math.ceil((r[1] - r[0]) / self.get_ctx_interval(k)))
        return tuple(space_shape)

    def get_ctx_idx(self, ctx_name, ctx_val) -> int:
        r = self.get_ctx_range(ctx_name)
        return int((ctx_val - r[0]) / self. get_ctx_interval(ctx_name))

    def get_coor_by_ctx(self, ctx_val: Dict) -> Tuple[int]:
        cell_idx = tuple([
            self.get_ctx_idx(k, ctx_val[k])
            for k in ctx_val
        ])
        return cell_idx
    
    def update_time_ctx(self, ctx_snapshot: Dict, cur_time: datetime):
        if self.have_ctx(TIME_CTX):
            ctx_snapshot[TIME_CTX] = datetime_to_mins(cur_time)
        if self.have_ctx(WEEKDAY_CTX):
            ctx_snapshot[WEEKDAY_CTX] = cur_time.date().weekday() 


