#!/bin/python

import glob
import toml
from concurrent import futures
from typing import List, Optional

from checks import Check
from util.cargo import Cargo, Command
from util.git import TemporaryWorkdir 
from util.notes import update_notes

class RustChecks(Check):
    TYPE = 'rust'

    def __init__(self, json):
        super().__init__(json)
        version = json.get('version', 'stable')
        force_default_features = json.get('force-default-features', False)
        if isinstance(version, list):
            self.checks = [RustCheck(v, json, force_default_features=force_default_features) for v in version]
            if json.get('try_fuzz_target'):
                self.checks += [RustCheck(v, json, fuzz_target=True, force_default_features=force_default_features) for v in version]
        else:
            if json.get('try_fuzz_target'):
                self.checks = [RustCheck(version, json, fuzz_target=True, force_default_features=force_default_features)]
            self.checks = [RustCheck(version, json, force_default_features=force_default_features)]

    def run(self, executor: futures.ThreadPoolExecutor, commit: str, notes: List[str]):
        futs = []
        for check in self.checks:
            futs.append(executor.submit(lambda: check.run_(executor, commit)))
        for fut in futures.as_completed(futs):
            notes += fut.result()

class RustCheck(Check):
    TYPE = None

    def __init__(self, version, json, fuzz_target=False, force_default_features=False):
        super().__init__(json)
        self.version: str = version
        self.fuzz_target: bool = fuzz_target
        self.force_default_features: bool = force_default_features
        self.jobs: List[str] = json.get('jobs', ['build', 'test', 'examples'])
        self.fuzz_dir: str = json.get('fuzz_dir', 'fuzz/fuzz_targets')
        self.fuzz_iters: int = json.get('fuzz_iters', 1000000)
        self.features: Optional[List[str]] = json.get('features')
        self.workdir_suffix: Optional[str] = json.get('working-dir')

    def run_(self, executor: futures.ThreadPoolExecutor, commit: str) -> List[str]:
        def run_cargo_cmd(cmd: Command, workdir: str) -> List[str]:
            notes: List[str] = []
            notes_str: str = cmd.notes_str()
            if self.workdir_suffix is not None:
                notes_str += ' # /' + self.workdir_suffix
            update_notes(notes, cmd.notes_str(), lambda: cmd.run(), workdir=workdir, note_ref='check-commit')
            return notes

        notes: List[str] = []
        with TemporaryWorkdir(commit) as workdir:
            if self.jobs != ['fuzz']:
                cargo = Cargo(cwd=workdir, cwd_suffix=self.workdir_suffix, version=self.version, fuzz_target=self.fuzz_target, force_default_features=self.force_default_features)
            if 'fuzz' in self.jobs:
                cwd_suffix: str = ''
                if self.workdir_suffix is not None:
                    cwd_suffix = self.workdir_suffix
                cwd_suffix += '/' + self.fuzz_dir
                fuzz_cargo = Cargo(cwd=workdir, cwd_suffix=cwd_suffix, version=self.version, fuzz_target=True, force_default_features=self.force_default_features)

            # Run jobs
            for job in self.jobs:
                if job == 'build':
                    notes += run_cargo_cmd(cargo.BUILD, workdir )
                    if self.features is not None:
                        notes += run_cargo_cmd(cargo.build_command(self.features), workdir)
                        if len(self.features) > 1:
                            for feature in self.features:
                                notes += run_cargo_cmd(cargo.build_command([feature]), workdir)
                elif job == 'test':
                    notes += run_cargo_cmd(cargo.TEST, workdir)
                    if self.features is not None:
                        notes += run_cargo_cmd(cargo.test_command(self.features), workdir)
                        if len(self.features) > 1:
                            for feature in self.features:
                                notes += run_cargo_cmd(cargo.test_command([feature]), workdir)
                elif job == 'examples':
                    examples = cargo.toml().get('example')
                    if examples is not None:
                        for example in examples:
                            notes += run_cargo_cmd(cargo.example_command(example), workdir)
                elif job == 'fuzz':
                    notes += run_cargo_cmd(fuzz_cargo.test_command(self.features), workdir)
                    tests = glob.glob(workdir + cwd_suffix + '/*.rs')
                    for test in tests:
                        test = test.split('/')[-1][:-3] # strip .rs
                        command = fuzz_cargo.fuzz_command(test, self.fuzz_iters)
                        notes += run_cargo_cmd(command, workdir)
        return notes


