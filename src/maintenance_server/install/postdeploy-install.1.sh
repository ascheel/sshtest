#!/usr/bin/env bash

export TMPDIR="/tmp"
export SETTINGS_FILE="${HOME}/.maintenance.yml"

header () {
    echo "****************************"
    echo "$@"
    echo "****************************"
}

header "Installing OS packages"
sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/AmazonLinux/hashicorp.repo | tee ${LOGDIR}/${LOGSTAMP}.postdeploy-install-1.hashicorp_repo.log
sudo yum install \
    python3 \
    awscli \
    git \
    yum-utils \
    shadow-utils \
    vault \
    -y | tee ${LOGDIR}/${LOGSTAMP}.postdeploy-install-1.yum_install.log 2>&1

header "Installing pip"
# Install pip3
curl -s https://bootstrap.pypa.io/get-pip.py > ${TMPDIR}/get-pip.py
python3 ${TMPDIR}/get-pip.py | tee ${LOGDIR}/${LOGSTAMP}.postdeploy-install-1.pip_install.log 2>&1

header "Installing python packages."
python3 -m pip install \
    troposphere \
    boto3 \
    botocore \
    hvac \
    requests \
    gitpython \
    --upgrade | tee ${LOGDIR}/${LOGSTAMP}.postdeploy-install-1.python3_package_install.log 2>&1

pushd ${HOME} >/dev/null 2>&1

header "Installing venv and pip"
python3 -m venv .venv
. ${HOME}/.venv/bin/activate
python3 -m pip install pip --upgrade >${LOGDIR}/${LOGSTAMP}.postdeploy-install-1.upgrade_pip.log 2>&1

header "Installing python packages."
# Need to install this AFTER files get moved into place.
[[ ! -f "${HOME}/requirements.txt" ]] && cp -v ${HOME}/maintenance_server_source/files/home/requirements.txt ${HOME}/requirements.txt
python3 -m pip install -r ${HOME}/requirements.txt >${LOGDIR}/${LOGSTAMP}.postdeploy-install-1.install_requirements.log 2>&1

header "Setting timezone to America/Denver"
bash postdeploy-timezone.sh

header "Executing postdeploy-install.2.py"
python3 postdeploy-install.2.py | tee ${LOGDIR}/${LOGSTAMP}.postdeploy-install-1.step_2.log 2>&1

header "Executing post-deploy Hubble script"
python3 postdeploy-hubble.py >${LOGDIR}/${LOGSTAMP}.postdeploy-install-1.hubble.log 2>&1

header "Executing post-deploy Splunk script"
python3 postdeploy-splunk.py >${LOGDIR}/${LOGSTAMP}.postdeploy-install-1.splunk.log 2>&1

header "Moving crontabs into place"
sudo python3 postdeploy-crontab.py >${LOGDIR}/${LOGSTAMP}.postdeploy-install-1.step_2.log 2>&1

header "Enabling TCP Forwarding in SSH"
sudo bash postdeploy-sshd.sh

header "Adding entries to ~/.ssh/config"
python3 postdeploy-sshconfig.py

header "Downloading and unpacking EDR Falcon Sensor"
rm -rfv ${HOME}/ansible/playbooks/edr-falcon-deployment
git \
    clone \
    --depth=1 \
    --branch=main \
    gitcorp.adobe.net:scheel/edr-falcon-deployment \
    ${HOME}/ansible/playbooks/edr-falcon-deployment
rm -rf ${HOME}/ansible/playbooks/edr-falcon-deployment/.git

header "Install TMUX"
bash postdeploy-tmux.sh

popd >/dev/null 2>&1

