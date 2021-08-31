from collections.abc import Iterable
from datetime import datetime
import re

from config import PROCESSED_TIME_FORMAT, DEVICE_MULTI_STATE_SUFFIX

def datetime_parser(s):
    time_reg = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}\s[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,3})?$")
    if isinstance(s, str):
        if time_reg.search(s):
            try:
                return datetime.strptime(s, PROCESSED_TIME_FORMAT)
            except:
                pass
        return s
    if isinstance(s, Iterable):
        return json_datetime_hook(s)
    return s

def json_datetime_hook(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            obj[k] = datetime_parser(v)
    elif isinstance(obj, list):
        obj = [datetime_parser(x) for x in obj]
    return obj

def datetime_to_seconds(dt: datetime) -> int:
    t = dt.time()
    return (t.hour * 60 + t.minute) * 60 + t.second

def datetime_to_mins(dt: datetime) -> int:
    t = dt.time()
    return t.hour * 60 + t.minute

def bounding_box(points):
    coordinates = list(zip(*points))
    return [[min(coors) for coors in coordinates], [max(coors)+1 for coors in coordinates]]



def get_bound(box):
    mid = len(box) // 2
    return box[:mid], box[mid:]

def does_intersect(box_i, box_j):
    mins_i, maxs_i = get_bound(box_i)
    mins_j, maxs_j = get_bound(box_j)
    for idx in range(len(mins_i)):
        if maxs_j[idx] <= mins_i[idx] or maxs_i[idx] <= mins_j[idx]:
            return False
    return True

def compute_intersection_area(box_i, box_j):
    # This method assume the input boxes does intersect
    mins_i, maxs_i = get_bound(box_i)
    mins_j, maxs_j = get_bound(box_j)
    mins = [max(i,j) for i,j in zip(mins_i, mins_j)]
    maxs = [min(i,j) for i,j in zip(maxs_i, maxs_j)]
    return mins+maxs

def compute_union_area(box_i, box_j):
    mins_i, maxs_i = get_bound(box_i)
    mins_j, maxs_j = get_bound(box_j)
    mins = [min(i,j) for i,j in zip(mins_i, mins_j)]
    maxs = [max(i,j) for i,j in zip(maxs_i, maxs_j)]
    return mins+maxs

def does_contain(box_i, box_j):
    mins_i, maxs_i = get_bound(box_i)
    mins_j, maxs_j = get_bound(box_j)
    for i in range(len(mins_i)):
        if mins_i[i] < mins_j[i]  or maxs_i[i] > maxs_j[i]:
            return False
    return True

def does_contain_point(box, point):
    mins_i, maxs_i = get_bound(box)
    for i in range(len(mins_i)):
        if point[i] < mins_i[i] or point[i] >= maxs_i[i]:
            return False
    return True

def compute_area(box):
    mins, maxs = get_bound(box)
    area = 1
    for i, low in enumerate(mins):
            area *= (maxs[i] - low)
    return area

def match_user_groups(user_group_1, user_group_2):
    return set(user_group_1) == set(user_group_2)

def get_d_state_str(d_evt):
    state = d_evt[0]
    if DEVICE_MULTI_STATE_SUFFIX not in state:
        return state
    else:
        return state + "#" + str(d_evt[2])


def check_HS_thermo_mode(time):
    # Since Health Science building change the heating mode and the default setpoint, 
    # we need this information as a context
    day = time.day
    month = time.month
    if month < 5 or month > 9:
        return "heating"
    
    if month == 5 and day < 13:
        return "heating"
    return "cooling"