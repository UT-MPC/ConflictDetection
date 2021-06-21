from collections.abc import Iterable
from datetime import datetime
import re

from config import PROCESSED_TIME_FORMAT

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
    return [[min(coors) for coors in coordinates], [max(coors) for coors in coordinates]]



def get_bound(box):
    mid = len(box) // 2
    return box[:mid], box[mid:]

def compute_intersection_area(box_i, box_j):
    # This method assume the input boxes does intersect
    mins_i, maxs_i = get_bound(box_i)
    mins_j, maxs_j = get_bound(box_j)
    mins = [max(i,j) for i,j in zip(mins_i, mins_j)]
    maxs = [min(i,j) for i,j in zip(maxs_i, maxs_j)]
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
        if point[i] < mins_i[i] or point[i] > maxs_i[i]:
            return False
    return True