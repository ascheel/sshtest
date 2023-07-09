import boto3
import sys
import os
import json
import datetime
import socket
import argparse
import yaml


def stringify_dates(_obj):
    """
    Converts all datetime objects into string equivalents.

    Args:
        _obj (list, dict): input list or dictionary to modify

    Returns:
        input type: new object with strings
    """
    import copy

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


class Address:
    def __init__(self, ip, **kwargs):
        self.__ip          = ip
        self.private_ip    = kwargs.get("private_ip")
        self.__type        = kwargs.get("type")
        self.__id          = kwargs.get("id")
        self.__name        = kwargs.get("name")
        self.__elastic     = kwargs.get("elastic")
        self.__associated  = kwargs.get("unassociated")
    
    @property
    def ip(self):
        return self.__ip
    
    @ip.setter
    def ip(self, _in):
        self.__ip = _in

    @property
    def associated(self):
        return self.__associated
    
    @associated.setter
    def associated(self, _in):
        self.__associated = _in

    @property
    def unused_eip(self):
        if self.__elastic and not self.__associated:
            return True
        return False

    @property
    def id(self):
        return self.__id if self.__id else "Unknown"
    
    @id.setter
    def id(self, _in):
        self.__id = _in
    
    @property
    def elastic(self):
        return "Yes" if self.__elastic else "No"
    
    @elastic.setter
    def elastic(self, _in):
        self.__elastic = _in
    
    @property
    def name(self):
        return self.__name if self.__name else "Unknown"
    
    @name.setter
    def name(self, _in):
        self.__name = _in
    
    @property
    def type(self):
        return self.__type if self.__type else "Unknown"
    
    @type.setter
    def type(self, _in):
        self.__type = _in

class EIP:
    def __init__(self, **kwargs):
        self.profile_name = kwargs.get("profile_name")
        self.region_name  = kwargs.get("region_name")
        self.aws          = boto3.Session(profile_name=self.profile_name)
        self.ec2          = self.aws.resource("ec2", region_name=self.region_name)
        self.addresses    = {}
        self.elastic_flag = kwargs.get("flag")

    def gather_eip(self):
        addresses = self.ec2.meta.client.describe_addresses().get("Addresses")
        if not addresses:
            return
        for address in addresses:
            if address.get("PublicIp"):
                ip = address["PublicIp"]
                associated = address.get("AssociationId")
                if not self.addresses.get(ip):
                    self.addresses[ip] = Address(ip)
                self.addresses[ip].private_ip = address.get("PrivateIpAddress")
                self.addresses[ip].elastic = True
                self.addresses[ip].associated = True if address.get("AssociationId") else False
            #import pdb; pdb.set_trace()

    def gather_instances(self):
        paginator = self.ec2.meta.client.get_paginator("describe_instances")
        pages = paginator.paginate()
        for page in pages:
            for reservation in page["Reservations"]:
                for instance in reservation["Instances"]:
                    ip = instance.get("PublicIpAddress")
                    if not ip:
                        # Instance has no public
                        continue
                    if not self.addresses.get(ip):
                        self.addresses[ip] = Address(ip)
                    self.addresses[ip].id   = instance["InstanceId"]
                    self.addresses[ip].name = self.get_tag(instance.get("Tags"), "Name")
                    self.addresses[ip].type = "ec2"
    
    def gather_rds_instances(self):
        client = self.aws.client("rds", region_name=self.region_name)
        rdss = client.describe_db_instances().get("DBInstances")
        if not rdss:
            return
        for rds in rdss:
            if not rds.get("Endpoint"):
                continue
            address = rds["Endpoint"]["Address"]
            ip = socket.gethostbyname(address)
            if not self.addresses.get(ip):
                self.addresses[ip] = Address(ip)
            self.addresses[ip].id   = rds["DBInstanceIdentifier"]
            self.addresses[ip].name = self.get_tag(rds.get("Tags"), "Name")
            self.addresses[ip].type = "rds"

    def gather_nat_gateways(self):
        self.nats = []
        paginator = self.ec2.meta.client.get_paginator("describe_nat_gateways")
        pages = paginator.paginate()
        for page in pages:
            for nat in page["NatGateways"]:
                for address in nat["NatGatewayAddresses"]:
                    ip = address["PublicIp"]
                    if not self.addresses.get(ip):
                        self.addresses[ip] = Address(ip)
                    self.addresses[ip].id   = nat["NatGatewayId"]
                    self.addresses[ip].name = self.get_tag(nat.get("Tags"), "Name")
                    self.addresses[ip].type = "ngw"
    
    def gather_elbs(self):
        elb = self.aws.client("elbv2", region_name=self.region_name)
        paginator = elb.get_paginator("describe_load_balancers")
        pages = paginator.paginate()
        for page in pages:
            for elb in page["LoadBalancers"]:
                for az in elb["AvailabilityZones"]:
                    for address in az["LoadBalancerAddresses"]:
                        ip = address["IpAddress"]
                        if not self.addresses.get(ip):
                            self.addresses[ip] = Address(ip)
                        self.addresses[ip].id   = elb["LoadBalancerName"]
                        self.addresses[ip].name = elb["DNSName"]
                        self.addresses[ip].type = "elb"
    
    def get_tag(self, tags, key):
        if not tags:
            return None
        for tag in tags:
            if tag["Key"].lower() == key.lower():
                return tag["Value"]

    def print(self):
        if len(self.addresses):
            line = "{:20} {:10} {:15}: {:4} {:10} {:25} {}".format(
                "AWS Account",
                "Region",
                "Public IP",
                "EIP?",
                "Resource",
                "Resource ID",
                "Description"
            )
            print("\n")
            print("=" * len(line))
            print(line)
        for key, address in self.addresses.items():
            # if address.ip == "3.217.180.84":
            #     import pdb; pdb.set_trace()
            if address.elastic == "No" and self.elastic_flag:
                continue
            if not address.associated and address.elastic == "Yes":
                address.name = "UNUSED"
                address.id   = "UNUSED"
                address.type = "---"
            line = "{:20} {:10} {:15}: {:4} {:10} {:25} {}".format(
                self.profile_name,
                self.region_name,
                address.ip,
                address.elastic,
                address.type,
                address.id,
                address.name
            )
            print(line)
    
    @staticmethod
    def list(**kwargs):
        """
        Elastic IPs can be used by:
        EC2 instances
            Should be able to get this with eip.instance_id
        RDS instances
            rds.endpoint.address
        NAT Gateways
            ec2.describe_nat_gateways().NatGatewayAddresses
        ELB

        Network Interfaces
        """
        eip = EIP(**kwargs)
        eip.gather_eip()
        eip.gather_elbs()
        eip.gather_instances()
        eip.gather_rds_instances()
        eip.gather_nat_gateways()
        eip.print()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-e",
        "--elastic",
        help="Only show elastic IPs. Default displays all public IPs",
        action="store_true"
    )
    args = parser.parse_args()

    settings = yaml.load(open("/etc/ea/ea.yml", "r").read(), Loader=yaml.FullLoader)

    for profile in settings["aws"]["accounts"]:
        for region in settings["aws"]["regions"]:
            EIP.list(profile_name=profile, region_name=region, flag=args.elastic)
    


if __name__ == "__main__":
    main()
