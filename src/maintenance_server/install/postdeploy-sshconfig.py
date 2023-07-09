#!/usr/bin/env python3

import os
import re
import datetime
import yaml
import shutil


class SSH:
    def __init__(self):
        self.source = os.path.splitext(os.path.abspath(__file__))[0] + '.yml'
        self.file = os.path.join(os.path.expanduser('~'), '.ssh', 'config')
    
    def host_in_config(self, hosts):
        if not os.path.isfile(self.file):
            return False
        if isinstance(hosts, str):
            hosts = [hosts,]
        contents = open(self.file, 'r').read()
        for host in hosts:
            _host = re.escape(host)
            pattern = r"^[ \t]*Host\s+([a-zA-Z0-9\.]+\s+)*" + _host + r"([a-zA-Z0-9\.]+\s+)*$"
                
            for line in contents.splitlines():
                if re.search(pattern, line):
                    return True
        return False

    def populate_output(self):
        if not os.path.isfile(self.file):
            return []
        return open(self.file, 'r').read().splitlines()

    def write(self):
        hosts = yaml.load(open(self.source, 'r').read(), Loader=yaml.CLoader)['hosts']
        _output = self.populate_output()
        changes = False
        for host in hosts:
            if isinstance(host['Host'], str):
                host['Host'] = [host['Host'],]
            print(f"Checking Host {host['Host']}")

            if self.host_in_config(host['Host']):
                print(f"Host {' '.join(host['Host'])} already in file")
                continue
            changes = True
            for key, value in host.items():
                if key == 'Host':
                    _output.append(f'{key} {" ".join(value)}')
                else:
                    _output.append(f'\t{key} {value}')
            _output.append('')
        if changes:
            _tmp_file = '/tmp/ssh_config'
            open(_tmp_file, 'w').write('\n'.join(_output))
            _backup_file = self.file + f'.{datetime.datetime.now().strftime("%y%m%d_%H%M")}'
            if os.path.isfile(self.file):
                shutil.move(self.file, _backup_file)
            shutil.move(_tmp_file, self.file)
            print(f"Added host(s) to {self.file}")

    
def main():
    ssh = SSH()
    ssh.write()


if __name__ == "__main__":
    main()

