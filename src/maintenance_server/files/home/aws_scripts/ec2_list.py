import boto3
import botocore
import yaml
import sys

def p(_object):
    import json
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

class EC2:
    def __init__(self, **kwargs):
        self.profile = kwargs.get("profile_name")
        self.region = kwargs.get("region_name")
        self.aws = boto3.Session(profile_name=self.profile)
        self.ec2 = self.aws.resource("ec2", region_name=self.region)
        self.emr = self.aws.client("emr", region_name=self.region)
    
    def get_instances(self):
        _paginator = self.ec2.meta.client.get_paginator("describe_instances")
        for _page in _paginator.paginate():
            for _reservation in _page["Reservations"]:
                for _instance in _reservation["Instances"]:
                    yield _instance["InstanceId"]

    def get_tag(self, tags, key, or_else=None):
        if not tags:
            return or_else
        for tag in tags:
            # if tag["Key"] == "Name":
            #     import pdb; pdb.set_trace()
            # print("Tag: {}".format(tag))
            # print("Key: {}".format(key))
            if tag["Key"].lower() == key.lower():
                value = tag["Value"]
                if value.lower() == "true":
                    value = True
                if value.lower() == "false":
                    value = False
                if value.lower() == "none":
                    value = None
                if value == "":
                    value = None
                if value is None:
                    value = or_else
                return value
        return or_else

    def get_emr_clusters(self):
        _paginator = self.emr.get_paginator("list_clusters")
        for _page in _paginator.paginate():
            for _cluster in _page["Clusters"]:
                yield _cluster["Id"]

    def get_emr_name(self, _emr_id):
        if not _emr_id:
            return ""
        for _id in self.get_emr_clusters():
            _paginator = self.emr.get_paginator("list_clusters")
            for _page in _paginator.paginate():
                for _cluster in _page["Clusters"]:
                    if _cluster["Id"] == _emr_id:
                        return _cluster["Name"]
        return None

    def list(self):
        for _id in self.get_instances():
            _instance   = self.ec2.Instance(_id)
            _name       = self.get_tag(_instance.tags, "Name", "(None)")
            _stack_name = self.get_tag(_instance.tags, "aws:cloudformation:stack-name", "")
            _emr_id     = self.get_tag(_instance.tags, "aws:elasticmapreduce:job-flow-id")
            _emr        = self.get_emr_name(_emr_id)
            _ip         = _instance.public_ip_address
            print(
                "{:20} {:10} {:75} {:20} {:15} {:50} {}".format(
                    self.profile,
                    self.region,
                    str(_name),
                    _id,
                    str(_ip),
                    _stack_name,
                    _emr
                )
            )


def main():
    TESTING = False
    if TESTING:
        ec2 = EC2(profile_name="na-ea-devold", region_name="us-west-2")
        ec2.list()
        sys.exit()
    settings = yaml.load(open("/etc/ea/ea.yml", "r").read(), Loader=yaml.FullLoader)
    for _profile in settings["aws"]["accounts"]:
        for _region in settings["aws"]["regions"]:
            ec2 = EC2(profile_name=_profile, region_name=_region)
            ec2.list()

if __name__ == "__main__":
    main()
