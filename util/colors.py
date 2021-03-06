
class bcolors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    MAGENTA = '\033[95m'
    RED = '\033[91m'
    YELLOW = '\033[33m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'

def bold(s: str):
    return bcolors.BOLD + s + bcolors.ENDC

def yellow(s: str):
    return bcolors.YELLOW + s + bcolors.ENDC

def magenta(s: str):
    return bcolors.MAGENTA + s + bcolors.ENDC

def green(s: str):
    return bcolors.GREEN + s + bcolors.ENDC
