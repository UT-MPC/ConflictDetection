import logging
from typing import Dict

from .ContextInterval import ContextInterval
class Trigger():
    def __init__(self, config: Dict[str, str]):
        super().__init__()
        self.prev_state = None
        self.ctx_interval = {}
        for ctx in config:
            self.ctx_interval[ctx] = ContextInterval(config[ctx])

    def does_trigger(self, state: Dict) -> bool:
        flag = True
        for ctx, ctx_interval in self.ctx_interval.items():
            if ctx in state:
                cur_val = state[ctx]
                prev_val = None if self.prev_state is None else self.prev_state[ctx]
                flag = ctx_interval.contain(cur_val) and \
                        (not ctx_interval.contain(prev_val))
                if not flag:
                    break
            else:
                logging.info("No context {} present.".format(ctx))
                flag = False
                break
        self.prev_state = state
        return flag

    