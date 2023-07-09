+import boto3
import json
import yaml
import csv
import os

OUTPUT_FILENAME="images.csv"


class AMI:
    def __init__(self, **kwargs):
        self.profile = kwargs.get("profile")
        self.region = kwargs.get("region")
        self.aws = boto3.Session(profile_name=self.profile)
        self.ec2 = self.aws.client('ec2', region_name=self.region)
        self.images = {}
    
    def get_instances(self):
        paginator = self.ec2.get_paginator('describe_instances')
        for page in paginator.paginate():
            for reservation in page['Reservations']:
                for instance in reservation["Instances"]:
                    yield instance

    def get_image_details(self, ami):
        images = self.ec2.describe_images(ImageIds=[ami,])['Images']
        return {} if len(images) == 0 else images[0]

    def greater_than_or_equal(self, ver1, ver2):
        _ver1 = [int(item) for item in ver1.split('.')]
        _ver2 = [int(item) for item in ver2.split('.')]
        for x in range(len(_ver1)):
            if _ver1[x] < _ver2[x]:
                return False
            elif _ver1[x] > _ver2[x]:
                return True
        return True

    def is_good_imagefactory_version(self, text):
        minversion = '6.4.2'
        version_string = text.split('_')[-1]
        is_good = self.greater_than_or_equal(version_string, minversion)


    def is_imagefactory(self, ami):
        image = self.images[ami]
        if image is None:
            return False
        _name        = image.get('Name')
        _owner       = image.get('OwnerId')
        if _owner == '993267408692' and _name.startswith('IF_'):
            return True
        return False

    def get_tag(self, tags, key):
        for tag in tags:
            if tag['Key'].lower() == key.lower():
                return tag['Value']
        return None

    def scan(self):
        with open(OUTPUT_FILENAME, 'a') as csvfile:
            output = csv.writer(csvfile)
            for instance in self.get_instances():
                _id        = instance['InstanceId']
                _ami       = instance['ImageId']
                _launch    = instance['LaunchTime']
                _tags      = instance.get('Tags', [])
                _customer  = self.get_tag(_tags, 'Adobe.Customer')
                _creator   = self.get_tag(_tags, 'Adobe.Creator')
                _archpath  = self.get_tag(_tags, 'Adobe.ArchPath')
                if not self.images.get('_ami'):
                    self.images[_ami] = self.get_image_details(_ami)
                if not self.is_imagefactory(_ami):
                    print(f"{self.profile:20}{_id}: {self.get_tag(_tags, 'Name')} - {_launch} - {self.images[_ami].get('Name')}")
                    _row = [self.profile, _id, _ami, _launch, _customer, _creator, _archpath, self.images[_ami].get('Name'), self.images[_ami].get('CreationDate'), self.images[_ami].get('OwnerId')]
                    output.writerow(_row)


def main():
    os.remove(OUTPUT_FILENAME)
    open(OUTPUT_FILENAME, 'w').write("account,Instance ID,AMI,Launch,Customer,Creator,ArchPath,Image Name,Image Creation Date,Image Owner\n")
    profiles = [profile for profile in yaml.load(open(os.path.join(os.path.expanduser('~'), 'de.yml'), 'r').read(), Loader=yaml.CLoader)['aws']['accounts']]
    regions  = [region for region in yaml.load(open(os.path.join(os.path.expanduser('~'), 'de.yml'), 'r').read(), Loader=yaml.CLoader)['aws']['regions']]
    for profile in profiles:
        for region in regions:
            print(f"{profile}: {region}")
            ami = AMI(profile=profile, region=region)
            ami.scan()


if __name__ == "__main__":
    main()

