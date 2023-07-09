import boto3
import sys
import os
import argparse
import yaml
import json
import copy


### Arts AWS Instance Name Copy Script
###
### If an instance does not have a Name tag, copies the value from a potential list of sources.


class NameCopy:
    def __init__(self, **kwargs):
        self.profiles       = None
        self.regions        = kwargs.get("region")
        self.run_production = kwargs.get("production")
        self.dry_run        = kwargs.get("dry_run")
        if self.dry_run:
            self.run_production = True

        self.settings_file = "/etc/de/de.yml"
        if os.path.isfile(self.settings_file):
            self.settings = yaml.safe_load(open(self.settings_file, "r").read())
            self.profiles = self.profiles or copy.deepcopy(self.settings["aws"]["accounts"])
            self.regions = self.regions or copy.deepcopy(self.settings["aws"]["regions"])
            if not self.run_production:
                for key, value in self.settings["aws"]["accounts"].items():
                    if value["env"].lower().startswith("prod"):
                        del self.profiles[key]

        if kwargs.get("profiles"):
            self.profiles = kwargs.get("profiles")

        self.source_tags = (
            "Adobe.Customer",
            "aws:cloudformation:stack-name",
            "aws:autoscaling:groupName"
        )
        self.source_resource = (
            "emr_cluster_name",
        )

    def get_tag(self, tags ,tag):
        for _tag in tags:
            if _tag["Key"] == tag:
                return _tag["Value"]
        return None

    def get_new_tag(self, tags, **kwargs):
        emr = kwargs.get("emr")
        name = self.get_tag(tags, "Name")
        if name:
            return None
        for _tag in self.source_tags:
            value = self.get_tag(tags, _tag)
            if value:
                return value
        for _item in self.source_resource:
            if _item == "emr_cluster_name":
                _cluster_id = self.get_tag(tags, "aws:elasticmapreduce:job-flow-id")
                if _cluster_id:
                    _data = emr.describe_cluster(
                        ClusterId=_cluster_id
                    )
                    return _data["Cluster"]["Name"] + " (EMR)"
        return None
    
    def scan(self):
        for profile in self.profiles:
            aws = boto3.Session(profile_name=profile)
            for region in self.regions:
                print(f"Processing {profile} ({region})")
                ec2 = aws.client("ec2", region_name=region)
                emr = aws.client("emr", region_name=region)
                paginator = ec2.get_paginator("describe_instances")
                count = 0
                count2 = 0
                for page in paginator.paginate():
                    for reservation in page["Reservations"]:
                        for instance in reservation["Instances"]:
                            # print(f"  Instance: {instance['InstanceId']}")
                            new_tag = self.get_new_tag(instance.get("Tags"), emr=emr)
                            if new_tag:
                                count += 1

                                print(f"    ({count: 4}) - Adding name to {profile}:{region}:{instance['InstanceId']} - {new_tag}")
                                
                                new_tag = [ { "Key": "Name", "Value": new_tag } ]
                                if not self.dry_run:
                                    ec2.create_tags(
                                        Resources = [ instance["InstanceId"] ],
                                        Tags = new_tag
                                    )
                            else:
                                count2 += 1

                                if not self.get_tag(instance.get("Tags"), "Name"):
                                    print(f"    ({count2: 4}) - Unable to find new name for {profile}:{region}:{instance['InstanceId']}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--profile",
        help="AWS Profile (draws from /etc/de/de.yml if not provided)",
        action="append"
    )
    parser.add_argument(
        "-r",
        "--region",
        help="AWS Region (draws from /etc/de/de.yml if not provided)",
        action="append"
    )
    parser.add_argument(
        "--production",
        help="Run in production? (ignored if using -p|--profile)",
        action="store_true"
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        help="Preview without changing.",
        action="store_true"
    )
    args = parser.parse_args()
    nc = NameCopy(profiles=args.profile, regions=args.region, production=args.production, dry_run=args.dry_run)
    nc.scan()


if __name__ == "__main__":
    main()
