
import os
import subprocess
import toml

from util import colors, now_str

class Cargo:
    def __init__(self, version=None, cwd=None, cwd_suffix=None):
        self.cwd = cwd
        self.version = version
        if cwd_suffix is not None:
            self.cwd += f"/{cwd_suffix}"
        self.cwd_suffix = cwd_suffix

        try:
            os.unlink(self.cwd + '/Cargo.lock')
        except:
            pass

        self.UPDATE = Command("update", cwd_suffix=cwd_suffix, short_ver_str=version)
        self.BUILD = Command("build", cwd_suffix=cwd_suffix, short_ver_str=version)
        self.TEST = Command("test", cwd_suffix=cwd_suffix, short_ver_str=version)
        self.RUN = Command("run", cwd_suffix=cwd_suffix, short_ver_str=version)

        self.init_commands = [ self.UPDATE ]
        if self.version < "1.31.0":
            self.init_commands.append(FixVersionCommand("cc", "1.0.41", cwd_suffix=cwd_suffix, short_ver_str=version))
            self.init_commands.append(FixVersionCommand("serde_json", "1.0.39", cwd_suffix=cwd_suffix, short_ver_str=version))
            self.init_commands.append(FixVersionCommand("serde_derive", "1.0.98", cwd_suffix=cwd_suffix, short_ver_str=version))

        self.initialized = False

    def initialize(self):
        if self.initialized:
            return
        self.initialized = True

        for command in self.init_commands:
            command.run(self)

    def build_command(self, features):
        ret = self.BUILD
        if features is not None:
            ret.args = [ f"--features={' '.join(features)}" ]
        return ret

    def test_command(self, features):
        ret = self.TEST
        if features is not None:
            ret.args = [ f"--features={' '.join(features)}" ]
        return ret

    def example_command(self, example_toml):
        ret = self.RUN
        ret.args = [ '--example', example_toml['name'] ]
        if 'required-features' in example_toml:
            ret.args += [ f"--features={' '.join(example_toml['required-features'])}" ]
        return ret

    def fuzz_command(self, test_case, iters=100000):
        return FuzzCommand(test_case, iters, cwd_suffix=cwd_suffix, short_ver_str=self.version)

    def toml(self):
        return toml.load(self.cwd + '/Cargo.toml')

class Command:
    def __init__(self, cmd, args=None, cwd_suffix=None, short_ver_str=None, allow_fail=False):
        self.cmd = cmd
        self.allow_fail = allow_fail 

        self.cwd_str = None
        if cwd_suffix is not None:
            self.cwd_str = f"cwd {cwd_suffix}"

        if short_ver_str is None:
            short_ver_str = "stable"

        self.short_ver_str = short_ver_str
        ver_str = subprocess.check_output(["cargo", "+" + short_ver_str, "-V"])
        self.full_ver_str = ver_str.decode('ascii').strip()

        ver_str = subprocess.check_output(["rustc", "+" + short_ver_str, "-V"])
        self.full_ver_str += ', ' + ver_str.decode('ascii').strip()

        if args is None:
            self.args = []
        else:
            self.args = args

    def args_str(self):
        if len(self.args) == 0:
            return ""
        else:
            spacer = "' '"
            return f"'{spacer.join(self.args)}'"

    def run_str(self):
        prefix = f"{colors.yellow('cargo')} +{colors.bold(self.short_ver_str):15} {colors.green(self.cmd):15} {self.args_str():40}"
        prefix += f" # {now_str()}"
        if self.cwd_str is not None:
            prefix += f" / {self.cwd_str}"
        prefix += f" / {self.full_ver_str}"
        return prefix

    def notes_str(self):
        prefix = f"{self.full_ver_str} {self.cmd}"
        if len(self.args) > 0:
            prefix += " " + self.args_str()
        if self.cwd_str is not None:
            prefix += " # " + self.cwd_str
        return prefix

    def run(self, cargo, env=None):
        cargo.initialize()
        cmd = [ "cargo", "+" + self.short_ver_str, self.cmd ]
        for arg in self.args:
            cmd.append(arg)

        print(self.run_str())
        completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cargo.cwd, env=env)
        if completed.returncode != 0:
            if self.allow_fail:
                print ("## (above command failed, continuing)")
            else:
                print ("Command failed:", ' '.join(cmd))
                print (completed.stderr.decode("ascii"))
                completed.check_returncode() # trigger an exception

        return completed.stdout.decode("ascii")


class FixVersionCommand(Command):
    def __init__(self, package, version, cwd_suffix=None, short_ver_str=None):
        super().__init__("update", ["-p", package, "--precise", version], cwd_suffix, short_ver_str, allow_fail=True)

class FuzzCommand(Command):
    def __init__(self, test_case, iters, cwd_suffix=None, short_ver_str=None):
        super().__init__("hfuzz", ["run", test_case], cwd_suffix, short_version_str)
        self.iters = iters

    def run(self, cargo, env=None):
        if env is None:
            env = os.environ.copy()
        else:
            env |= os.environ.copy()

        env['HFUZZ_BUILD_ARGS'] = '--features honggfuzz_fuzz'
        env['HFUZZ_RUN_ARGS'] = '--exit_upon_crash -v -N' + str(self.iters)
        super().run(cargo, env=env)

    def notes_str(self):
        return f"{self.full_ver_str}) cargo hfuzz run {self.args[1]} # iters {self.iters}, {self.cwd_str}"

    def run_str(self):
        # append after date comment
        return super().run_str() + " HFUZZ_BUILD_ARGS='--features honggfuzz_fuzz' HFUZZ_RUN_ARGS=-N" + str(self.iters) 

