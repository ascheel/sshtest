#!/usr/bin/env python3
import yaml
import os
import inventory
import json
import sys


class Stats:
    def __init__(self):
        self.inventory = inventory.Inventory()
        self.instances = self.inventory.instances
        self.accounts = {"total": 0}

    @staticmethod
    def print():
        print("AWS accounts:")
        stats = Stats()
        for instance_id, data in stats.instances.items():
            if not stats.accounts.get(data["account"]):
                stats.accounts[data["account"]] = 0
            stats.accounts["total"] += 1
            stats.accounts[data["account"]] += 1
        
        _list = sorted([_ for _ in stats.accounts])
        for account in _list:
            print(f"{account:20} - {stats.accounts[account]}")
            


def main():
    Stats.print()


if __name__ == "__main__":
    main()
