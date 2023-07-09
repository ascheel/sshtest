#!/usr/bin/env bash

pushd ~/ansible

for account in $(python3 ${HOME}/bin/list_aws_accounts.py)
do
    ansible-playbook -i ${account} playbooks/yum_update_kernel_reboot.yml
done

popd