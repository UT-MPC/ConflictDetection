from typing import Dict

from .sim_config import *
class Action():
    def __init__(self, config: Dict):
        super().__init__()
        self.actions = {}
        for d, a in config.items():
            self.actions[device_short.get(d,d)] = a

    def get_actions(self):
        return self.actions

    def __repr__(self):
        return str(self.actions)