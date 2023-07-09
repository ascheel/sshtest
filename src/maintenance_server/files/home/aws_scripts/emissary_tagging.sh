#!/usr/bin/env bash

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"

pushd $scriptdir

[[ ! -d ".venv" ]] && python3 -m venv .venv
. .venv/bin/activate

python3 emissary_tagging.py

deactivate

popd
