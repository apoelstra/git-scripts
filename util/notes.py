
import git
import os

from time import gmtime, strftime

def attach_note(message, note_ref = "commits"):
    date = strftime("%Y-%m-%dT%H:%M:%S", gmtime())

    os.environ['GIT_NOTES_REF'] = "refs/notes/" + note_ref
    git.Git().notes("append", "-m", date + "\n" + message)

