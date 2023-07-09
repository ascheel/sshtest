import boto3
import os
import json


AWS_STACKNAME = "DevOpsMaintenanceServer"
AWS_REGION    = "us-east-1"


def get_output(outputs, key):
    for output in outputs:
        if output["OutputKey"] == key:
            return output["OutputValue"]


def main():
    aws = boto3.Session(profile_name="na-ea-prod")
    cfn = aws.client("cloudformation", region_name=AWS_REGION)
    data = cfn.describe_stacks(StackName=AWS_STACKNAME)
    outputs = data["Stacks"][0]["Outputs"]
    ip = get_output(outputs, "ServerIP")
    print(ip, end="")

    with open(f"{os.environ['HOME']}/.ssh/maint", "w") as f_out:
        text = [
            "Host maint maintenance %IP%",
            "\tHostname %IP%",
            "\tUser ea",
            "\tIdentityFile /home/scheel/.ssh/id_rsa_devops",
            "\tProxyJump jump.prod-va6.ea.adobe.net",
            ""
        ]
        for line in text:
            line = line.replace("%IP%", ip)
            f_out.write(line)
            f_out.write("\n")


if __name__ == "__main__":
    main()

