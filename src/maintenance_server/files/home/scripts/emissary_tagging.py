import boto3
import sys
import os
import json
import datetime
import socket
import argparse
import yaml


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


class Address:
    def __init__(self, ip, **kwargs):
        self.__ip          = ip
        self.private_ip    = kwargs.get("private_ip")
        self.__type        = kwargs.get("type")
        self.__id          = kwargs.get("id")
        self.__name        = kwargs.get("name")
        self.__elastic     = kwargs.get("elastic")
        self.__associated  = kwargs.get("unassociated")
    
    @property
    def ip(self):
        return self.__ip
    
    @ip.setter
    def ip(self, _in):
        self.__ip = _in

    @property
    def associated(self):
        return self.__associated
    
    @associated.setter
    def associated(self, _in):
        self.__associated = _in

    @property
    def unused_eip(self):
        if self.__elastic and not self.__associated:
            return True
        return False

    @property
    def id(self):
        return self.__id if self.__id else "Unknown"
    
    @id.setter
    def id(self, _in):
        self.__id = _in
    
    @property
    def elastic(self):
        return "Yes" if self.__elastic else "No"
    
    @elastic.setter
    def elastic(self, _in):
        self.__elastic = _in
    
    @property
    def name(self):
        return self.__name if self.__name else "Unknown"
    
    @name.setter
    def name(self, _in):
        self.__name = _in
    
    @property
    def type(self):
        return self.__type if self.__type else "Unknown"
    
    @type.setter
    def type(self, _in):
        self.__type = _in

class EIP:
    def __init__(self, **kwargs):
        self.profile_name = kwargs.get("profile_name")
        self.region_name  = kwargs.get("region_name")
        self.aws          = boto3.Session(profile_name=self.profile_name)
        self.ec2          = self.aws.resource("ec2", region_name=self.region_name)
        self.addresses    = {}
        self.elastic_flag = kwargs.get("flag")

    def set_eip_tags(self):
        addresses = self.ec2.meta.client.describe_addresses().get("Addresses")
        if not addresses:
            return
        for address in addresses:
            _id = address["AllocationId"]
            _ip = address["PublicIp"]
            
            tags = address.get("Tags")
            emissary = self.get_tag(tags, "emissary", exact=True)
            if emissary == None:
                tags = [{"Key": "emissary", "Value": "trusted"}]
                self.ec2.meta.client.create_tags(Resources=[_id,], Tags=tags)
                emissary = "trusted (new)"
            print("{:25} {:15} {:15} {:30} {}".format(self.profile_name, self.region_name, _ip, _id, emissary))

    def get_tag(self, tags, key, **kwargs):
        exact = kwargs.get("exact")
        if exact not in (False, True, None):
            raise ValueError("'exact' keyword argument must be True or False.")
        if not tags:
            return None
        for tag in tags:
            tag_key = None
            if not exact:
                tag_key = tag["Key"].lower()
                _key = key.lower()
            else:
                tag_key = tag["Key"]
                _key = key
            if tag_key == _key:
                return tag["Value"]

def main():
    settings = yaml.load(open("/etc/ea/ea.yml", "r").read(), Loader=yaml.FullLoader)

    for profile in settings["aws"]["accounts"]:
        for region in settings["aws"]["regions"]:
            e = EIP(profile_name=profile, region_name=region)
            e.set_eip_tags()

if __name__ == "__main__":
    main()
