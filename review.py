#!/bin/python

import argparse

from util.notes import attach_note

def main():
    parser = argparse.ArgumentParser("sticks an OK message on a given commit")
    parser.add_argument('--message', '-m', default='OK', help="message to put in the note (default: OK)")
    parser.add_argument('--commit', '-c', default='HEAD', help="commit to add the note to (default: HEAD)")
    args = parser.parse_args()

    attach_note(args.message, commit=args.commit, note_ref="review")

if __name__ == '__main__':
    main()

