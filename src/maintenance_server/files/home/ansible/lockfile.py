import os
import sys
import argparse


class Lockfile:
    def __init__(self, lockname, lockpid=None):
        self.lockname = lockname
        self.lockfile = f'/tmp/{self.lockname}.lock'
        self.__pid = None
        if lockpid:
            self.__pid = lockpid

    def __enter__(self):
        self.create_lockfile()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if os.getpid() == self.pid and os.path.exists(self.lockfile):
            self.remove_lockfile()

    def _lockexists(self):
        return os.path.exists(self.lockfile)
    
    def create_lockfile(self):
        if self.__lockvalid():
            sys.exit(EnvironmentError("Lock file exists."))
        open(self.lockfile, 'w').write(self.pid)

    def remove_lockfile(self):
        os.remove(self.lockfile)

    @property
    def pid(self):
        if self.__pid:
            return self.__pid
        if not self._lockexists():
            return ""
        _pid = open(self.lockfile, 'r').read()
        if not _pid.isnumeric():
            raise ValueError(f"Contents of {self.lockfile} not a PID.")
        return _pid
    
    def stored_pid(self):
        return open(self.lockfile, 'r').read()

    def __lockvalid(self):
        if not self._lockexists():
            return False
        if not self.__processexists():
            os.remove(self.lockfile)
            return False
        # if not self.__ispython():
        #     os.remove(self.lockfile)
        #     return False
        return True
    
    def __processexists(self):
        _pidfile = f"/proc/{self.stored_pid()}/cmdline"

        if os.path.exists(_pidfile):
            return True
        return False

    def __ispython(self):
        _cmd = open(f'/proc/{self.pid}/cmdline', 'r').read().split('\x00')[0]
        if _cmd.split(os.sep)[-1] in ('python', 'python3'):
            return True
        return False

    @staticmethod
    def lock_exists(lockname):
        _lockfile = Lockfile(lockname)
        return _lockfile.__lockvalid()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "name",
        help="Name of the locked process."
    )
    parser.add_argument(
        "-c",
        "--check",
        help="Check if lock file exists.",
        action="store_true"
    )
    parser.add_argument(
        "-p",
        "--pid",
        help="Manually assign PID.",
        type=str
    )
    parser.add_argument(
        "-r",
        "--remove",
        help="Remove lockfile.",
        action="store_true"
    )
    args = parser.parse_args()
    _lockfile = None
    if args.pid:
        _lockfile = Lockfile(args.name, args.pid)
    else:
        _lockfile = Lockfile(args.name)
    if not args.check and not args.remove:
        _lockfile.create_lockfile()

    if args.check:
        return 1 if _lockfile.lock_exists() else 0

if __name__ == "__main__":
    main()

