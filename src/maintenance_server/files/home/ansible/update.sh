#!/usr/bin/env bash

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"

pushd $scriptdir

[[ ! -d ".venv" ]] && python3 -m venv .venv
. ${HOME}/.venv/bin/activate

python3 build.py -u -s ~/.ssh/aws -a ~/ansible

deactivate

popd
