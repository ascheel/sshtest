#!/bin/bash
 
# check for root
if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi
 
# install splunk, potentially needs customized depending on your environment
yum -y install splunkforwarder
 
# enable boot-start, set to run as user splunk
/opt/splunkforwarder/bin/splunk enable boot-start -user splunk --accept-license --answer-yes --no-prompt
 
# disable management port
mkdir -p /opt/splunkforwarder/etc/apps/UF-TA-killrest/local
cat > /opt/splunkforwarder/etc/apps/UF-TA-killrest/local/server.conf << EOF
[httpServer]
disableDefaultPort = true
EOF
 
# ensure splunk home is owned by splunk, except for splunk-launch.conf
chown -R splunk:splunk /opt/splunkforwarder
chown root:splunk /opt/splunkforwarder/etc/splunk-launch.conf
chmod 644 /opt/splunkforwarder/etc/splunk-launch.conf
 
# Does the admin user exist?
fgrep "admin" /opt/splunkforwarder/etc/passwd >/dev/null 2>&1 || /opt/splunkforwarder/bin/splunk add user admin -password changeme -role admin -auth admin:changeme

# change admin pass
/opt/splunkforwarder/bin/splunk edit user admin -password $(head -c 500 /dev/urandom | sha256sum | base64 | head -c 16 ; echo) -auth admin:changeme
 
# ensure user splunk can read /var/log
setfacl -Rm u:splunk:r-x,d:u:splunk:r-x /var/log

# Restart splunk
service splunk restart

# Restart it again because the first time, systemctl didn't know about it
systemctl restart splunk
