
import os
import subprocess
import time

from util import colors

def now_str():
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())

class Cargo:
    def __init__(self, version=None, cwd = None):
        self.cwd = cwd
        self.version = version

        try:
            os.unlink(self.cwd + '/Cargo.lock')
        except:
            pass

        self.UPDATE = Command("update", short_ver_str=version)
        self.BUILD = Command("build", short_ver_str=version)
        self.TEST = Command("test", short_ver_str=version)

        self.UPDATE.run(self)
        if version < "1.31.0":
            FixVersionCommand("cc", "1.0.41", short_ver_str=version).run(self)
            FixVersionCommand("serde_json", "1.0.39", short_ver_str=version).run(self)
            FixVersionCommand("serde_derive", "1.0.98", short_ver_str=version).run(self)


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

    def fuzz_command(self, test_case, iters=100000):
        return FuzzCommand(test_case, iters, short_ver_str=self.version)

class Command:
    def __init__(self, cmd, args=None, short_ver_str=None, allow_fail=False):
        self.cmd = cmd
        self.allow_fail = allow_fail 

        if short_ver_str is None:
            short_ver_str = "stable"

        self.short_ver_str = short_ver_str
        ver_str = subprocess.check_output(["cargo", "+" + short_ver_str, "-V"])
        self.full_ver_str = ver_str.decode('ascii').strip()

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
        return f"{colors.yellow('cargo')} +{colors.bold(self.short_ver_str):15} {colors.green(self.cmd):15} {self.args_str():40} # {now_str()}"

    def notes_str(self):
        if len(self.args) == 0:
            return f"{self.full_ver_str} {self.cmd}"
        else:
            return f"{self.full_ver_str} {self.cmd} {self.args_str()}"

    def run(self, cargo, env=None):
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
    def __init__(self, package, version, short_ver_str=None):
        super().__init__("update", ["-p", package, "--precise", version], short_ver_str, allow_fail=True)

class FuzzCommand(Command):
    def __init__(self, test_case, iters, short_ver_str=None):
        super().__init__("hfuzz", ["run", test_case], short_ver_str)
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
        return f"{self.full_ver_str}) cargo hfuzz run {self.args[1]} # iters {self.iters}"

    def run_str(self):
        # append after date comment
        return super().run_str() + " HFUZZ_BUILD_ARGS='--features honggfuzz_fuzz' HFUZZ_RUN_ARGS=-N" + str(self.iters) 

