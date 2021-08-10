class ContextInterval():
    def __init__(self, interval):
        super().__init__()
        self.interval = interval
        if type(interval) == set:
            self.type = "Cate"
        elif type(interval) == list:
            self.type = "Num"

    def contain(self, ctx_val):
        if ctx_val is None:
            return False
        if self.type == "Cate":
            return ctx_val in self.interval
        elif self.type == "Num":
            return ctx_val >= self.interval[0] and ctx_val <= self.interval[1]
        return False