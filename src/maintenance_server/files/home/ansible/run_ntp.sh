#!/usr/bin/env bash

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd)"

pushd "$scriptdir"

for account in $(python3 ${HOME}/bin/list_aws_accounts.py)
do
    echo "Processing ${account}"
    ansible-playbook -i ${account}.yml playbooks/ntp/ntp.yml
done

popd
