#!/bin/python

import subprocess
from concurrent import futures
from typing import Any, Dict, List, MutableMapping, Optional

from checks import Check
from util.cargo import Cargo, Command
from util.git import TemporaryWorkdir 
from util.notes import check_is_note 

class AutoToolsCheck(Check):
    TYPE = 'autotools'

    def __init__(self, json):
        self.run_bins: List[str] = json.get('run-bins', [])
        self.configure_matrix: List[str] = json.get('configure-matrix', [[]])
        super().__init__(json)

    def notes_str(self, config):
        return "./autogen.sh && ./configure " + ' '.join(config) + " && make -j8; " + " && ".join(self.run_bins)

    def run_cmd(self, thread_name: str, cmd: List[str], workdir: str):
        print (' '.join(cmd) + " ## thread " + thread_name)
        completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=workdir)
        if completed.returncode != 0:
            print ("Command failed:", ' '.join(cmd))
            print (completed.stderr.decode("ascii"))
            completed.check_returncode() # trigger an exception

    def real_run(self, thread_name: str, config: List[str], commit: str, note: str):
        with TemporaryWorkdir(commit) as workdir:
            self.run_cmd(thread_name, ["./autogen.sh"], workdir)
            self.run_cmd(thread_name, ["./configure"] + config, workdir)
            self.run_cmd(thread_name, ["make", "-j8"], workdir)
            for bin in self.run_bins:
                self.run_cmd(thread_name, bin.split(' '), workdir)
        return note

    def run(self, commit: str, notes: List[str]):
        with futures.ThreadPoolExecutor() as executor:
            futs = []
            for config in self.configure_matrix:
                note = self.notes_str(config)
                if check_is_note(note, '.', commit=commit, note_ref='check-commit'):
                    print ("# already done", note) # Note already inserted
                else:
                    thread_name = str(len(futs))
                    futs.append(executor.submit(lambda: self.real_run(thread_name, config, commit, note)))

            for fut in futures.as_completed(futs):
                notes += [fut.result()]




