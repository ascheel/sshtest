import boto3
import botocore
import yaml
import json
import sys
import socket


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


class Route53:
    def __init__(self, **kwargs):
        self.profile = kwargs.get("profile_name")
        self.region = kwargs.get("region_name")
        self.aws = boto3.Session(profile_name=self.profile)
        self.r53 = self.aws.client("route53domains", region_name=self.region)
    
    def scan(self):
        paginator = self.r53.get_paginator("list_domains")
        for page in paginator.paginate():
            for domain in page["Domains"]:
                yield domain


def main():
    print("Checking for domains.")
    
    settings = yaml.load(open("/etc/ea/ea.yml", "r").read(), Loader=yaml.FullLoader)
    profiles = settings["aws"]["accounts"]
    regions = settings["aws"]["regions"]

    bad_regions = []
    owned_domains = []

    for profile in profiles:
        print("Profile: {}".format(profile))
        
        for region in regions:
            if region in bad_regions:
                continue
            # if region in ("us-west-1", "us-west-2"):
            #     continue
            print("    Region: {}".format(region))
            
            r53 = Route53(profile_name=profile, region_name=region)

            try:
                for domain in r53.scan():
                    owned_domains.append(domain)
            except botocore.exceptions.EndpointConnectionError as e:
                bad_regions.append(region)
                print("    Bad region")
                continue
    for domain in owned_domains:
        _name = domain["DomainName"]
        print("Domain: {}".format(_name))


if __name__ == "__main__":
    main()
