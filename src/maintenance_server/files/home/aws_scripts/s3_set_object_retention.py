import os
import sys
import boto3
import botocore
import datetime
import yaml
import json


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


class Retention:
    def __init__(self):
        self.settings = yaml.full_load(open("/etc/ea/ea.yml", "r").read())
        self.retention_days = 30
        self.paths = [
            "s3://ea-aep-bucket-prod/etl/logs/",
            "s3://ea-d365-irl1-bucket-prod/etl/logs/",
            "s3://ea-d365-aus3-bucket-prod/etl/logs/"
        ]
        self.buckets = [item.split("/")[2] for item in self.paths]

    def list_buckets(self, s3):
        results = s3.list_buckets()
        return [bucket["Name"] for bucket in results["Buckets"]]

    def list_files(self, s3, path):
        bucket_name = path.split("/")[2]
        key         = "/".join(path.split("/")[3:])
        if bucket_name not in self.buckets:
            return None
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket_name, Prefix=key):
            for content in page.get("Contents", []):
                yield content["Key"]

    def get_retention_days(self, s3, bucket_name, key):
        results = s3.get_object_retention(
            Bucket=bucket_name,
            Key=key
        )
        p(results)

    def go(self):
        profiles = self.settings["aws"]["accounts"]
        regions = self.settings["aws"]["regions"]
        for profile in profiles:
            self.profile = profile
            print(f"{profile}")
            aws = boto3.Session(profile_name=profile)
            s3 = aws.client("s3", region_name="us-east-1")
            self.buckets = self.list_buckets(s3)
            count = 0
            for path in self.paths:
                print(path.split("/")[2])
                for _file in self.list_files(s3, path):
                    print(_file)
                    count += 1
                    print(self.get_retention_days(s3, path.split("/")[2], _file))
            print(count)

def main():
    r = Retention()
    r.go()


if __name__ == "__main__":
    main()
