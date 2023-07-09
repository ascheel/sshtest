#!/usr/bin/env python3

import inventory
import sys


def _trim(text):
    # Throws out everything after the first space.  If there is a colon, it throws out everything after the first.
    return text.split(" ")[0].split(":")[0]


def main():
    instances = None
    if len(sys.argv) == 1:
        instances = []
        while True:
            data = input("Next text (blank to search): ")
            if not data:
                break
            data = _trim(data)
            instances.append(data)
    else:
        instances = sys.argv[1:]

    i = inventory.Inventory()
    i.export_to_ansible_oneshot(instances=instances)


if __name__ == "__main__":
    main()

