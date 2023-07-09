import base64
import requests
import json
import yaml
import os
import sys
import datetime
import tarfile
import shutil


class Create:
    def __init__(self):
        start_time = datetime.datetime.now()
        
        # self.tmpdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hardener_files")
        self.tmp    = "/tmp"
        self.tmpdir = os.path.join(self.tmp, "if_hardener")
        if not os.path.exists(self.tmpdir):
            os.makedirs(self.tmpdir)

        self.image_filename = os.path.join(self.tmpdir, "images.txt")

        self.script_file = os.path.join(self.tmp, "harden.py")
        self.script_template = "harden.template.py"

        _artifactory_creds = os.path.join(os.path.expanduser("~"), ".artifactory_creds.conf")
        self.artifactory_user = None
        self.artficatory_pass = None
        with open(_artifactory_creds, "r") as f_in:
            for line in f_in:
                if line.strip().split("=")[0].strip() == "login":
                    self.artifactory_user = line.strip().split("=")[1].strip()
                if line.strip().split("=")[0].strip() == "password":
                    self.artifactory_pass = line.strip().split("=")[1].strip()
        
        if not self.artifactory_user:
            raise ValueError("Artifactory user not set.")
        if not self.artifactory_pass:
            raise ValueError("Artifactory password not set.")

        self.repo_template_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "imagefactory.repo.template")

        self.OS_MAP = {
            "amazon_linux": "artifactory-uw2.adobeitc.com/artifactory/rpm-image-factory-hardener-prod-release/amazon-linux/generic/",
            "amazon_linux_2": "artifactory-uw2.adobeitc.com/artifactory/rpm-image-factory-hardener-prod-release/amazon-linux-2/generic/",
            "centos7": "artifactory-uw2.adobeitc.com/artifactory/rpm-image-factory-hardener-prod-release/centos-7/generic/",
            "centos8": "artifactory-uw2.adobeitc.com/artifactory/rpm-image-factory-hardener-prod-release/centos-8/generic/",
            "rhel7": "artifactory-uw2.adobeitc.com/artifactory/rpm-image-factory-hardener-prod-release/rhel-7/generic/",
            "rhel8": "artifactory-uw2.adobeitc.com/artifactory/rpm-image-factory-hardener-prod-release/rhel-8/generic/",
            "ubuntu18": "artifactory-uw2.adobeitc.com/artifactory/debian-image-factory-hardener-prod-local/ubuntu-18/generic/",
            "ubuntu20": "artifactory-uw2.adobeitc.com/artifactory/debian-image-factory-hardener-prod-local/ubuntu-20/generic/"
        }

        self.oslist = [_os for _os in self.OS_MAP]

        self.tarball_name = os.path.join(self.tmp, "if_hardener.tar.gz")

        end_time = datetime.datetime.now()

    def copy_scripts(self):
        src = "harden.sh"
        dst = f"{os.path.join(self.tmpdir, src)}"
        print(f"Copying script: {src} -> {dst}")
        shutil.copyfile(src, dst)
    
    def create_repo_file(self, osname):
        print(f"Creating repo file for {osname}.")
        VARIABLE_MAP = {
            "ARTIFACTORY_USER": self.artifactory_user,
            "ARTIFACTORY_PASSWORD": self.artifactory_pass,
            "BASEURL": self.OS_MAP[osname]
        }

        repo_filename = f"/tmp/if_hardener/imagefactory_{osname}.repo"
        with open(self.repo_template_file, "r") as f_in, open(repo_filename, "w") as f_out:
            for line in f_in:
                for key, value in VARIABLE_MAP.items():
                    line = line.replace(f"%{key}%", VARIABLE_MAP[key])
                f_out.write(line)
    
    def create_repos(self):
        for _os in self.oslist:
            self.create_repo_file(_os)

    def create_image_id_file(self):
        if not os.path.isfile(self.image_filename):
            print("Retrieving imagefactory image IDs.")
            url = "https://imagefactory.corp.adobe.com:8443/imagefactory/binary/details/?cloud_or_pkg_type=aws"
            data = requests.get(url)
            text = data.content

            image_info = json.loads(text)
            _ids = []
            for image in image_info:
                _id = image["imageId"]
                for _, value in _id.items():
                    _ids.append(value)
            open(self.image_filename, "w").write("\n".join(_ids))
        else:
            print("Image file already exists.")
        
    def create_tarball(self):
        print("Creating tarball.")
        if os.path.exists(self.tarball_name):
            os.remove(self.tarball_name)
        with tarfile.open(self.tarball_name, "x:gz") as tar:
            tar.add(self.tmpdir, arcname=os.path.basename(self.tmpdir))
    

    def create_script(self):
        print("Creating hardening script.")
        tarball_contents = base64.b64encode(open(self.tarball_name, "rb").read()).decode()

        with open(self.script_file, "w") as f_out, open(self.script_template, "r") as f_in:
            for line in f_in:
                line = line.replace("%TARBALL%", tarball_contents)
                f_out.write(line)

    @staticmethod
    def go():
        c = Create()
        c.copy_scripts()
        c.create_image_id_file()
        c.create_repos()
        c.create_tarball()
        c.create_script()


def main():
    Create.go()
    print()
    print("*" * 50)
    print("Run on remote side:")
    print()
    print("sudo amazon-linux-extras install -y epel")
    print("sudo yum install epel-release -y")
    print("sudo yum install python3 pwgen -y")
    print("sudo python3 -m ensurepip")
    print("sudo python3 -m pip install pyyaml")
    print("sudo python3 -m pip install requests")
    print("sudo python3 harden.py")


if __name__ == "__main__":
    main()
