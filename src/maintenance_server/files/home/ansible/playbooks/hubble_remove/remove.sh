#!/usr/bin/env bash

yum -y remove hubblestack
exitstatus="$?"

# Did that fail?  Let's try again.
if [[ "$exitstatus" != "0" ]]; then
    yum --setopt=tsflags=noscripts -y remove hubblestack
    exitstatus2="$?"
fi

# Did THAT one fail?  Let's try yet again.
if [[ "$exitstatus2" != "0" ]]; then
    rpm -e --noscripts hubblestack
    exitstatus3="$?"
fi

if [[ "$exitstatus3" != "0" ]]; then
    echo "Failed all 3 uninstall attempts.  My bad."
    exit $exitstatus
fi
