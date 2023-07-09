import boto3
import sys
import os
import datetime
import argparse
import json
import logging
from botocore.config import Config


### This is Art Scheel's AWS S3 Bucket Emptying utility.  This utility
### will permanently destroy all contents of an S3 Bucket.
###
### USE WITH CAUTION!!!
###
### There is no "undo"


def sizeof_fmt(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


class Empty:
    def __init__(self, args):
        self.args = args

        config = Config(
            retries = {
                'max_attempts': 10,
                'mode': 'standard'
            }
        )

        if self.args.profile:
            self.aws = boto3.Session(profile_name=self.args.profile)
        else:
            self.aws = boto3.Session()

        self.s3         = self.aws.resource("s3", config=config)
        self.bucket     = self.s3.Bucket(self.args.bucket)
        self.versioning = self.s3.BucketVersioning(self.args.bucket).status == "Enabled"

        self.log = logging
        self.format = "%(asctime)s - %(name)s - %(pathname)s:%(lineno)-4d - %(levelname)-8s - %(message)s"
        self.log.getLogger("botocore").setLevel(logging.CRITICAL)
        self.log.getLogger("urllib3").setLevel(logging.CRITICAL)
        self.log.basicConfig(format=self.format, level=logging.INFO)

    def empty(self):
        count                 = 0
        total_size            = 0
        sub_size              = 0
        thousand              = []
        
        start_time = datetime.datetime.now()
        timediff = None

        paginator_description = None
        paginator_sub         = None

        if self.versioning:
            paginator_description = 'list_object_versions'
            paginator_sub         = 'Versions'
        else:
            paginator_description = 'list_objects_v2'
            paginator_sub         = 'Contents'
        
        paginator = self.s3.meta.client.get_paginator(paginator_description)
        for page in paginator.paginate(Bucket=self.args.bucket):
            if page["KeyCount"] == 0:
                self.log.info("No files in bucket.")
                break
            for _obj in page[paginator_sub]:
                _key  = _obj["Key"]
                _size = _obj["Size"]
                _keypair = {"Key": _key}
                if self.versioning:
                    _keypair["VersionId"] = _obj["VersionId"]
                count += 1
                total_size += _size
                sub_size += _size
                self.log.debug(f"Marking {_keypair['Key']} for deletion.")
                thousand.append(_keypair)
                if len(thousand) >= 1000:
                    results = self.s3.meta.client.delete_objects(
                        Bucket=self.args.bucket,
                        Delete={
                            "Objects": thousand,
                            "Quiet": True
                        }
                    )
                    current_time = datetime.datetime.now()
                    timediff = (current_time - start_time)
                    persec = total_size // timediff.total_seconds()
                    # self.log.info(f"{str(timediff).split('.')[0]}: Deleted {count:,} - {sizeof_fmt(total_size)}   (+{sizeof_fmt(sub_size)}) - {count//timediff.total_seconds()}/sec, {sizeof_fmt(persec)} per sec")
                    print(f"{str(datetime.datetime.now()).split('.')[0]} - {str(timediff).split('.')[0]}: Deleted {count:,} - {sizeof_fmt(total_size):8}   (+{sizeof_fmt(sub_size):8}) - {count//timediff.total_seconds():7}/sec, {sizeof_fmt(persec):5} per sec")
                    thousand = []
                    sub_size = 0
        
        if len(thousand) > 0:
            results = self.s3.meta.client.delete_objects(
                Bucket=self.args.bucket,
                Delete={
                    "Objects": thousand,
                    "Quiet": True
                }
            )
            end_time = datetime.datetime.now()
            secs = (end_time - start_time).total_seconds()
            persec = total_size // secs
            # self.log.info(f"{str(timediff).split('.')[0]}: Deleted {count:,} - {sizeof_fmt(total_size)}   (+{sizeof_fmt(sub_size)}) - {count//timediff.total_seconds()}/sec, {sizeof_fmt(persec)} per sec")
            if not timediff:
                # If it's empty, just make it 1 second.
                timediff = datetime.timedelta(seconds=1)
            print(f"{str(datetime.datetime.now()).split('.')[0]} - {str(timediff).split('.')[0]}: Deleted {count:,} - {sizeof_fmt(total_size):8}   (+{sizeof_fmt(sub_size):8}) - {count//timediff.total_seconds():7}/sec, {sizeof_fmt(persec):5} per sec")



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--profile",
        help="AWS Profile."
    )
    parser.add_argument(
        "-b",
        "--bucket",
        help="AWS S3 Bucket Name"
    )
    parser.add_argument(
        "--yes-really",
        help="Are you SURE you really want to empty this bucket?  There is no backing out or undoing.",
        action="store_true"
    )
    args=parser.parse_args()

    if not args.bucket:
        sys.exit("No bucket specified.")
    
    if not args.yes_really:
        sys.exit("You're not really sure.")

    empty = Empty(args)
    empty.empty()


if __name__ == "__main__":
    main()
