
import git
import os

from time import gmtime, strftime

def attach_note(message, commit='HEAD', note_ref = "commits"):
    date = strftime("%Y-%m-%dT%H:%M:%S", gmtime())

    repo = git.Repo()
    with repo.git.custom_environment(GIT_NOTES_REF="refs/notes/" + note_ref):
        repo.git.notes("append", "-m", date + "\n" + message, commit)

def check_is_note(item, workdir, commit='HEAD', note_ref = "commits"):
    repo = git.Repo(path=workdir, search_parent_directories=True)
    with repo.git.custom_environment(GIT_NOTES_REF="refs/notes/" + note_ref):
        try:
            notes = repo.git.notes("show", commit)
        except:
            notes = ""
        return item in notes

def update_notes(notes, new_note, command, commit='HEAD', workdir=None, note_ref='commits'):
    if check_is_note(new_note, workdir, commit=commit, note_ref=note_ref):
        print ("# already done", new_note) # Note already inserted
    else:
        command()
        notes += [new_note]


