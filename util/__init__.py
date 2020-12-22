
import time

def now_str() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())

