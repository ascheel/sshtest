#!/usr/bin/env bash

header () {
    python3 scripts/print_header.py "$@"
}

debug () {
    [[ "$DEBUG" != "1" ]] && return 0
    echo "*********************"
    echo "DEBUG $(basename $0):$@"
    echo "*********************"
}

# Create tmp directory if it does not exist.
export TMPDIR="tmp"
export UPLOAD="${TMPDIR}/upload"
[[ ! -d ${TMPDIR} ]] && mkdir ${TMPDIR}

if [[ -z "$ISLOCAL" ]]; then
    header "Installing packages."

    mkdir ~/.pip
    cat > ~/.pip/pip.conf << EOF
[global]
index-url = https://pypi.python.org/simple
extra-index-url = https://${ARTIFACTORY_USERNAME}:${ARTIFACTORY_PASSWORD}@artifactory-uw2.adobeitc.com/artifactory/api/pypi/pypi-adobe-acs-release/simple
EOF

    # Install pip3
    curl -s https://bootstrap.pypa.io/get-pip.py > ${TMPDIR}/get-pip.py
    python3 ${TMPDIR}/get-pip.py

    # Install python packages
    pip3 install boto3 cfndeploy troposphere hvac

    # Install yum packages
    yum install -y awscli rsync
fi

header "Uploading DevOps SSH key if necessary"
python3 scripts/ec2-keypair.py

[[ ! -d "~/.ssh" ]] && mkdir ~/.ssh
chmod 700 ~/.ssh

echo "$DEVOPS_KEY" > ~/.ssh/id_rsa_devops
echo "$EA_KEY" > ~/.ssh/id_rsa_ea
echo "$GIT_KEY" > ~/.ssh/id_rsa_adobeea_git
chmod 600 ~/.ssh/id_rsa*

case $ENVIRONMENT in
    dev)
        export AWS_CFN_PARAM_SubnetId="subnet-02b6731b584ab2c7b"
        export PROXYJUMP="jump.dev-va6.ea.adobe.net"
        export GITBRANCH="dev"
        ;;
    stage)
        export AWS_CFN_PARAM_SubnetId="subnet-01ef739676783e58b"
        export PROXYJUMP="jump.stage-va6.ea.adobe.net"
        export GITBRANCH="master"
        ;;
    prod)
        export AWS_CFN_PARAM_SubnetId="subnet-0f216b7477621c310"
        export PROXYJUMP="jump.prod-va6.ea.adobe.net"
        export GITBRANCH="master"
        ;;
    *)
        ;;
esac

header "Creating/updating cloudformation stack"

export AWS_REGION="us-east-1"
export AWS_STACKNAME="DataEngineeringMaintenanceServer"
export AWS_TEMPLATEFILE="templates/maintenance_server.yml"

# export AWS_CFN_PARAM_AMI="ami-038b6a47537abba0e"
export AWS_CFN_PARAM_AMI="ami-0dd1a60392327b6ce"
export AWS_CFN_PARAM_Env="$ENVIRONMENT"
export AWS_CFN_PARAM_InstanceType="t3.xlarge"

export AWS_CFN_TAG_Adobe_ArchPath="DX.DE"
export AWS_CFN_TAG_Adobe_Customer="DE.Internal"
export AWS_CFN_TAG_Adobe_Owner="de-devops@adobe.com"

export AWS_CFN_CAPABILITY_NAMED_IAM="1"

cfndeploy \
    --stackname "$AWS_STACKNAME" \
    --template "$AWS_TEMPLATEFILE" \
    --region "$AWS_REGION" \
    "$@"

if [[ $? != 0 ]]; then
    exit 1
fi

debug "${LINENO}"

SERVERIP="$(python3 scripts/serverip.py)"
SERVERUSER="ec2-user"

debug "${LINENO}"

cat > ${TMPDIR}/ssh_config <<EOF
Host *
    StrictHostKeyChecking no
    LogLevel QUIET

Host ${PROXYJUMP}
    User ea
    IdentityFile ~/.ssh/id_rsa_ea

Host ${SERVERIP}
    User ${SERVERUSER}
    IdentityFile ~/.ssh/id_rsa_devops
EOF

while : ; do
    ssh -F ${TMPDIR}/ssh_config -oProxyJump=${PROXYJUMP} ${SERVERIP} "echo connection test"
    _status="$?"
    echo "Exit status: $_status"
    if [[ $_status == 0 ]]; then

        echo "Connection successful. Continuing."
        break
    else
        echo "Server not yet complete setting up."
    fi
    sleep 5
done

header "Copying kickstart script"

scp -F ${TMPDIR}/ssh_config -oProxyJump=${PROXYJUMP} "install/kickstart.sh" ${SERVERIP}:.
ssh -F ${TMPDIR}/ssh_config -oProxyJump=${PROXYJUMP} ${SERVERIP} chmod 700 /home/${SERVERUSER}/kickstart.sh
if [[ $? != 0 ]]; then
    echo "Transfer of files failed."
    exit 1
fi

debug "${LINENO}"
echo "File transfer complete."


echo "Server ready for installation.  Log into the server and execute kickstart.sh"
