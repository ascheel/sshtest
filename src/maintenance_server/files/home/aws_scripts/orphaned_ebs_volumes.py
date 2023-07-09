import boto3
import botocore
import os
import sys
import yaml
import json
from aws_costs import Costs

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


class Volume:
    def __init__(self, profile, region, size):
        self.profile = profile
        self.region  = region
        self.size    = size

class EBS:
    def __init__(self):
        self.orphaned_volumes = []
        self.aws              = None
        self.profile          = None
        self.region           = None
    
    def go(self):
        c = Costs()
        total_cost = 0
        count = 0
        settings = yaml.load(open("/etc/ea/ea.yml", "r").read(), Loader=yaml.FullLoader)
        profiles = settings["aws"]["accounts"]
        regions = settings["aws"]["regions"]
        for profile in profiles:
            #print("Profile: {}".format(profile))
            self.profile = profile
            self.aws = boto3.Session(profile_name=self.profile)
            for region in regions:
                cost = c.unit_cost_ebs(region)[0]
                self.region = region
                self.ec2 = self.aws.client("ec2", region_name=self.region)
                paginator = self.ec2.get_paginator("describe_volumes")
                for page in paginator.paginate():
                    for volume in page["Volumes"]:
                        if not volume["Attachments"]:
                            size = volume["Size"]
                            volume_cost = size * cost
                            total_cost += volume_cost
                            volume_id = volume["VolumeId"]
                            print(f"{self.profile:30} {self.region:15} {volume_id:25} {size:>5} GB   ${volume_cost}")

                            # p(volume)
                            # print(volume_cost)
                            # print(total_cost)
        print(f"                                                                  Total: ${total_cost}")
                



def main():
    ebs = EBS()
    ebs.go()

if __name__ == "__main__":
    main()

