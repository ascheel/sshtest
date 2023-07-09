import boto3
import botocore
import copy
import sys
import os
import json
import datetime
import yaml


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return 

def stringify_dates(_obj):
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

def p(_dict):
    print(json.dumps(stringify_dates(_dict), indent=4))


class S3:
    def __init__(self, profile, region, testing=True):
        self.profile = profile
        self.region  = region
        self.TESTING = testing
        self.aws = boto3.Session(profile_name=self.profile)
        self.s3 = self.aws.resource("s3", region_name=self.region)

    @staticmethod
    def roll_it():
        config_file = "/etc/ea/ea.yml"
        settings = yaml.load(open(config_file, "r").read(), Loader=yaml.FullLoader)
        region = "us-east-1"
        for profile in settings["aws"]["accounts"]:
            s3 = S3(profile, region, testing=False)
            s3.iterate()

    def list_buckets(self):
        data = self.s3.meta.client.list_buckets()
        for bucket in data["Buckets"]:
            yield bucket["Name"]

    def validate_tag(self, value):
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        if value.lower() == "none":
            return None
        
    def put_tag(self, bucket, tagname, value):
        tags = self.get_tags(bucket)
        tags2 = []
        for tag in tags:
            if tag["Key"] != "VersioningNotRequired":
                tags2.append(tag)
        tags2.append(
            {
                "Key": "VersioningNotRequired",
                "Value": "True"
            }
        )
        set_tag = bucket.Tagging().put(Tagging={"TagSet": tags2})

    def get_tags(self, bucket):
        tags = []
        try:
            tags = bucket.Tagging().tag_set
        except botocore.exceptions.ClientError:
            tags = []
        return tags

    def get_tag(self, bucket, tagname):
        tags = self.get_tags(bucket)
        for tag in tags:
            if tag["Key"] == tagname:
                return self.validate_tag(tag["Value"])
        return None

    def iterate(self):
        for bucket_name in self.list_buckets():
            bucket = self.s3.Bucket(bucket_name)
            versioning = bucket.Versioning().status
            versioning_tag = self.get_tag(bucket, "VersioningNotRequired")
            print("{:15} {:10} {:75}: {:10}: {:20}".format(self.profile, self.region, bucket.name, str(versioning), str(versioning_tag)), end="")
            if versioning == None and versioning_tag != True:
                if not self.TESTING:
                    self.put_tag(bucket, "VersioningNotRequired", "True")
                    print("Fixed.", end="")
                else:
                    print("Fixed, but not really (testing).", end="")
            print()


def main():
    S3.roll_it()


if __name__ == "__main__":
    main()

