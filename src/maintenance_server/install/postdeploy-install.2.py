#!/usr/bin/env python3

import os
import sys
import yaml
import hvac
import subprocess
import shlex
from git import Repo
import shutil
import re
import collections.abc
import stat
import hashlib


class Install:
    def __init__(self):
        # maintenance settings
        self.homedir        = os.path.expanduser('~')
        self.repodir        = os.path.join(self.homedir, 'maintenance_server_source')
        self.settings_file  = os.path.join(self.homedir, 'de.yml')
        self.settings_base  = os.path.join(self.repodir, 'files', 'home', 'de.yml')
        self.vault_config   = os.path.join(self.homedir, '.vault.yml')
        self.vault_settings = None
        self.vault_client   = None
        self.settings       = self.get_settings()

        # git settings    
        self.sshdir                 = os.path.join(self.homedir, '.ssh')
        self.git_ssh_keyfile        = os.path.join(self.sshdir, 'id_rsa_adobegit')
        self.git_key_vault_location = 'vault::acs_de/cicd/git::ssh/key'
        self.git_host               = 'gitcorp.adobe.net'
        self.git_repo               = f'{self.git_host}:es/maintenance_server' # gitcorp translates to git.corp.adobe.com

        # ssh
        self.ssh_vault_path = 'vault::acs_de/ssh'
        self.ssh_configfile  = os.path.join(self.sshdir, 'config')
    
        # aws
        self.aws_creds_file          = os.path.join(self.homedir, '.aws', 'credentials')
        self.aws_creds_vault_path    = 'vault::acs_de/service-accounts/aws'

        # vault backup
        self.backup_password_path = 'vault::acs_de/projects/maintenance::backup_encryption_key'

        # artifactory
        self.artifactory_key_path = 'vault::acs_de/cicd/artifactory::adobeea/artifactory api key'
        self.pypi_index           = 'artifactory-uw2.adobeitc.com/artifactory/api/pypi/pypi-adobe-acs-release/simple'

        # Installation
        self.script                = os.path.abspath(__file__)
        self.scriptdir             = os.path.dirname(self.script)
        self.install_settings_file = f"{os.path.splitext(self.script)[0]}.yml"
        self.install_settings      = yaml.load(open(self.install_settings_file, 'r').read(), Loader=yaml.CLoader)

    def get_vault_secret(self, secret_path):
        if not secret_path.startswith('vault::'):
            raise ValueError("Vault path must start with vault::")
        _key = None
        if '::' in secret_path.split('::', 1)[1]:
            _, _path, _key = secret_path.split("::")
        else:
            _, _path = secret_path.split('::')

        _mount_point, _path = _path.split('/', 1)

        _secret = self.vault_client.kv.v2.read_secret_version(
            mount_point=_mount_point,
            path=_path,
            raise_on_deleted_version=True
        )
        if not _secret.get('data', {}).get('data'):
            raise ValueError(f"Could not retrieve secret: {self.git_key_vault_location}")
        if _key:
            value = _secret['data']['data'][_key]
        else:
            value = _secret['data']['data']
        return value

    def set_vault_client(self):
        print("Initializing Vault client.")
        _host      = self.vault_settings['host']
        _roleid    = self.vault_settings['role-id']
        _secretid  = self.vault_settings['secret-id']
        _namespace = self.vault_settings['namespace']
        self.vault_client = hvac.Client(_host, namespace=_namespace)
        self.vault_client.auth.approle.login(role_id=_roleid, secret_id=_secretid)
        print(f"Vault is authenticated: {self.vault_client.is_authenticated()}")

    def set_bashrcd(self):
        _dir = os.path.join(self.homedir, '.bashrc.d')
        if not os.path.exists(_dir):
            os.mkdir(_dir, 0o755)
        _exists = False
        with open(os.path.join(self.homedir, '.bashrc'), 'r') as f_in:
            for line in f_in:
                if 'bashrc.d' in line:
                    _exists = True
        if not _exists:
            with open(os.path.join(self.homedir, '.bashrc'), 'a') as f_out:
                output = [
                    'bashdir="${HOME}/.bashrc.d"',
                    'if [[ -d "$bashdir" ]]; then',
                    '\tfor file in "${bashdir}"/*; do',
                    '\t\t. "$file"',
                    '\tdone',
                    'fi'
                ]
                f_out.write('\n'.join(output))
                f_out.write('\n')

    def get_settings(self):
        if not os.path.exists(self.settings_file):
            print(f"Settings file does not exist.")
            return {}
        return yaml.safe_load(open(self.settings_file, 'r').read())

    def save_settings(self):
        open(self.settings_file, 'w').write(yaml.dump(self.settings, Dumper=yaml.CDumper))

    # git stuff
    def set_git_creds(self):
        if not os.path.isdir(self.sshdir):
            os.mkdir(self.sshdir, mode=0o700)
        if not os.path.exists(self.git_ssh_keyfile):
            _gitkey = self.get_vault_secret(self.git_key_vault_location)
            with open(self.git_ssh_keyfile, 'w') as f_out:
                f_out.write(_gitkey)
                f_out.write('\n')

            os.chmod(self.git_ssh_keyfile, 0o600)
        self.set_ssh_config()
    
    def ssh_has_git(self):
        with open(self.ssh_configfile, 'r') as f_in:
            for line in f_in:
                if self.git_host in line:
                    print("Git server already present in ~/.ssh/config")
                    return True
        print("Git server not present in ~/.ssh/config")
        return False

    def set_ssh_config(self):
        config_addition = [
            f'Host {self.git_host} git.corp.adobe.com',
            f'\tHostname {self.git_host}',
            '\tUser git',
            f'\tIdentityFile {self.git_ssh_keyfile}',
            '\n'
        ]
        if not os.path.exists(self.ssh_configfile):
            with open(self.ssh_configfile, 'w') as f_out:
                f_out.write('\n'.join(config_addition))
                if not self.ssh_has_git():
                    f_out.write('\n'.join(config_addition))
        
        os.chmod(self.ssh_configfile, 0o600)

    def set_vault_creds(self):
        print("Setting vault credentials.")
        if os.path.isfile(self.vault_config):
            self.vault_settings = yaml.load(open(self.vault_config, 'r').read(), Loader=yaml.CLoader)
        if not self.vault_settings:
            print("Settings not found.")
            self.vault_settings = {}
        if not self.vault_settings.get('role-id'):
            print("Role-ID not found.")
            print()
            print("For Data Engineering, get your credentials from:")
            print("    vault::acs_de/vault::prod/acs_de_approle_read/[role-id|secret-id]")
            print()
            self.vault_settings['role-id']   = input("Role-id:   ")
            self.vault_settings['secret-id'] = input("Secret-id: ")
            self.vault_settings['namespace'] = input("Enter Vault namespace [dx_analytics]: ")
            self.vault_settings['host']      = input("Enter Vault host [https://vault-amer.adobe.net]: ")

            if not self.vault_settings['namespace']:
                self.vault_settings['namespace'] = 'dx_analytics'
            if self.vault_settings['namespace'].lower() == "none":
                self.vault_settings['namespace'] = None
            if not self.vault_settings['host']:
                self.vault_settings['host'] = 'https://vault-amer.adobe.net'
            open(self.vault_config, 'w').write(yaml.dump(self.vault_settings, Dumper=yaml.CDumper))

    def git_ssh_fingerprint_exists(self):
        known_hosts_file = os.path.join(self.sshdir, 'known_hosts')
        if not os.path.exists(known_hosts_file):
            return False
        with open(known_hosts_file, 'r') as f_in:
            for line in f_in:
                if self.git_host in line:
                    return True
        return False

    def get_git_ssh_fingerprint(self):
        return self.exec(f"ssh-keyscan {self.git_host}").stdout.decode()

    def add_git_server_fingerprint(self):
        if self.git_ssh_fingerprint_exists():
            return
        fingerprint = self.get_git_ssh_fingerprint()
        open(os.path.join(self.sshdir, 'known_hosts'), 'a').write(fingerprint)

    # def get_git_repo(self):
    #     # First, delete old repo data.
    #     self.add_git_server_fingerprint()

    #     if os.path.isdir(self.repodir):
    #         print(f"Found directory: {self.repodir} - Deleting.")
    #         shutil.rmtree(self.repodir)
    #         print("Done.")

    #     print(f"Cloning repo: {self.git_repo}")
    #     repo = Repo.clone_from(
    #         self.git_repo,
    #         self.repodir,
    #         branch='dev'
    #     )
    #     print("Done.")
    #     self.get_settings()

    def set_ssh_keys(self):
        key_data   = self.get_vault_secret(self.ssh_vault_path)
        for key, data in key_data.items():
            if key.startswith('id_'):
                sshfile = os.path.join(self.sshdir, key)
                if os.path.exists(sshfile):
                    # Skip.  Assume the key on disk is good to go.
                    # print(f"Skipping ssh file: {sshfile} already exists.")
                    continue
                else:
                    print(f"Writing ssh file: {sshfile}")
                    open(sshfile, 'w').write(data)
                    os.chmod(sshfile, 0o600)

    def dict_update(self, dict1, dict2):
        for k, v in dict2.items():
            if isinstance(v, collections.abc.Mapping):
                dict1[k] = self.dict_update(dict1.get(k, {}), v)
            else:
                dict1[k] = v
        return dict1

    def merge_settings(self):
        self.dict_update(self.settings, yaml.safe_load(open(self.settings_base, 'r').read()))

    def set_aws_credentials(self):
        """
        Grabs data from vault and writes out aws credentials.  Account must
        exist in both vault and settings file.
        """
        cred_data = self.get_vault_secret(self.aws_creds_vault_path)
        settings = self.settings.copy()
        if not os.path.exists(os.path.split(self.aws_creds_file)[0]):
            os.mkdir(os.path.split(self.aws_creds_file)[0], mode=0o700)
        with open(self.aws_creds_file, 'w') as f_out:
            for account in settings['aws']['accounts']:
                pattern1 = re.compile(f'^{account}\/(ea|devops)-automation\/access_key$')
                pattern2 = re.compile(f'^{account}\/(ea|devops)-automation\/secret_key$')

                access = None
                secret = None
                for key, value in cred_data.items():
                    if pattern1.match(key):
                        access = value
                    elif pattern2.match(key):
                        secret = value
                self.settings['aws']['accounts'][account]['aws_access_key'] = access
                self.settings['aws']['accounts'][account]['aws_secret_key'] = secret
                f_out.write(f'[{account}]\n')
                f_out.write(f'aws_access_key_id = {access}\n')
                f_out.write(f'aws_secret_access_key = {secret}\n')
                f_out.write('\n')
        os.chmod(self.aws_creds_file, 0o600)

    def set_backup_encryption_key(self):
        self.settings['backup_encryption_key'] = self.get_vault_secret(self.backup_password_path)
    
    def set_artifactory_creds(self):
        username = 'adobeea'
        apikey   = self.get_vault_secret(self.artifactory_key_path)
        self.settings['artifactory'] = { 'username': username, 'apikey': apikey }

    def set_pip_conf(self):
        pipdir = os.path.join(self.homedir, '.pip')
        pipfile = os.path.join(pipdir, 'pip.conf')
        if not os.path.exists(pipdir):
            os.mkdir(pipdir, 0o700)
        with open(pipfile, 'w') as f_out:
            output = [
                '[global]',
                'index-url = https://pypi.python.org/simple',
                f'extra-index-url = https://{self.settings["artifactory"]["username"]}:{self.settings["artifactory"]["apikey"]}@{self.pypi_index}'
            ]
            f_out.write('\n'.join(output))
            f_out.write('\n')
        os.chmod(pipfile, 0o600)

    def move_ignored(self, path, ignore):
        for item in ignore:
            if path.startswith(item):
                return True
        return False

    def sha256sum_file(self, filename):
        if not os.path.isfile(filename):
            return None

        _BUFSIZE = 4096
        _hash = hashlib.sha256()
        with open(filename, 'rb') as f_in:
            while True:
                data = f_in.read(_BUFSIZE)
                if not data:
                    break
                _hash.update(data)
            return _hash.hexdigest()

    def sha256sum(self, data):
        return hashlib.sha256(data).digest()

    def files_match(self, file1, file2):
        return self.sha256sum_file(file1) == self.sha256sum_file(file2)

    def delete(self, name):
        # Can be directory or file
        name = name.replace('~', os.path.expanduser('~'))
        if os.path.exists(name):
            if os.path.isfile(name):
                print(f"    Deleting file: {name}")
                os.remove(name)
            elif os.path.isdir(name):
                print(f"    Deleting dir: {name}")
                shutil.rmtree(name)
                

    def create(self, name):
        name = name.replace('~', os.path.expanduser('~'))
        if os.path.exists(name):
            if not os.path.isdir(name):
                raise EnvironmentError("File exists and is not directory: {name}")
        else:
            os.makedirs(name)

    def move_files(self):
        for move in self.install_settings['install']['file-moves']:
            src = move['src']
            dst = move['dst'].replace('~', os.path.expanduser('~'))
            prod_only = move.get('prod_only', False)
            ignore = move.get('ignore', [])
            original_mode = None

            if prod_only and os.environ.get('ENVIRONMENT') != 'prod':
                continue
            if src == 'crontabs':
                # This is now handled in postdeploy-crontab.py
                continue

            # if src == 'crontabs':
            #     # Special actions for directories owned by root
            #     original_mode = stat.S_IMODE(os.stat(dst).st_mode)
            #     cmd = f"sudo chmod 777 {dst}"
            #     results = self.exec(cmd)

            srcdir = os.path.join(self.repodir, 'files', src)
            for _root, _dir, _files in os.walk(srcdir):
                for _file in _files:
                    long_source  = os.path.join(_root, _file)
                    short_source = long_source.replace(os.path.join(self.repodir, 'files', src), '')

                    # Ignore
                    if self.move_ignored(short_source, ignore):
                        continue

                    while short_source.startswith('/'):
                        short_source = short_source[1:]
                    full_destination = os.path.join(dst, short_source)
                    _dir = os.path.split(full_destination)[0]

                    if self.files_match(long_source, full_destination):
                        # print(f"Files match, do not copy: {short_source}")
                        continue

                    if not os.path.isdir(_dir):
                        print(f"Creating directory: {_dir}")
                        os.makedirs(_dir)
                    print(f"Copying: {short_source}")
                    # os.rename(long_source, full_destination)
                    shutil.copy2(long_source, full_destination)
            
            # if src == 'crontabs':
            #     cmd = f"sudo chmod {oct(original_mode)[2:]} {dst}"
            #     results = self.exec(cmd)

    def preinstall(self):
        # Delete:
        for item in self.install_settings['pre-install']['delete']:
            if item:
                self.delete(item)

        # Create
        for item in self.install_settings['pre-install']['create']:
            if item:
                self.create(item)

    def postinstall(self):
        # Delete:
        for item in self.install_settings['post-install']['delete']:
            if item:
                self.delete(item)

        # Create
        for item in self.install_settings['post-install']['create']:
            if item:
                self.create(item)

    def exec(self, cmd):
        cmd = shlex.split(cmd)
        proc = subprocess.run(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return proc

    def go(self):
        print("Initializing installation.")

        # Pre-install
        self.preinstall()

        # Setup
        self.set_bashrcd()
        self.set_vault_creds()
        self.set_vault_client()

        # Download
        # self.set_git_creds()
        # self.get_git_repo()

        # Credentials
        self.merge_settings()
        self.set_ssh_keys()
        self.set_aws_credentials()
        self.set_backup_encryption_key()
        self.set_artifactory_creds()
        
        # OS Config
        self.set_pip_conf()
        self.save_settings()

        # Move files into place
        self.move_files()

        # Post-install
        self.postinstall()


def main():
    install = Install()
    install.go()


if __name__ == "__main__":
    main()
