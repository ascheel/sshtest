import boto3
import argparse
import json
from dateutil import parser
import datetime
import copy
import sys
import csv
import time
import os
import re


### Touches all stale (not used in 335+ days) roles.
###
### This role is DIRECTLY in support of https://jira.corp.adobe.com/browse/GLADOS-1323  
### "Support exceptions for IAM users/roles policies"  
### Specifically: 'the team feels we should ask the product teams to just touch the role (vs file exception)'  
### The script is supplied "AS-IS, no warranty" and is a WORKAROUND.  This is NOT a fix nor a patch.  It just resets the clock.  
### 
### This is Art Scheel's Role Touch Script.  
### In Linux (and Unix, etc), to 'touch' a file is to update its timestamp.  
### It does not modify the file, only the time-related metadata.  
### This script does the same thing for stale AWS Roles.  
### 
### 1) Iterates through all role names or ARNs as provided by a text file or command line arguments.
### 2) Rejects roles not yet old enough (no cheating.)
### 3) Creates copy of existing Trust Relationship
### 4) Appends a Trust Relationship to the role that allows itself to sts:AssumeRole
### 5) Pauses for a small time period between adding the trust relationship and assuming the role.  This is necessary because AWS takes time to implement the new trust relationship.
### 6) Assumes the role we're touching
### 7) Executes sts.get_caller_identity() which just gets 'Who am I?' kind of information.
### 8) Restores the previous Trust Relationship
### 
### Note:  The role takes a LONG time to update the last activity timestamp after execution. Sometimes 30+ minutes.  The script works, but you may not see immediate results.  
### Note2: Just in case it's needed, all modifications are saved to /tmp/role-touch.{account id}.{timestamp}.csv  
### 


class Trust:
    def __init__(self, **kwargs):
        """
        Constructor.  Takes the args entry from module argparse
        """
        args                   = kwargs.get("args")
        self.profile           = args.profile
        self.access_key_id     = args.access_key_id
        self.secret_access_key = args.secret_access_key
        self.force             = args.force

        if self.profile:
            self.aws = boto3.Session(profile_name=self.profile)
        elif self.access_key_id and self.secret_access_key:
            self.aws = boto3.Session(
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key
            )
        else:
            # Assume we have environment variables
            self.aws = boto3.Session()

        self.iam                   = self.aws.resource("iam")
        self.sts                   = self.aws.client("sts")
        self.account_id            = self.aws.client("sts").get_caller_identity()["Account"]
                  
        self.input_file            = args.file
        self.output_file           = f"/tmp/role-touch.{self.account_id}.{self.timestamp()}.csv"
        self.csv_fh                = open(self.output_file, "w")
        self.csv                   = csv.writer(self.csv_fh)
        self.role_list_args        = args.role

        self.age_to_expire_in_days = 335
        self.fail_threshold        = 5
        self.seconds_to_sleep      = 10
        self.seconds_array         = (10, 30, 60, 90, 120)
        self.count                 = 0

        self.arn_pattern           = re.compile("arn:aws:iam::\d{1,12}:role\/.*")

        self.__role_list           = None

    def timestamp(self):
        """
        Gives us a timestamp

        Returns:
            string: YYMMDD-hhmm formatted timestamp
        """
        _format = "%y%m%d-%H%M"
        return datetime.datetime.now().strftime(_format)

    def banner(self):
        """
        Just a banner.
        """
        path = os.path.abspath(__file__)
        with open(path, "r") as f_in:
            for line in f_in:
                if line.startswith("###"):
                    print(line[3:], end="")
        input("(Press a key to continue...)")
        print()

    def role_exists(self, role_name):
        return role_name in self.role_list
    
    @property
    def role_list(self):
        if not self.__role_list:
            self.__role_list = []
            _paginator = self.iam.meta.client.get_paginator("list_roles")
            for _page in _paginator.paginate():
                for _role in _page["Roles"]:
                    self.__role_list.append(_role["RoleName"])
        return self.__role_list

    def loop_file(self):
        """
        Iterates through roles as provided from a file.
        
        Args:
            filename (string): File name containing strings of role names or ARNs, one per line.
        """
        if not self.input_file:
            return
        if not os.path.isfile(self.input_file):
            raise FileNotFoundError(f"File {self.input_file} does not exist or is not file.")

        self.loop([line for line in open(self.input_file, "r").read().splitlines()])

    def loop_arguments(self):
        """
        Iterates through roles as provided from the CLI

        Args:
            role_list (list): List of role names or ARNs.
        """

        self.loop(self.role_list_args or [])

    def loop(self, _list):
        """
        Iterates through all roles from text file and touches them if necessary.
        """
        for role_name in _list:
            role_name = role_name.strip()
            if not role_name:
                continue
            self.count += 1
            if self.arn_pattern.match(role_name):
                # They passed in an ARN
                role_name = role_name.split("/")[-1]

            if not self.role_exists(role_name):
                print()
                print(f"Role name: {role_name} does not exist.")
                continue

            role = self.iam.Role(role_name)
            role_age = self.get_role_age(role)
            print()
            print(f"Role name: {role_name} ({role_age}d) - ({self.count})")

            if role_age < self.age_to_expire_in_days and not self.force:
                # Skip it.  We don't want to allow cheating
                print(f"    Role recently used.  Skipping.")
                continue

            self.touch_role(role)

    def roll(self):
        """
        Iterates through all roles and touches them if necessary.
        """
        self.banner()
        sys.exit()

        count = 0
        _row = ["Account ID", "Role Name", "Original Trust Relationship", "Temporary New Trust Relationship"]
        self.csv.writerow(_row)
        
        paginator = self.iam.meta.client.get_paginator("list_roles")
        for _page in paginator.paginate():
            for _role in _page["Roles"]:
                role_name = _role["RoleName"]
                role = self.iam.Role(role_name)
                role_age = self.get_role_age(role)
                if role_age >= self.age_to_expire_in_days:
                    count += 1
                    print()
                    print(f"Role name: {role_name} ({role_age}d) - ({count})")
                    self.touch_role(role)
    
    def is_aws_role(self, role):
        """
        Is this an AWS-owned-and-managed-role?

        Args:
            role (IAM.Role()): The role

        Returns:
            bool: True if aws role
        """
        path = role.path
        return path.startswith("/aws-service-role")
    
    def touch_role(self, role):
        """
        Resets the clock on a role

        Args:
            role (IAM.Role()): The role
        """
        role_name = role.role_name
        doc_before = copy.deepcopy(role.assume_role_policy_document)
        doc_after = self.append_root_statement(role)

        _row = [self.account_id, role.role_name, doc_before, doc_after]
        self.csv.writerow(_row)
        # print(f"Original policy: {doc_before}")
        # print(f"New policy:      {doc_after}")
        
        if self.is_aws_role(role):
            print("    AWS-maintained Role.  Ignoring.")
            return
        if "mavlink" in role.role_name.lower():
            print("    MAVLINK role.  Ignoring.")
            return

        _needs_changed = False
        if not self.already_has_statement(role):
            _needs_changed = True

        if _needs_changed:
            self.iam.meta.client.update_assume_role_policy(
                RoleName=role.role_name,
                PolicyDocument=json.dumps(doc_after)
            )
            print("    Updated Trust Relationship.")
        
        print(f"    Sleeping for {self.seconds_to_sleep} seconds.")
        time.sleep(self.seconds_to_sleep)
    
        # _arn = f"arn:aws:iam::{self.account_id}:role/{role.role_name}"
        
        fail_count = 0
        passed = False
        for _seconds_to_sleep in self.seconds_array:
            try:
                # AWS Wants a new object, otherwise it just complains about permissions.
                tmp_aws = None
                if self.profile:
                    tmp_aws = boto3.Session(profile_name=self.profile)
                elif self.access_key_id and self.secret_access_key:
                    tmp_aws = boto3.Session(
                        aws_access_key_id=self.access_key_id,
                        aws_secret_access_key=self.secret_access_key
                    )
                else:
                    # Assume we have environment variables
                    tmp_aws = boto3.Session()

                assume_role_object = tmp_aws.client("sts").assume_role(
                    RoleArn=role.arn,
                    RoleSessionName="AssumeRoleSession"
                )
                # assume_role_object = self.sts.assume_role(
                #     RoleArn=role.arn,
                #     RoleSessionName="AssumeRoleSession"
                # )
                creds = assume_role_object["Credentials"]
                sub_sts = boto3.client(
                    "sts",
                    aws_access_key_id=creds["AccessKeyId"],
                    aws_secret_access_key=creds["SecretAccessKey"],
                    aws_session_token=creds["SessionToken"]
                )
                
                # This is what actually resets our clock.
                # If you don't want to print it, then don't.
                data = sub_sts.get_caller_identity()
                # print(json.dumps(data, indent=4, default=str))
                print("    Touched.")
                passed = True
                break
            except self.sts.exceptions.ClientError:
                fail_count += 1
                print(f"    FAILED. ({fail_count}/{len(self.seconds_array)}) (Sleeping for {_seconds_to_sleep} sec)")
                print(f"        {sys.exc_info()}")
                time.sleep(_seconds_to_sleep)
        if not passed:
            print(f"    FAILED PERMANENTLY.  Bailing.")

        if _needs_changed:
            self.iam.meta.client.update_assume_role_policy(
                RoleName=role_name,
                PolicyDocument=json.dumps(doc_before)
            )
            print("    Trust Relationship rolled back.")

    def already_has_statement(self, role):
        """
        Checks if the role already has a root statement for us to use.

        Args:
            role (IAM.Role()): The role

        Returns:
            bool: True if it has the statement
        """
        for statement in role.assume_role_policy_document["Statement"]:
            if statement == self.get_doc():
                return True
        return False

    def append_root_statement(self, role):
        """
        Adds our root trust relationship statement

        Args:
            role (IAM.Role()): The role

        Returns:
            string: The new statement
        """
        doc = copy.deepcopy(role.assume_role_policy_document)
        doc["Statement"].append(self.get_doc())
        return doc
    
    def get_doc(self):
        """
        Creates and returns a root document for use in the trust relationship statement

        Returns:
            string: The statement
        """
        return {
            "Effect": "Allow",
            "Principal" : {
                "AWS": f"arn:aws:iam::{self.account_id}:root"
            },
            "Action": "sts:AssumeRole"
        }


    def get_role_age(self, role):
        """
        Gets the age of the role based on when it was last used, if ever.
        If it's never been used, then it assumes last used date was date of creation.

        Args:
            role (IAM.Role()): The role

        Returns:
            int: Number of days since it was last used.
        """
        date_today     = datetime.datetime.now().replace(tzinfo=None)
        date_created   = role.create_date.replace(tzinfo=None)
        date_last_used = role.role_last_used.get("LastUsedDate", date_created).replace(tzinfo=None)
        _diff = date_today - date_last_used
        return _diff.days
    
    def disclaimer(self):
        print()
        print("Disclaimer:  PLEASE allow a long time for your last-used dates to update.  I have seen it take 1-2 hours in some cases.")
        print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        "--profile",
        help="The profile to use within AWS."
    )
    parser.add_argument(
        "-a",
        "--access_key_id",
        help="AWS Access Key ID"
    )
    parser.add_argument(
        "-s",
        "--secret_access_key",
        help="AWS Secret Access Key"
    )
    parser.add_argument(
        "-f",
        "--file",
        help="List of role ARN identifiers or Role name in a text file, one item per line"
    )
    parser.add_argument(
        "-r",
        "--role",
        help="role name or role ARN.  Supports multiple.",
        action="append"
    )
    parser.add_argument(
        "--force",
        help="Force role refresh.",
        action="store_true"
    )
    args = parser.parse_args()

    trust = Trust(args=args)
    # trust.roll()
    trust.loop_file()
    trust.loop_arguments()
    trust.disclaimer()

if __name__ == "__main__":
    main()
