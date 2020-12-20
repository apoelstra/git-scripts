#!/bin/bash

## Usage and initialization

set -e
export GIT_NOTES_REF=refs/notes/label-pr
# ../master/ path used for Andrew's worktree directory structure
# I *think* this is the only thing that's hardcoded to my setup
REMOTES_DIR=../master/.git/refs/remotes/

function usage() {
    echo "Usage: $0 <URL prefix> <remote ref prefix> <master branches>"
    echo "Example: $0 https://github.com/ElementsProject/rust-elements/pull/ pr/ master"
    exit 1
}

if [ "$1" == "" ]; then
    usage
fi

if [ "$2" == "" ]; then
    usage
fi

if [ "$3" == "" ]; then
    # should have at least one "master" branch
    usage
fi


## Prints all children of a commit $1 which don't lie in the list $2
#
# Prints in postfix "reverse" order
#
# Uses $3 as a depth counter, which we need to do to make sure we're
# using a distinct variable each time we recurse (bash does not have
# stack frames)
function recurse() {
    local commit
    # First check if this is even a real commit, and get its hex id
    if commit[$3]=$(git rev-parse "$1" 2>/dev/null); then
        # Then check that it's not in the blacklist $2
        if ! echo "$2" | grep -q "${commit[$3]}"; then
            for parent in $(git log -1 "${commit[$3]}" --pretty=%P); do
                recurse "$parent" "$2" "$(($3 + 1))"
            done       
            echo -n "${commit[$3]} "
        fi
    fi
}

### Actual code ###

# 0. Setup
URL_PREFIX="$1"
REMOTE_PREFIX="$2"

# 1. Get list of all "commits in master" i.e. the first-parent log of master
maintree=
shift 2
for master in $@; do
    maintree="$maintree $(git log --pretty=%H --first-parent "$master")"
done

# 2. Loop through every PR that we have in our remote refs
for i in $(ls "$REMOTES_DIR$REMOTE_PREFIX")
do
    PR_LINK="$URL_PREFIX$i"
    echo -n "PR $i ... "

    # 2a. For this PR, find list of all its commits which are not directly in master
    PR_COMMITS=$(recurse "$REMOTE_PREFIX$i/head" "$maintree")
    N_COMMITS=$(echo $PR_COMMITS | wc -w)

    echo -n "found $N_COMMITS commits ... "

    # 2b. For each commit, check if it is already labelled, and label it if not
    iterated=0
    label_count=0
    for commit in $PR_COMMITS; do
        iterated=$(($iterated + 1)) ## Increment first so user sees 1-indexed value

        if ! git notes show "$commit" 2>/dev/null | grep -q "$PR_LINK"; then
            git notes append "$commit" -m "PR: $PR_LINK ($iterated/$N_COMMITS)"
            label_count=$(($label_count + 1))
        fi
    done
    echo "labeled $label_count/$N_COMMITS commits"
done

