
import git
import subprocess
import tempfile

class TemporaryWorkdir:
    def __init__(self):
        self.tempdir = tempfile.TemporaryDirectory()
        print(self.tempdir)

    def __enter__(self):
        repo = git.Repo() # Throw exception if we are not in a git repo
        head = repo.rev_parse("HEAD")

        self.tempdir_name = self.tempdir.__enter__()
        git.Git().worktree("add", self.tempdir_name, head)
        return self.tempdir_name

    def __exit__(self, exc_type, exc_val, exc_tb):
        git.Git().worktree("remove", "--force", self.tempdir_name)
        self.tempdir.__exit__(exc_type, exc_val, exc_tb)
        return False

