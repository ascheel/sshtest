#!/usr/bin/env bash

ENV="$1"
[[ -z "$ENV" ]] && ENV="prod"

USER="$2"
[[ -z "$USER" ]] && USER="ea"

case $ENV in
    dev)
        PROXYJUMP="jump.dev-va6.ea.adobe.net"
        ;;
    stage)
        PROXYJUMP="jump.stage-va6.ea.adobe.net"
        ;;
    prod)
        PROXYJUMP="jump.prod-va6.ea.adobe.net"
        ;;
    *)
        ;;
esac

eval $(/home/scheel/git/aws_scripts/awscreds na-ea-${ENV})
export AWS_REGION="us-east-1"
export AWS_STACKNAME="DevOpsMaintenanceServer"
SERVERIP=$(python3 scripts/serverip.py)

echo "Host:      ${SERVERIP}"
echo "ProxyJump: ${PROXYJUMP}"
echo "User:      ${USER}"

ssh -oProxyJump=${PROXYJUMP} -i ~/.ssh/id_rsa_devops ${USER}@${SERVERIP}
