import subprocess
import os
import sys
import shlex


class Java:
    def __init__(self):
        pass

    def exec(self, cmd):
        return subprocess.run(
            shlex.split(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    def installed(self):
        binary = "java"
        for _path in os.environ["PATH"].split(os.pathsep):
            _pathcheck = os.path.join(_path, binary)
            if os.path.isfile(_pathcheck) and os.access(_pathcheck, os.X_OK):
                return True
        return False
    
    def version(self):
        if not self.installed():
            return None
        cmd = "java -version"
        results = self.exec(cmd)
        import pdb; pdb.set_trace()


def main():
    java = Java()


if __name__ == "__main__":
    main()
