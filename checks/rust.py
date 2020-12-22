#!/bin/python

import glob
import toml

from checks import Check
from util.cargo import Cargo
from util.notes import update_notes

class RustChecks(Check):
    TYPE = 'rust'

    def __init__(self, json):
        super().__init__(json)
        version = json.get('version', 'stable')
        if isinstance(version, list):
            self.checks = [RustCheck(v, json) for v in version]
        else:
            self.checks = [RustCheck(version, json)]

    def run(self, workdir, notes):
        for check in self.checks:
            check.run(workdir, notes)

class RustCheck(Check):
    TYPE = None

    def __init__(self, version, json):
        super().__init__(json)
        self.version = version
        self.jobs = json.get('jobs', ['build', 'test', 'examples'])
        self.fuzz_dir = json.get('fuzz_dir', 'fuzz/fuzz_targets')
        self.fuzz_iters = json.get('fuzz_iters', 1000000)
        self.features = json.get('features')
        self.workdir_suffix = json.get('working-dir')

    def run(self, workdir, notes):
        def run_cargo_cmd(cargo, cmd, workdir, notes):
            notes_str = cmd.notes_str()
            if self.workdir_suffix is not None:
                notes_str += ' # /' + self.workdir_suffix
            update_notes(notes, cmd.notes_str(), lambda: cmd.run(cargo), workdir=workdir, note_ref='check-commit')

        if self.jobs != ['fuzz']:
            cargo = Cargo(cwd=workdir, cwd_suffix=self.workdir_suffix, version=self.version)
        if 'fuzz' in self.jobs:
            cwd_suffix = (self.workdir_suffix or '') + '/' + self.fuzz_dir
            fuzz_cargo = Cargo(cwd=workdir, cwd_suffix=cwd_suffix, version=self.version)

        # Run jobs
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
            elif job == 'examples':
                examples = cargo.toml().get('example')
                if examples is not None:
                    for example in examples:
                        run_cargo_cmd(cargo, cargo.example_command(example), workdir, notes)
            elif job == 'fuzz':
                tests = glob.glob(workdir + '/*.rs')
                for test in tests:
                    test = test.split('/')[-1][:-3] # strip .rs
                    command = fuzz_cargo.fuzz_command(test, self.fuzz_iters)
                    run_cargo_cmd(fuzz_cargo, command, workdir, notes)


