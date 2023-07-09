#!/usr/bin/env

for account in $(python3 ${HOME}/bin/list_aws_accounts.py)
do
    ansible-playbook -i ${account}.yml playbooks/wfe_cleanup/wfe_cleanup.yml
done
