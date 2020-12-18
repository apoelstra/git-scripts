#!/bin/python

import argparse
import git
import glob
import os
import sys

from util import colors
from util.git import TemporaryWorkdir, cherry_pick, actual_merge_base
from util.cargo import Cargo
from util.notes import attach_note

def check_commit(workdir, cmds, do_extras=False):
    notes = []

    ## Run commands, collecting notes
    for command in cmds:
        cmd = command.split('-')
        # rust or rust-1.29.0
        if cmd[0] == 'rust':
            version = 'stable' if len(cmd) < 2 else cmd[1]
            cargo = Cargo(cwd=workdir, version=version)
            notes.append(cargo.build())
            notes.append(cargo.test())
        # fuzz-hongfuzzdir-iters
        elif cmd[0] == 'fuzz':
            iters = 1000000 if len(cmd) < 2 else cmd[1]
            direct = '-'.join(cmd[2:]) # lol am i pythoning right
            cargo = Cargo(cwd=workdir + '/' + direct, version='nightly')
            tests = glob.glob(direct + '/*.rs')
            for test in tests:
                test = test.split('/')[-1][:-3] # strip .rs
                notes.append(cargo.fuzz(test, iters))
        else:
            print(f"Unknown command {cmd[0]}")
            sys.exit(1)

    return notes


def main():
    ## Parse commands
    parser = argparse.ArgumentParser("Runs checks on the current commit (in a /tmp workdir) and records them as git notes")
    args, unknown_args = parser.parse_known_args()
    # Commands starting with ! should only be run on the tip
    normal_cmd = []
    tip_cmd = []
    for cmd in unknown_args[1:]:
        if cmd[0] == '!':
            tip_cmd.append(cmd[1:])
        else:
            normal_cmd.append(cmd)

    ## Get commits which are on the provided ref but not on master
    tip = unknown_args[0]
    base = actual_merge_base('master', tip)
    commit_list = [x.hexsha for x in git.Repo().iter_commits(f"{base}..{tip}")]
    commit_list.reverse()

    ## Iterate over all commits in-place
    for commit in commit_list:
        with TemporaryWorkdir(commit) as workdir:
            notes = check_commit(workdir, normal_cmd)
            if commit == commit_list[-1]:
                notes += check_commit(workdir, tip_cmd)
            ## Attach notes, if any
            if notes:
                attach_note("\n".join(notes), note_ref="check-commit", commit=commit)
            else:
                attach_note("(no action)", note_ref="check-commit", commit=commit)

    ## Determine whether we were already based on master
    master = git.Git().rev_parse('master')

    ## If not, rebase and check each PR
    if not git.Repo().is_ancestor(tip, master) and master != base:
        with TemporaryWorkdir(base.hexsha) as workdir:
            for commit in commit_list:
                new_head = cherry_pick(workdir, commit)
                notes = check_commit(workdir, normal_cmd)
                if commit == commit_list[-1]:
                    notes += check_commit(workdir, tip_cmd)
                ## Attach notes, if any
                if notes:
                    notes = ["rebased as " + new_head] + notes
                    attach_note("\n".join(notes), note_ref="check-commit", commit=commit)
                else:
                    attach_note("(no action)", note_ref="check-commit", commit=commit)


if __name__ == '__main__':
    main()

