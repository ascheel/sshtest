import sys
import os
import boto3
import botocore
import json
import datetime
import copy
import builtins
import yaml
import hvac
from getpass import getpass
import pytz
import argparse

"""
Checks for users, particularly their required tags.
"""

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


def validate(text):
    """
    validates true/false strings into True and False python datatypes

    Args:
        text ([type]): [description]
    
    Returns:
        [type]: [description]
    """
    if text.lower() == "true":
        return True
    if text.lower() == "false":
        return False
    return text


def p(_obj):
    """
    print lists and dictionaries in a nice, pretty format
    
    Args:
        _obj (list, dict): object to print.
    """
    print(json.dumps(stringify_dates(_obj), indent=4))

def print(*args, **kwargs):
    """
    custom print() function so we can color our outputs.
    
    Returns:
        results from builtin print()
    """
    if 'color' in kwargs:
        _color = kwargs['color']
        del kwargs['color']
        if is_color_term() and _color:
            new_args = []
            for arg in args:
                new_args.append('{}{}{}'.format(color(_color), args[0], color('default')))
            args = tuple(new_args)
    return builtins.print(*args, **kwargs)

def color(c):
    """
    Returns ANSI color codes based on an input color name
    :param c: string color name
    :returns: string ANSI color code
    """
    c = c.lower()
    ansi = {
        'black': '\033[0;30m',
        'darkred': '\033[0;31m',
        'darkgreen': '\033[0;32m',
        'darkyellow': '\033[0;33m',
        'darkblue': '\033[0;34m',
        'darkmagenta': '\033[0;35m',
        'darkcyan': '\033[0;36m',
        'gray': '\033[0;37m',

        'darkgray': '\033[1;30m',
        'red': '\033[1;31m',
        'green': '\033[1;32m',
        'yellow': '\033[1;33m',
        'blue': '\033[1;34m',
        'magenta': '\033[1;35m',
        'cyan': '\033[1;36m',
        'white': '\033[1;37m',

        'blackbg': '\033[40m',
        'redbg': '\033[41m',
        'greenbg': '\033[42m',
        'yellowbg': '\033[43m',
        'bluebg': '\033[44m',
        'magentabg': '\033[45m',
        'cyanbg': '\033[46m',
        'whitebg': '\033[47m',

        'reset': '\033[0;0m',
        'bold': '\033[1m',
        'reverse': '\033[2m',
        'underline': '\033[4m',

        'clear': '\033[2J',
    #   'clearline': '\033[K',
        'clearline': '\033[2K',
    #   'save': '\033[s',
    #   'restore': '\033[u',
        'save': '\0337',
        'restore': '\0338',
        'linewrap': '\033[7h',
        'nolinewrap': '\033[7l',

        'up': '\033[1A',
        'down': '\033[1B',
        'right': '\033[1C',
        'left': '\033[1D',

        'default': '\033[0;0m',
    }
    if c.lower() == 'list':
        return ansi
    if c not in ansi:
        return ansi["default"]
    return ansi[c]


def is_color_term():
    """
    Checks if currnet TERM environment variable is allows color
    :returns: boolean True if color-allowed, otherwise False
    """
    terms = ('xterm', 'vt100', 'screen')
    TERM = os.environ.get('TERM', None)
    if not TERM:
        return False
    for term in terms:
        if TERM.startswith(term):
            return True
    return False


class IAM:
    def __init__(self, profile):
        self.profile = profile
        self.aws = boto3.Session(profile_name=self.profile)
        
        # Default to us-east-1 because it's irrelevant
        self.iam = self.aws.resource("iam", region_name="us-east-1")

        self.settings = yaml.load(open(IAM.config_file(), "r").read(), Loader=yaml.FullLoader)

        creds = yaml.load(open(os.path.join(os.path.expanduser("~"), ".adobenet.yml"), "r").read(), Loader=yaml.FullLoader)

    @staticmethod
    def config_file():
        return "{}.yml".format(os.path.splitext(os.path.abspath(__file__))[0])

    @staticmethod
    def roll_it(args):

        #config_file = "{}.yml".format(os.path.splitext(os.path.abspath(__file__))[0])
        settings = yaml.load(open(IAM.config_file(), "r").read(), Loader=yaml.FullLoader)
        settings2 = yaml.load(open("/etc/ea/ea.yml", "r").read(), Loader=yaml.FullLoader)
        profiles = settings2["aws"]["accounts"]
        for profile in profiles:
            i = IAM(profile)
            i.print_good = args.print_good
            i.print_all  = args.print_all
            i.scan()

    def users(self):
        paginator = self.iam.meta.client.get_paginator("list_users")
        pages = paginator.paginate()
        for page in pages:
            #p(page)
            for user in page["Users"]:
                yield user["UserName"]
            #yield page

    def get_tag(self, _obj, _tag):
        tags = _obj.tags or []
        for tag in tags:
            if tag["Key"].lower() == _tag.lower():
                return validate(tag["Value"])
        return None

    def user_has_old_access_keys(self, user):
        if isinstance(user, str):
            user = self.iam.User(username)
        access_keys = user.access_keys

        for key in access_keys.all():
            _last_used = self.iam.meta.client.get_access_key_last_used(AccessKeyId=key.id)["AccessKeyLastUsed"]
            _last_used = _last_used.get("LastUsedDate")
            #import pdb; pdb.set_trace()
            nowtime = pytz.utc.localize(datetime.datetime.utcnow())
            thentime = _last_used
            if thentime == None:
                return True
            age = (nowtime - thentime).days
            if age > 364:
                return True
        return False

    def has_iam_password(self, user):
        login_profile = self.iam.LoginProfile(user)
        try:
            login_profile.create_date
            return True
        except:
            return False

    def get_account_last_used(self, user):
        last_used = "Never"
        password_last_used = user.password_last_used
        if password_last_used:
            last_used = password_last_used
        for access_key in user.access_keys.all():
            access_key_last_used = self.iam.meta.client.get_access_key_last_used(AccessKeyId=access_key.id)
            access_key_last_used = access_key_last_used["AccessKeyLastUsed"]
            access_key_last_used = access_key_last_used.get("LastUsedDate")
            
            if last_used == "Never" and access_key_last_used:
                last_used = access_key_last_used
                continue
                
            if access_key_last_used and (access_key_last_used > last_used or last_used == "Never"):
                last_used = access_key_last_used
        return last_used

    def age_in_days(self, thentime):
        if isinstance(thentime, str):
            return thentime
        nowtime = pytz.utc.localize(datetime.datetime.utcnow())
        if not thentime:
            return None
        days = (nowtime - thentime).days
        if days == 0:
            return "Today"
        return "{} d".format(days)

    def scan(self):
        line = "{:20} {:30} {:10} {:10} {}".format(
            "AWS Account",
            "IAM User",
            "Last Used",
            "Has Pass",
            "Created"
        )
        print("=" * len(line))
        print(line)
        for _username in self.users():
            _user         = self.iam.User(_username)
            _last_used    = self.get_account_last_used(_user)
            _last_used    = self.age_in_days(_last_used)
            _created      = _user.create_date.strftime("%Y/%m/%d")
            _has_password = self.has_iam_password(_user)
            color = None
            if _username in self.settings["whitelist"]:
                # Is it in our friendly list of names to never check?
                color = None
            if _has_password:
                color = "red"
            if not self.print_all:
                if color == "red" and self.print_good:
                    continue
                if color != "red" and not self.print_good:
                    continue
            print(
                "{:20} {:30} {:10} {:10} {}".format(
                    self.profile,
                    _username,
                    str(_last_used),
                    "Yes" if _has_password else "No",
                    _created
                ),
                color=color
            )


def main():
    #i = IAM()
    #i.scan()
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-g",
        "--print-good",
        help="Prints good accounts.  Default is to print only bad accounts.",
        action="store_true",
        default=False
    )
    group.add_argument(
        "-a",
        "--print-all",
        help="Prints all accounts, regardless of good/bad status.",
        action="store_true",
        default=False
    )
    args = parser.parse_args()
    IAM.roll_it(args)

if __name__ == "__main__":
    main()
