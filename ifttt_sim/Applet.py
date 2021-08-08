from ifttt_sim import Trigger, Action
class Applet():
    def __init__(self, trigger: Trigger, action: Action):
        self.trigger = trigger
        self.action = action

    
