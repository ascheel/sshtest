import boto3
import json
import yaml


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


class ECS:
    def __init__(self, profile, region):
        self.__fresh_start = True
        self.profile = profile
        self.region  = region
        self.set_env()

    def set_env(self, profile=None, region=None):
        changed = False

        if profile and profile != self.profile:
            self.profile = profile
            changed = True
            
        if region and region != self.region:
            self.region = region
            changed = True
        
        if changed or self.__fresh_start:
            self.aws = boto3.Session(profile_name=self.profile)
            self.ecs = self.aws.client("ecs", region_name=self.region)
            self.__fresh_start = False
        
    def get_clusters(self):
        paginator = self.ecs.get_paginator("list_clusters")
        for page in paginator.paginate():
            for cluster in page["clusterArns"]:
                yield cluster

    def list_tasks(self, **kwargs):
        cluster = kwargs.get("cluster")
        if not cluster:
            raise ValueError("Must provide cluster name or arn")

        paginator = self.ecs.get_paginator("list_tasks")
        for page in paginator.paginate(cluster=cluster):
            for arn in page["taskArns"]:
                yield arn

    @staticmethod
    def go():
        settings = yaml.full_load(open("/etc/ea/ea.yml", "r").read())
        for profile in settings["aws"]["accounts"]:
            for region in settings["aws"]["regions"]:
                ecs = ECS(profile, region)
                for arn in ecs.get_clusters():
                    # print(arn)
                    cluster = arn.split("/")[-1]
                    for task in ecs.list_tasks(cluster=arn):
                        # print(f"    {task}")
                        #cluster = task.split("/")[-2]
                        task = task.split("/")[-1]
                        # print(cluster)
                        # print(task)
                        print(f"{profile:20} {region:15} {cluster:60} {task}")


def main():
    ECS.go()


if __name__ == "__main__":
    main()
