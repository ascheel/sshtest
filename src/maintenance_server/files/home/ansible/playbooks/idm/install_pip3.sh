#!/usr/bin/env bash

if [[ "$(id -u)" != "0" ]]; then
    echo "This script must be ran as root." 1>&2
    exit 1
fi

curl https://bootstrap.pypa.io/get-pip.py | python3
