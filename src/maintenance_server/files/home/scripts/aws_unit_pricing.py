import os
import sys
import json
import requests
import sqlite3
import re
import yaml
import socket


### CloudEfficiency Unit Pricing estimates by Art Scheel
###
### For a new API key: https://cloudefficiency.corp.adobe.com/#/user/<Your AdobeNet ID>/settings
### If you have never had an API key before, reach out to @kejones or @rengh with the CloudEfficiency team.


class CF:
    abbrs = {
        "us-west-1": "USW1-",
        "us-west-2": "USW2-",
        "us-east-1": "",
        "us-east-2": "USE2-",
        "ap-southeast-2": "APS2-",
        "ap-southeast-1": "APS1-",
        "ap-east-1": "APE1-",
        "ap-northeast-1": "APN1-",
        "ap-northeast-2": "APN2-",
        "ap-south-1": "APS3",
        "ca-central-1": "CAN1-",
        "eu-central-1": "EUC1-",
        "eu-north-1": "EUN1-",
        "eu-west-1": "EU-",
        "eu-west-2": "EUW2-",
        "eu-west-3": "EUW3-",
        "sa-east-1": "SAE1-"
    }
    COL1 = 14
    COL2 = 60
    class EMR:
        def __init__(self, **kwargs):
            self.outer      = kwargs.get("outer")
            self.size       = kwargs.get("size")
            self.count      = kwargs.get("count")
            self.drive_size = kwargs.get("drive_size")
            self.duration   = kwargs.get("duration")
            self.region     = kwargs.get("region")
            self.instances  = []
            for _ in range(self.count):
                self.instances.append(
                    CF.EC2(
                        outer=self.outer,
                        size=self.size,
                        count=self.count,
                        drive_size=self.drive_size,
                        duration=self.duration,
                        region=self.region
                    )
                )
        
        def unitcost(self):
            product_string = f"{CF.abbrs[self.region]}BoxUsage:{self.size}"
            sql = "SELECT avg_unit_price, unit FROM cost WHERE product_name = ? AND usage_description = ? AND region = ?"
            values = ("Amazon Elastic MapReduce", product_string, self.region)
            return self.outer._db_scalar(sql, values)

        def cost(self):
            _total = 0

            _emr_unit_cost = self.unitcost()
            _ec2_unit_cost = self.instances[0].unitcost()
            _ebs_unit_cost = self.instances[0].volume.unitcost()

            _total += _emr_unit_cost * self.count * self.duration
            _total += _ec2_unit_cost * self.count * self.duration
            _total += _ebs_unit_cost * self.count * (self.duration / 720) * self.drive_size
            return _total

        def print(self):
            _output = []
            _ec2 = []
            _ebs = []
            
            # EMR
            _desc = self.size
            _formula = f"{self.duration}hrs * ${self.unitcost():01,.4f}/hr * {self.count} qty"
            _cost = self.duration * self.unitcost() * self.count
            _total = f"${_cost: 6,.2f}"
            _output.append(f"EMR:    {_desc:{CF.COL1}}: {_formula:{CF.COL2}} = {_total}")

            # EC2
            _formula = f"{self.duration}hrs * ${self.instances[0].unitcost():01,.4f}/hr * {self.count} qty"
            _cost = self.duration * self.instances[0].unitcost() * self.count
            _total = f"${_cost: 6,.2f}"
            _output.append(f"  EC2:  {_desc:{CF.COL1}}: {_formula:{CF.COL2}} = {_total}")

            # EBS
            _desc = f"{self.drive_size} GB gp2"
            _formula = f"({self.duration}hrs / 720hrs) * ${self.instances[0].volume.unitcost():01,.4f}/hr * {self.count} qty * {self.drive_size} GB"
            _cost = (self.duration / 720) * self.instances[0].volume.unitcost() * self.count * self.drive_size
            _total = f"${_cost: 6,.2f}"
            _output.append(f"  EBS:  {_desc:{CF.COL1}}: {_formula:{CF.COL2}} = {_total}")

            return _output

    class EC2:
        def __init__(self, **kwargs):
            self.outer      = kwargs.get("outer")
            self.size       = kwargs.get("size")
            self.drive_size = kwargs.get("drive_size")
            self.duration   = kwargs.get("duration")
            self.region     = kwargs.get("region")
            self.count      = kwargs.get("count")
            self.volume     = CF.EBS(
                outer=self.outer,
                drive_size=self.drive_size,
                duration=self.duration,
                region=self.region
            )
            self.operating_system = 'Linux'

        def print(self):
            _output = []

            # EC2
            _formula = f"{self.duration}hrs * ${self.unitcost():01,.4f}/hr * {self.count} qty"
            _cost = self.duration * self.unitcost() * self.count
            _total = f"${_cost: 6,.2f}"
            _output.append(f"EC2:    {self.size:{CF.COL1}}: {_formula:{CF.COL2}} = {_total}")

            # EBS
            _desc = f"{self.drive_size} GB gp2"
            _formula = f"({self.duration}hrs / 720hrs) * ${self.volume.unitcost():01,.4f}/hr * {self.drive_size} GB * {self.count} qty"
            _cost = (self.duration / 720) * self.volume.unitcost() * self.drive_size * self.count
            _total = f"${_cost: 6,.2f}"
            _output.append(f"  EBS:  {_desc:{CF.COL1}}: {_formula:{CF.COL2}} = {_total}")

            return _output

        def cost(self):
            _total = 0

            _ec2_unit_cost = self.unitcost()
            _ebs_unit_cost = self.volume.unitcost()

            _total += _ec2_unit_cost * self.duration
            _total += _ebs_unit_cost * (self.duration / 720) * self.drive_size
            return _total

        def unitcost(self):
            product_string = f"{CF.abbrs[self.region]}BoxUsage:{self.size}"
            sql = "SELECT avg_unit_price, unit FROM cost WHERE product_name = ? AND usage_description = ? AND region = ? AND operation = ?"
            values = ("Amazon Elastic Compute Cloud", product_string, self.region, self.operating_system)
            return self.outer._db_scalar(sql, values)
        
    class EBS:
        def __init__(self, **kwargs):
            self.outer      = kwargs.get("outer")
            self.drive_size = kwargs.get("drive_size")
            self.duration   = kwargs.get("duration")
            self.region     = kwargs.get("region")
        
        def unitcost(self):
            product_string = f"{CF.abbrs[self.region]}EBS:VolumeUsage.gp2"
            sql = "SELECT avg_unit_price, unit FROM cost WHERE product_name = ? AND usage_description = ? AND region = ?"
            values = ("Amazon Elastic Compute Cloud", product_string, self.region)
            return self.outer._db_scalar(sql, values)
        
        def cost(self):
            _total = 0

            _ebs_unit_cost = self.unitcost()
            _total += _ebs_unit_cost * self.duration * self.drive_size
            return _total

        def print(self):
            _cost = self.duration * self.unitcost()
            return [ f"EBS:  {self.duration}hrs * ${self.unitcost():0,.4f}/hr = ${_cost:0,.2f}", ]

    class S3:
        def __init__(self, **kwargs):
            # We assume "S3 Standard" tier is used for all storage.
            self.outer    = kwargs.get("outer")
            self.size     = kwargs.get("size")
            self.egress   = kwargs.get("egress")
            self.region   = kwargs.get("region")
            self.duration = kwargs.get("duration")
            self.transfer = CF.S3_transfer_out(
                egress=self.egress,
                outer=self.outer,
                region=self.region
            )
        
        def unitcost(self):
            product_string = f"{CF.abbrs[self.region]}TimedStorage-ByteHrs"
            sql = "SELECT avg_unit_price, unit FROM cost WHERE product_name = ? AND usage_description = ? AND region = ?"
            values = ("Amazon Simple Storage Service", product_string, self.region)
            return self.outer._db_scalar(sql, values) / 30 / 24
        
        def cost(self):
            _total = 0

            _storage_unit_cost  = self.unitcost()
            _transfer_unit_cost = self.transfer.unitcost()
            
            _total += _storage_unit_cost * self.size * self.duration
            _total += _transfer_unit_cost * self.egress
            return _total
        
        def print(self):
            _output = []

            # S3
            _desc = f"{self.size} GB"
            _formula = f"{self.duration}hrs * ${self.unitcost():01,.6f}/GB/hr"
            _cost = self.unitcost() * self.size * self.duration
            _total = f"${_cost: 6,.2f}"
            _output.append(f"S3:     {_desc:{CF.COL1}}: {_formula:{CF.COL2}} = {_total}")

            # S3 Transfer out
            _desc = f"{self.egress} GB Out"
            _formula = f"{self.egress}GB * ${self.transfer.unitcost():01,.4f}/GB"
            _cost = self.egress * self.transfer.unitcost()
            _total = f"${_cost: 6,.2f}"
            _output.append(f"  Out:  {_desc:{CF.COL1}}: {_formula:{CF.COL2}} = {_total}")

            return _output

    class S3_transfer_out:
        def __init__(self, **kwargs):
            self.outer = kwargs.get("outer")
            self.egress = kwargs.get("egress")
            self.region = kwargs.get("region")

        def unitcost(self):
            product_string = f"{CF.abbrs[self.region]}DataTransfer-Out-Bytes"
            sql = "SELECT avg_unit_price, unit FROM cost WHERE product_name = ? AND usage_description = ? AND region = ?"
            values = ("Amazon Simple Storage Service", product_string, self.region)
            return self.outer._db_scalar(sql, values)
        
        def cost(self):
            _total = 0
            _transfer_unit_cost = self.unitcost()
            _total += _transfer_unit_cost * self.egress
            return _total
        
        def print(self):
            _output = []

            _formula = f"{self.egress}GB * ${self.transfer.unitcost():01,.4f}/GB"
            _cost = self.egress * self.transfer.unitcost()
            _total = f"${_cost:6,.2f}"
            _output.append(f"S3 out: {self.egress:{CF.COL1}}:{_formula:{CF.COL2}} = {_total}")
        
            return _output

    def set_header(self):
        self.set_token()
        self.header   = { "Authorization": f"Bearer {self.token}" }

    def set_rawdata(self):
        self.set_header()
        self.rawdata = requests.post(self.url, headers=self.header)
        while self.rawdata.status_code <= 400 and self.rawdata.status_code >= 499:
            self.set_header()
            self.rawdata = requests.post(self.url, headers=self.header)
            

    def set_token(self, new=False):
        if new:
            os.remove(self.tokenfile)
        _tokendata = {}
        _token = None
        if os.path.isfile(self.tokenfile):
            _data = open(self.tokenfile, "r").read()
            try:
                print("Reading token data from file.")
                _tokendata = yaml.safe_load(_data)
            except:
                pass
            _token = _tokendata.get('key')
        if not _token:
            print("No API key found.  Please supply an API key.")
            print("Obtain an API key from:  https://cloudefficiency.corp.adobe.com/#/user/<Your AdobeNet ID>/settings")
            print()
            _token = input("API key:")
            print()
            print(f"Is this API key correct?: {_token}")
            _choice = input("Correct? (Y/N): ")
            if _choice.lower() in ('y', 'yes'):
                breakpoint()
                _tokendata = {'key': _token}
                open(self.tokenfile, "w").write(yaml.dump(_tokendata))
        self.token = _token


    def __init__(self):
        self.tokenfile = os.path.join(os.path.expanduser('~'), '.cloudefficiency.yml')
        self.url      = "https://cloudefficiency.corp.adobe.com/api/v2/billing/aws_unit_pricing"
        self._dbfile  = "/tmp/costs.db"
        self.USE_FILE = True
        self.__data   = None
        self.__db     = None
        self.region   = "us-east-1"
        self.cart     = []
        self.token    = None
        self.rawdata  = None
        self.header   = None
        self.set_rawdata()

        # Fields:
        #   region
        #   product_name
        #   usage_description
        #   subcategory
        #   operation
        #   avg_unit_price
        #   unit
    
    @property
    def db(self):
        if not self.__db:
            print("Creating database.")
            if self.USE_FILE:
                if os.path.exists(self._dbfile):
                    os.remove(self._dbfile)
                self.__db = sqlite3.connect(self._dbfile)
            else:
                self.__db = sqlite3.connect(":memory:")
            sql = """
            CREATE TABLE cost (
                region TEXT,
                product_name TEXT,
                usage_description TEXT,
                subcategory TEXT,
                operation TEXT,
                avg_unit_price REAL,
                unit TEXT
            )
            """
            self._db_exec(sql)
            self.db.commit()
            print("Populating database.")
            for values in self.data["data"]:
                # _region = item[0]
                # _product_name = item[1]
                # _usage_description = item[2]
                # _subcategory = item[3]
                # _operation = item[4]
                # _avg_unit_price = float(item[5])
                # _unit = item[6]
                sql = """
                INSERT INTO
                    cost (
                        region,
                        product_name,
                        usage_description,
                        subcategory,
                        operation,
                        avg_unit_price,
                        unit
                    )
                    values (?, ?, ?, ?, ?, ?, ?)
                """
                self._db_exec(sql, values)
            self.db.commit()
            print("Done.")
        return self.__db

    def get_emr_cost(self, size, hours, region=None):
        unit_cost = self.get_emr_unit_cost(size, region)
        return unit_cost * hours

    def get_ec2_cost(self, size, hours, region=None):
        unit_cost = self.get_ec2_unit_cost(size, region)
        return unit_cost * hours

    def get_ec2_unit_cost(self, size, region=None):
        sql = "SELECT avg_unit_price, unit FROM cost WHERE product_name = ? AND usage_description = ?, AND region = ?"

        _region = region or self.region
        product_string = f"{CF.abbrs[_region]}BoxUsage:{size}"
        values = ("Amazon Elastic Compute Cloud", product_string, _region)
        # Unit is "Hrs"
        return self._db_scalar(sql, values)

    def get_emr_unit_cost(self, size, region=None):
        sql = "SELECT avg_unit_price, unit FROM cost WHERE product_name = ? AND usage_description = ? AND region = ?"

        _region = region or self.region
        product_string = f"{CF.abbrs[_region]}BoxUsage:{size}"
        values = ("Amazon Elastic MapReduce", product_string, _region)
        # Unit is "Hrs"
        return self._db_scalar(sql, values)

    def get_instance_sizes(self):
        sql = "SELECT usage_description FROM cost WHERE product_name = ?"
        values = ("Amazon Elastic Compute Cloud",)
        rows = self._db_rows(sql, values)
        sizes = []
        for row in rows:
            if ("boxusage" in row[0].lower() or "spotusage" in row[0].lower()) and ":" in row[0]:
                sizes.append(row[0].lower().split(":")[1])
        return sorted(list(set(sizes)))

    def _db_exec(self, sql, values=None):
        self._db_rows(sql, values)
    
    def _db_rows(self, sql, values=None):
        cur = self.db.cursor()
        if values:
            cur.execute(sql, values)
        else:
            cur.execute(sql)
        return cur.fetchall()

    def _db_row(self, sql, values=None):
        data = self._db_rows(sql, values)
        if data:
            return data[0]
        else:
            print(f"SQL Query: {sql}")
            print(f"Values:")
            print(json.dumps(values, indent=4))
            sys.exit("No data from database.")
        
    def _db_scalar(self, sql, values=None):
        return self._db_row(sql, values)[0]

    def new_emr(self):
        print("New EMR Cluster.")
        _size = input("Master instance size: ")
        _count = int(input("Number of nodes (total = master + slaves): "))
        _drive_size = int(input("Size of the drives in all instances (GB): "))
        _duration = self.fix_duration(input("How long will this resource live: "))
        return CF.EMR(
                outer=self,
                size=_size,
                count=_count,
                drive_size=_drive_size,
                duration=_duration,
                region=self.region
            )

    def new_ec2(self):
        print("New EC2 Instance.")
        _size = input("Instance size: ")
        _count = int(input("Number of instances: "))
        _drive_size = int(input("Size of the drive in instance (GB): "))
        _duration = self.fix_duration(input("How long will this resource live: "))
        return CF.EC2(
            outer=self,
            size=_size,
            drive_size=_drive_size,
            duration=_duration,
            region=self.region,
            count=_count
        )
    
    def new_s3(self):
        print("New S3 Stoage.")
        _size = int(input("Data to be stored (GB): "))
        _duration = self.fix_duration(input("How long will data be kept in S3: "))
        _egress = int(input("How much data will be transferred out of the AWS ecosystem (GB): "))
        return CF.S3(
            outer=self,
            size=_size,
            duration=_duration,
            egress=_egress,
            region=self.region
        )

    def fix_duration(self, _input):
        # Default is hours
        if isinstance(_input, int):
            return
        if isinstance(_input, float):
            _input = int(_input)
            return
        _input = _input.lower()

        if not re.match("\d+[hdwmy]", _input):
            raise ValueError("Invalid duration specified.")
        if re.match("\d+h", _input):
            # Found hours
            _input = int(_input[:-1])
        elif re.match("\d+d", _input):
            # Found days
            _input = int(_input[:-1]) * 24
        elif re.match("\d+w", _input):
            # Found weeks
            _input = int(_input[:-1]) * 24 * 7
        elif re.match("\d+m", _input):
            # Found months
            _input = int(_input[:-1]) * 24 * 30
        elif re.match("\d+y", _input):
            # Found years
            _input = int(_input[:-1]) * 24 * 365
        return _input

    def human_time(self, hours):
        days, hours = divmod(hours, 24)
        return f"{days}d-{hours}h"

    def ask(self):
        default_region = "us-east-1"
        print("ACS Data Engineering cost approximation calculator")
        print("")
        _region = input(f"Region [{default_region}]: ")
        _region = _region or default_region
        while True:
            print("")
            print("Add new item:")
            print("1) New EMR Cluster")
            print("2) New EC2 Instance")
            print("3) New EBS Volume")
            print("4) New RDS Instance")
            print("5) New S3 Storage")
            print("")
            data = input("Add cost for what resource? (Q or Blank to quit, T for current total): ")
            print("")
            if data.lower() in ("", "q"):
                break
            elif data.lower() == "t":
                self.display_total()
                continue
            elif data == "1":
                self.cart.append(self.new_emr())
            elif data == "2":
                self.cart.append(self.new_ec2())
            elif data == "3":
                self.cart.append(self.new_ebs())
            elif data == "4":
                self.cart.append(self.new_rds())
            elif data == "5":
                self.cart.append(self.new_s3())
            else:
                print(f"Invalid option: {data}")

    def ceiling(self, number, interval=1200):
        total = interval
        while total < number:
            total += interval
        return total
    
    def display_total(self):
        total = 0
        for item in self.cart:
            print("\n".join(item.print()))
            total += item.cost()
        print()
        print(f"       Total: ${total: 0,.2f}")
        print(f"     Rounded: ${self.ceiling(total): 0,.2f}")
        total = self.ceiling(total)
        print(f"     + Base:  $ 4,800.00")
        total += 4800
        print("              ============")
        print(f"      Total:  ${total: 0,.2f}")

    @property
    def data(self):
        if not self.__data:
            print("Retrieving data.")
            self.rawdata = requests.post(self.url, headers=self.header)
            print(repr(self.rawdata))
            self.__data = json.loads(self.rawdata.content.decode())
            print("Done retrieving data.")
            if self.__data.get("errors"):
                for _error in self.__data["errors"]:
                    print(f"Error: {_error}")
                sys.exit(1)
            elif not self.__data.get("data"):
                print(f"Error: No data returned.")
        return self.__data

    def get(self):
        # data = { "product_name": "Amazon Elastic Compute Cloud" }
        print(json.dumps(self.data, indent=4, default=str))
        open("/tmp/aws.txt", "w").write(json.dumps(self.data, indent=4))
    
    def run_local(self):
        _hostname = socket.getfqdn()
        if _hostname.startswith('maintenance'):
            print("This script cannot run within AWS due to Adobe's DNS requirements.")
            print("Please run this script on your work laptop.")
            print("(cloudefficiency.corp.adobe.com is not reachable over the MCT hub.)")
            sys.exit(1)


def main():
    cf = CF()
    cf.run_local()
    cf.ask()
    cf.display_total()

if __name__ == "__main__":
    main()

