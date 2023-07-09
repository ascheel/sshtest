#!/usr/bin/env bash

set -e

# Download hubble
export TMPDIR="downloads/hubble"
[[ ! -d "${TMPDIR}" ]] && mkdir -p "${TMPDIR}"

if [[ -z "$ISLOCAL" ]]; then
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
    pip3 install hvac
fi

python3 scripts/package_hubble.py

