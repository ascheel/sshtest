#!/usr/bin/env python3

import yaml
import os
import argparse
import sys
import inventory


class Find:
    def __init__(self):
        self.root = os.path.dirname(os.path.abspath(__file__))

        self.inventory = inventory.Inventory()
        self.instances = self.inventory.instances

    def go(self, **kwargs):
        instances = self.__get_instances()
        _found, _unfound = self.inventory.find(**kwargs, instances=instances)

        for instance_id in _unfound:
            _launch      = self.inventory.launched(instance_id)
            if _launch:
                _launch = _launch.strftime("%Y-%m-%d %H:%M")
            _seen        = self.inventory.last_seen(instance_id)
            if _seen:
                _seen = _seen.strftime("%Y-%m-%d %H:%M")
            print(f"{instance_id:19} - not found (Launch: {_launch}, Seen: {_seen}).")
        for instance_id in _found:
            _aws_account = self.instances[instance_id]['account']
            _private_ip  = self.instances[instance_id]['private_ip']
            _name        = self.instances[instance_id]['name']
            _launch      = self.instances[instance_id]['launch_time'].strftime("%Y-%m-%d %H:%M")
            print(f"{instance_id:19} - {_aws_account:15} - {_private_ip:15} {_name} (Launch: {_launch})")


        print(f"Not found: {len(_unfound)}")
        print(f"Found:     {len(_found)}")
    
    def __get_instances(self):
        # No instances passed via command line.  Ask for them.
        instances = []
        while True:
            data = input("Next text (blank to search): ")
            if not data:
                break
            data = self.trim(data)
            instances.append(data)

        return sorted(list(set(instances)))

    def trim(self, text):
        # Throws out everything after the first space.  If there is a colon, it throws out everything after the first.
        return text.split(" ")[0].split(":")[0]


    def compile_date_data(self):
        self.inventory.compile_date_data()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--id",
        help="Search by instance ID only",
        action="store_true"
    )
    args = parser.parse_args()

    find = Find()
    find.go(id_only=args.id)

if __name__ == "__main__":
    main()

