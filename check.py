#!/bin/python

import argparse
import git
import glob
import os
import sys

from util import colors
from util.git import TemporaryWorkdir, cherry_pick, actual_merge_base
from util.cargo import Cargo
from util.notes import attach_note, check_is_note

def update_notes(cargo, cmd, notes):
    new_note = cmd.notes_str()
    if check_is_note(new_note, cargo.cwd, note_ref="check-commit"):
        print("# skipping (already done)", cmd.run_str())
    else:
        cmd.run(cargo)
        notes += [new_note]

def check_commit(workdir, cmds, notes, do_extras=False):
    ## Run commands, collecting notes
    for command in cmds:
        cmd = command.split('-')
        # rust or rust-1.29.0
        if cmd[0] == 'rust':
            version = 'stable' if len(cmd) < 2 else cmd[1]
            cargo = Cargo(cwd=workdir, version=version)
            update_notes(cargo, cargo.BUILD, notes)
            update_notes(cargo, cargo.TEST, notes)
        # fuzz-hongfuzzdir-iters
        elif cmd[0] == 'fuzz':
            iters = 1000000 if len(cmd) < 2 else cmd[1]
            direct = '-'.join(cmd[2:]) # lol am i pythoning right
            cargo = Cargo(cwd=workdir + '/' + direct, version='nightly')
            tests = glob.glob(direct + '/*.rs')
            for test in tests:
                test = test.split('/')[-1][:-3] # strip .rs
                update_notes(cargo, cargo.fuzz_command(test, iters), notes)
        else:
            print(f"Unknown command {cmd[0]}")
            sys.exit(1)


def main():
    ## Parse commands
    parser = argparse.ArgumentParser("Runs checks on the current commit (in a /tmp workdir) and records them as git notes")
    parser.add_argument('--master', default='master', help="Set the master branch that we should base work off of")
    args, unknown_args = parser.parse_known_args()
    # Commands starting with ! should only be run on the tip
    normal_cmd = []
    tip_cmd = []
    for cmd in unknown_args[1:]:
        if cmd[0] == '!':
            tip_cmd.append(cmd[1:])
        else:
            normal_cmd.append(cmd)

    ## Determine whether we were already based on master
    master = git.Git().rev_parse(args.master)

    ## Get commits which are on the provided ref but not on master
    tip = unknown_args[0]
    base = actual_merge_base(args.master, tip)
    commit_list = [x for x in git.Repo().iter_commits(f"{base}..{tip}")]
    commit_list.reverse()

    print ("Master is", master)
    print ("Merge base is", base)

    ## Iterate over all commits in-place
    for commit in commit_list:
        with TemporaryWorkdir(commit) as workdir:
            notes = []
            check_commit(workdir, normal_cmd, notes)
            if commit == commit_list[-1]:
                check_commit(workdir, tip_cmd, notes)
            ## Attach notes, if any
            if notes:
                attach_note("\n".join(notes), note_ref="check-commit", commit=commit)


    ## If not already based on master, rebase and check each PR
    if master != base.hexsha:
        with TemporaryWorkdir(base.hexsha) as workdir:
            for commit in commit_list:
                notes = []
                new_head = cherry_pick(workdir, commit)
                check_commit(workdir, normal_cmd, notes)
                if commit == commit_list[-1]:
                    check_commit(workdir, tip_cmd, notes)
                ## Attach notes, if any
                if notes:
                    attach_note("\n".join(notes), note_ref="check-commit", commit=new_head)
                    notes = [f"rebased for merge-testing on {base} as {new_head}"] + notes
                    attach_note("\n".join(notes), note_ref="check-commit", commit=commit)


if __name__ == '__main__':
    main()

