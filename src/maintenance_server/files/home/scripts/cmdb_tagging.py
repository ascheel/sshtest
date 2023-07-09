import boto3
import botocore
import sys
import os
import datetime
import json
import copy
import yaml


DRY_RUN = False


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


class AWS:
    def __init__(self, **kwargs):
        self.profile_name = kwargs.get("profile_name")
        self.region_name = kwargs.get("region_name")
        
        self.aws = boto3.Session(profile_name=self.profile_name)
        self.ec2 = self.aws.resource("ec2", region_name=self.region_name)
        self.emr = self.aws.client("emr", region_name=self.region_name)
        self.rds = self.aws.client("rds", region_name=self.region_name)
        self.s3  = self.aws.resource("s3", region_name=self.region_name)

        self.settings = yaml.load(open("/etc/ea/ea.yml", "r").read(), Loader=yaml.FullLoader)

    def get_tag(self, tags, key):
        if not tags:
            return
        for tag in tags:
            if tag["Key"].lower() == key.lower():
                return tag["Value"]

    def scan_rds(self):
        self.scan_rds_clusters()
        self.scan_rds_instances()

    def scan_rds_clusters(self):
        category = "rds"
        paginator = self.rds.get_paginator("describe_db_clusters")
        for page in paginator.paginate():
            for cluster in page["DBClusters"]:
                name                = cluster["DBClusterIdentifier"]
                arn                 = cluster["DBClusterArn"]
                tags                = self.rds.list_tags_for_resource(ResourceName=arn)["TagList"]
                CMDB_hostname       = self.get_tag(tags, "CMDB_hostname")
                CMDB_device_service = self.get_tag(tags, "CMDB_device_service")
                CMDB_environment    = self.get_tag(tags, "CMDB_environment")

                info = "{:20} - {:10} - {:4} - {:30} {:60}".format(self.profile_name, self.region_name, category, name, arn)

                CMDB_device_service_new = None
                if not CMDB_device_service:
                    CMDB_device_service_new = "Consulting - AWS - rds"
                    if not DRY_RUN:
                        tag = [{"Key": "CMDB_device_service", "Value": CMDB_device_service_new},]
                        self.rds.add_tags_to_resource(ResourceName=arn, Tags=tag)
                    print("{} CMDB_device_service: ({} => {})".format(info, str(CMDB_device_service), CMDB_device_service_new))
                
                CMDB_environment_new = None
                if not CMDB_environment:
                    CMDB_environment_new = "Consulting Engineering Services - {} - {}".format(self.short_region_name, self.env)
                    if not DRY_RUN:
                        tag = [{"Key": "CMDB_environment", "Value": CMDB_environment_new},]
                        self.rds.add_tags_to_resource(ResourceName=arn, Tags=tag)
                    print("{} CMDB_environment:    ({} => {})".format(info, str(CMDB_environment), CMDB_environment_new))

    @property
    def short_region_name(self):
        return self.settings["aws"]["regions"][self.region_name]["short"]

    @property
    def env(self):
        return self.settings["aws"]["accounts"][self.profile_name]["env"]

    def scan_rds_instances(self):
        category = "rds"
        paginator = self.rds.get_paginator("describe_db_instances")
        for page in paginator.paginate():
            for instance in page["DBInstances"]:
                name                = instance["DBInstanceIdentifier"]
                arn                 = instance["DBInstanceArn"]
                tags                = self.rds.list_tags_for_resource(ResourceName=arn)["TagList"]
                CMDB_hostname       = self.get_tag(tags, "CMDB_hostname")
                CMDB_device_service = self.get_tag(tags, "CMDB_device_service")
                CMDB_environment    = self.get_tag(tags, "CMDB_environment")

                info = "{:20} - {:10} - {:4} - {:30} {:60}".format(self.profile_name, self.region_name, category, name, arn)

                CMDB_device_service_new = None
                if not CMDB_device_service:
                    CMDB_device_service_new = "Consulting - AWS - rds"
                    if not DRY_RUN:
                        tag = [{"Key": "CMDB_device_service", "Value": CMDB_device_service_new},]
                        self.rds.add_tags_to_resource(ResourceName=arn, Tags=tag)
                    print("{} CMDB_device_service: ({} => {})".format(info, str(CMDB_device_service), CMDB_device_service_new))
                
                CMDB_environment_new = None
                if not CMDB_environment:
                    CMDB_environment_new = "Consulting Engineering Services - {} - {}".format(self.short_region_name, self.env)
                    if not DRY_RUN:
                        tag = [{"Key": "CMDB_environment", "Value": CMDB_environment_new},]
                        self.rds.add_tags_to_resource(ResourceName=arn, Tags=tag)
                    print("{} CMDB_environment:    ({} => {})".format(info, str(CMDB_environment), CMDB_environment_new))

    def scan_s3(self):
        # S3 is global.  Only need to check for 1 region.  Let's pick Virginia...
        if self.profile_name != "us-east-1":
            return
        category = "s3"
        for bucket in self.s3.meta.client.list_buckets()["Buckets"]:
            bucket_id = bucket["Name"]
            b = self.s3.Bucket(bucket_id)
            tagging = b.Tagging()
            tags = None
            try:
                tags = tagging.tag_set
            except botocore.exceptions.ClientError:
                pass
            CMDB_device_service = self.get_tag(tags, "CMDB_device_service")
            CMDB_environment    = self.get_tag(tags, "CMDB_environment")

            info = "{:20} - {:10} - {:4} - {:50}".format(self.profile_name, self.region_name, category, bucket_id)

            CMDB_device_service_new = None
            if not CMDB_device_service:
                CMDB_device_service_new = "Consulting - AWS - s3"
                if not DRY_RUN:
                    tag = [{"Key": "CMDB_device_service", "Value": CMDB_device_service_new},]
                    tagging.put(Tagging={"TagSet": tag})
                print("{} CMDB_device_service: ({} => {})".format(info, str(CMDB_device_service), CMDB_device_service_new))
            
            CMDB_environment_new = None
            if not CMDB_environment:
                CMDB_environment_new = "Consulting Engineering Services - {} - {}".format(self.short_region_name, self.env)
                if not DRY_RUN:
                    tag = [{"Key": "CMDB_environment", "Value": CMDB_environment_new},]
                    tagging.put(Tagging={"TagSet": tag})
                print("{} CMDB_environment:    ({} => {})".format(info, str(CMDB_environment), CMDB_environment_new))
            

    def scan_emr_instances(self, cluster_id):
        category = "emr"
        paginator = self.emr.get_paginator("list_instances")
        for page in paginator.paginate(ClusterId=cluster_id):
            for instance in page["Instances"]:
                state = instance["Status"]["State"]
                if state.startswith("TERMINATED"):
                    continue
                instance_id         = instance["Ec2InstanceId"]
                i                   = self.ec2.Instance(instance_id)
                name                = self.get_tag(i.tags, "Name")
                CMDB_hostname       = self.get_tag(i.tags, "CMDB_hostname")
                CMDB_device_service = self.get_tag(i.tags, "CMDB_device_service")
                CMDB_environment    = self.get_tag(i.tags, "CMDB_environment")

                info = "{:20} - {:10} - {:4} - {:30} {:60}".format(self.profile_name, self.region_name, category, instance_id, str(name))

                CMDB_device_service_new = None
                if not CMDB_device_service or CMDB_device_service == "Consulting - AWS - ec2":
                    CMDB_device_service_new = "Consulting - AWS - emr"
                    if not DRY_RUN:
                        i.create_tags(Tags=[{"Key": "CMDB_device_service", "Value": CMDB_device_service_new},])
                    print("{} CMDB_device_service: ({} => {})".format(info, str(CMDB_device_service), CMDB_device_service_new))
                
                CMDB_environment_new = None
                if not CMDB_environment:
                    CMDB_environment_new = "Consulting Engineering Services - {} - {}".format(self.short_region_name, self.env)
                    if not DRY_RUN:
                        i.create_tags(Tags=[{"Key": "CMDB_environment", "Value": CMDB_environment_new},])
                    print("{} CMDB_environment:    ({} => {})".format(info, str(CMDB_environment), CMDB_environment_new))

    def scan_emr(self):
        category = "emr"
        paginator = self.emr.get_paginator("list_clusters")
        for page in paginator.paginate():
            for cluster in page["Clusters"]:
                if cluster["Status"]["State"].startswith("TERMINATED"):
                    continue
                cluster_id   = cluster["Id"]
                name         = cluster["Name"]
                # CMDB_hostname = self.get_tag()
                self.scan_emr_instances(cluster_id)

    def scan_ec2(self):
        category = "ec2"
        paginator = self.ec2.meta.client.get_paginator("describe_instances")
        for page in paginator.paginate():
            for reservation in page["Reservations"]:
                for instance in reservation["Instances"]:
                    instance_id         = instance["InstanceId"]
                    i                   = self.ec2.Instance(instance_id)
                    name                = self.get_tag(i.tags, "Name")
                    #print("Tags: {}".format(i.tags))
                    CMDB_hostname       = self.get_tag(i.tags, "CMDB_hostname")
                    CMDB_device_service = self.get_tag(i.tags, "CMDB_device_service")
                    CMDB_environment    = self.get_tag(i.tags, "CMDB_environment")

                    info = "{:20} - {:10} - {:4} - {:30} {:60}".format(self.profile_name, self.region_name, category, instance_id, str(name))

                    CMDB_device_service_new = None
                    if not CMDB_device_service:
                        CMDB_device_service_new = "Consulting - AWS - ec2"
                        if not DRY_RUN:
                            i.create_tags(Tags=[{"Key": "CMDB_device_service", "Value": CMDB_device_service_new},])
                        print("{} CMDB_device_service: ({} => {})".format(info, str(CMDB_device_service), CMDB_device_service_new))
                    
                    CMDB_environment_new = None
                    if not CMDB_environment:
                        CMDB_environment_new = "Consulting Engineering Services - {} - {}".format(self.short_region_name, self.env)
                        if not DRY_RUN:
                            i.create_tags(Tags=[{"Key": "CMDB_environment", "Value": CMDB_environment_new},])
                        print("{} CMDB_environment:    ({} => {})".format(info, str(CMDB_environment), CMDB_environment_new))


def main():
    settings = yaml.load(open("/etc/ea/ea.yml", "r").read(), Loader=yaml.FullLoader)
    accounts = settings["aws"]["accounts"]
    regions = settings["aws"]["regions"]
    for profile_name in accounts:
        print("Profile: {}".format(profile_name))
        for region_name in regions:
            print("  Scanning Region: {}".format(region_name))
            a = AWS(profile_name=profile_name, region_name=region_name)
            a.scan_ec2()
            a.scan_emr()
            a.scan_rds()
            #a.scan_s3()


if __name__ == "__main__":
    main()


