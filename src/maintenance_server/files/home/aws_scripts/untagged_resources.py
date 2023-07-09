import boto3
import botocore
import sys
import yaml
import os
import colorama
import json
import csv
import datetime


settings_file = "/etc/ea/ea.yml"
settings      = yaml.full_load(open(settings_file, "r").read())


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


class UnTagged:
    def __init__(self, **kwargs):
        self.profile = kwargs.get("profile_name")
        self.aws     = boto3.Session(profile_name=self.profile)

        self.needed_tags = (
            "Adobe.Customer",
            "Adobe.ArchPath",
            "Adobe.Owner",
            "Adobe.EA.Creator",
            "Adobe.EA.Description"
        )
        
        self.output_file = "/home/scheel/Documents/aws_untagged_resources.{}.csv".format(datetime.datetime.now().strftime("%F-%H%M"))
        self.output_lines = [["Account", "Region", "Service", "ID", "Name"] + list(self.needed_tags)]

        # Scan:
        #  ec2
        #  s3
        #  lambda
        #  emr
        #  ebs
        #  ecs
        #  eks
        #  ecr
        #  dynamo

    def clean_output(self):
        _output_lines = []
        for line in self.output_lines:
            if not line[5] or not line[6]:
                # We only want lines that do not have Adobe.Customer or Adobe.ArchPath
                _output_lines.append(line)
        self.output_lines = [self.output_lines[0],] + _output_lines

    @staticmethod
    def scan(**kwargs):
        all_rows = []
        for profile in settings["aws"]["accounts"]:
            print("{}".format(profile))
            # profile = kwargs.get("profile_name")
            u = UnTagged(profile_name=profile)
            u.scan_ec2()
            u.scan_ebs()
            u.scan_s3()
            u.scan_lambda()
            u.scan_emr()
            u.scan_dynamo()

            # u.scan_ecs()
            # u.scan_eks()
            # u.scan_ecr()
            u.clean_output()
            all_rows += u.output_lines
        with open(u.output_file, "w") as f_out:
            writer = csv.writer(f_out)
            writer.writerows(all_rows)

    def __get_tag(self, tags, key):
        for tag in tags:
            if tag["Key"].lower() == key.lower():
                return tag["Value"]
        return None

    def __list_ec2_instances(self, ec2, region):
        paginator = ec2.meta.client.get_paginator("describe_instances")
        for page in paginator.paginate():
            for reservation in page["Reservations"]:
                for instance in reservation["Instances"]:
                    tags = instance.get("Tags", [])
                    _name = self.__get_tag(tags, "Name") or ""
                    line = [self.profile, region, "ec2", instance["InstanceId"], _name]
                    for _tag in self.needed_tags:
                        line.append(self.__get_tag(tags, _tag))
                    self.output_lines.append(line)

    def scan_dynamo(self):
        print("    Scanning DynamoDB tables.")
        for _region in settings["aws"]["regions"]:
            print("        Region: {}".format(_region))
            dynamo = self.aws.client("dynamodb", region_name=_region)
            results = dynamo.list_tables()
            for table in results["TableNames"]:
                _details = dynamo.describe_table(TableName=table)["Table"]
                _id = _details["TableId"]
                _arn = _details["TableArn"]
                data = dynamo.list_tags_of_resource(ResourceArn=_arn)
                tags = data["Tags"]
                line = [self.profile, _region, "DynamoDB", _id, _arn]
                for _tag in self.needed_tags:
                    line.append(self.__get_tag(tags, _tag))
                self.output_lines.append(line)

    def scan_ec2(self):
        print("    Scanning EC2 resources.")
        for _region in settings["aws"]["regions"]:
            print("        Region: {}".format(_region))
            ec2 = self.aws.resource("ec2", region_name=_region)
            self.__list_ec2_instances(ec2, _region)

    def scan_ebs(self):
        print("    Scanning EBS volumes.")
        for _region in settings["aws"]["regions"]:
            print("        Region: {}".format(_region))
            ec2 = self.aws.resource("ec2", region_name=_region)
            results = ec2.meta.client.describe_volumes()
            for volume in results["Volumes"]:
                _id = volume["VolumeId"]
                tags = volume.get("Tags", [])
                _name = self.__get_tag(tags, "Name")
                line = [self.profile, _region, "EBS", _id, _name]
                for _tag in self.needed_tags:
                    line.append(self.__get_tag(tags, _tag))
                self.output_lines.append(line)
    
    def scan_s3(self):
        print("    Scanning S3 buckets.")
        s3 = self.aws.resource("s3", region_name="us-east-1")
        results = s3.meta.client.list_buckets()
        for bucket in results["Buckets"]:
            _name = bucket["Name"]
            tags = None
            try:
                tags = s3.BucketTagging(_name).tag_set
            except s3.meta.client.exceptions.ClientError as e:
                tags = []
            line = [self.profile, None, "s3", _name, ""]
            for _tag in self.needed_tags:
                line.append(self.__get_tag(tags, _tag))
            self.output_lines.append(line)
    
    def __get_lambda_tags(self, tags):
        output_tags = []
        for key, value in tags.items():
            output_tags.append({"Key": key, "Value": value})
        return output_tags

    def scan_lambda(self):
        print("    Scanning Lambda")
        for _region in settings["aws"]["regions"]:
            print("        Region: {}".format(_region))
            aws_lambda = self.aws.client("lambda", region_name=_region)
            results = aws_lambda.list_functions()
            for function in results["Functions"]:
                _name = function["FunctionName"]
                _arn = function["FunctionArn"]
                tags = self.__get_lambda_tags(aws_lambda.list_tags(Resource=_arn)["Tags"])
                line = [self.profile, _region, "Lambda", _name, ""]
                for _tag in self.needed_tags:
                    line.append(self.__get_tag(tags, _tag))
                self.output_lines.append(line)

    # Scan for network resources (NAT Gateways, etc)

    def scan_emr(self):
        print("    Scanning EMR")
        for _region in settings["aws"]["regions"]:
            print("        Region: {}".format(_region))
            emr = self.aws.client("emr", region_name=_region)
            results = emr.list_clusters()
            for cluster in results["Clusters"]:
                _status = cluster["Status"]["State"]
                if _status.lower().startswith("terminated"):
                    continue
                _name = cluster["Name"]
                _id = cluster["Id"]
                tags = emr.describe_cluster(ClusterId=_id)["Cluster"]["Tags"]
                line = [self.profile, _region, "EMR", _id, _name]
                for _tag in self.needed_tags:
                    line.append(self.__get_tag(tags, _tag))
                self.output_lines.append(line)


def main():
    UnTagged.scan(profile_name="na-ea-dev")


if __name__ == "__main__":
    main()
