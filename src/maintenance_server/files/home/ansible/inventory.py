#!/usr/bin/env python3

import boto3
import sys
import os
import paramiko
import re
import yaml
import json
import ipaddress
import datetime
import time
import logging
import traceback
import shutil
import hashlib
import copy
import socket
import re
from EASSH import EASSH


class Inventory:
    def __init__(self, **kwargs):
        self.arg_filename = kwargs.get('filename')
        self.ssh_filename = kwargs.get('ssh')
        self.ansible_dir  = kwargs.get('ansible')

        self.log_format     = "%(asctime)s - %(name)s - %(pathname)s:%(lineno)-4d - %(levelname)-8s - %(message)s"
        self.loglevel       = kwargs.get('loglevel', 'INFO').upper()
        self.log            = self.__set_logging(self.loglevel)

        self.root           = os.path.split(os.path.abspath(__file__))[0]
        self.settings_file  = os.path.join(os.path.expanduser('~'), 'de.yml')
        self.settings       = yaml.load(open(self.settings_file, "r").read(), Loader=yaml.CLoader)

        self.datadir        = os.path.join(self.root, self.settings["inventory"]["datadir"])
        if not os.path.isdir(self.datadir):
            os.makedirs(self.datadir)

        self.date_format    = "%Y-%m-%d_%H%M%S"
        _timestamp          = datetime.datetime.now().strftime(self.date_format)
        self.instance_old   = self.arg_filename or os.path.join(self.datadir, "instances.yml")
        self.instance_file  = os.path.join(self.datadir, f"instances.{_timestamp}.yml")
        self.symlink()

        self.profiles       = [profile for profile in self.settings["aws"]["accounts"]]
        self.regions        = self.settings['aws']['regions']
        self.user_list      = self.settings['inventory']['users']

        self.sshdir = os.path.join(os.path.expanduser('~'), '.ssh')
        self.ssh_blacklist  = ['id_rsa_adobegit']

        self.sleep_seconds = (2, 5, 10, 15, 30, 60)

        # Fix SSH pairs for first attempts
        _attempts = []
        for _item in self.settings['inventory'].get('first_attempts', []):
            _user, _key = _item.split(',')
            _user = _user.strip()
            _key = _key.strip()
            _attempts.append((_user, _key))
        self.settings['inventory']['first_attempts'] = _attempts

        self.instances = None
        self.date_data = {}
        
        self.aws = {}
        self.region = None

        self.__aws_data = None

        self.nines = []
        self.nines_count = 0
    
        self.attempt_array = []

        self.__proxy_ips = self.__populate_proxy_ips()

        self.report = {
            "existing":   [],
            "new":        [],
            "terminated": [],
            "timeout":    [],
            "success":    [],
            "failure":    [],
            "skip":       []
        }

        # logging.basicConfig()
        # logging.getLogger("paramiko").setLevel(logging.DEBUG)

        self.__ssh_keys   = None
        # self.prep_variables()

        self.__load_existing_instances()

    def local_time(self, utc):
        _now = time.time()
        _offset = datetime.datetime.fromtimestamp(_now) - datetime.datetime.utcfromtimestamp(_now)
        return utc.replace(tzinfo=None) + _offset

    def compile_date_data(self):
        for _id, _values in self.instances.items():
            self.date_data[_id] = {
                'launched': _values['launch_time'],
                'seen': datetime.datetime.now()
            }
        print(f"{datetime.datetime.now()} - Compiling date data.  Please stand by.")
        for filename in reversed(sorted(self.instance_file_list())):
            if not re.match('instances\.[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{6}\.yml', os.path.split(filename)[1]):
                continue
            print(f"Working {filename}")
            _data = yaml.load(open(os.path.join(self.datadir, filename), 'r'), Loader=yaml.CLoader)['instances']
            for _id, _values in _data.items():
                if _id in self.date_data:
                    continue
                self.date_data[_id] = {
                    'launched': _values['launch_time'],
                    'seen': self.get_file_timestamp(filename)
                }
        print(f"{datetime.datetime.now()} - Completed compiling date data.")
        self.save()

    def get_file_timestamp(self, filename):
        filename = os.path.split(filename)[1]
        filedate = filename.split('.')[1]
        return datetime.datetime.strptime(filedate, self.date_format)

    def instance_file_list(self):
        for filename in reversed(sorted(os.listdir(self.datadir))):
            yield os.path.join(self.datadir, filename)

    def last_seen(self, instance_id):
        return self.date_data.get(instance_id, {}).get('seen')

    def launched(self, instance_id):
        return self.date_data.get(instance_id, {}).get('launched')

    def set_ssh(self, path):
        self.ssh_filename = path
    
    def set_ansible_dir(self, path):
        self.ansible_dir = path

    def prep_variables(self):
        _ = self.ssh_keys
        _ = self.aws_data

    @property
    def ssh_keys(self):
        if not self.__ssh_keys:
            self.log.info("Gathering keys.")
            _hashes = []
            self.__ssh_keys = []
            if self.settings["inventory"]["explicit_keys"]:
                keylist = self.settings['inventory']["keys"]
            else:
                keylist = os.listdir(self.sshdir)
            for filename in keylist:
                _fullname = os.path.join(self.sshdir, filename)
                if not filename.startswith("id_"):
                    # Only use files starting with id_
                    self.log.debug(f"  File {filename} is not a key, skipping.")
                    continue
                if filename.endswith(".pub"):
                    # Skip public keys files
                    self.log.debug(f"  Key {filename} is public, skipping.")
                    continue
                if filename in self.ssh_blacklist:
                    continue

                _hash = self.sha256sum(open(_fullname, "r").read())
                if _hash not in _hashes:
                    self.log.info(f"  Key {filename} found with hash {_hash[54:]}.")
                    _hashes.append(_hash)
                    self.__ssh_keys.append(filename)
                else:
                    # Key is already here under a different name.  Don't want it.
                    self.log.info(f"    Key {filename} is a duplicate. ({_hash[54:]})")
                    continue
        return self.__ssh_keys

    def __populate_proxy_ips(self):
        ips = []
        for vpc, data in self.settings['proxies'].items():
            ip = data['host']
            if not self._is_ip(ip):
                ip = socket.gethostbyname(ip)
            ips.append(ip)
        return list(set(ips))

    def __set_logging(self, level=None):
        log = logging
        if level:
            loglevel = getattr(log, level)
        else:
            loglevel = log.INFO
        if not isinstance(loglevel, int):
            raise ValueError(f"Invalid LOGLEVEL: {loglevel}")
        log.basicConfig(format=self.log_format, level=loglevel)
        log.getLogger("botocore").setLevel(logging.CRITICAL)
        log.getLogger("urllib3").setLevel(logging.CRITICAL)
        if loglevel == logging.INFO:
            log.getLogger("paramiko").setLevel(logging.CRITICAL)
        else:
            log.getLogger("paramiko").setLevel(loglevel)
        return log


    @property
    def aws_data(self):
        if not self.__aws_data:
            self.__aws_data = {}
            self.log.info("Gathering AWS Instance Data.  This may take a while.")
            for _profile in self.profiles:
                self.log.info(f"  Checking profile {_profile}")
                if not self.__aws_data.get(_profile):
                    self.__aws_data[_profile] = {}
                aws = self.conn(_profile)
                for _region in self.regions:
                    if not self.__aws_data[_profile].get(_region):
                        self.__aws_data[_profile][_region] = {}

                    _message = f"    Checking region {_region}"
                    _count = 0

                    client = aws.client('ec2', region_name=_region)
                    paginator = client.get_paginator('describe_instances')
                    for _page in paginator.paginate():
                        for _reservation in _page['Reservations']:
                            for _instance in _reservation['Instances']:
                                _count += 1
                                self.__aws_data[_profile][_region][_instance['InstanceId']] = _instance
                    if _count > 0:
                        _message += f"  ({_count})"
                    self.log.info(_message)
        return self.__aws_data

    def conn(self, profile):
        if not self.aws.get(profile):
            self.aws[profile] = boto3.Session(profile_name=profile)

            # Load AWS data
        return self.aws[profile]
    
    def __load_existing_instances(self):
        self.log.debug("Loading existing instances.")
        if not os.path.isfile(self.instance_old):
            self.instances = {}
            return
        _data = yaml.load(open(self.instance_old, "r").read(), Loader=yaml.CLoader)
        self.instances = _data['instances']
        self.report["existing"] = [instance_id for instance_id in self.instances]
        self.log.debug(f"Loaded {len(self.report['existing'])} instances.")
        
        _dates_file = os.path.join(self.datadir, "dates.yml")
        if os.path.isfile(_dates_file):
            self.date_data = yaml.load(open(_dates_file, 'r').read(), Loader=yaml.CLoader)
        else:
            self.date_data = {}

    def _is_terminated(self, instance_id):
        # Check if it exists in AWS
        
        _gotit = False
        _instance = self._get_aws_instance(instance_id)
        if _instance and _instance['State']['Name'] == 'terminated':
            self.log.debug(f"Instance {instance_id} is terminated.")
            return True
        elif _instance:
            self.log.debug(f"Instance {instance_id} exists and not terminated.")
            return False
        else:
            self.log.debug(f"Instance {instance_id} is not in AWS anymore.")
            return True

    def _get_aws_instance(self, instance_id):
        for _account in self.aws_data:
            for _region in self.aws_data[_account]:
                if self.aws_data[_account][_region].get(instance_id):
                    self.aws_data[_account][_region][instance_id]['region'] = _region
                    self.aws_data[_account][_region][instance_id]['account'] = _account
                    return self.aws_data[_account][_region][instance_id]

    def __update_instances(self):
        _count = 0
        self.log.info("Updating instances.")
        _instances = copy.deepcopy(self.instances)
        for instance_id, _values in _instances.items():
            _account = _values['account']
            _region = _values['region']

            if self._is_terminated(instance_id):
                _count += 1
                self.log.info(f"Removing data for instance {instance_id}")
                del self.instances[instance_id]
                self.report["terminated"].append(instance_id)
            else:
                _new_data = self._get_aws_metadata(instance_id)
                self.instances[instance_id].update(_new_data)
        self.log.info(f"  Found {_count} deleted instances.")
        
    def get_tag(self, instance_id, key):
        for _key, value in self._get_tags(self.instances[instance_id]).items():
            if _key.lower() == key.lower():
                return value

    def _get_tags(self, data):
        _output = {}
        tags = data.get('Tags', [])
        for tag in tags:
            _output[tag['Key']] = tag['Value']
        return _output
    
    def _get_aws_metadata(self, instance_id):
        _instance = self._get_aws_instance(instance_id)
        _output = {
            'id':           instance_id,
            'account':      _instance['account'],
            'region':       _instance['region'],
            'vpc':          _instance.get('VpcId'),
            'ami':          _instance['ImageId'],
            'size':         _instance['InstanceType'],
            'launch_time':  _instance['LaunchTime'],
            'private_ip':   _instance.get('PrivateIpAddress'),
            'public_ip':    _instance.get('PublicIpAddress'),
            'state':        _instance['State']['Name'],
            'subnet':       _instance.get('SubnetId'),
            'tags':         self._get_tags(_instance),
            'env':          self.settings['aws']['accounts'][_instance['account']]['env'],
            'name':         self._get_tags(_instance).get('Name'),
            'keypair_name': _instance.get('KeyName')
        }
        return _output

    def _instance_data(self, _id):
        _instance = self._get_aws_instance(_id)
        if not _instance:
            raise ValueError(f"Instance {_id} not found.")

        _output = self._get_aws_metadata(_id)
        _output['ssh_key'] = None
        _output['user'] = None
        _output['notes'] = None
        _output['skip'] = None
        _output['os'] = None
        return _output
    
    def __find_new_instances(self):
        self.log.info("Finding new instances.")
        for _account, _regions in self.aws_data.items():
            for _region, _instances in _regions.items():
                for instance_id, _instance in _instances.items():
                    if not self.instances.get(instance_id):
                        self.instances[instance_id] = self._instance_data(instance_id)
                        self.report["new"].append(instance_id)
    
    def __get_proxy_info(self, vpc):
        if not self.settings['proxies'].get(vpc):
            return {}
        self.log.debug(f"Found proxy information: {self.settings['proxies'][vpc]}")
        return self.settings['proxies'][vpc]
    
    def _is_ip(self, ip):
        output = True
        try:
            ipaddress.ip_address(ip)
        except:
            output = False
        return output

    def sha256sum(self, text=None, **kwargs):
        if text and kwargs.get("file"):
            raise ValueError("Both text and file specified.  Choose one.")
        if not text and not kwargs.get("file"):
            raise ValueError("text or file required.")
        
        m = hashlib.sha256()
        if text:
            m.update(text.encode())
            return m.hexdigest()
        elif kwargs.get("file"):
            m.update(open(kwargs["file"], "r").read().encode())
            return m.hexdigest()
        else:
            raise NotImplementedError("Not sure how you got here.")

    def __user_key_sum(self, instance_id, user, key):
        return f"{instance_id},{user},{key}"

    def __already_tried(self, _user, _key, _array):
        _text = self.__user_key_sum(_user, _key)
        _sum = self.sha256sum(_text)
        return _sum in _array

    def __try_instance(self, instance_id):
        if self.instances[instance_id]['state'] == 'terminated':
            self.instances[instance_id]['skip'] = True
            self.instances[instance_id]['skip_note'] = 'terminated'
            self.instances[instance_id]['skip_date'] = str(datetime.datetime.now())
            self.log.info("  Terminated, skipping.")
            return
        if not self.instances[instance_id].get('keypair_name'):
            self.instances[instance_id]['skip'] = True
            self.instances[instance_id]['skip_note'] = 'no key pair'
            self.instances[instance_id]['skip_date'] = str(datetime.datetime.now())
            self.log.info("  Created without key pair, skipping.")
        if not self.instances[instance_id].get('user') and not self.instances[instance_id].get('skip'):
            host = self.instances[instance_id]['private_ip']

            if self.__get_proxy_info(self.instances[instance_id]['vpc']):
                self.log.debug("  Connecting with proxy.")
            else:
                self.log.debug("  Connecting without proxy.")
            
            if not host:
                self.log.info(f"    No host defined for {instance_id}.  (Is it pending termination?)")
                return
                # This logic should never get hit.  Terminated instances should be skipped.


            self.log.debug("  First attempts.")
            for user, key in self.settings['inventory']['first_attempts']:
                # Try our first attempts
                self.log.debug(f"    User {user} / Key {key}")
                code = self.__try_user_key(instance_id, user, key)
                self.log.debug(f"    Return code: {code}")
                if code in (0, 1):
                    return code

            for user in self.user_list:
                # Iterate over users
                for key in self.ssh_keys:
                    # Iterate over keys
                    self.log.debug(f"  Trying key {key}")
                    code = self.__try_user_key(instance_id, user, key)
                    self.log.debug(f"  Return code: {code}")
                    if code == 0:
                        self.log.debug("    Success.")
                    elif code == 1:
                        self.log.debug("    Timeout.")
                    elif code == 2:
                        self.log.debug("    Permission Denied.")
                    elif code == 3:
                        self.log.debug("    EOFError.")
                    elif code == 11:
                        self.log.debug("    Proxy Timeout.")
                    elif code == 12:
                        self.log.debug("    Proxy Permission Denied.")
                    elif code == 13:
                        self.log.debug("    Proxy EOFError")
                    elif code == 999:
                        self.log.debug("    999 error")
                    elif code == -1:
                        self.log.debug("    Skipped [-1])")
                    else:
                        self.log.debug(f"    Unknown error ({code})")
                    if code in (0, 1):
                        return code
                    # If we got this far, should we assume another attempt is needed?
                    if code != -1:
                        self.log.debug(f"Sleeping for {self.sleep_seconds[self.nines_count]} seconds.")
                        # No delay if we skipped a login attempt.
                        time.sleep(self.sleep_seconds[self.nines_count])
                    continue
            # If we got this far, it's a failure.
            self.report["failure"].append(instance_id)
            # Should we skip it?
            if self.settings['inventory']['skip_on_no_creds']:
                self.instances[instance_id]['skip'] = True
                self.instances[instance_id]['skip_note'] = "No credentials found."
                self.instances[instance_id]['skip_date'] = str(datetime.datetime.now())
                self.log.info("No successful combination of credentials found.  Skipping permanently.")
            else:
                self.log.info("No successful combination of credentials found.")


    def is_jump_host(self, instance_id):
        for _ip in ('public_ip', 'private_ip'):
            if self.instances[instance_id][_ip] in self.__proxy_ips:
                return True
        return False

    def __try_user_key(self, instance_id, user, key):
        if self.__user_key_sum(instance_id, user, key) in self.attempt_array:
            self.log.debug(f"  Key combo already tried: {user} / {key}")
            return -1
        elif self.instances[instance_id].get('user'):
            return -1
        elif self.instances[instance_id].get('skip'):
            return -1

        host = self.instances[instance_id]['private_ip']
        port = self.instances[instance_id].get('port', 22)
        proxy_info = self.__get_proxy_info(self.instances[instance_id]['vpc'])
        self.log.debug(f"  Private IP: {self.instances[instance_id]['private_ip']}")
        self.log.debug(f"  Public IP:  {self.instances[instance_id]['public_ip']}")
        self.log.debug(f"  Proxy info: {proxy_info}")

        key_file = os.path.join(self.sshdir, key)
        results = None
        
        if self.is_jump_host(instance_id):
            self.log.debug("Detected jump host.")
            if not self.instances[instance_id]['public_ip']:
                raise ValueError(f"Instance {instance_id} is a jump host, but has no public IP.")
            # This should be pre-defined in settings.yml and have a public IP.
            # Only jump hosts should get in without a proxy.  All others should use a jump host.
            host = self.instances[instance_id]['public_ip']
            self.log.info(f"  Trying {instance_id} ({self.instances[instance_id]['account']}): {user}@{host} / {key}")
            self.log.debug("  Jump host.  Connecting without proxy.")
            self.log.debug(f"  Host: {host}")
            self.log.debug(f"  User: {user}")
            self.log.debug(f"  Key: {key_file}")
            self.log.debug(f"  Port: {port}")
            results = EASSH.try_login(
                host,
                user,
                key_file,
                port,
                detect_os=True
            )
        elif not proxy_info:
            self.log.debug("Did not detect proxy.  Using public IP.")
            # No proxy info, use the public IP.
            host = self.instances[instance_id]['public_ip']
            self.log.info(f"  Trying {instance_id} ({self.instances[instance_id]['account']}): {user}@{host} / {key}")
            self.log.debug("  Connecting without proxy.")
            self.log.debug(f"  Host: {host}")
            self.log.debug(f"  User: {user}")
            self.log.debug(f"  Key: {key_file}")
            self.log.debug(f"  Port: {port}")
            results = EASSH.try_login(
                host,
                user,
                key_file,
                port,
                detect_os=True
            )
        elif proxy_info:
            self.log.info(f"  Trying {instance_id} ({self.instances[instance_id]['account']}): {user}@{host} / {key}")
            self.log.debug(f"Proxy detected: {proxy_info}")
        # _public_ip = self.instances[instance_id]['public_ip']
        # if proxy_info and not _public_ip:
            self.log.debug("  Connecting with proxy.")
            self.log.debug("  Proxy defined, but no public IP.")
            self.log.debug(f"  Host: {host}")
            self.log.debug(f"  User: {user}")
            self.log.debug(f"  Key: {key_file}")
            self.log.debug(f"  Port: {port}")
            self.log.debug(f"  Proxy host: {proxy_info['host']}")
            self.log.debug(f"  Proxy user: {proxy_info['user']}")
            self.log.debug(f"  Proxy key: {proxy_info['key']}")
            self.log.debug(f"  Proxy port: {proxy_info['port']}")
            results = EASSH.try_login(
                host,
                user,
                key_file,
                port,
                proxy_host=proxy_info['host'],
                proxy_user=proxy_info['user'],
                proxy_key=proxy_info['key'],
                proxy_port=proxy_info['port'],
                detect_os=True
            )
        else:
            raise ValueError(f"Instance {instance_id} has no proxy defined and has no public IP.")

        if results['returncode'] == 0:
            self.instances[instance_id]['user'] = results['user']
            self.instances[instance_id]['ssh_key'] = results['key']
            self.instances[instance_id]['os'] = results['os']
            self.log.info("    Success")
        elif results['returncode'] == 1:
            # Timeout
            self.instances[instance_id]['skip'] = True
            self.instances[instance_id]['skip_note'] = 'Timeout'
            self.instances[instance_id]['skip_date'] = str(datetime.datetime.now())
            self.log.info("    Timeout")
        elif results['returncode'] == 999:
            # Banner timeout?
            if instance_id not in self.nines:
                self.nines.append(instance_id)
                self.log.debug(f"  Adding instance {instance_id} to self.nines.")
            else:
                self.log.debug(f"  Instance {instance_id} already in self.nines.")
            self.log.debug(f"  {self.nines}")
            self.log.debug(f"    Unknown failure ({results['returncode']})")
        self.attempt_array.append(self.__user_key_sum(instance_id, user, key))
        return results['returncode']

    def instance_needs_tried(self, instance_id):
        if self.instances[instance_id].get('user'):
            return False
        if self.instances[instance_id].get('skip'):
            return False
        return True
    
    def __populate_login_details(self):
        _instance_count = 0
        for instance_id in self.instances:
            if self.instance_needs_tried(instance_id):
                self.log.info(f"Instance: {instance_id}")
                code = self.__try_instance(instance_id)
                if code in (0, 1):
                    if code == 0:
                        # Successful login?  Got our details.  NEXT!
                        self.log.debug("  Success code received.  Moving to next instance.")
                        self.report['success'].append(instance_id)
                    elif code == 1:
                        # Timeout?  No need to try more.  Network issue.
                        self.log.debug("  Timeout code received.  Moving to next instance.")
                        self.report['timeout'].append(instance_id)
                    if self.instances[instance_id]['skip'] != True:
                        _instance_count += 1
                        if _instance_count % 10 == 0:
                            self.save()
                    continue
                else:
                    self.log.debug(f"  Code {code} received.  Trying next user/key combo.")
                _instance_count += 1
                if _instance_count % 10 == 0:
                    self.save()
            else:
                self.log.debug(f"Instance {instance_id} already populated.")
        self.save()

    def get_ansible_dict_by_id(self, instance_id):
        instance = self.instances.get(instance_id)
        if not instance:
            raise ValueError(f"Instance {instance_id} does not exist in inventory.")
        
        proxy_info = self.__get_proxy_info(instance["vpc"])
        host = instance["private_ip"]

        if self.is_jump_host(instance_id):
            host = instance['public_ip']
        elif not proxy_info and instance['public_ip']:
            host = instance['public_ip']

        _dict = {
            'ansible_connection': 'ssh',
            'ansible_host': host,
            'ansible_ssh_private_key_file': instance['ssh_key'],
            'ansible_user': instance['user'],
            'env': self.settings['aws']['accounts'][instance['account']]['env'],
            'name': instance['name'],
            'os': instance['os'],
            'region': instance['region'],
            'splunk_dir': self.settings['aws']['accounts'][instance['account']]['splunk_dir']
        }
        if proxy_info:
            _dict['ansible_ssh_common_args'] = f'-oProxyJump={proxy_info["host"]}'
        return _dict

    def os_map(self, instance_id):
        return self.settings['inventory']['os_map'].get(self.instances[instance_id]['os'], 'unknown')

    def export_to_ansible_oneshot(self, instances):
        _data = {}
        _found = []
        _unfound = []
        for instance_id in instances:
            if not self.instances.get(instance_id):
                _unfound.append(instance_id)
                self.log.debug("Instance not found.")
                continue
            _found.append(instance_id)
            _os = self.os_map(instance_id)
            _data.setdefault(_os, {"hosts": {}})
            _data[_os]["hosts"][instance_id] = self.get_ansible_dict_by_id(instance_id)
        
        if len(_found) == 0:
            print("No instances found.  Nothing to do.")
            sys.exit(1)

        filename = None
        num = -1
        while True:
            num += 1
            if num == 0:
                filename = "/tmp/oneshot.yml"
            else:
                filename = f"/tmp/oneshot.{num}.yml"
            if not os.path.exists(filename):
                break
            
        print("Found:")
        for instance_id in _found:
            print(f"  {instance_id}")
        print(f"{len(_found)} instances.")
        print("")
        print("Not found:")
        for instance_id in _unfound:
            print(f"  {instance_id}")
        print(f"{len(_unfound)} instances.")
        open(filename, "w").write(yaml.dump(_data))
        print("")
        print(f"File {filename} created.")

    def export_to_ansible(self):
        self.log.info(f"Exporting Ansible information to {self.ansible_dir}")
        _data = {}
        for instance_id, instance in self.instances.items():
            if instance['skip']:
                continue
            self.log.debug(f"Instance data:")
            self.log.debug(json.dumps(instance, indent=4, default=str))
            self.log.debug(f"Exporting {instance_id}")

            _data.setdefault(self.os_map(instance_id), {"hosts": {}})

            _ansible_instance = self.get_ansible_dict_by_id(instance_id)
            _data[self.os_map(instance_id)]['hosts'][instance_id] = _ansible_instance

        ansible_file = os.path.join(self.ansible_dir, 'ansible_inventory.yml')
        self.log.debug(f"Writing out to {ansible_file}")
        if os.path.exists(ansible_file):
            os.remove(ansible_file)
        open(ansible_file, 'w').write(yaml.dump(_data, Dumper=yaml.CDumper))

    def _translate_tilde_in_path(self, path):
        return path.replace('~', os.path.expanduser('~'))

    def _has_ssh_include(self):
        _ssh_config = os.path.join(os.path.expanduser('~'), ".ssh", "config")
        _test_lines = (f"Include {self.ssh_filename}", f"Include {self._translate_tilde_in_path(self.ssh_filename)}")
        with open(_ssh_config, "r") as f_in:
            for line in f_in:
                line = line.strip()
                if line in _test_lines:
                    self.log.debug(f"Found {line}")
                    return True
        self.log.debug("Include line not found.")
        return False

    def _insert_ssh_include(self):
        if self._has_ssh_include():
            return
        else:
            _ssh_config = os.path.join(os.path.expanduser('~'), ".ssh", "config")
            _backup     = f"{_ssh_config}.{datetime.datetime.now().strftime('%Y-%m-%d')}"
            self.log.debug(f"Backing up {_ssh_config} to {_backup}")
            shutil.copy2(_ssh_config, _backup)
            _ssh_config_content = open(_ssh_config, "r").read()
            os.remove(_ssh_config)
            with open(_ssh_config, "w") as f_out:
                f_out.write(f"Include {self.ssh_filename}\n")
                if not _ssh_config_content.startswith("Include "):
                    f_out.write("\n")
                f_out.write(_ssh_config_content)

    def export_to_ssh(self):
        self.log.info(f"Exporting SSH information to {self.ssh_filename}")
        f_out = open(self.ssh_filename, "w")
        count = 0
        for instance_id, instance in self.instances.items():
            self.log.debug(f"Instance data:")
            self.log.debug(json.dumps(instance, indent=4, default=str))
            self.log.debug(f"Exporting {instance_id}")
            if instance['skip']:
                self.log.debug(f"Skipping ({instance.get('skip_note')}).")
                continue
            if instance['state'] == 'terminated':
                self.log.debug("Skipping (terminated).")
                continue
            proxy_info = self.__get_proxy_info(instance["vpc"])
            host = instance["private_ip"]

            if self.is_jump_host(instance_id):
                host = instance["public_ip"]
            elif not proxy_info and instance["public_ip"]:
                host = instance["public_ip"]
            name = self.get_tag(instance_id, "Name")

            _names = []
            if name:
                _names += self.__fix_name(name)
                _names += self.__fix_name(name.lower())
                _names = list(set(_names))

            _key = instance['ssh_key']
            if _key:
                _key = os.path.join("~", ".ssh", _key)

            _text = []
            _text.append(f"Host {instance_id} {host} {' '.join(_names)}")
            _text.append(f"\tHostname {host}")
            _text.append(f"\tUser {instance['user']}")
            _text.append(f"\tIdentityFile {_key}")
            if host and ipaddress.IPv4Address(host).is_private:
                if proxy_info:
                    _text.append(f"\tProxyJump {proxy_info['host']}")
            f_out.write("\n".join(_text))
            f_out.write("\n\n")
            count += 1
        self.log.info(f"Exported {count} connections to {self.ssh_filename}")
        self._insert_ssh_include()


    def __fix_name(self, name):
        return (name.replace(" ", ""), name.replace(" ", "_"), name.replace(" ", "-"))


    def roll(self):
        if self.arg_filename:
            return
        self.__update_instances()
        self.__find_new_instances()
        self.__populate_login_details()

    def __get_counts(self):
        counts = {}
        for instance_id, instance in self.instances.items():
            account = instance['account']
            if not counts.get(account):
                counts[account] = 0
            counts[account] += 1
        return counts

    def save(self):
        self.log.info(f"Saving progress to {self.instance_file}.")
        _output_data = {
            'metadata': {
                'timestamp': datetime.datetime.now(),
                'count': {
                    'total': len(self.instances)
                }
            },
            'instances': self.instances,
            # 'dates': self.date_data
        }
        for _account, _count in self.__get_counts().items():
            _output_data['metadata']['count'][_account] = _count
        _data = yaml.dump(_output_data, Dumper=yaml.CDumper)
        open(self.instance_file, "w").write(_data)
        
        open(os.path.join(self.datadir, "dates.yml"), 'w').write(yaml.dump(self.date_data, Dumper=yaml.CDumper))
        self.log.debug("Done.")

    def display_report(self):
        for instance_id in self.instances:
            if self.instances[instance_id].get('skip'):
                self.report['skip'].append(instance_id)

        for _report in self.report:
            self.report[_report] = sorted(list(set(self.report[_report])))

        # Existing
        print(f"Existing instances ({len(self.report['existing'])})")
        count = 0
        for instance_id in self.report['existing']:
            count += 1
            print(f"  {count:>3}. {instance_id}")
        
        # New
        print()
        print(f"New instances ({len(self.report['new'])})")
        count = 0
        for instance_id in self.report['new']:
            count += 1
            print(f"  {count:>3}. {instance_id}")
        
        # Terminated
        print()
        print(f"Terminated instances ({len(self.report['terminated'])})")
        count = 0
        for instance_id in self.report['terminated']:
            count += 1
            print(f"  {count:>3}. {instance_id}")
        
        # Timeouts
        print()
        print(f"Timeouts ({len(self.report['timeout'])})")
        count = 0
        for instance_id in self.report['timeout']:
            count += 1
            print(f"  {count:>3}. {instance_id}")
        
        # Success
        print()
        print(f"Credentials found ({len(self.report['success'])})")
        count = 0
        for instance_id in self.report['success']:
            count += 1
            print(f"  {count:>3}. {instance_id}")
        
        # Failure
        print()
        print(f"New instances, couldn't log in ({len(self.report['failure'])})")
        count = 0
        for instance_id in self.report['failure']:
            count += 1
            print(f"  {count:>3}. {instance_id}")

        # Skipped
        print()
        print(f"Skipped instances ({len(self.report['skip'])})")
        count = 0
        for instance_id in self.report['skip']:
            count += 1
            print(f"  {count:>3}. {instance_id}")
        
    # def update_aws_metadata(self):
    #     for instance_id, instance in self.instances.items():
    #         if instance['state'] != 'terminated':
    #             continue
            
    
    def symlink(self):
        if self.arg_filename:
            return
        _instance_previous = os.path.split(os.path.join(self.datadir, "instances.previous.yml"))[1]
        _instance_old      = os.path.split(self.instance_old)[1]
        _instance_new      = os.path.split(self.instance_file)[1]

        # _max_count = self.settings["inventory"]["max_backups"]
        
        # for count in range(_max_count + 100, 0, -1):
        #     filename = f"instances.{count}.yml"

        #     if count > _max_count:
        #         if os.path.exists(os.path.join(self.datadir, filename)):
        #             os.remove(os.path.join(self.datadir, filename))
        #         continue

        #     if count == 1:
        #         filename_next = "instances.yml"
        #     else:
        #         filename_next = f"instances.{count - 1}.yml"

        #     if os.path.exists(os.path.join(self.datadir, filename)):
        #         if not os.path.islink(os.path.join(self.datadir, filename)):
        #             raise EnvironmentError(f"File {filename} needs to be a symlink if it exists.")
        #         os.remove(os.path.join(self.datadir, filename))
        #     if os.path.exists(os.path.join(self.datadir, filename_next)):
        #         os.symlink(os.readlink(os.path.join(self.datadir, filename_next)), os.path.join(self.datadir, filename))
        #         os.remove(os.path.join(self.datadir, filename_next))
        #         self.log.debug(f"Creating link: {filename_next} => {filename}")

        # Link to new
        if os.path.islink(self.instance_old):
            os.remove(self.instance_old)

        os.symlink(_instance_new, self.instance_old)
        self.log.debug(f"Symlink created: {_instance_new} => {_instance_old}")

    def find(self, **kwargs):
        id_only = kwargs.get("id_only")
        instances = kwargs.get("instances")
                    
        _found_instance_ids = []
        _unfound_instance_ids = []
        if kwargs.get("nullusers"):
            for instance_id, instance in self.instances.items():
                if not instance['user']:
                    _found_instance_ids.append(instance_id)
        else:
            for item in instances:
                foundit = False
                for instance_id, instance in self.instances.items():
                    if instance['state'] == 'terminated':
                        continue
                    if instance_id == item:
                        _found_instance_ids.append(instance_id)
                        foundit = True
                        continue
                    if id_only:
                        # We checking only for instance IDs?  NEXT!
                        continue
                    for key, value in instance.items():
                        if item.lower() in str(value).lower():
                            _found_instance_ids.append(instance_id)
                            foundit = True
                if not foundit:
                    _unfound_instance_ids.append(item)
        _found_instance_ids = sorted(list(set(_found_instance_ids)))
        _unfound_instance_ids = sorted(list(set(_unfound_instance_ids)))
        return (_found_instance_ids, _unfound_instance_ids)


def main():
    sys.exit("This is a library and should not be executed directly.")


if __name__ == "__main__":
    main()
