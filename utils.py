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