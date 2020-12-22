#!/bin/python

import glob
import toml
from typing import List, Optional

from checks import Check
from util.cargo import Cargo, Command
from util.notes import update_notes

class RustChecks(Check):
    TYPE = 'rust'

    def __init__(self, json):
        super().__init__(json)
        version = json.get('version', 'stable')
        if isinstance(version, list):
            self.checks = [RustCheck(v, json) for v in version]
            if json.get('try_fuzz_target'):
                self.checks += [RustCheck(v, json, fuzz_target=True) for v in version]
        else:
            if json.get('try_fuzz_target'):
                self.checks = [RustCheck(version, json, fuzz_target=True)]
            self.checks = [RustCheck(version, json)]

    def run(self, workdir, notes):
        for check in self.checks:
            check.run(workdir, notes)

class RustCheck(Check):
    TYPE = None

    def __init__(self, version, json, fuzz_target=False):
        super().__init__(json)
        self.version: str = version
        self.fuzz_target: bool = fuzz_target
        self.jobs: List[str] = json.get('jobs', ['build', 'test', 'examples'])
        self.fuzz_dir: str = json.get('fuzz_dir', 'fuzz/fuzz_targets')
        self.fuzz_iters: int = json.get('fuzz_iters', 1000000)
        self.features: Optional[List[str]] = json.get('features')
        self.workdir_suffix: Optional[str] = json.get('working-dir')

    def run(self, workdir: str, notes: List[str]):
        def run_cargo_cmd(cmd: Command, workdir: str, notes: List[str]):
            notes_str: str = cmd.notes_str()
            if self.workdir_suffix is not None:
                notes_str += ' # /' + self.workdir_suffix
            update_notes(notes, cmd.notes_str(), lambda: cmd.run(), workdir=workdir, note_ref='check-commit')

        if self.jobs != ['fuzz']:
            cargo = Cargo(cwd=workdir, cwd_suffix=self.workdir_suffix, version=self.version, fuzz_target=self.fuzz_target)
        if 'fuzz' in self.jobs:
            cwd_suffix: str = ''
            if self.workdir_suffix is not None:
                cwd_suffix = self.workdir_suffix
            cwd_suffix += '/' + self.fuzz_dir
            fuzz_cargo = Cargo(cwd=workdir, cwd_suffix=cwd_suffix, version=self.version, fuzz_target=True)

        # Run jobs
        for job in self.jobs:
            if job == 'build':
                run_cargo_cmd(cargo.BUILD, workdir, notes)
                if self.features is not None:
                    run_cargo_cmd(cargo.build_command(self.features), workdir, notes)
                    if len(self.features) > 1:
                        for feature in self.features:
                            run_cargo_cmd(cargo.build_command([feature]), workdir, notes)
            elif job == 'test':
                run_cargo_cmd(cargo.TEST, workdir, notes)
                if self.features is not None:
                    run_cargo_cmd(cargo.test_command(self.features), workdir, notes)
                    if len(self.features) > 1:
                        for feature in self.features:
                            run_cargo_cmd(cargo.test_command([feature]), workdir, notes)
            elif job == 'examples':
                examples = cargo.toml().get('example')
                if examples is not None:
                    for example in examples:
                        run_cargo_cmd(cargo.example_command(example), workdir, notes)
            elif job == 'fuzz':
                tests = glob.glob(workdir + '/*.rs')
                for test in tests:
                    test = test.split('/')[-1][:-3] # strip .rs
                    command = fuzz_cargo.fuzz_command(test, self.fuzz_iters)
                    run_cargo_cmd(command, workdir, notes)


