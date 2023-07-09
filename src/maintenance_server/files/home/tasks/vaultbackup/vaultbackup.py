#!/usr/bin/env python3

import sys
import datetime
import json
import yaml
import logging
import argparse

# For vault
import hvac

# Needed to get token from Secrets Manager
import boto3
import botocore

# For Encryption
import hashlib
from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA512
from Crypto.Protocol import KDF
from Crypto.Util import Counter
import base64
import os


class Encryption:
    def __init__(self):
        self.iterations = 10000
    
    def sha256sum(self, *args, **kwargs):
        """Get hex checksum"""

        return_bytes = kwargs.get("bytes")
        args2 = []
        for arg in args:
            if isinstance(arg, str):
                args2.append(arg.encode())
            else:
                args2.append(arg)
        _input = b''.join(args2)
        if not isinstance(_input, bytes):
            raise ValueError("Input data must be in bytes.")
        m = hashlib.sha256()
        m.update(_input)
        if return_bytes:
            return m.digest()
        else:
            return m.hexdigest()

    def encrypt_cfb(self, _input, _password, _salt):
        """Encrypts using AES in CFB mode"""
        password = _password.encode()
        key_iv = KDF.PBKDF2(password, _salt, 64, count=self.iterations, hmac_hash_module=SHA512)
        key = key_iv[:32]
        iv  = key_iv[32:48]
        cipher = AES.new(key, AES.MODE_CFB, iv=iv)
        encrypted = cipher.encrypt(_input.encode())
        return encrypted
    
    def decrypt_cfb(self, _encrypted, _password, _salt):
        password = _password.encode()
        key_iv = KDF.PBKDF2(password, _salt, 64, count=self.iterations, hmac_hash_module=SHA512)
        key = key_iv[:32]
        iv = key_iv[32:48]
        cipher = AES.new(key, AES.MODE_CFB, iv=iv)
        decrypted = cipher.decrypt(_encrypted).decode()
        return decrypted


class Vault:
    def __init__(self, **kwargs):
        self.vault_url     = f"https://{kwargs['url']}"
        self.vault_token   = kwargs.get("token")
        self.vault_approle = kwargs.get("role_id")
        self.vault_secret  = kwargs.get("secret_id")
        self.client        = hvac.Client(url=self.vault_url)
        if self.vault_token:
            self.client.token  = self.vault_token
        else:
            self.client.auth.approle.login(role_id=self.vault_approle, secret_id=self.vault_secret)
            self.vault_token = self.client.token

    def list_secrets(self, path):
        while path.endswith("/"):
            path = path[:-1]
        data = self.client.list(path)["data"]
        # print(f"Path: {path}")
        for key in data["keys"]:
            # print(f"Key:  {key}")
            fullpath = f"{path}/{key}"
            if not key.endswith("/"):
                # Is secret
                yield fullpath
            else:
                yield from self.list_secrets(fullpath)


class Backup:
    def __init__(self):
        self.logger = logging.getLogger("vaultbackup")
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("botocore").setLevel(logging.WARNING)
        
        # Console log handler
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        self.logger.propagate = False

        self.warn     = self.logger.warning
        self.error    = self.logger.error
        self.critical = self.logger.critical
        self.info     = self.logger.info
        self.debug    = self.logger.debug

        self.vault     = None
        self.client    = None
        self.scriptdir = os.path.split(os.path.abspath(__file__))[0]

        self.backup_passphrase = open(os.path.join(os.path.expanduser("~"), ".backup-password"), "r").readline().strip()

        self.aws_profile = "na-ea-prod"
        self.aws_region  = "us-east-1"
        self.s3_bucket   = "ea-bucket-prod"
        self.s3_path     = "vault_backup"

        self.aws = boto3.Session(profile_name=self.aws_profile)
        self.s3  = self.aws.client("s3", region_name=self.aws_region)

        self.enc = Encryption()

    def fix_secret(self, text):
        return f"{text[:4]}{'X' * len(text[4:])}"

    def backup(self):
        # data = self.client.read("auth/approle/role/dx_ea_approle/role-id")
        # print(data)
        # sys.exit()

        settings = yaml.safe_load(open(os.path.join(os.path.expanduser("~"), ".vault-backup.yml")).read())
        for url, paths in settings["hosts"].items():
            for path, auth in paths.items():
                self.info(f"Server: {url}")
                self.info(f"Path: {path}")
                self.debug(f"role-id: {auth['role-id']}")
                self.debug(f"secret-id: {self.fix_secret(auth['secret-id'])}")
                vault  = Vault(url=url, role_id=auth['role-id'], secret_id=auth['secret-id'])
                client = vault.client

                decrypted_data = {}
                for secret_path in vault.list_secrets(path):
                    self.debug(f"    Processing {secret_path}")
                    secret = client.read(secret_path)
                    decrypted_data[secret_path] = secret
                
                output_data = self.encrypt(decrypted_data)
                
                base_filename = f"vault_backup.{url}.{path}.{self.timestamp()}.bin"

                key = f"{self.s3_path}/{base_filename}"
                display_path = f"s3://{self.s3_bucket}/{key}"
                self.info(f"Uploading: {display_path} ({len(output_data)} bytes)")
                self.s3.put_object(Bucket=self.s3_bucket, Key=key, Body=output_data)
    
    def encrypt(self, data):
        # The Salt
        _salt = os.urandom(128)

        # Encrypt our data
        encrypted_data = self.enc.encrypt_cfb(json.dumps(data), self.backup_passphrase, _salt)

        # Get our HMAC
        hmac = self.enc.sha256sum(self.backup_passphrase.encode(), encrypted_data, bytes=True)

        # _salt=128, hmac=32
        output_data = _salt + hmac + encrypted_data
        return output_data

    def decrypt(self, data):
        _salt = data[:128]              # The Salt        128 bytes
        stored_hmac = data[128:160]     # Stored HMAC      32 bytes
        _encrypted_data = data[160:]    # Encrypted Data
        calculated_hmac = self.enc.sha256sum(self.backup_passphrase, _encrypted_data, bytes=True)
        if calculated_hmac != stored_hmac:
            self.critical("Calculated HMAC differs from stored HMAC.  Has the data been tampered with?")
            return sys.exit()
        _decrypted_data = self.enc.decrypt_cfb(_encrypted_data, self.backup_passphrase, _salt)
        return _decrypted_data

    def restore(self, filename):
        # Download the file
        key = f"{self.s3_path}/{filename}"
        
        try:
            self.s3.head_object(Bucket=self.s3_bucket, Key=key)
        except self.s3.exceptions.ClientError as e:
            sys.exit("Backup file not found.")
    
        request = self.s3.get_object(Bucket=self.s3_bucket, Key=key)
        raw_data = request["Body"].read()

        data = self.decrypt(raw_data)
        print(repr(data))
        print(json.dumps(json.loads(data), indent=4))
        
    def list(self):
        paginator = self.s3.get_paginator("list_objects_v2")
        _list = []
        counter = 0
        for page in paginator.paginate(Bucket=self.s3_bucket, Prefix=self.s3_path):
            for content in page["Contents"]:
                counter += 1
                key = content["Key"].split("/")[1]
                size = content["Size"]
                _list.append(key)
                print(f"{counter:>6,}: {key:90} ({size:>9,} bytes)")

    def timestamp(self):
        return datetime.datetime.now().strftime("%Y-%m-%d.%H%M")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-b",
        "--backup",
        help="Initiate backup of all paths.",
        action="store_true"
    )
    group.add_argument(
        "-l",
        "--list",
        help="List all available backups. (Warning: Can be large)",
        action="store_true"
    )
    group.add_argument(
        "-r",
        "--restore",
        help="List all secrets stored in the specified file.  Warning, secrets are printed to STDOUT!!!"
    )
    args = parser.parse_args()

    backup = Backup()
    
    if args.backup:
        backup.backup()
    elif args.list:
        backup.list()
    elif args.restore:
        backup.restore(args.restore)


if __name__ == "__main__":
    main()


