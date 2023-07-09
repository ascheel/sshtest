#!/usr/bin/env bash

_dir="${HOME}/tasks/vault_token_rotate"

pushd ${_dir}

if [[ ! -d ".venv" ]]; then
    python3 -m venv .venv
    python3 -m pip install -r requirements.txt
fi

python3 ${_dirHOME}/tasks/vault_token_rotate/rotate.py

popd
