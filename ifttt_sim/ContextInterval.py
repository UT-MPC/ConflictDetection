from .sim_config import *

class ContextInterval():
    def __init__(self, ctx, interval):
        super().__init__()
        if ctx in cate_context:
            self.interval = set(interval)
            self.type = "Cate"
        else:
            self.interval = list(interval)
            self.type = "Num"

    def contain(self, ctx_val):
        if ctx_val is None:
            return False
        if self.type == "Cate":
            return ctx_val in self.interval
        elif self.type == "Num":
            return ctx_val >= self.interval[0] and ctx_val <= self.interval[1]
        return False

    def __repr__(self):
        return str(self.interval)