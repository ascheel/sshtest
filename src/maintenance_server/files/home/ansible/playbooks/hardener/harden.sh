#!/usr/bin/env bash

function user_password () {
    user=$1
    id -u ${user} >/dev/null 2>&1
    exitstatus=$?
    if [[ ${exitstatus} == 1 ]]; then
        echo "User ${user} does not exist."
        return 0
    fi
    
    echo "Setting password for user ${user}."
    pwgen 30 1 | sudo passwd ${user} --stdin >/dev/null 2>&1
    if [[ $? != 0 ]]; then
        echo "Failed to set password."
        return 1
    fi
    return 0
}

echo "Hardening notes visible here:  https://git.corp.adobe.com/image-factory/imagefactory_hardening_scripts"

echo "Ensuring passwords exist for all Linux logins."
for user in ec2-user ubuntu centos ea de
do
    user_password $user
done

touch /etc/modprobe.d/CIS.conf
fgrep "install cramfs /bin/true" /etc/modprobe.d/CIS.conf || echo "install cramfs /bin/true" >> /etc/modprobe.d/CIS.conf
fgrep "install hfs /bin/true" /etc/modprobe.d/CIS.conf || echo "install hfs /bin/true" >> /etc/modprobe.d/CIS.conf
fgrep "install hfsplus /bin/true" /etc/modprobe.d/CIS.conf || echo "install hfsplus /bin/true" >> /etc/modprobe.d/CIS.conf
fgrep "install squashfs /bin/true" /etc/modprobe.d/CIS.conf || echo "install squashfs /bin/true" >> /etc/modprobe.d/CIS.conf
fgrep "install udf /bin/true" /etc/modprobe.d/CIS.conf || echo "install udf /bin/true" >> /etc/modprobe.d/CIS.conf
fgrep "install vfat /bin/true" /etc/modprobe.d/CIS/conf || echo "install vfat /bin/true" >> /etc/modprobe.d/CIS.conf
fgrep "install jffs2 /bin/true" /etc/modprobe.d/CIS/conf || echo "install jffs2 /bin/true" >> /etc/modprobe.d/CIS.conf
fgrep "install freevxfs /bin/true" /etc/modprobe.d/CIS/conf || echo "install freevxfs /bin/true" >> /etc/modprobe.d/CIS.conf
grep "^net.ipv4.ip_forward" /etc/sysctl.conf || echo "net.ipv4.ip_forward = 0" >> /etc/sysctl.conf
sysctl -w net.ipv4.ip_forward=0

grep "^DenyUsers" /etc/ssh/sshd_config || echo "DenyUsers root admin" >> /etc/ssh/sshd_config

cmd="/opt/image-factory-hardener/bin/exec --status --skip-checks-file=/tmp/if_hardener/skip-checks-file.yml"
$cmd

exitstatus=$?
if [[ "$exitstatus" != 0 ]];
then
    echo "Error executing hardener: ${cmd}"
    exit 1
fi

