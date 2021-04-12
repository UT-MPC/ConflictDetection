from datetime import datetime
import re

from config import PROCESSED_TIME_FORMAT
def json_datetime_hook(dct):
    time_reg = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}\s[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,3})?$")
    for k, v in dct.items():
        if isinstance(v, str) and time_reg.search(v):
            try:
                dct[k] = datetime.strptime(v, PROCESSED_TIME_FORMAT)
            except:
                pass
    return dct