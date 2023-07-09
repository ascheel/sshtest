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

    def remove(self, **kwargs):
        _nulls, _ = self.inventory.find(**kwargs, nullusers=True)

        for instance_id in _nulls:
            _aws_account = self.instances[instance_id]['account']
            _name        = self.instances[instance_id]['name']
            _launch      = self.instances[instance_id]['launch_time'].strftime("%Y-%m-%d %H:%M")
            print(f"{instance_id:19} - {_aws_account:15} - {_name} (Launch: {_launch})")
            self.inventory.instances.pop(instance_id)
        self.inventory.save()
        self.inventory.symlink()

        print(f"Null users:     {len(_nulls)}")


def main():
    find = Find()
    find.remove()

if __name__ == "__main__":
    main()

