#!/bin/python

from concurrent import futures
import subprocess
from typing import List

from checks import Check
from util import colors, now_str
from util.git import TemporaryWorkdir 
from util.notes import update_notes

class WasmPackCheck(Check):
    TYPE = 'wasm-pack'

    def __init__(self, json):
        super().__init__(json)
        self.features = json.get('features')

        ver_str = subprocess.check_output(["wasm-pack", "--version"])
        self.full_ver_str = ver_str.decode('ascii').strip()

    def notes_str(self, features):
        prefix = f"{self.full_ver_str}"
        if features is not None:
            prefix += f" --features=\"{' '.join(features)}\""
        return prefix

    def run_str(self, features):
        prefix = f"{colors.yellow('wasm-pack')} test --node"
        if features is not None:
            prefix += f" --features=\"{' '.join(features)}\""
        prefix += f" # {now_str()} / {self.full_ver_str}"
        return prefix

    def run(self, executor: futures.ThreadPoolExecutor, commit: str, notes: List[str]):
        with TemporaryWorkdir(commit) as workdir:
            def real_run(features):
                cmd = ['wasm-pack', 'test', '--node' ]
                if features is not None:
                    cmd += [ '--', f"--features={' '.join(features)}"]

                print(self.run_str(features))
                completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=workdir)
                if completed.returncode != 0:
                    print ("Command failed:", ' '.join(cmd))
                    print (completed.stderr.decode("ascii"))
                    completed.check_returncode() # trigger an exception

            update_notes(notes, self.notes_str(None), lambda: real_run(None), workdir=workdir, note_ref='check-commit')
            if self.features is not None:
                update_notes(notes, self.notes_str(self.features), lambda: real_run(self.features), workdir=workdir, note_ref='check-commit')
                for feature in self.features:
                    update_notes(notes, self.notes_str([feature]), lambda: real_run([feature]), workdir=workdir, note_ref='check-commit')

