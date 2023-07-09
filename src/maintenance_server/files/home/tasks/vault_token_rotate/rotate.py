import hvac
import yaml
import json
import os
import sys
import boto3
from dateutil import parser
import datetime
import argparse
import logging
import requests
import socket


class Rotate:
    def __init__(self, **kwargs):
        # General
        LEVELS = {
            "DEBUG":    logging.DEBUG,
            "INFO":     logging.INFO,
            "WARNING":  logging.WARNING,
            "ERROR":    logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }

        self.DATETIME_FORMAT     = "%Y-%m-%dT%H:%M:%S"

        self.force_update        = kwargs.get("force_update")
        self.loglevel            = kwargs.get("loglevel")
        logging.basicConfig(
            format='%(asctime)s %(message)s',
            datefmt='%Y-%d-%m %H:%M:%S -',
            level=LEVELS[self.loglevel]
        )
        logging.getLogger('botocore').setLevel(logging.CRITICAL)
        self.read_only           = kwargs.get("read_only")
        if self.read_only:
            logging.debug("(Read Only: No updates will be made to Secrets Manager.)")

        # AWS Setup
        self.region_name         = kwargs.get("region_name")
        self.profile_name        = kwargs.get("profile_name")        
        self.rotate_age_in_hours = kwargs.get("expiration")

        logging.debug(f"Processing profile {self.profile_name} for region {self.region_name}.")
        logging.debug(f"Tokens expire if less than {self.rotate_age_in_hours} hours in the future.")

        # Get secret
        self.sm           = self.sm_client()
        self.sm_path      = kwargs.get("secrets_path")
        self.sm_secret    = self.get_sm_secret()

        # Vault Setup
        self.vault_host = self.fix_hostname(self.sm_secret.get("host"))

        # New token s.AtzXiMCcNcwpOijyaXhjIQVS expires at 2020-12-26 03:33:05.798821 (101.0 h)

    def sm_client(self):
        logging.debug("Getting vault client.")
        aws = None
        if self.profile_name:
            aws = boto3.Session(profile_name=self.profile_name)
        else:
            aws = boto3.Session()
        return aws.client("secretsmanager", region_name=self.region_name)

    def get_sm_secret(self):
        data = json.loads(self.sm.get_secret_value(SecretId=self.sm_path)["SecretString"])
        if not data.get("token_expiry_date"):
            # If it doesn't exist, set it to now so it automatically expires and it's forced to renew.
            data["token_expiry_date"] = datetime.datetime.now().strftime(self.DATETIME_FORMAT)
        if not data.get("vault_token"):
            # Blank if not exists.  Need SOME value.
            data["vault_token"] = ""
        return data
    
    def expires_in_hours(self, _datetime_object=None):
        expiry = _datetime_object or parser.parse(self.sm_secret.get("token_expiry_date"))
        if not expiry:
            # Return 0 to force an update.  This secret NEEDS an expiry timestamp.
            return 0
        seconds = (expiry - datetime.datetime.now()).total_seconds()
        minutes = seconds // 60
        hours   = minutes / 60
        return hours

    def __write_sm_secret(self):
        _secret = json.dumps(self.sm_secret)
        if not self.read_only:
            self.sm.update_secret(
                SecretId=self.sm_path,
                SecretString=_secret
            )
            logging.debug("New secret updated.")

    def _does_authenticate(self, token=None):
        _token = token or self.sm_secret["vault_token"]
        _client = None
        try:
            _client = hvac.Client(url=self.vault_host, token=_token)
        except socket.timeout as e:
            return -1
        except requests.exceptions.ConnectTimeout as e:
            return -1
        authenticated = _client.is_authenticated() == True
        if authenticated:
            logging.debug("We are authenticated.")
        else:
            logging.debug("We are not authenticated.")
        return authenticated
    
    def fix_hostname(self, hostname):
        _MAP = {
            "https://vault.dev.va6.adobe.net": "https://vault-ext.dev.or1.adobe.net"
        }
        return _MAP.get(hostname, hostname)


    def mask(self, text):
        if len(text) <= 4:
            return "****"
        out_text = "*" * (len(text) - 4)
        out_text += text[-4:]
        return out_text

    def go(self):
        _hours = self.expires_in_hours()
        _future_past = "future" if _hours >= 0 else "past"

        logging.debug(f"Current Token expires at {self.sm_secret['token_expiry_date']} ({round(_hours, 1)} h [{_future_past}])")
        
        _authenticates = self._does_authenticate()
        if _authenticates == -1:
            # Timeout, bad server.  Just skip it
            logging.CRITICAL(f"{self.profile_name:20} - {self.region_name:15} - CRITICAL connection timeout for {self.sm_secret['host']}")
            return

        log_text = None
        if _hours <= self.rotate_age_in_hours or not _authenticates or self.force_update:
            logging.debug("Rotation needed.")
            if _hours <= self.rotate_age_in_hours:
                logging.debug("(Reason: Old token)")
            if not _authenticates:
                logging.debug("(Reason: Token does not authenticate)")
            if self.force_update:
                logging.debug("(Reason: Update forced)")

            role_id = self.sm_secret["role"]
            secret  = self.sm_secret["secret"]
            
            _client_vault = hvac.Client(url=self.vault_host)
            # _client_vault.auth_approle(role_id, secret)
            # Deprecation replacement:
            _client_vault.auth.approle.login(role_id, secret)
            
            _new_token  = _client_vault.token
            _new_expiry = parser.parse(_client_vault.lookup_token()["data"]["expire_time"]).replace(tzinfo=None)

            _new_expiry_string = _new_expiry.strftime('%Y-%m-%dT%H:%M:%S')

            _future_past_2 = "future" if self.expires_in_hours(_new_expiry) >= 0 else "past"

            logging.info(f"{self.profile_name:20} - {self.region_name:15} - New token generated: {self.mask(_new_token)} expires {_new_expiry_string}")
            logging.debug(f"New token expires at {_new_expiry} ({round(self.expires_in_hours(_new_expiry), 1)} h [{_future_past_2}])")

            # Here we update our secret (in memory)
            self.sm_secret["token_expiry_date"] = _new_expiry_string
            self.sm_secret["vault_token"]       = _new_token

            # Now, let's write it out to AWS
            self.__write_sm_secret()
        else:
            logging.debug(f"{self.profile_name:20} - {self.region_name:15} - Token rotation not needed: {self.mask(self.sm_secret['vault_token'])} expires {self.sm_secret['token_expiry_date']}")
        # logging.info(f"{self.profile_name:20} - {self.region_name:15} - {log_text}")
    
    @staticmethod
    def BETA():
        return False
        

def iterate():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--force",
        help="Force an update to all secrets managers.",
        action="store_true"
    )
    parser.add_argument(
        "-p",
        "--profile",
        help="Profile to process against.",
        action="append"
    )
    parser.add_argument(
        "-r",
        "--read-only",
        help="Read only mode.  Don't write anything to secrets manager.  Still generates a new token.",
        action="store_true"
    )
    parser.add_argument(
        "-l",
        "--loglevel",
        help="DEBUG, INFO, WARNING, ERROR, CRITICAL",
        default="INFO"
    )
    args = parser.parse_args()

    _loglevel = args.loglevel.upper()

    if _loglevel not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        raise ValueError(f"Bad value for LOGLEVEL: {_loglevel}.  Valid values: {_loglevel}")

    settings_file = f"{os.path.splitext(os.path.abspath(__file__))[0]}.yml"
    settings      = yaml.safe_load(open(settings_file, "r").read())

    expiration    = settings["global"]["expiration_in_hours"]
    path          = settings["global"]["secrets_manager_path"]

    secrets       = settings["secrets"]
    if Rotate.BETA:
        secrets   = [
            'na-ea-dev',
            'na-ea-stage',
            'na-ea-d365-dev',
            'na-ea-d365-stage-amer',
            'na-ea-d365-stage-apac',
            'na-ea-d365-stage-emea'
        ]
    for secret in secrets:
        values = settings["secrets"][secret]
        if args.profile and secret not in args.profile:
            continue

        r = Rotate(
            profile_name=values["profile"],
            region_name=values["region"],
            expiration=expiration,
            secrets_path=path,
            loglevel=_loglevel,
            force_update=args.force,
            read_only=args.read_only
        )
        r.go()

def main():
    iterate()


if __name__ == "__main__":
    main()
