import urllib.request
import yaml
import os
import sys
import json
import hashlib
import datetime
import argparse
import hvac
import shlex
import tarfile
import requests


"""
The entire point of this script is that Hubble is stored within S3.  This means
that it goes over the S3 endpoint and does NOT egress through an Adobe-controlled
network.  Because of this, our network is not whitelisted.  We have to grab them
from Gauntlet because it's not behind an S3 endpoint and is whitelisted, already.
"""


class Hubble:
    def __init__(self, **kwargs):
        self.vault_path = 'acs_de/projects/maintenance'
        self.role_id    = os.environ.get('VAULT_ROLE_ID')
        self.secret_id  = os.environ.get('VAULT_ROLE_SECRET')
        self.host       = os.environ.get('VAULT_HOST')
        self.namespace  = 'dx_analytics'

        self.client = hvac.Client(self.host, namespace=self.namespace)
        self.client.auth.approle.login(role_id=self.role_id, secret_id=self.secret_id)

        self.destination = kwargs["destination"]
        if not self.destination:
            self.destination = os.environ.get('TMPDIR', '/tmp/downloads/hubble')
        if not self.destination.endswith('/hubble'):
            self.destination += '/hubble'

        self.playbook = 'files/home/ansible/playbooks/hubble/hubble.yml.template'

        self.map = {}

        self.tarball_name = None

        self.artifactory_username = os.environ['ARTIFACTORY_USERNAME']
        self.artifactory_password = os.environ['ARTIFACTORY_PASSWORD']
        self.artifactory_repo     = os.environ['ARTIFACTORY_GENERIC_REPO']

    def version(self):
        return open('version.txt', 'r').read().splitlines()[0]

    def _reduce(self, _size, sizes=None):
        if not sizes:
            sizes = ("B", "KB", "MB", "GB", "TB", "PB")
        if _size < 1024:
            return f"{_size:,} {sizes[0]}"
        return self._reduce(round(_size / 1024, 2), sizes[1:])

    def get_secret(self, vault_path):
        mount_point, path = vault_path.split('/', 1)
        return self.client.kv.v2.read_secret_version(mount_point=mount_point, path=path)['data']['data']

    def get_urls(self):
        mount_point, path = self.vault_path.split('/', 1)
        secret = self.client.kv.v2.read_secret_version(mount_point=mount_point, path=path)['data']['data']
        for key, url in secret.items():
            if key.startswith('hubble/'):
                # Key format MUST be hubble/{os}
                _os = key.split('/')[1]
                yield (_os, url)
    
    def download_al1(self, url, filename):
        auth = (self.artifactory_username, self.artifactory_password)
        with requests.get(url, auth=auth, stream=True) as r:
            r.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

    def download_single(self, _os, _url, long_filename):
        part_filename = f"{long_filename}.part"
        _time_start = datetime.datetime.now()
        try:
            if 'al1609' in long_filename:
                self.download_al1(_url, part_filename)
            else:
                urllib.request.urlretrieve(_url, part_filename)

        except urllib.error.HTTPError as e:
            if e.code >= 400 and e.code < 500:
                print(f"Unable to download Hubble for {_os}")
            return
        os.rename(part_filename, long_filename)
        _time_end = datetime.datetime.now()
        _size = os.stat(long_filename).st_size
        _secs = (_time_end - _time_start).seconds
        _speed = self._reduce(_size // _secs)
        return _speed
        

    def download(self):
        for _os, _url in self.get_urls():
            _filename = _url.split('?')[0].split('/')[-1]
            self.map[_os] = _filename

            print(f"Downloading {_filename}.  ", end="")
            sys.stdout.flush()
            if not os.path.isdir(self.destination):
                os.makedirs(self.destination)

            long_filename = os.path.join(self.destination, _filename)
            if not os.path.isfile(long_filename):
                _speed = self.download_single(_os, _url, long_filename)
                if _speed:
                    print(f'Download speed: {_speed}ps.  ', end="")
                else:
                    continue
            else:
                print("Exists.", end="")
            print()

    def patch(self):
        print(f"Patching hubble playbook.")
        dst = os.path.join(self.destination, 'hubble.yml')
        with open(self.playbook, 'r') as f_in, open(dst, 'w') as f_out:
            for line in f_in:
                for _os, _filename in self.map.items():
                    line = line.replace(f'%{_os}%', _filename)
                f_out.write(line)
    
    def package(self):
        self.tarball_name = os.path.join(os.path.dirname(self.destination), f'hubble.{self.version()}.tar.gz')
        if os.path.isfile(self.tarball_name):
            print(f"Tarball exists.")
        else:
            print(f"Creating tarball: {self.tarball_name}.  ", end="")
            with tarfile.open(self.tarball_name, 'x:gz') as tar:
                tar.add(self.destination, arcname=os.path.basename(self.destination))
            print("Done.")

    def upload(self):
        headers = {
            'Content-type': 'application/octet-stream'
        }
        print("Uploading to Artifactory.")
        url = f"https://artifactory-uw2.adobeitc.com/artifactory/{self.artifactory_repo}/hubble/{os.path.basename(self.tarball_name)}"
        response = requests.put(
            url,
            data=open(self.tarball_name, 'rb'),
            headers=headers,
            auth=(self.artifactory_username, self.artifactory_password)
        )
        if response.status_code >= 400 and response.status_code < 500:
            print("Failed to upload file.")
        else:
            data = json.loads(response.text)
            print(f"You can find your file at: {data['downloadUri']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-d',
        '--destination',
        help="Destination directory."
    )
    args = parser.parse_args()

    hubble = Hubble(destination=args.destination)
    hubble.download()
    hubble.patch()
    hubble.package()
    hubble.upload()


if __name__ == "__main__":
    main()
