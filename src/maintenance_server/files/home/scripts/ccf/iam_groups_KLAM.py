# from adobe_ldap import AdobeIAM
import yaml
import os
import sys
import json
import ldap
import argparse


class AdobeIAM:
    def __init__(self):
        self.user = "adobeea@adobe.com"
        self.password = os.environ.get("LDAP_PASSWORD")
        if not self.password:
            sys.exit("Set the following environment variable and run again:\n\nexport LDAP_PASSWORD=<adobeea generic password from vault>\n")

        self.host = "ldaps://or1adodc01.adobenet.global.adobe.com:636"
        self.port = 636
        self.path = "cn=Users,dc=adobenet,dc=global,dc=adobe,dc=com"

        self.group = "EA_DEV_ADMIN_GROUP"

        self.l = ldap.initialize(self.host)
        self.l.set_option(ldap.OPT_REFERRALS, 0)
        self.l.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
        self.l.set_option(ldap.OPT_X_TLS, ldap.OPT_X_TLS_DEMAND)
        self.l.set_option(ldap.OPT_X_TLS_DEMAND, True)
        self.l.simple_bind_s(self.user, self.password)

    def members(self, group):
        results = self.l.search_s(
            self.path,
            ldap.SCOPE_SUBTREE,
            f'sAMAccountName={group}',
            ["member"]
        )

        if not self.group_exists(group):
            raise ValueError(f"LDAP group {group} does not exist.")

        members = [self.parse_text(member.decode()) for member in results[0][1]["member"]]
        return sorted(members)

    def group_exists(self, group):
        results = self.l.search_s(
            self.path,
            ldap.SCOPE_SUBTREE,
            f"sAMAccountName={group}",
            ["member"]
        )

        return len(results) != 0

    def user_exists(self, user):
        results = self.l.search_s(
            self.path,
            ldap.SCOPE_SUBTREE,
            f"sAMAccountName={user}",
            ["memberOf"]
        )

        return len(results) != 0

    def member_of(self, user, group=None):
        results = self.l.search_s(
            self.path,
            ldap.SCOPE_SUBTREE,
            f"sAMAccountName={user}",
            ["memberOf"]
        )

        if not self.user_exists(user):
            raise ValueError(f"LDAP user {user} does not exist.")

        groups = [self.parse_text(_group.decode()) for _group in results[0][1]["memberOf"]]
        if not group:
            return sorted(groups)
        else:
            return group in groups

    def parse_text(self, text):
        return text.split(",")[0].split("=")[1]        


class Report:
    def __init__(self):
        self.iam = AdobeIAM()

        self.settings_file = "/etc/ea/ea.yml"
        self.settings = yaml.safe_load(open(self.settings_file, "r").read())
        profiles = [_profile for _profile in self.settings["aws"]["accounts"]]
        count1 = 0
        for profile in profiles:
            count1 += 1
            info             = self.settings["aws"]["accounts"][profile]
            acctno           = info["accountno"]
            env              = info["env"]
            group_owner      = info["ldap"]["owner"]
            group_read_only  = info["ldap"]["read_only"]
            group_power_user = info["ldap"]["power_user"]
            group_admin      = info["ldap"]["admin"]

            print(f"{count1:03}. AWS Account: {profile} - {acctno} ({env})")
            print(f"    Owner group: {group_owner}")
            print(f"    Members:")
            count2 = 0
            for user in self.iam.members(group_owner):
                count2 += 1
                print(f"        {count2:03}. {user}")

            print(f"    Read Only group: {group_read_only}")
            print(f"    Members:")
            count2 = 0
            for user in self.iam.members(group_read_only):
                count2 += 1
                print(f"        {count2:03}. {user}")

            print(f"    Owner group: {group_power_user}")
            print(f"    Members:")
            count2 = 0
            for user in self.iam.members(group_power_user):
                count2 += 1
                print(f"        {count2:03}. {user}")

            print(f"    Owner group: {group_admin}")
            print(f"    Members:")
            count2 = 0
            for user in self.iam.members(group_admin):
                count2 += 1
                print(f"        {count2:03}. {user}")


def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    report = Report()


if __name__ == "__main__":
    main()
