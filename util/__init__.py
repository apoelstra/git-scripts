
import threading
import time

def now_str() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())

def log(s: str):
    print(f"{now_str()} {threading.current_thread().name}-{threading.current_thread().ident}: {s}")

