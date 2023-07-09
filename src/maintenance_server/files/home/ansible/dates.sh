#!/usr/bin/env bash

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"

pushd $scriptdir

[[ ! -d ".venv" ]] && python3 -m venv .venv
. ${HOME}/.venv/bin/activate

PID="$$"
echo "Storing PID: $PID"

python3 lockfile.py "ansibledates" --pid $PID
if [[ $? != 0 ]]; then
    echo "Lock file exists. Exiting."
    exit 1
fi

python3 build.py -c

python3 lockfile.py "ansibledates" --remove

deactivate

popd
