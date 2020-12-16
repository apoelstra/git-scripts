
import subprocess

class Cargo:
    def __init__(self, version = ""):
        if version == "":
            self.version = "stable"
        else:
            self.version = version

    def run_cmd(self, *args):
        cmd = [ "cargo", "+" + self.version ]
        if args is not None:
            cmd.append(*args)
        rv = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = rv.communicate()
        if err:
            raise subprocess.CalledProcessError(rv, "cargo", err)

        return out.decode("ascii")

    def version_str(self):
        return self.run_cmd("-V")
        
    def build(self):
        return self.run_cmd("build")
        
    def test(self):
        return self.run_cmd("test")


