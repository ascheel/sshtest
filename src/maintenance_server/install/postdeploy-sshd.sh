#!/usr/bin/env bash

# This script enables AllowTcpForwarding by converting a
# "no" value to "yes"

if [[ $EUID != 0 ]]; then
    echo "Script must be ran as root."
    exit 1
fi

sshd_config_backup="/etc/ssh/sshd_config.$(date +%y%m%d_%H%M)"

if grep -E "^AllowTcpForwarding\s+yes$" /etc/ssh/sshd_config >/dev/null 2>&1; then
    # Already configured
    echo "sshd_config already configured."
    exit 0
elif grep -E "^AllowTcpForwarding\s+no$" /etc/ssh/sshd_config >/dev/null 2>&1; then
    # Currently set to "no".  Amend it.
    echo "Changing AllowTcpForwarding to yes"
    cat /etc/ssh/sshd_config | sed -r 's/^AllowTcpForwarding\s+no$/AllowTcpForwarding yes/g' > /tmp/sshd_config
    mv -v /etc/ssh/sshd_config ${sshd_config_backup}
    mv -v /tmp/sshd_config /etc/ssh/sshd_config
    chown root: /etc/ssh/sshd_config
    chmod 600 /etc/ssh/sshd_config
elif ! grep -E "^AllowTcpForwarding\s+yes$" /etc/ssh/sshd_config >/dev/null 2>&1; then
    # Not set at all.  Allow it.
    echo "AllowTcpForwarding not set.  Appending to /etc/ssh/sshd_config"
    cp -v /etc/ssh/sshd_config ${sshd_config_backup}
    echo "AllowTcpForwarding yes" >> /etc/ssh/sshd_config
else
    echo "Bad logic hit.  You shouldn't be here."
    exit 1
fi
systemctl restart sshd
if [[ $? != 0 ]]; then
    echo "Failed to restart OpenSSH server (sshd)."
    exit 1
fi
