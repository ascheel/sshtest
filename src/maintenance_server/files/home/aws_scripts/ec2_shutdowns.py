import boto3
import os
import sys
import json
import yaml
import datetime


def p(_object, **kwargs):
    to_file = kwargs.get("to_file", False)
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
    if not to_file:
        print(json.dumps(stringify_dates(_object), indent=4))
    else:
        open("debug.txt", "w").write(json.dumps(stringify_dates(_object), indent=4))


class Shutdown:
    def __init__(self):
        self.READ_ONLY = True

        self.NOPROD   = True
        self.PROD_ACCOUNTS = ("na-ea-prod", "na-ea-prod-ondemand", "na-ea-prodold", "na-ea-d365-prod")
        self.NOD365   = True
        self.D365_ACCOUNTS = ("na-ea-d365-dev", "na-ea-stage", "na-ea-prod")

        self.region   = None
        self.profile  = None
        self.aws      = None
        self.ec2      = None
        self.settings = yaml.safe_load(open("/etc/ea/ea.yml", "r").read())
        
    def _profiles(self):
        profiles = []
        for profile in self.settings["aws"]["accounts"]:
            if self.NOPROD and profile in self.PROD_ACCOUNTS:
                continue
            if self.NOD365 and profile in self.D365_ACCOUNTS:
                continue
            profiles.append(profile)
        return profiles

    def _regions(self):
        return [region for region in self.settings["aws"]["regions"]]

    def __get_instances(self):
        instances = {}
        paginator = self.ec2.get_paginator("describe_instances")
        for page in paginator.paginate():
            for reservation in page["Reservations"]:
                for instance in reservation["Instances"]:
                    instances[instance["InstanceId"]] = instance
        return instances
    
    def __get_instance(self, _id):
        return self.ec2.describe_instances(InstanceIds=[_id,])["Reservations"][0]["Instances"][0]

    def __get_tag(self, tags, tag):
        if not tags:
            return None
        for _tag in tags:
            if _tag["Key"].lower() == tag.lower():
                return _tag["Value"]

    def __shutdown_instances(self, ids):
        if not ids:
            # print("      No instances to shut down.")
            return
        print("Shutdown in progress.")
        print(f"  Profile: {self.profile}")
        print(f"    Region: {self.region}")
        new_tag = [{"Key": "Adobe.AutoShutdownDate", "Value": datetime.datetime.now().isoformat()},]
        for _id in ids:
            print(f"      {_id}")
        try:
            self.ec2.stop_instances(InstanceIds=ids, DryRun=self.READ_ONLY)
        except self.ec2.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "DryRunOperation":
                # self.ec2.create_tags(Resources=ids, Tags=new_tag)
                return
            p(e.response)
            return
        self.ec2.create_tags(Resources=ids, Tags=new_tag)

    def shutdown(self):
        instances = {}
        for profile in self._profiles():
            self.profile = profile
            for region in self._regions():
                self.region = region
                self.aws = boto3.Session(profile_name=self.profile)
                self.ec2 = self.aws.client("ec2", region_name=self.region)

                ids_to_shutdown = []
                instances = self.__get_instances()
                for _id, _instance in instances.items():
                    _state    = _instance["State"]["Name"]
                    if _state not in ("pending", "running"):
                        # pending, running, shutting-down, terminated, stopping, stopped
                        continue
                    
                    _tags             = _instance.get("Tags")
                    _tag_autoshutdown = self.__get_tag(_tags, "Adobe.AutoShutdown") or ""
                    _tag_name         = self.__get_tag(_tags, "Name") or ""
                    print(f"{profile:15} {region:15} {_id:20} {_tag_autoshutdown:5} {_tag_name}")
                    if _tag_autoshutdown.lower().startswith("no"):
                        print("  Tagged.  No shutdown.")
                        continue
                    ids_to_shutdown.append(_id)
                self.__shutdown_instances(ids_to_shutdown)
        
    @staticmethod
    def go():
        shutdown = Shutdown()
        shutdown.shutdown()


def main():
    Shutdown.go()


if __name__ == "__main__":
    main()
