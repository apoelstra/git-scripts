
import os
import subprocess
import toml
from typing import Any, Dict, List, MutableMapping, Optional

from util import colors, now_str

class Cargo:
    def __init__(self, version: Optional[str] = None, cwd: str = '.', cwd_suffix: Optional[str] = None, fuzz_target: bool = False):
        self.cwd: str = cwd
        self.version: str = version or 'stable'
        if cwd_suffix is not None:
            self.cwd += f"/{cwd_suffix}"
        self.cwd_suffix: Optional[str] = cwd_suffix
        self.fuzz_target: bool = fuzz_target

        ver_str: bytes = subprocess.check_output(["cargo", "+" + self.version, "-V"])
        self.full_ver_str: str = ver_str.decode('ascii').strip()

        try:
            os.unlink(self.cwd + '/Cargo.lock')
        except:
            pass

        self.UPDATE: Command = Command("update", self)
        self.BUILD: Command = Command("build", self)
        self.TEST: Command = Command("test", self)
        self.RUN: Command = Command("run", self)

        self.init_commands: List[Command] = [ self.UPDATE ]
        if self.version < "1.31.0":
            self.init_commands.append(FixVersionCommand("cc", "1.0.41", self))
            self.init_commands.append(FixVersionCommand("serde_json", "1.0.39", self))
            self.init_commands.append(FixVersionCommand("serde", "1.0.98", self))
            self.init_commands.append(FixVersionCommand("serde_derive", "1.0.98", self))

        self.initialized: bool = False

    def initialize(self) -> None:
        if self.initialized:
            return
        self.initialized = True

        for command in self.init_commands:
            command.run()

    def build_command(self, features: Optional[List[str]]):
        ret = self.BUILD
        if features is not None:
            ret.args = [ f"--features={' '.join(features)}" ]
        return ret

    def test_command(self, features: Optional[List[str]]):
        ret = self.TEST
        if features is not None:
            ret.args = [ f"--features={' '.join(features)}" ]
        return ret

    def example_command(self, example_toml: Dict[str, str]):
        ret = self.RUN
        ret.args = [ '--example', example_toml['name'] ]
        if 'required-features' in example_toml:
            ret.args += [ f"--features={' '.join(example_toml['required-features'])}" ]
        return ret

    def fuzz_command(self, test_case: str, iters: int = 100000):
        return FuzzCommand(test_case, iters, self)

    def toml(self) -> MutableMapping[str, Any]:
        return toml.load(self.cwd + '/Cargo.toml')

class Command:
    def __init__(self, cmd: str, cargo: Cargo, args=None, allow_fail=False):
        self.cmd: str = cmd
        self.cargo: Cargo = cargo
        self.allow_fail: bool = allow_fail

        if args is None:
            self.args = []
        else:
            self.args = args

    def args_str(self) -> str:
        if len(self.args) == 0:
            return ""
        else:
            spacer = "' '"
            return f"'{spacer.join(self.args)}'"

    def run_str(self) -> str:
        prefix = f"{colors.yellow('cargo')} +{colors.bold(self.cargo.version):15} {colors.green(self.cmd):15} {self.args_str():40}"
        prefix += f" # {now_str()}"
        if self.cargo.fuzz_target:
            prefix += " RUSTFLAGS='--cfg=rust_secp_fuzz'"
        if self.cargo.cwd_suffix is not None:
            prefix += f" / {self.cargo.cwd_suffix}"
        prefix += f" / {self.cargo.full_ver_str}"
        return prefix

    def notes_str(self) -> str:
        prefix = f"{self.cargo.full_ver_str} {self.cmd}"
        if len(self.args) > 0:
            prefix += " " + self.args_str()
        if self.cargo.cwd_suffix is not None:
            prefix += " # " + self.cargo.cwd_suffix
        if self.cargo.fuzz_target:
            prefix += "# '--cfg=rust_secp_fuzz'"
        return prefix

    def run(self, env: Optional[Dict[str, str]]=None) -> str:
        if env is None:
            env = os.environ.copy()
        else:
            env.update(os.environ)

        if self.cargo.fuzz_target:
            env['RUSTFLAGS'] = (env.get('RUSTFLAGS') or '') + '--cfg=rust_secp_fuzz'

        self.cargo.initialize()
        cmd = [ "cargo", "+" + self.cargo.version, self.cmd ]
        for arg in self.args:
            cmd.append(arg)

        print(self.run_str())
        completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.cargo.cwd, env=env)
        if completed.returncode != 0:
            if self.allow_fail:
                print ("## (above command failed, continuing)")
            else:
                print ("Command failed:", ' '.join(cmd))
                print (completed.stderr.decode("ascii"))
                completed.check_returncode() # trigger an exception

        return completed.stdout.decode("ascii")


class FixVersionCommand(Command):
    def __init__(self, package: str, version: str, cargo: Cargo):
        super().__init__("update", cargo, args=["-p", package, "--precise", version], allow_fail=True)

class FuzzCommand(Command):
    def __init__(self, test_case: str, iters: int, cargo: Cargo):
        super().__init__("hfuzz", cargo, args=["run", test_case])
        self.iters = iters

    def run(self, env=None):
        if env is None:
            env = os.environ.copy()
        else:
            env |= os.environ.copy()

        env['HFUZZ_BUILD_ARGS'] = '--features honggfuzz_fuzz'
        env['HFUZZ_RUN_ARGS'] = '--exit_upon_crash -v -N' + str(self.iters)
        super().run(env=env)

    def notes_str(self):
        prefix = f"{self.full_ver_str}) cargo hfuzz run {self.args[1]} # iters {self.iters}"
        if self.cargo.cwd_suffix is not None:
            prefix += ", cwd {self.cargo.cwd_suffix}"
        return prefix

    def run_str(self):
        # append after date comment
        return super().run_str() + " HFUZZ_BUILD_ARGS='--features honggfuzz_fuzz' HFUZZ_RUN_ARGS=-N" + str(self.iters)

