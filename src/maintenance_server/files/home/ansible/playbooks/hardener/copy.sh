#!/usr/bin/env bash

hostname="$1"

scp /tmp/harden.py ${hostname}:harden.py
if [[ $? != 0 ]]; then
	echo "Failed to copy harden.py"
	exit 1
fi

echo ""
echo "**********************************"
echo "Run on remote side:"
echo ""
echo "sudo amazon-linux-extras install -y epel"
echo "sudo yum install epel-release -y"
echo "sudo yum install python3 pwgen -y"
echo "sudo python3 -m ensurepip"
echo "sudo python3 -m pip install pyyaml"
echo "sudo python3 -m pip install requests"
echo "sudo python3 harden.py"

ssh ${hostname}
