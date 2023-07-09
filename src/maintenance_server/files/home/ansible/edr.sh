#!/usr/bin/env bash

export ARTIFACTORY_USER="adobeea"
export ARTIFACTORY_KEY=""
export CUSTOMER_ID_CHECKSUM="7a66ddc57590483b96f043b6c5ec97c1-6e"
export JIRA_PROJECT="DATAENGTT"
export ADOBE_SVC_ID="321040"

pushd ~/ansible

for account in $(python3 ${HOME}/bin/list_aws_accounts.py)
do
	echo "Starting EDR deployment for $env" | ts '[%Y-%m-%d %H:%M:%S]' > /var/log/maintenance/edr.times.log
	ansible-playbook -i ${env}.yml playbooks/edr-falcon-deployment/playbook.yml | ts '[%Y-%m-%d %H:%M:%S]'
	echo "Finished EDR deployment for $env" | ts '[%Y-%m-%d %H:%M:%S]' > /var/log/maintenance/edr.times.log
done

popd

