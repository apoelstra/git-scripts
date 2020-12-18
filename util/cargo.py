
import os
import subprocess
import time

from util import colors

def now_str():
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())

class Cargo:
    def __init__(self, version = "", cwd = None):
        self.cwd = cwd
        if version == "":
            self.version = "stable"
        else:
            self.version = version
        self.ver_string = self.run_cmd("-V").strip()

        try:
            os.unlink(self.cwd + '/Cargo.lock')
        except:
            pass
        self.run_cmd("generate-lockfile")
        self.run_cmd("update")
        if self.ver_string < "cargo 1.31.0":
            self.fix_version("cc", "1.0.41")
            self.fix_version("serde_json", "1.0.39")
            self.fix_version("serde_derive", "1.0.98")

    def run_cmd(self, *args, env=None):
        cmd = [ "cargo", "+" + str(self.version) ]
        for arg in args:
            cmd.append(arg)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=self.cwd, env=env)
        out, err = proc.communicate()
        rv = proc.poll()
        if rv:
            print ("Unexpected return value %d from cargo " % rv, args)
            print (err.decode("ascii"))
            raise subprocess.CalledProcessError(rv, "cargo", err)

        return out.decode("ascii")

    def version_str(self):
        return self.ver_string
        
    def fix_version(self, package, ver):
        print(f"{now_str()} {colors.bold(self.version_str())}: {colors.green('fixing')} {colors.yellow(package)} to {colors.yellow(ver)}")
        try:
            self.run_cmd("update", "-p", package, "--precise", ver)
        except: # not all packages used by all repos
            pass
        return f"{self.version_str()} fix {package} to {ver}"

    def build(self):
        print (f"{now_str()} {colors.green('Building')} with {colors.bold(self.version_str())}")
        self.run_cmd("build")
        return self.version_str() + " build"
        
    def test(self):
        print (f"{now_str()} {colors.green('Testing')} with {colors.bold(self.version_str())}")
        self.run_cmd("test")
        return self.version_str() + " test"

    def fuzz(self, test_case, iters=100000):
        print (f"{now_str()} {colors.green('Fuzzing')} {colors.bold(test_case)} with {colors.bold(str(iters))} iters with {colors.bold(self.version_str())}")
        env = os.environ.copy()
        env['HFUZZ_BUILD_ARGS'] = '--features honggfuzz_fuzz'
        env['HFUZZ_RUN_ARGS'] = '--exit_upon_crash -v -N' + str(iters)
        self.run_cmd("hfuzz", "run", test_case, env=env)
        return f"{self.version_str()} fuzz {test_case} ({iters} iters)"

