#!/usr/bin/env python3
import urllib.request
import json
import argparse


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-a",
        "--acctno",
        help="Returns AWS account number.",
        action="store_true"
    )
    group.add_argument(
        "-e",
        "--env",
        help="Returns environment abbreviation.  dev|stage|prod",
        action="store_true"
    )
    args = parser.parse_args()

    MAP = {
        "825246229660": "dev",
        "703906229121": "stage",
        "138548266239": "prod",
        "885661242077": "prod",
        "272939673473": "dev",
        "715082977368": "stage",
        "675621389411": "prod",
        "706290578232": "dev",
        "059295778573": "prod"
    }

    doc = "http://169.254.169.254/latest/dynamic/instance-identity/document"
    data = json.loads(urllib.request.urlopen(doc).read())

    if args.acctno:
        print(data["accountId"], end="")
    elif args.env:
        print(MAP[data["accountId"]], end="")


if __name__ == "__main__":
    main()
