
from time import gmtime, strftime

def attach_note(message, note_ref = "commits"):
    date = strftime("%Y-%m-%dT%H:%M:%S")
    print("%s: %s" % (date, message))

