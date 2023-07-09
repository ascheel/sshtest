import boto3
import os
import json


def get_output(outputs, key):
    for output in outputs:
        if output["OutputKey"] == key:
            return output["OutputValue"]


def main():
    aws = boto3.Session()
    cfn = aws.client("cloudformation", region_name=os.environ["AWS_REGION"])
    data = cfn.describe_stacks(StackName=os.environ["AWS_STACKNAME"])
    outputs = data["Stacks"][0]["Outputs"]
    ip = get_output(outputs, "ServerIP")
    print(ip, end="")


if __name__ == "__main__":
    main()

