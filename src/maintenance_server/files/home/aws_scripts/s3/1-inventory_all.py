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
        self.profile = None
        self.region  = "us-east-1"
        self.aws     = None
        self.s3      = None

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
        f_out = open("s3_{}_inventory.csv".format(datetime.datetime.now().strftime("%F-%H%M")), "w")

        accounts = [_ for _ in yaml.full_load(open("/etc/ea/ea.yml", "r").read())["aws"]["accounts"]]
        writer = csv.writer(f_out)
        writer.writerow(["Account", "Bucket", "Key", "Size", "Modified"])

        _last_time = datetime.datetime.now()

        _grand_count = 0
        for account in accounts:
            self.profile = account
            self.aws = boto3.Session(profile_name=self.profile)
            self.s3 = self.aws.resource("s3", region_name=self.region)

            grand_total = 0
            buffer = []
            for bucket_name in self.list_buckets():
                count = 0
                total_size = 0
                bucket = self.s3.Bucket(bucket_name)
                try:
                    for _object in bucket.objects.all():
                        _grand_count += 1
                        count += 1
                        if not _grand_count % 100000:
                            _time_diff = datetime.datetime.now() - _last_time
                            _last_time = datetime.datetime.now()
                            print("100k records in {} sec ({:,}) ({:,}/sec)".format(_time_diff.seconds, _grand_count, 100000 // _time_diff.seconds))
                            #pass
                            #print("     {:70}   {:20,} ({} files)".format(bucket_name, total_size, count))
                        total_size += _object.size
                        row = [self.profile, _object.bucket_name, _object.key, _object.size, _object.last_modified]
                        buffer.append(row)
                        if len(buffer) > 10000:
                            [writer.writerow(_row) for _row in buffer]
                            buffer = []
                    print("{} - {:75} - {:20,} ({} files)".format(self.profile, bucket_name, total_size, count))
                    grand_total += total_size
                except self.s3.meta.client.exceptions.NoSuchBucket as e:
                    # Sometimes buckets are deleted, but takes several hours to propagate to other regions.
                    # If this happens, a bucket shows up in lists, but puke when you
                    # try to list its contents.
                    continue
            [writer.writerow(_row) for _row in buffer]
            buffer = []
            print("Grand total: {:,}".format(grand_total))

    @staticmethod
    def go(**kwargs):
        accounts = [_ for _ in yaml.full_load(open("/etc/ea/ea.yml", "r").read())["aws"]["accounts"]]
        s3 = S3()
        s3.scan()

    def list_buckets(self):
        buckets = self.s3.meta.client.list_buckets()
        for bucket in buckets["Buckets"]:
            yield bucket["Name"]


def main():
    profile=None
    bucket=None
    S3.go()


if __name__ == "__main__":
    main()
