#!/bin/python

import subprocess
from concurrent import futures
from typing import Any, Dict, List, MutableMapping, Optional

from checks import Check
from util import log
from util.cargo import Cargo, Command
from util.git import TemporaryWorkdir 
from util.notes import check_is_note 

class AutoToolsCheck(Check):
    TYPE = 'autotools'

    def __init__(self, json):
        self.run_bins: List[str] = json.get('run-bins', [])
        self.configure_matrix: List[List[str]] = json.get('configure-matrix', [[]])
        super().__init__(json)

    def notes_str(self, config):
        return "./autogen.sh && ./configure " + ' '.join(config) + " && make -j8; " + " && ".join(self.run_bins)

    def run_cmd(self, cmd: List[str], workdir: str):
        log (' '.join(cmd))
        completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=workdir)
        if completed.returncode != 0:
            log ("Command failed: " + ' '.join(cmd))
            log (completed.stderr.decode("ascii"))
            completed.check_returncode() # trigger an exception

    def real_run(self, executor, config: List[str], commit: str, note: str):
        with TemporaryWorkdir(commit) as workdir:
            self.run_cmd(["./autogen.sh"], workdir)
            self.run_cmd(["./configure"] + config, workdir)
            self.run_cmd(["make", "-j8"], workdir)

            futs = []
            for bin in self.run_bins:
                futs.append(executor.submit(lambda: self.run_cmd(bin.split(' '), workdir)))
            for fut in futures.as_completed(futs):
                pass
        return note

    def run(self, executor: futures.ThreadPoolExecutor, commit: str, notes: List[str]):
        futs = []
        for config in self.configure_matrix:
            note = self.notes_str(config)
            if check_is_note(note, '.', commit=commit, note_ref='check-commit'):
                log ("# already done " + note) # Note already inserted
            else:
                futs.append(executor.submit(lambda: self.real_run(executor, config, commit, note)))

        for fut in futures.as_completed(futs):
            notes += [fut.result()]




