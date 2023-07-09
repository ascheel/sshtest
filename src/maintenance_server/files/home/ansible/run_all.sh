#!/usr/bin/env bash

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"

pushd $scriptdir

./update.sh
./run_hubble.sh
./run_splunk.sh
./run_idm.sh
./run_ntp.sh

popd
