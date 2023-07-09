#!/usr/bin/python

import os
import sys
import json
import requests
import re
import shutil

def instance_id():
    data = requests.get("http://169.254.169.254/latest/dynamic/instance-identity/document").content
    data2 = json.loads(data)
    return data2["instanceId"]

file1 = "/opt/splunkforwarder/etc/system/local/inputs.conf"
file2 = "/tmp/inputs.conf"
file3 = "/opt/splunkforwarder/etc/system/local/inputs.conf.backup"
file_original = "/opt/splunkforwarder/etc/default/local/inputs.conf"

# Create the local directory if it does not exist.

_localdir = os.path.split(file3)[0]
if not os.path.isdir(_localdir):
    os.makedirs(_localdir)

if not os.path.isfile(file1):
    # Let's create it.
    _content = "[default]\nhost = "
    open(file1, "w").write(_content)

pattern = re.compile("^host\s*=\s*")

with open(file1, "r") as f_in, open(file2, "w") as f_out:
    for line in f_in:
        print(repr(line))
        if pattern.match(line):
            print("Matches")
            line = "host = {}\n".format(instance_id())
        f_out.write(line)

# os.rename(file1, file3)
# os.rename(file2, file1)

if os.path.isfile(file1):
    shutil.copyfile(file1, file3)
shutil.copyfile(file2, file1)
