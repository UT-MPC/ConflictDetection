from typing import Dict, List, Tuple
from rtree import index
from itertools import combinations

from ContextAccessor import ContextAccessor
from utils import *

def device_state_conflict(dis_i, dis_j):
    total_j = sum(dis_j)
    prob = 0
    for idx, p in enumerate(dis_i):
        prob += p * (total_j -  dis_j[idx])
    return prob

def device_capacity_conflict(dis, capacity):
    probs = [sum(x) for x in dis]
    ids = range(len(dis))
    prob = 1
    for i in range(0, capacity+1):
        cbs = list(combinations(ids, i))
        for c in cbs:
            pp = 1
            for i, p in enumerate(probs):
                # Multiply the probability of off for non-selected devices
                if i not in c:
                    pp *= (1-p)
            sel_prob = 0
            for idx in range(len(dis[0])):
                sel_pp = 1
                for i in c:
                    # Multiply the probability of staying in one state
                    sel_pp *= dis[i][idx]
                sel_prob += sel_pp
            pp *= sel_prob
            prob -= pp
    return prob

class ConflictDetector:
    def __init__(self, ctx_info: ContextAccessor, device_capacity: Dict):
        super().__init__()
        self.ctx_info = ctx_info
        self.capacity = device_capacity

    def predict_conflict_scenarios(self, habit_groups):
        users = list(habit_groups.keys())
        p = index.Property()
        p.dimension = len(self.ctx_info.get_all_ctx_ordered())
        final_conflicts = {x:[] for x in self.capacity}
        capacity_conflict_tree = {x:index.Index(properties=p) for x in self.capacity}
        capacity_conflict_id = {x:0 for x in self.capacity}
        min_conflict_prob = 0.0
        for user_i in range(len(users)):
        # for user_i in [0]:
            for device, groups in habit_groups[users[user_i]].items():
                r_tree = index.Index(properties=p)
                for i in range(len(groups)):
                    bound = groups[i]["box"][0] + groups[i]["box"][1] 
                    r_tree.insert(id=i, coordinates=bound, obj={(user_i, i)})
                tree_id = len(groups)
                for user_j in range(user_i+1, len(users)):
                    if device not in habit_groups[users[user_j]]:
                        # This user does not have this device
                        continue    
                    j_groups = habit_groups[users[user_j]][device]
                    for j, g in enumerate(j_groups):
                        bbox = g["box"][0] + g["box"][1]
                        intersects = list(r_tree.intersection(bbox, objects=True))
                        for intersect in intersects:
                            intersect_box = compute_intersection_area(intersect.bbox, bbox)
                            dis = intersect.object.union({(user_j, j)})
                            r_tree.insert(id=tree_id, coordinates=intersect_box, obj=dis)
                            tree_id += 1
                # Use the original box to intersect all
                for i in range(len(groups)):
                    bound = groups[i]["box"][0] + groups[i]["box"][1] 
                    intersects = list(r_tree.intersection(bound, objects=True))
                    # intersects = sorted(intersects, key = lambda x: len(x.object))

                    # First we calculate conflicts between two users
                    for ints in intersects:
                        if len(ints.object) == 2:
                            # compute conflict between two users
                            dis = [
                                habit_groups[users[x[0]]][device][x[1]]["dis"]
                                for x in ints.object
                            ]
                            prob = device_state_conflict(dis[0], dis[1])
                            if prob > min_conflict_prob:
                                final_conflicts[device].append({
                                    "users": ints.object,
                                    "box": ints.bbox,
                                    "prob": prob,
                                    "type": "DiffState",
                                })
                        if len(ints.object) > self.capacity[device] and self.capacity[device] != 0:
                            # Put capacity conflicts into a R-tree for further analysis
                            cap_box = ints.bbox
                            cap_ints = list(capacity_conflict_tree[device].intersection(cap_box, objects=True))
                            box_to_insert = ints.bbox
                            obj_to_insert = ints.object
                            is_included = False
                            for inter_box in cap_ints:
                                if (not is_included) and does_contain(cap_box, inter_box.bbox):
                                    capacity_conflict_tree[device].delete(inter_box.id, inter_box.bbox)
                                    dis_union = inter_box.object.union(ints.object)
                                    box_to_insert = inter_box.bbox
                                    obj_to_insert = dis_union
                                    is_included = True
                                if does_contain(inter_box.bbox, cap_box):
                                    capacity_conflict_tree[device].delete(inter_box.id, inter_box.bbox)
                                    dis_union = inter_box.object.union(ints.object)
                                    box_to_insert = cap_box
                                    obj_to_insert = dis_union
                                # capacity_conflict_tree[device].delete(inter_box.id, inter_box.bbox)
                                # dis_union = inter_box.object.union(ints)
                                # box_to_insert = compute_union_area(inter_box.bbox, cap_box)
                                # obj_to_insert = dis_union

                            capacity_conflict_tree[device].insert(
                                id=capacity_conflict_id[device],
                                coordinates=box_to_insert, 
                                obj = obj_to_insert,
                            )
                            capacity_conflict_id[device] += 1
        
        # print(capacity_conflict_id)
        max_box = [0]*len(self.ctx_info.get_ctx_space_shape()) + [
            x - 1
            for x in self.ctx_info.get_ctx_space_shape()
        ]
        for d, tree in capacity_conflict_tree.items():
            conflicts = list(tree.intersection(max_box, objects=True))
            for c in conflicts:
                dis = [ 
                    habit_groups[users[x[0]]][d][x[1]]["dis"]
                    for x in c.object
                ]
                prob = device_capacity_conflict(dis, self.capacity[d])
                if prob > min_conflict_prob:
                    final_conflicts[d].append({
                        "users": c.object,
                        "box": c.bbox,
                        "prob": prob,
                        "type": "Capacity"
                    })
        return final_conflicts
