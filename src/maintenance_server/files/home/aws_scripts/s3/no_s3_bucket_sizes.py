import boto3
import botocore
import sys
import os
import datetime
import json
import copy
import operator


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


def p(_object):
    print(json.dumps(stringify_dates(_object), indent=4))


class S3:
    def __init__(self, **kwargs):
        self.profile = kwargs.get("profile_name")
        if not self.profile:
            sys.exit("Profile is required.")
        region  = "us-east-1"
        self.aws = boto3.Session(profile_name=self.profile)
        self.s3 = self.aws.resource("s3", region_name=region)
        self.sizes = []

    def list_objects(self, bucket_name):
        client = self.s3.meta.client
        paginator = client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket_name)
        for page in pages:
            if page["KeyCount"] == 0:
                return
            for _object in page["Contents"]:
                # yield self.s3.ObjectSummary(bucket_name, _object["Key"])
                yield _object

    def versioning_enabled(self, bucket_name):
        bucket = self.s3.Bucket(bucket_name)
        versioning = bucket.Versioning().status
        return versioning

    def get_versions(self, bucket_name, prefix_key):
        paginator = self.s3.meta.client.get_paginator("list_object_versions")
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix_key):
            for version in page["Versions"]:
                if version["VersionId"] == "null":
                    continue
                yield version

    def scan(self):
        grand_total = 0
        for bucket_name in self.list_buckets():
            count = 0
            total_size = 0
            bucket = self.s3.Bucket(bucket_name)
            for _object in bucket.objects.all():
                count += 1
                if not count % 10000:
                    pass
                    #print("     {:70}   {:20,} ({} files)".format(bucket_name, total_size, count))
                total_size += _object.size
            print("{} - {:75} - {:20,} ({} files)".format(self.profile, bucket_name, total_size, count))
            self.sizes.append([bucket_name, total_size, count])
            grand_total += total_size
        print("Grand total: {:,}".format(grand_total))
        print("\n\n\n****************")
        for row in sorted(self.sizes):
            print("{} - {:75} - {:20,} ({} files)".format(self.profile, row[0], row[1], row[2]))

    @staticmethod
    def go(**kwargs):
        s3 = S3(**kwargs)
        s3.scan()

    def list_buckets(self):
        buckets = self.s3.meta.client.list_buckets()
        for bucket in buckets["Buckets"]:
            yield bucket["Name"]


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: {} <profile_name>".format(sys.argv[0]))
    profile = sys.argv[1]
    S3.go(profile_name=profile)


if __name__ == "__main__":
    main()
