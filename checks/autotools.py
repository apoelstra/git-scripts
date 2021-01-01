#!/bin/python

import subprocess
from typing import Any, Dict, List, MutableMapping, Optional

from checks import Check
from util.cargo import Cargo, Command
from util.notes import update_notes

class AutoToolsCheck(Check):
    TYPE = 'autotools'

    def __init__(self, json):
        self.run_bins: List[str] = json.get('run-bins', [])
        self.configure_matrix: List[str] = json.get('configure-matrix', [[]])
        super().__init__(json)

    def notes_str(self, config):
        return "./autogen.sh && ./configure " + ' '.join(config) + " && make -j8; " + " && ".join(self.run_bins)

    def run_cmd(self, cmd: List[str], workdir: str, notes: List[str]):
        print (' '.join(cmd))
        completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=workdir)
        if completed.returncode != 0:
            print ("Command failed:", ' '.join(cmd))
            print (completed.stderr.decode("ascii"))
            completed.check_returncode() # trigger an exception

    def real_run(self, config: List[str], workdir: str, notes: List[str]):
        self.run_cmd(["./autogen.sh"], workdir, notes)
        self.run_cmd(["./configure"] + config, workdir, notes)
        self.run_cmd(["make", "-j8"], workdir, notes)
        for bin in self.run_bins:
            self.run_cmd(bin.split(' '), workdir, notes)

    def run(self, workdir: str, notes: List[str]):
        for config in self.configure_matrix:
            update_notes(notes, self.notes_str(config), lambda: self.real_run(config, workdir, notes), workdir=workdir, note_ref='check-commit')




