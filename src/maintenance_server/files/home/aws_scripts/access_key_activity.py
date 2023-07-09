import sys
import os
import json
import yaml
import boto3
import argparse
import datetime
from dateutil import parser
import gzip
import csv
# import pytz


# This script relies on the git project es/aws-cloudtrail-data-events.  Please ensure it is deployed before attempting to run this script.

# Bucket name:  dx-ea-cloudtrail-<account-number>


class IAMAudit:
    def __init__(self, args):
        self.args = args
        self.validate_args()

        self.__acctno         = None
        self.__acct           = None
        self.__aws_details    = None

        self.__aws            = None
        self.__iam            = None
        self.__cloudtrail     = None
        self.__s3             = None

        self.__access_key_ids = None
        self.__time_start     = None
        self.__time_end       = None
        self.__regions        = None

        self.tmpdir           = os.path.join(os.path.expanduser("~"), "tmp")    # ~/tmp

        self.output_file      = os.path.join(self.tmpdir, "events.json")
        if os.path.isfile(self.output_file):
            os.remove(self.output_file)

        self.output_csv       = os.path.join(self.tmpdir, "events.csv")
        if os.path.isfile(self.output_csv):
            os.remove(self.output_csv)

    def validate_args(self):
        if (self.args.hours or self.args.days or self.args.weeks or self.args.months or self.args.years) and (self.args.start_time or self.args.end_time):
            sys.exit("hours/days/weeks/months/years cannot be used with either start_time or end_time")

    @property
    def regions(self):
        if not self.__regions:
            if not self.args.region:
                self.__regions = [_region for _region in self.aws_details["regions"]]
            else:
                self.__regions = [self.args.region,]
        return self.__regions

    @property
    def time_start(self):
        if not self.__time_start:
            if self.args.start_time:
                self.__time_start = (datetime.datetime.strptime(self.args.start_time, "%Y-%m-%d-%H%M")).astimezone(datetime.timezone.utc)
            elif self.args.hours:
                self.__time_start = (datetime.datetime.now() - datetime.timedelta(hours=self.args.hours)).astimezone(datetime.timezone.utc)
            elif self.args.days:
                self.__time_start = (datetime.datetime.now() - datetime.timedelta(days=self.args.days)).astimezone(datetime.timezone.utc)
            elif self.args.weeks:
                self.__time_start = (datetime.datetime.now() - datetime.timedelta(weeks=self.args.weeks)).astimezone(datetime.timezone.utc)
            elif self.args.months:
                self.__time_start = (datetime.datetime.now() - datetime.timedelta(months=self.args.months)).astimezone(datetime.timezone.utc)
            elif self.args.years:
                self.__time_start = (datetime.datetime.now() - datetime.timedelta(years=self.args.years)).astimezone(datetime.timezone.utc)
            else:
                self.__time_start = (datetime.datetime.now() - datetime.timedelta(hours=24)).astimezone(datetime.timezone.utc)
        return self.__time_start

    @property
    def time_end(self):
        if not self.__time_end:
            if self.args.end_time:
                self.__time_end = datetime.datetime.strptime(self.args.end_time).astimezone(datetime.timezone.utc)
            else:
                self.__time_end = datetime.datetime.now().astimezone(datetime.timezone.utc)
        return self.__time_end

    @property
    def aws(self):
        if not self.__aws:
            _acct = self.acct
            self.__aws = boto3.Session(profile_name=self.acct)
        return self.__aws
        
    @property
    def iam(self):
        if not self.__iam:
            self.__iam = self.aws.resource("iam")
        return self.__iam

    @property
    def cloudtrail(self):
        if not self.__cloudtrail:
            self.__cloudtrail = self.aws.client("cloudtrail")
        return self.__cloudtrail
    
    @property
    def s3(self):
        if not self.__s3:
            self.__s3 = self.aws.resource("s3")
        return self.__s3

    @property
    def aws_details(self):
        if not self.__aws_details:
            self.__aws_details = yaml.safe_load(open("/etc/ea/ea.yml", "r").read())["aws"]
        return self.__aws_details

    @property
    def acctno(self):
        if not self.__acct:
            # Use na-ea-dev to retrieve the account information.  Then discard it.
            aws = boto3.Session(profile_name="na-ea-dev")
            sts = aws.client("sts")
            data = {}
            try:
                data = sts.get_access_key_info(AccessKeyId=self.args.access_key_id)
            except:
                pass
            self.__acctno = data.get("Account", "INVALID ACCESS KEY ID")
        return self.__acctno
    
    @property
    def acct(self):
        if not self.__acct:
            for account, info in self.aws_details["accounts"].items():
                if info["accountno"] == self.acctno:
                    self.__acct = account
        return self.__acct

    @property
    def access_key_ids(self):
        if self.args.user:
            return [_key for _key in self.iam.User(self.args.user).access_keys.all()]
        if self.args.access_key_id:
            return [self.args.access_key_id,]
        return []
    
    def search(self):
        # Use Cloudtrail for now
        _attribute_key   = None
        _attribute_value = None
        
        if self.args.user:
            _attribute_key   = "Username"
            _attribute_value = self.args.user
        
        if self.args.access_key_id:
            _attribute_key   = "AccessKeyId"
            _attribute_value = self.args.access_key_id


        for _region in self.regions:
            self.__cloudtrail = self.aws.client("cloudtrail", region_name=_region)
            paginator = self.cloudtrail.get_paginator("lookup_events")
            for page in paginator.paginate(
                LookupAttributes=[
                    {
                        "AttributeKey": _attribute_key,
                        "AttributeValue": _attribute_value
                    }
                ],
                StartTime=self.time_start,
                EndTime=self.time_end
            ):
                print(page)
                for event in page["Events"]:
                    print(json.dumps(event, indent=4, default=str))
    
    def get_date_from_key(self, key):
        return parser.parse(key.split("/")[7].split("_")[3]).astimezone(datetime.timezone.utc)

    def search_get_log_list(self, bucket):
        print("Searching S3 for included dates.")

        loglist = []

        for _region in self.regions:
            _prefix = f"AWSLogs/{self.acctno}/CloudTrail/{_region}/"
            paginator = self.s3.meta.client.get_paginator("list_objects_v2")
            for page in paginator.paginate(
                Bucket=bucket,
                Prefix=_prefix
            ):
                for item in page["Contents"]:
                    _key = item["Key"]
                    _date = self.get_date_from_key(_key)
                    if not self.key_qualifies(_key):
                        continue
                    loglist.append([_date, _key])
        return [row[1] for row in sorted(loglist)]

    def download_all_events(self, _bucket_name, loglist):
        print("Downloading events from S3.")

        # Local location is self.tmpdri

        f_out = open(self.output_file, "a")
        f_out2 = open(self.output_csv, "a")
        writer = csv.writer(f_out2)

        for _key in loglist:
            _shortdir = os.path.split(_key)[0]
            _dir      = os.path.join(self.tmpdir, _shortdir)
            if not os.path.exists(_dir):
                os.makedirs(_dir)
            if not os.path.isdir(_dir):
                raise FileExistsError(f"{_dir} already exists and is not directory.")
            _filename = os.path.join(self.tmpdir, _key)
            if not os.path.exists(_filename):
                # print(f"Downloading file {_key}...", end="")
                print("-", end="")
                sys.stdout.flush()
                self.s3.meta.client.download_file(_bucket_name, _key, _filename)
                #print("  Done")
            _data = self.get_json_from_file(_filename)
            _records = self.get_qualifying_records(_data)
            _count = 0
            for _record in _records:
                _count += 1
                if not _count % 10:
                    print(".", end="")
                sys.stdout.flush()
                f_out.write(json.dumps(_record, indent=4))
                csv_line = self.get_csv_line(_record)
                writer.writerow(csv_line)

        print("")

    def get_csv_line(self, record):
        _account      = self.get_account_from_record(record)
        _user         = self.get_user_from_record(record)
        _access_key   = self.get_access_key_from_record(record)
        _event_name   = record.get("eventName")
        _event_target = self.get_event_target(record["requestParameters"])
        _source_ip    = record.get("sourceIPAddress")
        _region       = record.get("awsRegion")
        return [_account, _region, _access_key, _event_name, _event_target, _source_ip]

    def get_account_from_record(self, record):
        return record["userIdentity"]["accountId"]

    def get_event_target(self, _request_parameters):
        # This is for S3.  We'll handle others when the time comes.
        bucket = _request_parameters.get("bucketName")
        prefix = _request_parameters.get("prefix")
        return f"{bucket}:{prefix}"

    def get_qualifying_records(self, _data):
        _events = []
        for _record in _data["Records"]:
            _user = self.get_user_from_record(_record)
            _access_key = self.get_access_key_from_record(_record)
            if _access_key in self.access_key_ids or (not _access_key and _user and _user == self.args.user):
                _events.append(_record)
        return _events
    
    def get_json_from_file(self, filename):
        return json.loads(gzip.open(filename, "rb").read().decode())

    def get_access_key_from_record(self, record):
        _user_id = record.get("userIdentity")
        if _user_id:
            return _user_id.get("accessKeyId")
    
    def get_user_from_record(self, record):
        _user_id = record.get("userIdentity")
        if _user_id:
            _session_context = _user_id.get("sessionContext")
            if _session_context:
                _session_issuer = _session_context.get("sessionIssuer")
                if _session_issuer:
                    return _session_issuer.get("userName")

    def parse_all_events(self, loglist):
        print("Parsing Cloudtrail events.")

        _count_gap = 1
        _count = 0
        _events = []
        for _key in loglist:
            _filename = os.path.join(self.tmpdir, _key)
            _contents = self.get_json_from_file(_filename)
            for _record in _contents["Records"]:
                _access_key = self.get_access_key_from_record(_record)                   
                _user = self.get_user_from_record(_record)
                if _access_key in self.access_key_ids or (not _access_key and _user == self.args.user):
                    _events.append(_record)
                    _count += 1
                    if not _count % 10:
                        if _count >= 1000:
                            if not _count % 1000:
                                print(f" {_count}", end="")
                        elif _count >= 100:
                            if not _count % 100:
                                print(f" {_count}", end="")
                        elif _count >= 10:
                            if not _count % 10:
                                print(f" {_count}", end="")
                        else:
                            print(f" {_count}", end="")                            
                    sys.stdout.flush()
        print(f"\nTotal events: {_count}")
        return _events

    def search_logs(self):
        _bucket_name = f"dx-ea-cloudtrail-{self.acctno}"
        loglist = self.search_get_log_list(_bucket_name)
        self.download_all_events(_bucket_name, loglist)
        # events = self.parse_all_events(loglist)
        # print("Saving events to disk:")
        # with open(os.path.join(self.tmpdir, "events.json"), "w") as f_out:
        #     f_out.write(json.dumps(events))

    def key_qualifies(self, key):
        _date = self.get_date_from_key(key)
        return _date >= self.time_start and _date <= self.time_end

def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-u",
        "--user",
        help="User to look for."
    )
    group.add_argument(
        "-a",
        "--access-key-id",
        help="Access Key ID to look for"
    )
    parser.add_argument(
        "-s",
        "--start-time",
        help="The time to start searching.  Default is previous 24 hours.  Format: YYYY-MM-DD-HHMM (24 hour format, UTC)"
    )
    parser.add_argument(
        "-e",
        "--end-time",
        help="The time to end searching.  Default is now.  Format: YYYY-MM-DD-HHMM (24 hour format, UTC)"
    )
    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument(
        "-H",
        "--hours",
        help="How many hours in the past?  (Cannot be used with: -s, -e, -D, -W, -M, -Y)",
        type=int
    )
    group2.add_argument(
        "-D",
        "--days",
        help="Number of days in the past.  (Cannot be used with: -s, -e, -H, -W, -M, -Y)",
        type=int
    )
    group2.add_argument(
        "-W",
        "--weeks",
        help="Number of weeks in the past.  (Cannot be used with: -s, -e, -H, -D, -M, -Y)",
        type=int
    )
    group2.add_argument(
        "-M",
        "--months",
        help="Number of months in the past.  (Cannot be used with: -s, -e, -H, -D, -W, -Y)",
        type=int
    )
    group2.add_argument(
        "-Y",
        "--years",
        help="Number of years in the past.  (Cannot be used with: -s, -e, -H, -D, -M, -W)",
        type=int
    )
    parser.add_argument(
        "-r",
        "--region",
        help="The AWS region to search. Default is all."
    )
    args = parser.parse_args()

    audit = IAMAudit(args)
    audit.search_logs()


if __name__ == "__main__":
    main()
