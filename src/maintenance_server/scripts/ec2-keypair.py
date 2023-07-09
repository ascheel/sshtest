#!/usr/bin/env python3

import boto3
import os
import json
import hashlib
import base64


def p(_object):
    import datetime
    import copy
    def stringify_dates(_obj):
        """
        Converts all datetime objects into string equivalents.
        Args:
            _obj (list, dict): input list or dictionary to modify
        Returns:
            input type: new object with strings
        """
        def stringify_date(_obj):
            if isinstance(_obj, datetime.datetime):
                return _obj.isoformat()
            return _obj
        _obj_2 = copy.deepcopy(_obj)
        if isinstance(_obj_2, dict):
            for key, value in _obj_2.items():
                _obj_2[key] = stringify_dates(value)
        elif isinstance(_obj, list):
            for offset in range(len(_obj_2)):
                _obj_2[offset] = stringify_dates(_obj_2[offset])
        else:
            _obj_2 = stringify_date(_obj_2)
        return _obj_2
    print(json.dumps(stringify_dates(_object), indent=4))


def md5sum(_input):
    if isinstance(_input, str):
        _input = _input.encode()
    m = hashlib.md5()
    m.update(_input)
    return m.hexdigest()


class KeyPair:
    def __init__(self, **kwargs):
        self.region = kwargs.get("region", os.environ.get("AWS_REGION", "us-east-1"))

        self.aws = boto3.Session()
        self.ec2 = self.aws.client("ec2", region_name=self.region)

        self.keyname = "de-devops"
        dirname = os.path.split(os.path.split(os.path.abspath(__file__))[0])[0]
        self.key_filename = os.path.join(dirname, "files", "home", ".ssh", "id_rsa_devops.pub")

    def get_md5(self):
        _key = open(self.key_filename, "r").read().split()[1]
        _key2 = base64.b64decode(_key)
        return md5sum(_key2)

    def delete(self):
        data = self.ec2.delete_key_pair(
            KeyName=self.keyname
        )
    
    def create(self):
        data = self.ec2.import_key_pair(
            KeyName=self.keyname,
            PublicKeyMaterial=open(self.key_filename, "r").read()
        )

    @staticmethod
    def go():
        kp = KeyPair()
        kp.delete()
        kp.create()


def main():
    KeyPair.go()


if __name__ == "__main__":
    main()

