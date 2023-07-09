import boto3
import botocore
import sys
import os
import datetime
import json
import copy
import operator
import csv
import yaml


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

    def get_rows(self, sql, values=None):
        cur = self.db.cursor()
        cur.execute(sql, values)
        return cur.fetchall()
    
    def get_row(self, sql, values=None):
        return self.get_rows(sql, values)[0]
    
    def get_scalar(self, sql, values=None):
        return self.get_row(sql, values)[0]
    
    def db_exec(self, sql, values=None):
        self.get_rows(sql, values)
        
    def scan(self, **kwargs):
        _inbucket = kwargs.get("bucket")
        if not _inbucket:
            grand_total = 0
            f_out = open("s3_{}_inventory.csv".format(datetime.datetime.now().strftime("%F-%H%M")), "a")
            writer = csv.writer(f_out)
            writer.writerow(["Account", "Bucket", "Key", "Size", "Modified"])
            buffer = []
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
                    row = [self.profile, _object.bucket_name, _object.key, _object.size, _object.last_modified]
                    buffer.append(row)
                    if len(buffer) > 10000:
                        [writer.writerow(_row) for _row in buffer]
                        buffer = []
                print("{} - {:75} - {:20,} ({} files)".format(self.profile, bucket_name, total_size, count))
                self.sizes.append([bucket_name, total_size, count])
                grand_total += total_size
            [writer.writerow(_row) for _row in buffer]
            buffer = []
            print("Grand total: {:,}".format(grand_total))
            # print("\n\n\n****************")
            # for row in sorted(self.sizes, key=lambda x: x[1]):
            #     print("{} - {:75} - {:20,} ({} files)".format(self.profile, row[0], row[1], row[2]))
        else:
            f_out = open(f"s3_{datetime.datetime.now().strftime('%F-%H%M')}_{_inbucket}_inventory.csv", "a")
            writer = csv.writer(f_out)
            writer.writerow(["Account", "Bucket", "Key", "Size", "Modified"])
            buffer = []
            bucket = self.s3.Bucket(_inbucket)
            count = 0
            total_size = 0
            for _object in bucket.objects.all():
                count += 1
                total_size += _object.size
                row = [self.profile, _object.bucket_name, _object.key, _object.size, _object.last_modified]
                buffer.append(row)
                if len(buffer) > 10000:
                    [writer.writerow(_row) for _row in buffer]
                    buffer = []
            print("{} - {:75} - {:20,} ({} files)".format(self.profile, _inbucket, total_size, count))
            self.sizes.append([_inbucket, total_size, count])
            [writer.writerow(_row) for _row in buffer]

    @staticmethod
    def go(**kwargs):
        profile = kwargs.get("profile")
        bucket = kwargs.get("bucket")
        if not profile:
            accounts = [_ for _ in yaml.full_load(open("/etc/ea/ea.yml", "r").read())["aws"]["accounts"]]
            for account in accounts:
                s3 = S3(profile_name=account)
                s3.scan()
        else:
            s3 = S3(profile_name=profile)
            s3.scan(bucket=bucket)

    def list_buckets(self):
        buckets = self.s3.meta.client.list_buckets()
        for bucket in buckets["Buckets"]:
            yield bucket["Name"]


def main():
    profile=None
    bucket=None
    if len(sys.argv) not in (1, 3):
        sys.exit(f"Usage: {sys.argv[0]} [profile] [bucket]")
    elif len(sys.argv) == 3:
        profile = sys.argv[1]
        bucket = sys.argv[2]
    S3.go(profile=profile, bucket=bucket)


if __name__ == "__main__":
    main()
