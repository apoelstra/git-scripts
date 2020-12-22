
import git # type: ignore
import subprocess
import tempfile

from util import colors

class TemporaryWorkdir:
    def __init__(self, commit=git.Git().rev_parse('HEAD')):
        self.commit = commit
        self.tempdir = tempfile.TemporaryDirectory()

    def __enter__(self):
        repo = git.Repo() # Throw exception if we are not in a git repo
        print(f"{colors.magenta('Checking out')} commit {colors.bold(str(self.commit))}")

        self.tempdir_name = self.tempdir.__enter__()
        git.Git().worktree("add", self.tempdir_name, self.commit)
        return self.tempdir_name

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"{colors.magenta('Remove')} worktree for {colors.bold(str(self.commit))}")
        git.Git().worktree("remove", "--force", self.tempdir_name)
        self.tempdir.__exit__(exc_type, exc_val, exc_tb)
        return False

def actual_merge_base(master: git.Commit, branch: git.Commit) -> git.Commit:
    repo = git.Repo()
    i = 0
    while repo.is_ancestor(branch, f"{master}~{i}"):
        i += 1
    return repo.merge_base(f"{master}~{i}", branch)[0]

def cherry_pick(workdir, commit):
    repo = git.Repo(path=workdir, search_parent_directories=True)
    with repo.git.custom_environment(GIT_COMMITTER_DATE=str(commit.authored_date)):
        head = repo.git.rev_parse('HEAD')
        print(f"{colors.magenta('Cherry-picking')} commit {colors.bold(str(commit))} onto {colors.bold(str(head))}")
        repo.git.cherry_pick(commit, "--keep-redundant-commits")
        head = repo.git.rev_parse('HEAD')
        print(f"{colors.magenta('Cherry-picked')} as {colors.bold(str(head))}")
        return head

