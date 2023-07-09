#!/usr/bin/env bash

fgrep "^admin.*" /opt/splunkforwarder/etc/passwd >/dev/null 2>&1 || /opt/splunkforwarder/bin/splunk add user admin -password changeme -role admin -auth admin:changeme

#/opt/splunkforwarder/bin/splunk edit user admin -password $(head -c 500 /dev/urandom | sha256sum | base64 | head -c 16 ; echo) -auth admin:changeme
