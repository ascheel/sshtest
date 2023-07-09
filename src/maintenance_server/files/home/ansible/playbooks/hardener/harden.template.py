import os
import sys
import json
import yaml
import base64
import tarfile
import shutil
import subprocess
import shlex
import requests


class Harden:
    def __init__(self):
        self.tmp            = "/tmp"
        self.hardener_files = os.path.join(self.tmp, "if_hardener")
        self.tarball        = """%TARBALL%"""
        self.tarball_name   = os.path.join(self.tmp, "if_hardener.tar.gz")
        self.os_name        = None
        self.skip_file      = os.path.join(self.hardener_files, "skip-checks-file.yml")
        
        if os.path.exists("/tmp/is_local"):
            self.os_name = "amazon_linux_2"
        else:
            self.os_name = self.get_os()
        
        self.package_map = {
            "amazon_linux": "amazon-linux",
            "amazon_linux_2": "amazon-linux-2",
            "centos7": "centos-7",
            "centos8": "centos-8"
        }
        
    def check_root(self):
        if os.geteuid() != 0:
            print("Script must be ran as root.")
            sys.exit(1)
    
    def check_image_factory(self):
        url = "http://169.254.169.254/latest/dynamic/instance-identity/document"
        data = requests.get(url)
        text = data.content
        ami = json.loads(data.content)["imageId"]
        image_file = os.path.join(self.hardener_files, "images.txt")
        with open(image_file, "r") as f_in:
            for line in f_in:
                if line.startswith(ami):
                    print("Server is running ImageFactory.  Nothing to do.")
                    sys.exit(0)

    def get_os(self):
        import platform
        if "amzn1" in platform.release():
            return "amazon_linux"
        elif "amzn2" in platform.release():
            return "amazon_linux_2"
        elif "centos" in platform.dist():
            if "el7" in platform.release():
                return "centos7"
            elif "el8" in platform.release():
                return "centos8"
            else:
                raise OSError("Unknown operating system")
        elif "redhat" in platform.dist():
            if "el7" in platform.release():
                return "rhel7"
            elif "el8" in platform.release():
                return "rhel8"
            else:
                raise OSError("Unknown operating system")
        else:
            raise OSError("Unknown operating system")

    def extract(self):
        print("Extracting tarball.")
        if os.path.isdir(self.hardener_files):
            # print(f"Removing directory: '{self.hardener_files}'")
            shutil.rmtree(self.hardener_files)
        _tarball_contents = base64.b64decode(self.tarball)
        open(self.tarball_name, "wb").write(_tarball_contents)
        with tarfile.open(self.tarball_name, "r:gz") as tar:
            tar.extractall(self.tmp)

    def place_repo(self):
        print("Creating repo file.")
        repo_filename = os.path.join(self.hardener_files, f"imagefactory_{self.os_name}.repo")
        repo_target   = os.path.join("/etc/yum.repos.d", os.path.basename(repo_filename))
        if not os.path.exists(repo_target):
            print(f"Placing repo: {repo_target}")
            shutil.copyfile(repo_filename, repo_target)
        
    def exec(self, cmd):
        print(f"Executing: {cmd}")
        proc = subprocess.run(
            shlex.split(cmd),
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE
        )
        return proc

    def install_hardener(self):
        print("Installing hardener.")
        hardener_package = f"if-hardener-{self.package_map.get(self.os_name, self.os_name)}"
        results = self.exec(f"yum install {hardener_package} -y")
        if results.returncode:
            print(f"Package {hardener_package} installation failed.")
        
    def create_skip_checks_file(self):
        print("Saving checks-to-skip file.")
        # data = {
        #     "checks-to-skip": [
        #         "check1_1_3",
        #         "check1_1_8",
        #         "check6_2_8"
        #     ]
        # }
        # open(self.skip_file, "w").write(yaml.dump(data))
        data = [
            "checks-to-skip:",
            "  - check1_1_3",
            "  - check1_1_8",
            "  - check1_1_12",
            "  - check1_1_13",
            "  - check1_1_14",
            "  - check6_2_6",
            # "  - check6_2_8",
            # "  - check6_1_10",
            # "  - check6_1_11",
            # "  - check6_1_12"
        ]
        open(self.skip_file, "w").write("\n".join(data))
    
    def execute_hardener(self):
        cmd = f"sudo bash {os.path.join(self.hardener_files, 'harden.sh')}"
        results = self.exec(cmd)
        self.print_run_results(results)
        if results.returncode:
            print("Failure running hardener.")
            sys.exit(1)
        else:
            print("Hardener exited normally.")

    def print_run_results(self, results):
        print("*" * 50)
        print(f"    Exit status: {results.returncode}")
        print("    STDOUT:")
        for line in results.stdout.splitlines():
            print(f"        {line.decode()}")
        print("    STDERR:")
        for line in results.stderr.splitlines():
            print(f"        {line.decode()}")
        print("*" * 50)
    
    def go(self):
        # Running as root?
        self.check_root()

        # Extract tarball
        self.extract()

        # Check if it's already ImageFactory
        self.check_image_factory()

        # Copy repo into place
        self.place_repo()

        # Install IF Hardener
        self.install_hardener()

        # Put skip-checks-file in place
        self.create_skip_checks_file()

        # Run hardener
        self.execute_hardener()

        print()
        print()
        print("Checks not implemented.  Run this to implement hardener:")
        print("sudo /opt/image-factory-hardener/bin/exec --run --implement-high-risk --skip-checks-file=/tmp/if_hardener/skip-checks-file.yml")



def main():
    harden = Harden()
    harden.go()


if __name__ == "__main__":
    main()

