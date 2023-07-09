#!/usr/bin/env bash

export ENVIRONMENT="$1"
if [[ -z "$ENVIRONMENT" ]]; then
    echo "No environment input.  Assuming 'dev'."
    export ENVIRONMENT="dev"
fi
export ISLOCAL=1
export DEVOPS_KEY="$(cat ~/.ssh/id_rsa_devops)"
export EA_KEY="$(cat ~/.ssh/id_rsa_ea)"
export GIT_KEY="$(cat ~/.ssh/id_rsa_cicdgit)"

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

eval $(/home/scheel/git/maintenance_server/files/home/aws_scripts/awscreds ${ACCOUNT})
eval $(. /home/scheel/bin/artifactory.sh)
eval $(. /home/scheel/bin/vault.sh)

echo "Processing build for ${ENVIRONMENT}"

bash scripts/cicd-deploy-server.sh
