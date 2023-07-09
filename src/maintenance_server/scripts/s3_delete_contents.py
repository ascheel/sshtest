import boto3
import sys
import os


def list_objects(s3, bucketname):
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucketname):
        if not page.get("Contents"):
            continue
        for item in page["Contents"]:
            yield item["Key"]


def delete(bucket, region):
    aws = boto3.Session()
    s3 = aws.client("s3", region_name=region)

    for key in list_objects(s3, bucket):
        print(f"Deleting key: s3://{bucket}/{key}...   ", end="")
        sys.stdout.flush()
        s3.delete_object(Bucket=bucket, Key=key)
        print("Done")


def main():
    # bucketname = "cicd-demo-bucket"
    bucketname = os.environ["BUCKET"]
    region     = os.environ["AWS_REGION"]
    print(f"Bucket: {bucketname}")
    delete(bucketname, region)


if __name__ == "__main__":
    main()
