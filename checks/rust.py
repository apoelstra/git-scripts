#!/bin/python

import glob

from checks import Check
from util.cargo import Cargo
from util.notes import update_notes

class RustCheck(Check):
    TYPE = 'rust'

    def __init__(self, json):
        super().__init__(json)
        self.version = json.get('version', 'stable')
        self.jobs = json.get('jobs', ['build', 'test'])
        self.fuzz_dir = json.get('fuzz_dir', 'fuzz/fuzz_targets')
        self.fuzz_iters = json.get('fuzz_iters', 1000000)
        self.features = json.get('features')

    def run(self, workdir, notes):
        def run_cargo_cmd(cargo, cmd, workdir, notes):
            notes_str = cmd.notes_str()
            update_notes(notes, cmd.notes_str(), lambda: cmd.run(cargo), workdir=workdir, note_ref='check-commit')

        if 'build' in self.jobs or 'test' in self.jobs:
            cargo = Cargo(cwd=workdir, version=self.version)
        if 'fuzz' in self.jobs:
            workdir += '/' + self.fuzz_dir
            fuzz_cargo = Cargo(cwd=workdir, version=self.version)

        for job in self.jobs:
            if job == 'build':
                run_cargo_cmd(cargo, cargo.BUILD, workdir, notes)
                if self.features is not None:
                    run_cargo_cmd(cargo, cargo.build_command(self.features), workdir, notes)
                    if len(self.features) > 1:
                        for feature in self.features:
                            run_cargo_cmd(cargo, cargo.build_command([feature]), workdir, notes)
            elif job == 'test':
                run_cargo_cmd(cargo, cargo.TEST, workdir, notes)
                if self.features is not None:
                    run_cargo_cmd(cargo, cargo.test_command(self.features), workdir, notes)
                    if len(self.features) > 1:
                        for feature in self.features:
                            run_cargo_cmd(cargo, cargo.test_command([feature]), workdir, notes)
            elif job == 'fuzz':
                tests = glob.glob(workdir + '/*.rs')
                for test in tests:
                    test = test.split('/')[-1][:-3] # strip .rs
                    command = fuzz_cargo.fuzz_command(test, self.fuzz_iters)
                    run_cargo_cmd(fuzz_cargo, command, workdir, notes)


