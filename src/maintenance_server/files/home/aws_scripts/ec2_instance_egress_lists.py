import boto3
import botocore
import os
import sys
import yaml
import json
import ipaddress


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


class Ingress:
    def __init__(self, *args, **kwargs):
        self.profile = kwargs.get("profile_name")
        self.region = kwargs.get("region_name")

        self.settings = yaml.full_load(open("/etc/ea/ea.yml", "r").read())
        self.profiles = [_profile for _profile in self.settings["aws"]["accounts"]]
        self.regions  = [_region for _region in self.settings["aws"]["regions"]]

        self.instances = {}
        self.security_groups = {}

    def set_aws(self, profile, region):
        self.profile = profile
        self.region  = region
        self.aws     = boto3.Session(profile_name=self.profile)
        self.ec2     = self.aws.client("ec2", region_name=self.region)
    
    def __list_ec2_instances(self):
        paginator = self.ec2.get_paginator("describe_instances")
        for page in paginator.paginate():
            for reservation in page["Reservations"]:
                for instance in reservation["Instances"]:
                    _id = instance["InstanceId"]
                    if not self.instances.get(_id):
                        self.instances[_id] = instance
                    yield _id

    def __get_instance(self, instance_id):
        return self.instances[instance_id]

    def __list_ec2_security_groups(self):
        paginator = self.ec2.get_paginator("describe_security_groups")
        for page in paginator.paginate():
            for sg in page["SecurityGroups"]:
                _id = sg["GroupId"]
                if not self.security_groups.get(_id):
                    self.security_groups[_id] = sg
                yield _id
    
    def __list_sg_addresses(self, sg_id):
        _sg = self.__get_security_group(sg_id)
        for _perm in _sg["IpPermissions"]:
            for _range in _perm["IpRanges"]:
                yield _range["CidrIp"]

    def __get_security_group(self, sg_id):
        if not self.security_groups.get(sg_id):
            [_ for _ in self.__list_ec2_security_groups()]
        return self.security_groups[sg_id]

    def scan(self):
        # Iterate through EC2 instances
        for _id in self.__list_ec2_instances():
            print(f"        {_id}")
            instance = self.__get_instance(_id)
            if not instance["State"]["Name"] == "running":
                print(f"            Not running.")
                continue
            for _sg in instance["SecurityGroups"]:
                sg_id = _sg["GroupId"]
                sg = self.__get_security_group(sg_id)
                for address in self.__list_sg_addresses(sg_id):
                    star = " "
                    if not ipaddress.IPv4Address(address.split("/")[0]).is_private:
                        star = "*"
                    print(f"          {star}  {address}")

    @staticmethod
    def go():
        i = Ingress()
        for profile in i.profiles:
            print(f"{profile}")
            for region in i.regions:
                print(f"    {region}")
                i.set_aws(profile, region)
                i.scan()


def main():
    Ingress.go()


if __name__ == "__main__":
    main()
