#!/usr/bin/env python3

import yaml
import json
import argparse
import logging
import os
import sys
from dateutil import parser
import datetime
import boto3
import inventory


class Audit:
    def __init__(self, **kwargs):
        self.file       = kwargs.get("file")
        self.days       = kwargs.get("days")
        self.profile    = kwargs.get("profile")
        self.loglevel   = kwargs.get("loglevel").upper()
        self.condensed  = kwargs.get("condensed")

        self.inventory  = inventory.Inventory(filename=self.file)
        self.instances  = self.inventory.instances

        self.log_format = "%(asctime)s - %(name)s - %(pathname)s:%(lineno)-4d - %(levelname)-8s - %(message)s"
        self.log = self.__set_logging(self.loglevel)

        self.root           = os.path.split(os.path.abspath(__file__))[0]

        self.settings       = self.inventory.settings
        self.datadir        = os.path.join(self.root, self.settings["options"]["datadir"])

        self.__load_imagefactory_data()

        self.__aws = {}
        self.__images = {}

    def __set_logging(self, level=None):
        log = logging
        if level:
            loglevel = getattr(log, level)
        else:
            loglevel = log.INFO
        if not isinstance(loglevel, int):
            raise ValueError(f"Invalid LOGLEVEL: {loglevel}")
        log.basicConfig(format=self.log_format, level=loglevel)
        log.getLogger("botocore").setLevel(logging.CRITICAL)
        log.getLogger("urllib3").setLevel(logging.CRITICAL)
        return log

    def __load_imagefactory_data(self):
        self.log.debug("Loading imagefactory data")
        URL = "https://imagefactory.corp.adobe.com:8443/imagefactory/binary/details/?cloud_or_pkg_type=aws"
        iffile = os.path.join(self.datadir, "imagefactory.json")
        if not os.path.exists(iffile):
            self.log.error(f"ImageFactory input data must reside at {iffile} in json format.")
            self.log.error(f"  Please get this data using the below command from within the Adobe Corporate Network.")
            self.log.error(f"  Save that file at the above location.")
            self.log.error("Command: ")
            self.log.error(f"  curl '{URL}' > /tmp/imagefactory.json")
            self.log.error(f"         Note: This file may take several minutes to download.")
            sys.exit(1)
        self.ifdata = json.loads(open(iffile, "r").read())
        self.iflist = self.__cultivate_iflist()
        self.log.debug(f"  Loaded {len(self.iflist)} image IDs.")

    def __cultivate_iflist(self):
        _list = []
        for _image in self.ifdata:
            for _, _ami in _image["imageId"].items():
                _list.append(_ami)
        return _list

    def _get_tag(self, instance_id, key):
        return self.instances[instance_id]["tags"].get(key)

    def _missing_tags(self, instance_id):
        _missing = []
        for key in self.settings["options"]["ec2_required_tags"]:
            if not self._get_tag(instance_id, key):
                _missing.append(key)
        return _missing

    def _is_imagefactory(self, instance_id):
        return self.instances[instance_id]["ami"] in self.iflist

    def is_old(self, instance_id):
        _days = (datetime.datetime.now(self.instances[instance_id]["launch_time"].tzinfo) - self.instances[instance_id]["launch_time"]).days
        self.log.debug(f"  Instance age: {_days}")
        if _days > self.days:
            return True
        return False

    def is_blacklisted_profile(self, instance_id):
        _profile = self.instances[instance_id]["account"]
        if not self.profile:
            return False
        elif self.profile == _profile:
            return False
        elif self.profile != _profile:
            return True
        else:
            self.log.error("You shouldn't be here.")
            raise ValueError("You shouldn't be here.")

    def print_report_header(self):
        print(f"Data Engineering Standards Discrepency Report - {datetime.datetime.now()}")
        print(f"  Point of contact for report: Art Scheel <scheel@adobe.com>")
        print(f"Report criteria:")
        print(f"  Find instances younger than days: {self.days}")
        print(f"  Restrict instances to AWS profile: {self.profile}")
        print()

    def audit_file(self):
        self.report = {
            "missing_tags": {},
            "not_if":       {},
            "no_login":     []
        }
        
        self.print_report_header()

        _count = 0
        _count2 = 0

        for instance_id in self.instances:
            self.log.debug(f"Investigating {instance_id}")
            # Check launch time
            if self.is_old(instance_id):
                self.log.debug(f"  Instance is old.")
                continue

            # Skip invalid profiles
            if self.is_blacklisted_profile(instance_id):
                self.log.debug(f"  Profile not in range.")
                continue

            # Check for missing tags
            _missing = self._missing_tags(instance_id)
            _text = []
            if len(_missing):
                self.log.debug(f"  Missing tags: {', '.join(_missing)}")
                self.report["missing_tags"][instance_id] = _missing
                if self.condensed:
                    _text.append(f"{instance_id} - Missing tags: {', '.join(_missing)}")
                else:
                    _text.append(f"Missing tags: {', '.join(_missing)}")

            # Check if imagefactory
            _ami = self.instances[instance_id]["ami"]
            self.log.debug(f"  Found ami {_ami}.  Is in iflist: {_ami in self.iflist}")
            if _ami not in self.iflist:
                self.report["not_if"][instance_id] = self.instances[instance_id]["ami"]
                _desc = self._get_ami_description(instance_id)
                if self.condensed:
                    _text.append(f"{instance_id} - Not imagefactory ami: {_ami} - {_desc}")
                else:
                    _text.append(f"Not imagefactory ami: {_ami} - {_desc}")

            # Check if instance has successful login
            if not self.instances[instance_id]['user']:
                self.report["no_login"].append(instance_id)
                if self.condensed:
                    _text.append(f"{instance_id} - No login credentials found.")
                else:
                    _text.append(f"No login credentials found.")

            if len(_text):
                _count += 1
                if not self.condensed:
                    self._print_report_instance_header(instance_id, _count)

                for line in _text:
                    if self.condensed:
                        _count2 += 1
                        print(f"{_count2:5}) ", end="")
                    print(f"        {line}")

    def aws(self, profile):
        if not self.__aws.get(profile):
            self.__aws[profile] = boto3.Session(profile_name=profile)
        return self.__aws[profile]

    def _get_ami_description(self, instance_id):
        _ami = self.instances[instance_id]["ami"]
        if not self.__images.get(_ami):
            _profile = self.instances[instance_id]["account"]
            _ec2 = self.aws(_profile).client("ec2", region_name=self.instances[instance_id]["region"])
            results = _ec2.describe_images(ImageIds=[_ami,])
            _images = results["Images"]
            if not _images:
                return "Image does not exist."
            self.__images[_ami] = results["Images"][0]["Name"]
        return self.__images[_ami]


    def _print_report_instance_header(self, instance_id, count):
        _days = (datetime.datetime.now(self.instances[instance_id]["launch_time"].tzinfo) - self.instances[instance_id]["launch_time"]).days
        print("")
        print("*" * 80)
        print(f"{count:4}: Instance {instance_id} - {self.instances[instance_id]['account']} ({self.instances[instance_id]['region']})")
        print(f"        Launch Time: {self.instances[instance_id]['launch_time'].strftime('%Y-%M-%D')} ({_days} days)")
        print(f"        Image:       {self.instances[instance_id]['ami']} - {self._get_ami_description(instance_id)}")
        print(f"        Tags:")
        for tag, value in self.instances[instance_id]["tags"].items():
            print(f"          {tag:25}: {value}")
        print("       " + "=" * 40)
        print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-f",
        "--file",
        help="File to audit."
    )
    parser.add_argument(
        "-l",
        "--loglevel",
        help="Verbosity log level.  Default=info",
        default="info"
    )
    parser.add_argument(
        "-d",
        "--days",
        help="Ignore instances older than this number of days.",
        type=int,
        default=1000000
    )
    parser.add_argument(
        "-p",
        "--profile",
        help="Restrict results to a specific AWS profile."
    )
    parser.add_argument(
        "--condensed",
        help="Condensed report form.",
        action="store_true"
    )
    args = parser.parse_args()
    audit = Audit(
        file=args.file,
        loglevel=args.loglevel,
        days=args.days,
        profile=args.profile,
        condensed=args.condensed
    )
    audit.audit_file()


if __name__ == "__main__":
    main()
