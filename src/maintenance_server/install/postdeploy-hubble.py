#!/usr/bin/env python3

import yaml
import os
import hvac
import requests
import tarfile
import shutil


class Hubble:
    def __init__(self, **kwargs):
        self.tmpdir = os.path.join(os.path.expanduser('~'), 'tmp')
        if not os.path.isdir(self.tmpdir):
            os.makedirs(self.tmpdir)

        self.os_map = {
            'amazon_linux_1': 'amazon_linux',
            'amazon_linux_2': 'centos7:amazon_linux_2'
        }
        self.settings_file = os.path.join(os.path.expanduser('~'), '.vault.yml')
        self.vault_config = yaml.load(open(self.settings_file, 'r').read(), Loader=yaml.CLoader)
        self.vault_path = 'acs_de/cicd/artifactory'

        self.client = hvac.Client(
            self.vault_config['host'],
            namespace=self.vault_config['namespace']
        )
        self.client.auth.approle.login(
            self.vault_config['role-id'],
            self.vault_config['secret-id']
        )

        secret = self._get_secret(self.vault_path)
        self.artifactory_username = secret['release/username']
        self.artifactory_password = secret['release/password']
        self.artifactory_generic_repo = secret['release/generic/repo']
        self.artifactory_hubble_url = f'https://artifactory-uw2.adobeitc.com/artifactory/{self.artifactory_generic_repo}/hubble/hubble.{self.version()}.tar.gz'
        self.tarball_filename = os.path.join(self.tmpdir, os.path.basename(self.artifactory_hubble_url))

    def _get_secret(self, path):
        mount_point, path = path.split('/', 1)
        return self.client.kv.v2.read_secret_version(
            mount_point=mount_point,
            path=path,
            raise_on_deleted_version=True
        )['data']['data']

    def version(self):
        return open(os.path.join(os.path.expanduser('~'), 'maintenance_server_source', 'version.txt'), 'r').read().splitlines()[0]

    def download(self):
        auth = (self.artifactory_username, self.artifactory_password)
        with requests.get(self.artifactory_hubble_url, auth=auth, stream=True) as r:
            r.raise_for_status()
            with open(self.tarball_filename, 'wb') as f_out:
                for chunk in r.iter_content(chunk_size=8192):
                    f_out.write(chunk)
    
    def extract(self):
        with tarfile.open(self.tarball_filename, 'r:gz') as f_in:
            f_in.extractall(path=self.tmpdir)
    
    def move(self):
        src = os.path.join(self.tmpdir, 'hubble')
        for _file in os.listdir(src):
            filename = os.path.join(src, _file)
            if _file == 'hubble.yml':
                dst = os.path.join(
                    os.path.expanduser('~'),
                    'ansible',
                    'playbooks',
                    'hubble',
                    _file
                )
                shutil.move(filename, dst)
            elif _file.endswith('.rpm'):
                dst = os.path.join(
                    os.path.expanduser('~'),
                    'ansible',
                    'playbooks',
                    'hubble',
                    'packages',
                    _file
                )
                if not os.path.isdir(os.path.dirname(dst)):
                    os.makedirs(os.path.dirname(dst))
                shutil.move(filename, dst)

def main():
    hubble = Hubble()
    hubble.download()
    hubble.extract()
    hubble.move()


if __name__ == "__main__":
    main()
