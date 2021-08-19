from typing import Dict, List

from .Trigger import Trigger
from .Action import Action
class Applet():
    def __init__(self, trigger: Trigger, action: Action):
        self.trigger = trigger
        self.action = action


    def check_frame(self, ctx_state: Dict, device_state: Dict)->List[Dict[str,str]]:
        device_to_change = {}
        if self.trigger.does_trigger(ctx_state):
            action_list = self.action.get_actions()
            for d, state in action_list.items():
                if d in device_state and state != device_state[d]:
                    device_to_change[d] = state
        return device_to_change
    
    @classmethod
    def builder(cls, trigger_cfg: Dict, action_cfg: Dict):
        trigger = Trigger(trigger_cfg)
        action = Action(action_cfg)
        return cls(trigger, action)

    def __repr__(self):
        return "{{Trigger: {}, Action: {}}}".format(str(self.trigger), str(self.action))