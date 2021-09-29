from typing import Dict, List, Tuple
from rtree import index
from itertools import combinations
from scipy.stats import norm
import math
import heapq
import copy

from ContextAccessor import ContextAccessor
from utils import *
from config import *

def device_state_conflict(dis_i, dis_j, device, shareable_flag = True):
    if GRID_MODE.get(device, GRID_MODE["default"]) == "All":
        total_j = sum(dis_j)
        total_i = sum(dis_i)
        if not shareable_flag:
            return total_i * total_j
        prob = 0
        for idx, p in enumerate(dis_i):
            prob += p * (total_j -  dis_j[idx])
    else:
        mean0 = dis_i[0] - dis_j[0]
        mean1 = dis_j[0] - dis_i[0]
        var = dis_j[1] + dis_i[1]
        if var < 1e-6:
            return 1.0 if abs(dis_j[0] - dis_i[0])>=1 else 0.0
        prob = norm.sf(SOFT_VAL_THRESHOLD.get(device, 1), mean0, math.sqrt(var))
        prob += norm.sf(SOFT_VAL_THRESHOLD.get(device, 1), mean1, math.sqrt(var))
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

def get_true_intersection(rTree, box, isObjects=True):
    # Since our right edge is not included in the range, 
    # the intersection in RTree is different from ours. We need to recheck the intersection
    intersects = rTree.intersection(box, objects=isObjects)
    return [ints for ints in intersects if does_intersect(ints.bbox, box)]

class ConflictPredicator:
    def __init__(self, ctx_info: ContextAccessor, all_conflicts):
        super().__init__()
        self.ctx_info = ctx_info
        self.r_tree = {}
        p = index.Property()
        p.dimension = len(self.ctx_info.get_all_ctx_ordered())
        if p.dimension == 1:
            self.r_tree = all_conflicts
        else:
            for d in all_conflicts:
                self.r_tree[d] = index.Index(properties = p)
                for i, c in enumerate(all_conflicts[d]):
                    self.r_tree[d].insert(id=i, coordinates=c["box"], obj=c)

    def get_prob_conflict(self, ctx, user_pair, device):
        if len(self.ctx_info.get_all_ctx_ordered()) == 1:
            for c in self.r_tree[device]:
                if does_contain_point(c["box"], ctx):
                    if match_user_groups(user_pair, [x[0] for x in c["users"]]):
                        return c["prob"]
            return 0.
        else:
            upper = tuple([x + 1 for x in ctx])
            ctx = ctx + upper
            ints = get_true_intersection(self.r_tree[device], ctx)
            for intersection in ints:
                con = intersection.object
                if match_user_groups(user_pair, [x[0] for x in con["users"]]):
                    return con["prob"]
            # if none of the conflict contains the context, then we return 0
            return 0.



class ConflictDetector:
    def __init__(self, ctx_info: ContextAccessor, device_capacity: Dict):
        super().__init__()
        self.ctx_info = ctx_info
        self.capacity = device_capacity
                
    def predict_conflict_1d(self, habit_groups):
        final_conflicts = {x: [] for  x in self.capacity}
        users = list(habit_groups.keys())
        devices = list(self.capacity.keys())
        min_conflict_prob = 0.0
        for user_i in range(len(users)):
            for user_j in range(user_i+1, len(users)):
                for d, group_i in habit_groups[users[user_i]].items():
                    if d not in habit_groups[users[user_j]]:
                        continue
                    group_j = habit_groups[users[user_j]][d]
                    for ii, g_i in enumerate(group_i):
                        for jj, g_j in enumerate(group_j):
                            box_i = g_i["box"][0] + g_i["box"][1]
                            box_j = g_j["box"][0] + g_j["box"][1]
                            if does_intersect(box_i, box_j):
                                dis = [g_i["dis"], g_j["dis"]]
                                prob = device_state_conflict(dis[0], dis[1], d)
                                if self.capacity[d] == 1:
                                    prob = device_state_conflict(dis[0], dis[1], d, False)
                                
                                if prob > min_conflict_prob:
                                    final_conflicts[d].append({
                                        "users": {(users[user_i], ii),(users[user_j], jj)},
                                        "box": compute_intersection_area(box_i, box_j),
                                        "prob": prob,
                                        "type": "DiffState",
                                    })
        return final_conflicts
    def predict_conflict_scenarios(self, habit_groups):
        users = list(habit_groups.keys())
        p = index.Property()
        p.dimension = len(self.ctx_info.get_all_ctx_ordered())
        if p.dimension == 1:
            return self.predict_conflict_1d(habit_groups)
        final_conflicts = {x:[] for x in self.capacity}
        capacity_conflict_tree = {x:index.Index(properties=p) for x in self.capacity}
        capacity_conflict_id = {x:0 for x in self.capacity}
        min_conflict_prob = 0.0
        for user_i in range(len(users)):
        # for user_i in [0]:
            for device, groups in habit_groups[users[user_i]].items():
                inst_pair = []
                r_tree = index.Index(properties=p)
                for i in range(len(groups)):
                    bound = groups[i]["box"][0] + groups[i]["box"][1] 
                    r_tree.insert(id=i, coordinates=bound, obj={(users[user_i], i)})
                tree_id = len(groups)
                for user_j in range(user_i+1, len(users)):
                    if device not in habit_groups[users[user_j]]:
                        # This user does not have this device
                        continue    
                    j_groups = habit_groups[users[user_j]][device]
                    for j, g in enumerate(j_groups):
                        bbox = g["box"][0] + g["box"][1]
                        intersects = get_true_intersection(r_tree, bbox)
                        for intersect in intersects:
                            intersect_box = compute_intersection_area(intersect.bbox, bbox)
                            dis = intersect.object.union({(users[user_j], j)})
                            inst_pair.append({"coor": intersect_box, "dis": copy.deepcopy(dis)})
                            # r_tree.insert(id=tree_id, coordinates=intersect_box, obj=dis)
                            # tree_id += 1
                for pair in inst_pair:
                    dis = [
                        habit_groups[x[0]][device][x[1]]["dis"]
                        for x in pair["dis"]
                    ]
                    prob = device_state_conflict(dis[0], dis[1], device)
                    if self.capacity[device] == 1:
                        prob = device_state_conflict(dis[0], dis[1], device, False)
                    
                    if prob > min_conflict_prob:
                        final_conflicts[device].append({
                            "users": pair["dis"],
                            "box": pair["coor"],
                            "prob": prob,
                            "type": "DiffState",
                        })



                # Use the original box to intersect all
                # for i in range(len(groups)):
                #     bound = groups[i]["box"][0] + groups[i]["box"][1] 
                #     intersects = get_true_intersection(r_tree, bound)
                #     # intersects = sorted(intersects, key = lambda x: len(x.object))

                #     # First we calculate conflicts between two users
                #     for ints in intersects:
                #         if len(ints.object) == 2:
                #             # compute conflict between two users
                #             dis = [
                #                 habit_groups[x[0]][device][x[1]]["dis"]
                #                 for x in ints.object
                #             ]
                #             prob = device_state_conflict(dis[0], dis[1], device)
                #             if self.capacity[device] == 1:
                #                 prob = device_state_conflict(dis[0], dis[1], device, False)
                            
                #             if prob > min_conflict_prob:
                #                 final_conflicts[device].append({
                #                     "users": ints.object,
                #                     "box": ints.bbox,
                #                     "prob": prob,
                #                     "type": "DiffState",
                #                 })
                #             continue
                        # if len(ints.object) > self.capacity[device] and self.capacity[device] != 0 and self.capacity[device] != 1:
                        #     # Put capacity conflicts into a R-tree for further analysis
                        #     cap_box = ints.bbox
                        #     cap_ints = get_true_intersection(capacity_conflict_tree[device], cap_box)
                        #     box_to_insert = ints.bbox
                        #     obj_to_insert = ints.object
                        #     is_included = False
                        #     for inter_box in cap_ints:
                        #         if (not is_included) and does_contain(cap_box, inter_box.bbox):
                        #             capacity_conflict_tree[device].delete(inter_box.id, inter_box.bbox)
                        #             dis_union = inter_box.object.union(ints.object)
                        #             box_to_insert = inter_box.bbox
                        #             obj_to_insert = dis_union
                        #             is_included = True
                        #         if does_contain(inter_box.bbox, cap_box):
                        #             capacity_conflict_tree[device].delete(inter_box.id, inter_box.bbox)
                        #             dis_union = inter_box.object.union(ints.object)
                        #             box_to_insert = cap_box
                        #             obj_to_insert = dis_union
                        #         # capacity_conflict_tree[device].delete(inter_box.id, inter_box.bbox)
                        #         # dis_union = inter_box.object.union(ints)
                        #         # box_to_insert = compute_union_area(inter_box.bbox, cap_box)
                        #         # obj_to_insert = dis_union

                        #     capacity_conflict_tree[device].insert(
                        #         id=capacity_conflict_id[device],
                        #         coordinates=box_to_insert, 
                        #         obj = obj_to_insert,
                        #     )
                        #     capacity_conflict_id[device] += 1
        
        # print(capacity_conflict_id)
        # max_box = [0]*len(self.ctx_info.get_ctx_space_shape()) + [
        #     x - 1
        #     for x in self.ctx_info.get_ctx_space_shape()
        # ]
        # for d, tree in capacity_conflict_tree.items():
        #     conflicts = get_true_intersection(tree, max_box)
        #     for c in conflicts:
        #         dis = [ 
        #             habit_groups[x[0]][d][x[1]]["dis"]
        #             for x in c.object
        #         ]
        #         prob = device_capacity_conflict(dis, self.capacity[d])
        #         if prob > min_conflict_prob:
        #             final_conflicts[d].append({
        #                 "users": c.object,
        #                 "box": c.bbox,
        #                 "prob": prob,
        #                 "type": "Capacity"
        #             })
        return final_conflicts
