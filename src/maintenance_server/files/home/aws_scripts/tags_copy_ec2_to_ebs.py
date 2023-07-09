import boto3
import json
import yaml
import sys


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

    def __list_ec2_instances(self, ec2):
        paginator = ec2.meta.client.get_paginator("describe_instances")
        for page in paginator.paginate():
            for reservation in page["Reservations"]:
                for instance in reservation["Instances"]:
                    yield instance["InstanceId"]
    
    def __get_tag(self, tags, key):
        if not tags:
            return None
        for tag in tags:
            if tag["Key"].lower() == key.lower():
                return tag["Value"]
        return None

    def __add_tag(self, ec2, resource_id, key, value):
        client = ec2.meta.client
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

    def go(self):
        for profile in self.profiles:
            print("{}".format(profile))
            for region in self.regions:
                print("    {}".format(region))
                aws = boto3.Session(profile_name=profile)
                ec2 = aws.resource("ec2", region_name=region)
                
                for _id in self.__list_ec2_instances(ec2):
                    print("        {}".format(_id))
                    _instance = ec2.Instance(_id)
                    tags_instance = _instance.tags
                    for _volume in _instance.volumes.all():
                        print("            {}".format(_volume._id))
                        tags_volume = _volume.tags
                        for tag in tags_instance:
                            if not tag["Key"].startswith("Adobe"):
                                continue
                            elif tag["Key"].startswith("Adobe.EA.AWSBackup"):
                                continue
                            tag_instance = tag["Value"]
                            tag_volume   = self.__get_tag(tags_volume, tag["Key"])
                            if tag_volume:
                                if tag_instance == tag_volume:
                                    print(f"                {tag['Key']:20} ({tag_instance:40}) exists.")
                                    pass
                                else:
                                    print(f"                {tag['Key']:20} ({tag_instance:40}) exists and differs: {tag_volume}")
                            else:
                                print(f"                {tag['Key']:20} ({tag_instance:40}) copied to volume {_volume._id}")
                                self.__add_tag(ec2, _volume._id, tag["Key"], tag_instance)
                            


def main():
    t = Tags()
    t.go()


if __name__ == "__main__":
    main()
