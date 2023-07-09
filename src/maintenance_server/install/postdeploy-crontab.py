#!/usr/bin/env python3

import os
import sys


def check_root():
    if os.geteuid() != 0:
        print("This script must be executed as root.")
        sys.exit(1)


class Crontabs:
    def __init__(self):
        self.user = 'ec2-user'
        self.home = f'/home/{self.user}'
        self.src = os.path.join(
            self.home,
            'maintenance_server_source',
            'files',
            'crontabs'
        )
        self.dst = '/etc/cron.d'
        self.dev = os.environ.get('ENVIRONMENT') == "dev"

    def patch(self):
        for _file in os.listdir(self.src):
            src = os.path.join(self.src, _file)
            dst = os.path.join(self.dst, _file)
            with open(src, 'r') as f_in, open(dst, 'w') as f_out:
                for line in f_in:
                    line = line.replace('%user%', self.user)
                    line = line.replace('%home%', self.home)
                    if self.dev:
                        line = f"#dev# {line}"
                    f_out.write(line)


def main():
    check_root()
    
    crontabs = Crontabs()
    crontabs.patch()

if __name__ == '__main__':
    main()
