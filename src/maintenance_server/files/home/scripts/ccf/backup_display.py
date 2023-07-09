import sys
import os
import yaml
import boto3
import botocore
import json
import datetime
import argparse


### Art's script for listing all backup details for Adobe's QCR process.  Relies on /etc/de/de.yml


def p(_object):
    import datetime
    import copy
    def stringify_dates(_obj):
        """
        Converts all datetime objects into string equivalents.

        Args:
            _obj (list, dict): input list or dictionary to modify

        Returns:
            input type: new object with strings
        """
        def stringify_date(_obj):
            if isinstance(_obj, datetime.datetime):
                return _obj.isoformat()
            return _obj
        _obj_2 = copy.deepcopy(_obj)
        if isinstance(_obj_2, dict):
            for key, value in _obj_2.items():
                _obj_2[key] = stringify_dates(value)
        elif isinstance(_obj, list):
            for offset in range(len(_obj_2)):
                _obj_2[offset] = stringify_dates(_obj_2[offset])
        else:
            _obj_2 = stringify_date(_obj_2)
        return _obj_2
    print(json.dumps(stringify_dates(_object), indent=4))

class Backup:
    def __init__(self, **kwargs):
        self.profile     = kwargs.get("profile_name")
        self.region      = kwargs.get("region_name")
        self.aws         = boto3.Session(profile_name=self.profile)
        self.backup      = self.aws.client("backup", region_name=self.region)

        self.full        = kwargs.get("full")

        self.PRINT_RESTORES = True

        self.output_file = os.path.join(os.path.expanduser("~"), f"Documents/ccf_backup_attestation.{datetime.datetime.now().strftime('%Y-%m-%d')}")
        if self.full:
            self.output_file += ".full"
        self.output_file += ".txt"
        self.out = open(self.output_file, "a")

    def list_plans(self):
        plans = []
        next_token = None
        while True:
            results = None
            if next_token:
                results = self.backup.list_backup_plans(NextToken=next_token)
            else:
                results = self.backup.list_backup_plans()
            for plan in results["BackupPlansList"]:
                yield plan["BackupPlanId"]

            next_token = results.get("NextToken")
            if not next_token:
                break

    def get_plan(self, _id):
        results = self.backup.get_backup_plan(BackupPlanId=_id)
        plan = results["BackupPlan"]
        return plan

    def get_vault(self, _id):
        results = self.backup.describe_backup_vault(BackupVaultName=_id)
        return results

    def get_selections_by_plan(self, _id):
        selections = []
        next_token = None
        while True:
            results = None
            if next_token:
                results = self.backup.list_backup_selections(BackupPlanId=_id, NextToken=next_token)
            else:
                results = self.backup.list_backup_selections(BackupPlanId=_id)
            
            for selection in results["BackupSelectionsList"]:
                yield selection["SelectionId"]
            
            next_token = results.get("NextToken")
            if not next_token:
                break

    def list_vaults(self):
        vaults = []
        next_token = None
        while True:
            results = None
            if next_token:
                results = self.backup.list_backup_vaults(NextToken=next_token)
            else:
                results = self.backup.list_backup_vaults()

            for vault in results["BackupVaultList"]:
                yield vault["BackupVaultName"]
            
            next_token = results.get("NextToken")
            if not next_token:
                break

    def get_restore_points_from_vault_id(self, _id):
        restore_points = []
        next_token = None
        while True:
            results = None
            if next_token:
                results = self.backup.list_recovery_points_by_backup_vault(BackupVaultName=_id, NextToken=next_token)
            else:
                results = self.backup.list_recovery_points_by_backup_vault(BackupVaultName=_id)
            
            for point in results["RecoveryPoints"]:
                yield point
            
            next_token = results.get("NextToken")
            if not next_token:
                break

    def get_selection(self, plan_id, selection_id):
        return self.backup.get_backup_selection(BackupPlanId=plan_id, SelectionId=selection_id)["BackupSelection"]

    def _print(self, text):
        # print(text)
        self.out.write(text)
        self.out.write("\n")
        self.out.flush()

    def print_plans(self):
        self._print(f"Account: {self.profile}")

        self._print(f"    Region: {self.region}")
        # f_out = open(self.output_file, "w")
        for plan_id in self.list_plans():
            #print(f"        Plan: {plan_id}")
            plan     = self.get_plan(plan_id)
            planname = plan["BackupPlanName"]
            self._print(f"        Name: {planname}")
            for selection_id in self.get_selections_by_plan(plan_id):
                selection = self.get_selection(plan_id, selection_id)
                for tag in selection["ListOfTags"]:
                    self._print(f"            If tag \"{tag['ConditionKey']}\" == \"{tag['ConditionValue']}\"")
            self._print(f"            Rules:")
            for rule in plan["Rules"]:
                rulename  = rule["RuleName"]
                schedule  = rule["ScheduleExpression"]
                lifecycle = rule["Lifecycle"]
                vault     = self.get_vault(rule["TargetBackupVaultName"])
                self._print(f"                Name:      {rulename}")
                self._print(f"                Schedule:  {schedule}")
                self._print(f"                Lifecycle: {lifecycle}")
                self._print(f"                Backups:   {vault['NumberOfRecoveryPoints']}")
                if self.full:
                    for point in self.get_restore_points_from_vault_id(vault["BackupVaultName"]):
                        created = point["CreationDate"]
                        status  = point["Status"]
                        delete  = point["CalculatedLifecycle"]["DeleteAt"]
                        size    = point["BackupSizeInBytes"] / (2**30)
                        self._print(f"                    Created {created.strftime('%x %X')} - {size}GB - {status} - Delete after {delete}")

    def close_print(self):
        self.out.flush()
        self.out.close()

    @staticmethod
    def print(full=False):
        filename = f"/home/scheel/Documents/ccf_backup_attestation.{datetime.datetime.now().strftime('%Y-%m-%d')}"
        if full:
            filename += ".full"
        filename += ".txt"
        if os.path.exists(filename):
            os.remove(filename)

        settings = yaml.full_load(open("/etc/de/de.yml", "r").read())
        profiles = settings["aws"]["accounts"]
        regions = settings["aws"]["regions"]

        for profile in profiles:
            for region in regions:
                backup = Backup(profile_name=profile, region_name=region, full=full)
                backup.print_plans()
                backup.close_print()
        print(f"Saved to file: {filename}")


def main():
    # parser = argparse.ArgumentParser()
    # parser.add_argument(
    #     "-f",
    #     "--full",
    #     help="Display full printout, including all current backups in inventory.  By default, only a summary is displayed including schedules.",
    #     action="store_true"
    # )
    # args = parser.parse_args()
    Backup.print(full=False)
    Backup.print(full=True)


if __name__ == "__main__":
    main()

