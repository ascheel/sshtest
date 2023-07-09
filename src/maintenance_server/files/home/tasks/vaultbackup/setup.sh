#!/usr/bin/env bash

set -e

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"

# vsudo python3 -m pip install virtualenv

pushd "$scriptdir"

venvdir=".venv"

[[ ! -x "$venvdir" ]] && python3 -m venv "$venvdir"

. "${venvdir}/bin/activate"

python3 -Im ensurepip --upgrade --default-pip
python3 -m pip install -r requirements.txt

deactivate

popd

