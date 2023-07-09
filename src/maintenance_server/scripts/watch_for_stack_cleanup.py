import boto3
import sys
import json
import time
import os


def status_check(status):
    # 0 = success
    # 1 = fail
    # 2 = in progress
    success = ("DELETE_COMPLETE",)
    fail    = ("DELETE_FAILED",)
    if status in success:
        return 0
    elif status in fail:
        return 1
    else:
        return 2


def watch(stackname, region):
    aws = boto3.Session()
    cf = aws.client("cloudformation", region_name=region)
    while True:
        results = None
        try:
            results = cf.describe_stacks(StackName=stackname)
        except cf.exceptions.ClientError as e:
            print("Stack does not exist.")
            sys.exit(0)
        status = results["Stacks"][0]["StackStatus"]
        if status_check(status) == 2:
            continue
        if status_check(status) == 1:
            sys.exit(f"Stack {stackname} action failed.")
        if status_check(status) == 0:
            print("Cloudformation action successful")
            sys.exit(0)
        time.sleep(5)


def main():
    stackname = os.environ["AWS_STACKNAME"]
    region    = os.environ["AWS_REGION"]
    watch(stackname, region)


if __name__ == "__main__":
    main()
