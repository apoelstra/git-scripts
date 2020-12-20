#!/bin/python

import argparse
import regex
import git

from util.notes import attach_note, check_is_note

class PullRemote:
    def __init__(self, number, tip_commit):
        self.number = number
        self.tip_commit = tip_commit

    def __str__(self):
        return f"{{ PR\#{self.number}: self.tip }}"

    def ancestor_list(self, master_list):
        """
        List all ancestors of this remote that are not on master_list

        Includes the tip; returns ancestors in reverse (postfix) order.
        """
        ret = []
        ret_set = set()
        stack = [[self.tip_commit]]
        while len(stack) > 0:
            for tip in stack.pop():
                if tip in ret_set:
                    continue

                ret.append(tip)
                ret_set.add(tip)
                parents = [p for p in tip.parents if p.hexsha not in master_list]
                if len(parents) > 0:
                    stack.append(parents)
        ret.reverse()
        return ret

def main():
    ## 0. Parse arguments
    parser = argparse.ArgumentParser("Iterates through all refs that look like pull requests and label their respective commits. Usage: parent-label --url-prefix=github_url_prefix --ref-prefix=pr/ [list of master branches]")
    parser.add_argument('--url-prefix', required=True, help="Required. ex. https://github.com/MyOrg/project/pull/")
    parser.add_argument('--remote', required=True, help="Required. cal refs corresponding to PRs. Will search refs of the form <ref_prefix>/N/head ex. pr/")

    args, unknown_args = parser.parse_known_args()
    if len(unknown_args) == 0:
        unknown_args = ['master']

    ## 1. Search refs to find PRs
    repo = git.Repo()
    pr_list = []
    for ref in repo.refs:
        if isinstance(ref, git.RemoteReference) and ref.remote_name == args.remote:
            n = ref.remote_head.split('/', 2)
            if n[1] == "head":
                pr_list.append(PullRemote(n[0], ref.commit))

    print (f"Found {len(pr_list)} PRs.")

    ## 2. Get list of "on master" commits
    main_branch = set()
    for master in unknown_args:
        tip = repo.rev_parse(master)
        while len(tip.parents) > 0:
            main_branch.add(tip.hexsha)
            tip = tip.parents[0]
        main_branch.add(tip.hexsha) # initial commit
        print (f"Found {len(main_branch)} commits on main branch (searched from {master}).")

    ## 3. For each PR, run through its ancestors that are not on the master list
    for pr in pr_list:
        ancestor_list = pr.ancestor_list(main_branch)
        noted = 0
        for n, ancestor in enumerate(ancestor_list, start=1):
            new_note = f"PR: {args.url_prefix}{pr.number} ({n}/{len(ancestor_list)})"
            if not check_is_note(new_note, ".", commit=ancestor, note_ref="label-pr"):
                attach_note(new_note, commit=ancestor, note_ref="label-pr")
                noted += 1
        print (f"PR {args.url_prefix}{pr.number}: noted {noted}/{len(ancestor_list)}")

if __name__ == '__main__':
    main()

