#!/usr/bin/env python3

import os
import sys
import json
import requests
import subprocess
import shlex


def account_number():
    url = "http://169.254.169.254/latest/dynamic/instance-identity/document"
    content = requests.get(url).content
    return json.loads(content)["accountId"]


def main():
    executable = "/opt/if_sssd_util/bin/conf-sssd-groups.sh"
    if os.path.isfile(executable):
        # We are a go!
        simple_group = os.environ['IDM_LDAP_SIMPLE']
        sudo_group   = os.environ['IDM_LDAP_SUDO']
        command = f"{executable} -a {simple_group} -s {sudo_group}"
        results = subprocess.run(
            shlex.split(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        sys.exit(results.returncode)
    else:
        sys.exit("Not an imagefactory image.")


if __name__ == "__main__":
    main()

