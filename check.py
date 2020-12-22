#!/bin/python

import argparse
import git # type: ignore
import glob
import json
import os
from typing import List
import sys

import checks
from util import colors
from util.git import TemporaryWorkdir, cherry_pick, actual_merge_base
from util.cargo import Cargo, Command
from util.notes import attach_note, check_is_note

def main() -> None:
    ## Parse commands
    parser = argparse.ArgumentParser("Runs checks on the current commit (in a /tmp workdir) and records them as git notes")
    parser.add_argument('--master', default='master', help="Set the master branch that we should base work off of")
    args, unknown_args = parser.parse_known_args()

    ## Determine whether we were already based on master
    master = git.Git().rev_parse(args.master)

    ## Get commits which are on the provided ref but not on master
    tip = unknown_args[0]
    base = actual_merge_base(args.master, tip)
    commit_list = [x for x in git.Repo().iter_commits(f"{base}..{tip}")]
    commit_list.reverse()

    commands: List[Command] = json.loads(unknown_args[1], object_hook=checks.json_object_hook)

    print ("Master is", master)
    print ("Merge base is", base)

    ## Iterate over all commits in-place
    for commit in commit_list:
        with TemporaryWorkdir(commit) as workdir:
            notes: List[str] = []
            ## Run all commands
            for command in commands:
                if commit == commit_list[-1] or not command.only_tip:
                    command.run(workdir, notes)

            ## Attach notes, if any
            if notes:
                attach_note("\n".join(notes), note_ref="check-commit", commit=commit)

    ## If not already based on master, rebase and check each PR
    if master != base.hexsha:
        with TemporaryWorkdir(base.hexsha) as workdir:
            for commit in commit_list:
                notes = []
                new_head = cherry_pick(workdir, commit)
                ## Run all commands
                for command in commands:
                    if commit == commit_list[-1] or not command.only_tip:
                        command.run(workdir, notes)
                ## Attach notes, if any
                if notes:
                    attach_note("\n".join(notes), note_ref="check-commit", commit=new_head)
                    notes = [f"rebased for merge-testing on {base} as {new_head}"] + notes
                    attach_note("\n".join(notes), note_ref="check-commit", commit=commit)


if __name__ == '__main__':
    main()

