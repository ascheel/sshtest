#!/usr/bin/env bash

pkill splunkd

sleep 1

#service splunk restart

systemctl restart splunk

exit 0
