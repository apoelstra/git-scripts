#!/bin/python

import argparse
from concurrent import futures
import git # type: ignore
import glob
import json
import os
from typing import List, Optional, Tuple
import sys

import checks
from util import colors, log
from util.git import TemporaryWorkdir, cherry_pick, actual_merge_base
from util.cargo import Cargo 
from util.notes import attach_note, check_is_note

def run_commit(executor: futures.ThreadPoolExecutor, commit: str, old_commit: Optional[str], commands: List[checks.Check], is_tip: bool) -> Tuple[List[str], str, Optional[str]]:
    notes: List[str] = []
    for command in commands:
        if is_tip or not command.only_tip:
            command.run(executor, commit, notes)
    return notes, commit, old_commit

def main() -> None:
    ## Parse commands
    parser = argparse.ArgumentParser("Runs checks on the current commit (in a /tmp workdir) and records them as git notes")
    parser.add_argument('--master', default='master', help="Set the master branch that we should base work off of")
    parser.add_argument('--one', action='store_true', help="Only check one commit rather than iterating")
    args, unknown_args = parser.parse_known_args()

    ## Determine whether we were already based on master
    master = git.Git().rev_parse(args.master)

    ## Get commits which are on the provided ref but not on master
    tip = unknown_args[0]
    base = actual_merge_base(args.master, tip)
    commit_list = [x for x in git.Repo().iter_commits(f"{base}..{tip}")]
    commit_list.reverse()

    commands: List[checks.Check] = json.loads(unknown_args[1], object_hook=checks.json_object_hook)

    if args.one:
        log ("Only checking the one commit " + tip)
        commit_list = [tip]
    else:
        log ("Master is " + master)
        log ("Merge base is " + str(base))

    ## Start thread pool
    executor = futures.ThreadPoolExecutor(thread_name_prefix='git_check')
    futs = []

    ## Iterate over all commits in-place
    for commit in commit_list:
        futs.append(executor.submit(lambda: run_commit(executor, commit, None, commands, commit == commit_list[-1])))

    ## If not already based on master, rebase and check each PR
    if master != base.hexsha:
        rebased_commit_list = []
        with TemporaryWorkdir(base.hexsha) as workdir:
            for commit in commit_list:
                rebased_commit_list.append((commit, cherry_pick(workdir, commit)))

        for old_commit, commit in rebased_commit_list:
            futs.append(executor.submit(lambda: run_commit(executor, commit, old_commit, commands, commit == rebased_commit_list[-1])))

    ## Get results
    for fut in futs:
        notes, commit, old_commit = fut.result()
        log(f"Completed {colors.bold(str(commit))}. Notes {len(notes)}")
        ## Attach notes, if any
        if notes:
            attach_note("\n".join(notes), note_ref="check-commit", commit=commit)
            if old_commit:
                notes = [f"rebased for merge-testing on {base} as {commit}"] + notes
                attach_note("\n".join(notes), note_ref="check-commit", commit=old_commit)

    ## Ring bell to highlight workspace
    print("\a")


if __name__ == '__main__':
    main()

