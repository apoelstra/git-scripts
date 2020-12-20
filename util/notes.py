
import git
import os

from time import gmtime, strftime

def attach_note(message, commit='HEAD', note_ref = "commits"):
    date = strftime("%Y-%m-%dT%H:%M:%S", gmtime())

    repo = git.Repo()
    with repo.git.custom_environment(GIT_NOTES_REF="refs/notes/" + note_ref) as mygit:
        repo.git.notes("append", "-m", date + "\n" + message, commit)

def check_is_note(item, workdir, commit='HEAD', note_ref = "commits"):
    repo = git.Repo(path=workdir)
    with repo.git.custom_environment(GIT_NOTES_REF="refs/notes/" + note_ref) as mygit:
        try:
            notes = repo.git.notes("show", commit)
        except:
            notes = ""
        return item in notes

