import re
from datetime import datetime


DATETIME_TEMP = "%Y-%m-%d %H:%M:%S.%f"
ACT_IDX = 4
def split_line(line_str: str):
    segs = line_str.split()
    # The first and second segments in the line is date time
    # Some time does not have millisecond
    if '.' not in segs[1]:
        segs[1] = segs[1] + '.0'
    time = datetime.strptime(segs[0] + " " + segs[1], DATETIME_TEMP)

    # The 3rd and 4th segments are one device event
    device_evt = (segs[2], segs[3])

    # The 4th segment is an optional groundtruth activity of the user
    act = None if len(segs) < ACT_IDX + 1 else segs[ACT_IDX]

    return time, device_evt, act

    
def preprocess(filename: str):
    with open(filename) as f:
        line_str = f.readline()
        while line_str:
            time, d_evt, act = split_line(line_str)
            line_str = f.readline()
            

