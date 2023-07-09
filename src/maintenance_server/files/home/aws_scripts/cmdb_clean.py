import os
import subprocess
import sys
import shlex
import json


def cmdb_instances():
    data = exec('python2 /usr/local/bin/denali --device_service="Consulting - AWS - ec2" -o json')
    data = json.loads(data.stdout.read())
    results = data["results"]
    for result in results:
        
        yield result["name"]

def exec(cmd):
    return subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def main():
    print(json.dumps(data, indent=4))

if __name__ == "__main__":
    main()

