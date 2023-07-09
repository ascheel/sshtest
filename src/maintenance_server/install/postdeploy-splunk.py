import urllib.request
import yaml
import os
import datetime
import hvac
import shutil


class Splunk:
    def __init__(self):
        self.settings_file = os.path.join(os.path.expanduser('~'), '.vault.yml')
        self.vault_config = yaml.load(open(self.settings_file, 'r').read(), Loader=yaml.CLoader)
        self.vault_path = 'acs_de/projects/maintenance'

        self.client = hvac.Client(
            self.vault_config['host'],
            namespace=self.vault_config['namespace']
        )
        self.client.auth.approle.login(
            self.vault_config['role-id'],
            self.vault_config['secret-id']
        )
        
        self.tmpdir = os.path.join(os.path.expanduser('~'), 'tmp')
        if not os.path.isdir(self.tmpdir):
            os.makedirs(self.tmpdir)

        self.destination_directory = os.path.join(
            os.path.expanduser('~'),
            'ansible',
            'playbooks',
            'splunk',
            'packages'
        )
        if not os.path.isdir(self.destination_directory):
            os.makedirs(self.destination_directory)
        
        self.package_map = {}

    def _get_secret(self, path):
        mount_point, path = path.split('/', 1)
        return self.client.kv.v2.read_secret_version(
            mount_point=mount_point,
            path=path,
            raise_on_deleted_version=True
        )['data']['data']

    def _reduce(self, _size, sizes=None):
        if not sizes:
            sizes = ("B", "KB", "MB", "GB", "TB", "PB")
        if _size < 1024:
            return f"{_size:,} {sizes[0]}"
        return self._reduce(round(_size / 1024, 2), sizes[1:])

    def get_urls(self):
        secret = self._get_secret(self.vault_path)
        for key, url in secret.items():
            if key.startswith('splunk/'):
                # Key format MUST be hubble/{os}
                _pkg = key.split('/')[1]
                yield (_pkg, url)

    def download(self):
        for _pkg, _url in self.get_urls():
            _filename = os.path.basename(_url)
            self.package_map[_pkg] = _filename
            print(f"Downloading {_filename}.", end="")
            dst_filename = os.path.join(self.destination_directory, _filename)
            if not os.path.isfile(dst_filename):
                part_filename = f"{dst_filename}.part"
                if not os.path.isdir(os.path.dirname(part_filename)):
                    os.makedirs(os.path.dirname(part_filename))
                _time_start = datetime.datetime.now()
                try:
                    urllib.request.urlretrieve(_url, part_filename)
                except urllib.error.HTTPError as e:
                    if e.code >= 400 and e.code < 500:
                        print(f"Unable to download Splunk Forwarder for {_pkg}")
                    continue
                _time_end = datetime.datetime.now()
                shutil.move(part_filename, dst_filename)
                _size = os.stat(dst_filename).st_size
                _secs = (_time_end - _time_start).seconds or 1
                _speed = self._reduce(_size // _secs)
                print(f"Download speed: {_speed}ps.  ", end="")
            else:
                print("Exists.", end="")
            print()
    
    def patch(self):
        print(f"Patching splunk playbook.")
        splunkdir = os.path.join(
            os.path.expanduser('~'),
            'ansible',
            'playbooks',
            'splunk'
        )
        src = os.path.join(splunkdir, 'splunk.yml.template')
        dst = os.path.join(splunkdir, 'splunk.yml')
        with open(src, 'r') as f_in, open(dst, 'w') as f_out:
            for line in f_in:
                for _pkg, _filename in self.package_map.items():
                    line = line.replace(f'%{_pkg}%', _filename)
                f_out.write(line)

def main():
    splunk = Splunk()
    splunk.download()
    splunk.patch()


if __name__ == "__main__":
    main()
