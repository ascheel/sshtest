#!/usr/bin/env bash

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"

pushd "$scriptdir"

. .venv/bin/activate

python3 vaultbackup.py -b

deactivate

popd
