import boto3
import json
import yaml
import os
import sys
import datetime


def stringify_dates(_obj):
    """
    Converts all datetime objects into string equivalents.

    Args:
        _obj (list, dict): input list or dictionary to modify

    Returns:
        input type: new object with strings
    """
    import copy

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


def p(_object):
    print(json.dumps(stringify_dates(_object), indent=4))


class Backup:
    def __init__(self, **kwargs):
        self.profile = kwargs.get("profile_name")
        self.region  = kwargs.get("region_name")
        self.aws = boto3.Session(profile_name=self.profile)
        self.ec2 = self.aws.resource("ec2", region_name=self.region)
        self.emr_instances = [_id for _id in self.get_emr_instances()]
    
    def get_emr_instances(self):
        emr = self.aws.client("emr", region_name=self.region)
        paginator1 = emr.get_paginator("list_clusters")
        for page in paginator1.paginate():
            for cluster in page["Clusters"]:
                state = cluster["Status"]["State"]
                if state.upper().startswith("TERMINATED"):
                    continue
                cluster_id = cluster["Id"]
                paginator2 = emr.get_paginator("list_instances")
                for page in paginator2.paginate(ClusterId=cluster_id):
                    for instance in page["Instances"]:
                        yield instance["Ec2InstanceId"]

    def get_instances(self):
        paginator = self.ec2.meta.client.get_paginator("describe_instances")
        for page in paginator.paginate():
            for reservation in page["Reservations"]:
                for instance in reservation["Instances"]:
                    _id = instance["InstanceId"]
                    if _id in self.emr_instances:
                        continue
                    yield _id
    
    def get_tag(self, tags, key):
        if not tags:
            return None
        for tag in tags:
            if tag["Key"].lower() == key.lower():
                return tag["Value"]

    def tag_em(self):
        for instance_id in self.get_instances():
            instance = self.ec2.Instance(instance_id)
            tags = instance.tags
            name = self.get_tag(tags, "Name")
            tag_list = ["Adobe.EA.AWSBackup{}".format(_type) for _type in ("Hourly", "Daily", "Weekly", "Monthly")]
            new_tags = []
            for key in tag_list:
                value = self.get_tag(tags, key)
                print("{:20} {:15} {:20} {:40} {:25} {}".format(self.profile, self.region, instance_id, str(name), key, value), end="")
                if value == None:
                    new_tags.append({"Key": key, "Value": "yes"})
                    print("  (Fixed)", end="")
                print()
            if new_tags:
                instance.create_tags(Tags=new_tags)
                pass


def main():
    settings = yaml.load(open("/etc/ea/ea.yml", "r").read(), Loader=yaml.FullLoader)
    profiles = [account for account in settings["aws"]["accounts"]]
    regions  = [region for region in settings["aws"]["regions"]]
    for profile in profiles:
        for region in regions:
            b = Backup(region_name=region, profile_name=profile)
            b.tag_em()

if __name__ == "__main__":
    main()
