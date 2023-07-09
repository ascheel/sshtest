#!/usr/bin/env bash

set -e

header () {
    echo "****************************"
    echo "$@"
    echo "****************************"
}

export LOGSTAMP="$(date +'%Y%m%d-%H%M%S')"
export LOGDIR="${HOME}/logs/install"
[[ ! -d "${LOGDIR}" ]] && mkdir -p "${LOGDIR}"

cd ${HOME}

VAULT_CONFIG_FILE="${HOME}/.vault.yml"
GIT_SSH_KEYFILE="${HOME}/.ssh/id_rsa_adobegit"

[[ -n "$1" ]] && ENVIRONMENT="$1"
case $ENVIRONMENT in
    dev)
        GITBRANCH="dev"
        ;;
    stage|prod)
        GITBRANCH="master"
        ;;
    *)
        ENVIRONMENT="dev"
        GITBRANCH="dev"
        ;;
esac
echo "Environment set to: ${ENVIRONMENT}"
echo "GITBRANCH set to: ${GITBRANCH}"
export ENVIRONMENT

# Create SSH assets
[[ ! ~/.ssh ]] && mkdir ~/.ssh
chmod 700 ~/.ssh

if [[ ! -f ${VAULT_CONFIG_FILE} ]]; then
    header "Initializing Vault credentials."
    echo "Vault credentials not found."
    echo "Please find Vault credentials at vault::acs_de/vault::prod/acs_de_approle_read/{role-id|secret-id}"
    echo ""
    read -p "Role-ID: " vault_role_id
    read -p "Secret-ID: " vault_secret_id
    read -p "Vault Host [https://vault-amer.adobe.net]: " VAULT_ADDR
    read -p "Vault namespace [dx_analytics]: " VAULT_NAMESPACE
    echo ""

    if [[ -z "$vault_role_id" || -z "$vault_secret_id" ]]; then
        echo "No role-id/secret-id provided.  Exiting."
        exit 1
    fi
    [[ -z "$vault_host" ]] && vault_host="https://vault-amer.adobe.net"
    [[ -z "$vault_namespace" ]] && vault_namespace="dx_analytics"

    cat > ${VAULT_CONFIG_FILE} <<EOF
role-id: ${vault_role_id}
secret-id: ${vault_secret_id}
host: ${vault_host}
namespace: ${vault_namespace}
EOF
fi

export vault_role_id="$(fgrep "role-id:" ${VAULT_CONFIG_FILE} | awk '{ print $2 }')"
export vault_secret_id="$(fgrep "secret-id:" ${VAULT_CONFIG_FILE} | awk '{ print $2 }')"
export VAULT_ADDR="$(fgrep "host:" ${VAULT_CONFIG_FILE} | awk '{ print $2 }')"
export VAULT_NAMESPACE="$(fgrep "namespace:" ${VAULT_CONFIG_FILE} | awk '{ print $2 }')"

# Install Vault
sudo yum install -y yum-utils shadow-utils
sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/AmazonLinux/hashicorp.repo
sudo yum -y install vault

# Authenticate with Vault
header "Getting Vault token"
export VAULT_TOKEN="$(vault write auth/approle/login role_id="${vault_role_id}" secret_id="${vault_secret_id}" | fgrep "token " | sed 's/\s\+/ /g' | awk -F' ' '{ print $2 }')"

# Get git key
header "Configuring Git"
export GIT_KEY="$(vault kv get -mount=acs_de -field=ssh/key cicd/git)"
echo "${GIT_KEY}" > "${GIT_SSH_KEYFILE}"
chmod 600 ${GIT_SSH_KEYFILE}

# Install our OS packages
header "Installing OS packages"
sudo yum install git python3 -y | tee ${LOGDIR}/${LOGSTAMP}.kickstart.python3_install.log 2>&1

export GIT_SSH_COMMAND="ssh -oUser=git -oIdentityFile=${GIT_SSH_KEYFILE}"

# Add server host key to known_hosts
ssh-keyscan gitcorp.adobe.net >> ~/.ssh/known_hosts 2>/dev/null

# Refresh source
header "Refreshing source"
[[ -d maintenance_server_source ]] && rm -rf maintenance_server_source
git clone gitcorp.adobe.net:es/maintenance_server maintenance_server_source >${LOGDIR}/${LOGSTAMP}.kickstart.gitclone.log 2>&1
# Sleep to let the filesystem settle.
sleep 1
chmod 755 maintenance_server_source

pushd maintenance_server_source >/dev/null 2>&1
git checkout ${GITBRANCH}
popd >/dev/null 2>&1

# Update self
_thisscript="$(realpath $0)"
_thatscript="${HOME}/maintenance_server_source/install/kickstart.sh"
_sum1="$(sha256sum ${_thisscript} | awk '{ print $1 }')"
_sum2="$(sha256sum ${_thatscript} | awk '{ print $1 }')"
if [[ "${_sum1}" == "${_sum2}" ]]; then
    echo "Script already up to date."
else
    header "Updating self."
    cp -v "${_thatscript}" "${_thisscript}"
    chmod o+x "${_thisscript}"
    "${_thisscript}" "$@"
    exit 0
fi
# end update self

cp -v maintenance_server_source/install/postdeploy-* . | tee ${LOGDIR}/${LOGSTAMP}.kickstart.copy.log 2>&1
bash postdeploy-install.1.sh
rm -fv ~/postdeploy-* | tee -a ${LOGDIR}/${LOGSTAMP}.kickstart.copy.log 2>&1

