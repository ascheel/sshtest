#!/usr/bin/env bash

set -e

header () {
    python3 scripts/print_header.py "$@"
}

if [[ -z "$ISLOCAL" ]]; then
    header "Installing packages."

    mkdir ~/.pip
    cat > ~/.pip/pip.conf << EOF
[global]
index-url = https://pypi.python.org/sample
extra-index-url = https://${ARTIFACTORY_USERNAME}:${ARTIFACTORY_PASSWORD}@artifactory-uw2.adobeitc.com/artifactory/api/pypi/pypi-adobe-acs-release/simple
https://${ARTIFACTORY_USERNAME}:${ARTIFACTORY_PASSWORD}@artifactory-uw2.adobeitc.com/artifactory/api/pypi/pypi-adobe-acs-snapshot/simple
EOF

    # Install pip3
    curl -s https://bootstrap.pypa.io/get-pip.py | python3

    # Install python packages
    pip3 install boto3 cfndeploy troposphere
    
    # Install yum packages
    yum install -y awscli
fi

export AWS_REGION="us-east-1"
export AWS_STACKNAME="DevOpsMaintenanceServer"

# header "Deleting S3 contents"
# python3 scripts/s3_delete_contents.py

# if [[ $? != 0 ]]; then
#     echo "Failed to delete S3 contents."
#     exit 1
# fi

header "Tearing down cloudformation stack"

aws \
    cloudformation \
    delete-stack \
    --stack-name=${AWS_STACKNAME} \
    --region=${AWS_REGION}

if [[ $? != 0 ]]; then
    echo "Failed to remove cloudformation stack $AWS_STACKNAME."
    exit 1
fi

header "Waiting for teardown to complete."

python3 scripts/watch_for_stack_cleanup.py
