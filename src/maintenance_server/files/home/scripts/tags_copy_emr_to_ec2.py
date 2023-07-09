import boto3
import json
import yaml
import sys
import time
import botocore


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


class Tags:
    def __init__(self):
        self.settings = yaml.full_load(open("/etc/ea/ea.yml", "r").read())
        self.profiles = self.settings["aws"]["accounts"]
        self.regions  = self.settings["aws"]["regions"]

    def __list_emr_clusters(self, emr):
        paginator = emr.get_paginator("list_clusters")
        for page in paginator.paginate():
            for cluster in page["Clusters"]:
                if cluster["Status"]["State"].startswith("TERMINATED"):
                    continue
                if cluster["Status"]["State"] == "BOOTSTRAPPING":
                    continue
                # print("Status: {}".format(cluster["Status"]["State"]))
                yield cluster["Id"]

    def __get_tag(self, tags, key):
        if not tags:
            return None
        for tag in tags:
            if tag["Key"].lower() == key.lower():
                return tag["Value"]
        return None

    def __add_tag(self, ec2, resource_id, key, value):
        client = ec2.meta.client
        return
        client.create_tags(
            Resources=[
                resource_id,
            ],
            Tags=[
                {
                    "Key": key,
                    "Value": value
                }
            ]
        )

    def __get_instance_details(self, ec2, _id):
        client = ec2.meta.client
        instances = client.describe_instances(InstanceIds=[_id,])["Reservations"][0]["Instances"]
        if not instances:
            return None
        return instances[0]

    def __get_instances(self, emr, _id):
        paginator = emr.get_paginator("list_instances")
        for page in paginator.paginate(ClusterId=_id):
            for instance in page["Instances"]:
                yield instance["Ec2InstanceId"]

    def go(self):
        for profile in self.profiles:
            print(f"Profile: {profile}")
            for region in self.regions:
                print(f"    Region: {region}")
                aws = boto3.Session(profile_name=profile)
                
                ec2 = aws.resource("ec2", region_name=region)
                emr = aws.client("emr", region_name=region)
                for _id in self.__list_emr_clusters(emr):
                    print(f"        {_id}")
                    cluster = emr.describe_cluster(ClusterId=_id)
                    tags_cluster = cluster["Cluster"]["Tags"]

                    for instance_id in self.__get_instances(emr, _id):
                        print(f"            {instance_id}")
                        instance_details = self.__get_instance_details(ec2, instance_id)
                        tags_instance = instance_details.get("Tags", [])

                        for tag in tags_cluster:
                            if not tag["Key"].startswith("Adobe."):
                                continue
                            tag_target_value = self.__get_tag(tags_cluster, tag["Key"])
                            if tag_target_value == tag["Value"]:
                                print(f"{profile} {region} {tag['Key']:30} ({tag['Value']:30}) Tag already exists.")
                                pass
                            elif tag_target_value and tag_target_value != tag["Value"]:
                                print(f"{profile} {region} {tag['Key']:30} ({tag['Value']:30}) Tag already exists, but has different value: {tag_target_value}")
                                # print("            {:30} ({:30}) Tag exists: {}".format(tag_target, tag["Value"], tag_target_value))
                            elif not tag_target_value:
                                print(f"{profile} {region} {tag['Key']:30} ({tag['Value']:30}) Tag copied.")
                                # print("            {:30} ({:30}) Tag copied.".format(tag_target, tag["Value"]))
                                self.__add_tag(ec2, _id, tag['Key'], tag["Value"])
                            else:
                                raise ValueError("This shouldn't ever get hit.")





def main():
    t = Tags()
    t.go()


if __name__ == "__main__":
    main()
