from typing import Dict

class Action():
    def __init__(self, config: Dict):
        super().__init__()
        self.actions = config

    def get_actions(self):
        return self.actions