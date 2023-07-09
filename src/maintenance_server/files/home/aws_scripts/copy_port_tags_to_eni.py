import boto3
import botocore
import yaml
import json
import sys
import os

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

class EniCopy:
    def __init__(self, **kwargs):
        self.profile = kwargs.get("profile_name")
        self.region = kwargs.get("region_name")

        if not self.profile:
            sys.exit("No profile given.")
        if not self.region:
            sys.exit("No region given.")
        
        self.aws = boto3.Session(profile_name=self.profile)
        self.ec2 = self.aws.client("ec2", region_name=self.region)
        self.rds = self.aws.client("rds", region_name=self.region)

        self.settings = yaml.load(open("/etc/ea/ea.yml", "r").read(), Loader=yaml.FullLoader)

    def get_interfaces(self):
        """Iterate through network interfaces."""
        paginator = self.ec2.get_paginator("describe_network_interfaces")
        for page in paginator.paginate():
            for interface in page["NetworkInterfaces"]:
                if not interface.get("Attachment"):
                    continue
                status     = interface["Attachment"]["Status"]
                if status != "attached":
                    continue
                yield interface["NetworkInterfaceId"]

    def get_instances(self):
        """Iterate through instance IDs."""
        paginator = self.ec2.get_paginator("describe_instances")
        for _page in paginator.paginate():
            for _res in _page["Reservations"]:
                for _instance in _res["Instances"]:
                    yield _instance["InstanceId"]

    def get_tag(self, tags, key):
        for tag in tags:
            if tag["Key"].lower() == key.lower():
                return tag["Value"]
        return None

    def roll2(self):
        """Copy everything."""
        resource = self.aws.resource("ec2", region_name=self.region)
        for _id in self.get_instances():
            instance = resource.Instance(_id)
            interfaces = instance.network_interfaces

            ports         = self.get_tag(instance.tags, "Adobe.PublicPorts") or self.get_tag(instance.tags, "Adobe:PublicPorts")
            justification = self.get_tag(instance.tags, "Adobe.PortJustification") or self.get_tag(instance.tags, "Adobe:PortJustification")

            if ports or justification:
                new_tags = []
                if ports:
                    new_tags.append({"Key": "Adobe.PublicPorts", "Value": ports})
                    new_tags.append({"Key": "Adobe:PublicPorts", "Value": ports})
                if justification:
                    new_tags.append({"Key": "Adobe.PortJustification", "Value": justification})
                    new_tags.append({"Key": "Adobe:PortJustification", "Value": justification})
                for interface in interfaces:
                    interface_id  = interface._id
                    self.ec2.create_tags(Resources=[interface_id,], Tags=new_tags)

                    print("{} {} {} {}".format(self.profile, self.region, _id, interface_id))
                    print("    {} - {}".format(ports, justification))

    @staticmethod
    def roll():
        ec = EniCopy(profile_name="na-ea-dev", region_name="us-east-1")
        regions = ec.settings["aws"]["regions"]
        profiles = ec.settings["aws"]["accounts"]

        for profile in profiles:
            for region in regions:
                _ec = EniCopy(profile_name=profile, region_name=region)
                _ec.roll2()

def main():
    EniCopy.roll()

if __name__ == "__main__":
    main()

