#!/usr/bin/env bash

export ENVIRONMENT="$1"
if [[ -z "$ENVIRONMENT" ]]; then
    echo "No environment input.  Assuming 'dev'."
    export ENVIRONMENT="dev"
fi
export ISLOCAL=1

case $ENVIRONMENT in
    dev)
        ACCOUNT="na-ea-dev"
        ;;
    stage)
        ACCOUNT="na-ea-stage"
        ;;
    prod)
        ACCOUNT="na-ea-prod"
        ;;
    *)
        echo "Bad ENVIRONMENT"
        exit 1
        ;;
esac

eval $(/home/scheel/git/maintenance_server/files/home/aws_scripts/awscreds $ACCOUNT)
eval $(. /home/scheel/bin/artifactory.sh)
eval $(. /home/scheel/bin/vault.sh)

echo "Processing teardown for ${ENVIRONMENT}"

scripts/cicd-destroy-server.sh
