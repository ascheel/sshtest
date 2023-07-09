from __future__ import print_function

import datetime
import os
import random
import sys
import abc

import requests
import getpass
import json
import urllib3
import yaml

urllib3.disable_warnings(urllib3.exceptions.InsecurePlatformWarning)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
urllib3.disable_warnings(urllib3.exceptions.SNIMissingWarning)


# TODO - look into translating all the actual actions into runnable commands

class Colors(object):
    HEADER = '\033[95m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ENDC = '\033[0m'


class Credentials(object):
    def __init__(self):
        self.username = None
        self.password = None
        self.token = {
            'opsapi': {
                'token': ''
            }
        }
        self.parameters = None
        self.allowed_systems = ['opsapi', 'skms', 'cmdb', 'git']
        self.home_dir = os.getenv('HOME')
        self.ops_api_token_url = 'https://opsapi.adobe.net/o/token/'
        self.ops_api_url = 'https://opsapi.adobe.net/api'
        self.ops_api_version = 'v1'
        self.ops_api_client_id = 'BhgubzfWxB2VL0j1ZZyI7tWYCSwlzjCqd3gngFwu'
        self.create_api_token('opsapi')
        self.load_local_api_token('opsapi')

    def delete_local_api_token(self, system):
        """
        Attempts to delete the local token stored in the ini file
        :param system: The system to attempt to get the api token for. ie. 'opsapi', 'skms', 'cmdb', 'git'
        :type system: str
        :return: returns success of the delete
        :rtype: bool
        """
        with open('{0}/.denali/polaris.yaml'.format(self.home_dir), 'r') as f:
            config = yaml.load(f)

        if system in self.allowed_systems:
            if not config.get(system, {}).get('token'):
                print("\nLooks like your token doesn't exist. You're all set!\n\n")
                sys.exit(0)

            config[system]['token'] = ''

            with open('{0}/.denali/polaris.yaml'.format(self.home_dir), 'w+') as yamlfile:
                yaml.dump(config, yamlfile)

            return True

        else:
            print("Sorry {0} isn't a system I monitor API tokens for. Try 'opsapi'".format(system))
            return False

    def load_local_api_token(self, system):
        """
        Attempts to get the specified systems api token
        :param system: The system to attempt to get the api token for. ie. 'opsapi', 'skms', 'cmdb', 'git'
        :type system: str
        :return: returns the token you attempted to get
        :rtype: str or None
        """
        with open('{0}/.denali/polaris.yaml'.format(self.home_dir), 'r') as f:
            config = yaml.load(f)

        if system in self.allowed_systems:
            if not self.token.get(system, {}).get('token'):
                try:

                    self.token[system]['token'] = config[system]['token']
                except (KeyError, IndexError):
                    self.token[system]['token'] = ''

            return self.token[system]['token']

        else:
            print("Sorry {0} isn't a system I monitor API tokens for. Try 'opsapi'".format(system))
            return False

    def set_local_api_token(self, token, system):
        """
        Attempts to set the specified systems api token locally
        :param token: the token to be saved
        :type token: str
        :param system: The system to attempt to get the api token for. ie. 'opsapi', 'skms', 'cmdb', 'git'
        :type system: str
        :return: returns the success of the attempted save
        :rtype: bool
        """
        with open('{0}/.denali/polaris.yaml'.format(self.home_dir), 'r') as f:
            config = yaml.load(f)

        if system in self.allowed_systems:
            self.token[system]['token'] = token
            config[system]['token'] = token

            with open('{0}/.denali/polaris.yaml'.format(self.home_dir), 'w+') as yamlfile:
                yaml.dump(config, yamlfile)
                return True

        else:
            print("Sorry {0} isn't a system I monitor API tokens for. Try 'opsapi'".format(system))
            return False

    def delete_local_credentials(self, system):
        """
        Attempts to delete the local user credentials in the polaris.ini file
        :param system: The system to attempt to get the api token for. ie. 'opsapi', 'skms', 'cmdb', 'git'
        :type system: str
        :return: returns the success of the attempted delete
        :rtype: bool
        """
        with open('{0}/.denali/polaris.yaml'.format(self.home_dir), 'r') as f:
            config = yaml.load(f)

        if system in self.allowed_systems:
            if not config.get(system, {}).get('username'):
                print("\nLooks like your username doesn't exist. You're all set!\n\n")
                sys.exit(0)

            config[system]['username'] = ''

            with open('{0}/.denali/polaris.yaml'.format(self.home_dir), 'w+') as yamlfile:
                yaml.dump(config, yamlfile)
                return True

        else:
            print("Sorry {0} isn't a system I monitor API tokens for. Try 'opsapi'".format(system))
            return False

    def set_local_credentials(self, username, system):
        """
        Attempts to set the specified systems username and password
        :param username: Username to be saved
        :type username: str
        :param system: The system to attempt to get the api token for. ie. 'skms', 'cmdb', 'git'
        :type system: str
        :return: returns the success of the attempted set
        :rtype: bool
        """
        self.username = username
        with open('{0}/.denali/polaris.yaml'.format(self.home_dir), 'r') as f:
            config = yaml.load(f)

        if system in self.allowed_systems:
            config[system]['username'] = username
            with open('{0}/.denali/polaris.yaml'.format(self.home_dir), 'w+') as yamlfile:
                yaml.dump(config, yamlfile)
                return True

        else:
            print("Sorry {0} isn't a system I monitor API tokens for. Try 'opsapi'".format(system))
            return False

    def load_local_credentials(self, system):
        """
        Attempts to get the specified systems username
        :param system: The system to attempt to get the api token for. ie. 'skms', 'cmdb', 'git'
        :type system: str
        :return: returns the username you attempted to get
        :rtype: str or None
        """
        with open('{0}/.denali/polaris.yaml'.format(self.home_dir), 'r') as f:
            config = yaml.load(f)

        if system in self.allowed_systems:
            if not self.username:
                try:
                    self.username = config[system]['username']
                except (KeyError, IndexError):
                    self.username = None

            return self.username

        else:
            print("Sorry {0} isn't a system I monitor API tokens for. Try 'opsapi'".format(system))
            return False

    def create_api_token(self, system):
        """
        Attempts to get an api token from one of the Adobe systems, 'skms', 'cmdb', 'git'
        :param system: The system to attempt to get the api token for. ie. 'skms', 'cmdb', 'git'
        :type system: str
        :return: returns the token or None
        :rtype: str or None
        """
        if not self.home_dir:
            print("\n\nUnable to get home directory to grab the yaml file.\n")
            return False

        if system in self.allowed_systems:
            if not self.username:
                try:
                    self.load_local_credentials(system)
                except (KeyError, IndexError):
                    pass

            if not self.token[system]['token']:
                try:
                    self.load_local_api_token(system)
                except (KeyError, IndexError):
                    pass

        if system == 'opsapi':
            if not self.token[system]['token']:
                print(
                    "\nCouldn't find a saved token for system '{0}'. Provide credentials to get another one".format(
                        system))

                while True:
                    username = raw_input(
                        "Username [{0}]: ".format(self.username if self.username else getpass.getuser()))
                    if username:
                        if not self.username:
                            self.set_local_credentials(username, system)

                        break

                    elif not username and self.username:
                        break

                    elif not username and not self.username:
                        self.set_local_credentials(getpass.getuser(), system)
                        break

                    else:
                        print("You must enter a valid username. Please try again")

                password = getpass.getpass()
                # Set the username in the local credentials file

                data = {'grant_type': 'password', 'username': self.username, 'password': password,
                        'client_id': self.ops_api_client_id}
                # data.update({'client_id': client_id})

                res = requests.post(self.ops_api_token_url, data=data, verify=False, allow_redirects=False)
                json_token = json.loads(res.content)
                if res.status_code in [200, 201, 202, 205]:
                    self.set_local_api_token(json_token.get('access_token').encode('utf-8'), system)

                else:
                    print("Error: {0} Please try again".format(json_token.get('error_description')))
                    print("Error status_code: {0}".format(res.status_code))
                    sys.exit(1)

            return self.token[system]['token']

        else:
            print("\n\nI'm sorry, my responses are limited.. You must ask the right questions. I don't know system "
                  "'{0}'".format(system))
            sys.exit(1)


def __write_blank_config_file():
    if not os.path.exists('{0}/.denali/polaris.yaml'.format(os.getenv('HOME'))):
        config = """\
opsapi:
    token: ''
    username: ''
"""
        with open('{0}/.denali/polaris.yaml'.format(os.getenv('HOME')), 'w') as f:
            yaml.dump(yaml.load(config), f)


def __write_blank_api_map_file():
    if not os.path.isfile('{0}/.denali/polaris_api_map.json'.format(os.getenv('HOME'))):
        with open('{0}/.denali/polaris_api_map.json'.format(os.getenv('HOME')), "a") as api:
            pass


__write_blank_config_file()
__write_blank_api_map_file()
creds = Credentials()


def main(denali_variables, *parameters):
    p = []
    if not parameters[0]:
        p.append('help')

    else:
        for par in parameters[0].split(','):
            p.append(par)

    polaris = Polaris()
    api_map = polaris.api_map
    denali = parse_denali_variables(denali_variables)
    params = parse_args(p, api_map)

    if params.get('help') or not params:
        print_help(api_map, params.get('sub_help'))
        sys.exit(0)

    if params.get('delete') == 'token':
        success = polaris.delete_local_api_token('opsapi')
        if success:
            print("\n" + Colors.OKBLUE + "Great, I deleted your token.\n\n" + Colors.ENDC)
            sys.exit(0)

    if params.get('delete') == 'username':
        success = polaris.delete_local_credentials('opsapi')
        if success:
            print("\n" + Colors.OKBLUE + "Great, I deleted your username.\n\n" + Colors.ENDC)
            sys.exit(0)

    if not polaris.token['opsapi']['token']:
        polaris.create_api_token('opsapi')

    if not params.get('action'):
        print(Colors.WARNING + "You must supply the action you want to do. Pass in 'help' for the full "
                               "list of actions\n\n" + Colors.ENDC)
        sys.exit(1)

    action = sanitize_action(params.get('action').lower())
    method = params.get('method', '').lower()

    if not method:
        print(action)
        # print(api_map.get(action))
        # print(json.dumps(api_map, indent=4))
        if api_map.get(action).get('single_method'):
            method = 'update'

        else:
            print(Colors.WARNING + "You must supply the method you want to do. Pass in 'help' for the full "
                                   "list of methods\n\n" + Colors.ENDC)
            sys.exit(1)

    method = sanitize_method(method)

    if params:
        # Populate the dict with the arguments passed in as parameters to the main
        hydrate_arguments(action, method, params, api_map, denali)

        # Populate the dict with the query params passed in as parameters to the main
        hydrate_query_params(action, method, params, api_map, denali)

        # Check for missing query params that the user didn't provide
        check_missing_query_params(action, method, api_map)
        query_params = api_map.get(action).get('methods').get(method).get('query_params')

        # If method requires data to perform the request, lets get it
        if method == 'update' or method == 'create' or method == 'partial_update':
            check_missing_argument_data(action, method, api_map)

        # Create our request data
        data = create_request_data(action, method, api_map) if method not in ['list', 'retrieve', 'destroy'] else {}

        accept_map = {
            'txt': 'application/json',
            'csv': 'text/csv',
            'yaml': 'application/yaml',
            'yml': 'application/yaml',
            'xml': 'application/xml',
            'json': 'application/json'
        }

        out = denali.get('out')
        if out:
            for o in out:
                directory = o[:o.rfind('/')] if '/' in o and os.path.isdir(o[:o.rfind('/')]) else os.getcwd()
                file_name = o[o.rfind('/') + 1:] if '/' in o else o if len(o.split('/')) == 1 else o
                if file_name.__contains__('.'):
                    # if there is a . it means there is an extension and we need to handle that accordingly
                    ext = file_name.split('.')
                    accept = accept_map.get(ext[len(ext) - 1], False)
                    polaris.headers['accept'] = accept if accept else 'application/json'
                    res = getattr(polaris, api_map.get(action).get('command'))(query_params=query_params,
                                                                               data=data).run(method)
                    with open("{0}/{1}".format(directory, file_name), 'w') as f:
                        if ext[len(ext) - 1].__contains__('json'):
                            f.write(json.dumps(res, indent=4) + "\n")

                        elif ext[len(ext) - 1] in ['csv', 'yaml', 'xml', 'txt', 'yml']:
                            f.write(res)

                        else:
                            print(json.dumps(res, indent=4))

                else:
                    accept = accept_map.get(file_name)
                    polaris.headers['accept'] = accept if accept else 'application/json'
                    res = getattr(polaris, api_map.get(action).get('command'))(query_params=query_params,
                                                                               data=data).run(method)
                    if file_name in ['json', 'txt']:
                        print(json.dumps(res, indent=4))

                    elif file_name == 'csv':
                        print(res)

                    elif file_name == 'xml':
                        import xml.dom.minidom as xml
                        string = xml.parseString(res)
                        print(string.toprettyxml('  '))

                    elif file_name == 'yaml' or file_name == 'yml':
                        print(res)

                    else:
                        print(json.dumps(res, indent=4))

        else:
            res = getattr(polaris, api_map.get(action).get('command'))(query_params=query_params,
                                                                       data=data).run(method)
            print(json.dumps(res, indent=4))


def parse_args(parameters, api_map):
    """
    Parses the user provided args and creates a parameters dict from it
    :param api_map: the api map for the ops api
    :type api_map: dict
    :param parameters: User provided parameters
    :type parameters: list
    :return: returns a dict representation of the keyword tuple
    :rtype: dict
    """
    keywords = {}
    temp_action = [a for a in api_map.get('actions')]
    temp_action.append('all')

    for param in parameters:
        try:
            # for the case that there is only parameter passed and that parameter is just 'help'
            if len(param.split('=')) == 1 and len(parameters) == 1:
                p = param.strip('-')
                if 'help' in p or p == 'h':
                    keywords['help'] = True
                    return keywords

            elif (param == 'help' or param == 'h' or param == '-h' or param == '--help') and len(parameters) > 1:
                print("You must enter help in the format 'help' or 'help=<action>'\n")
                keywords['help'] = False
                return keywords

            # we attempt to split the parameter into key and value based on '=' or ' '
            try:
                key, value = param.split('=')
                key = key.strip('-')

            except ValueError:
                try:
                    key, value = param.split(' ')
                    key = key.strip('-')

                except ValueError:
                    try:
                        key, value = param.split(',')
                        key = key.strip('-')

                    except ValueError:
                        key, value = '', ''

            # we attempt to see if the parameter is help and if so what the sub help command is
            if 'help' in key or 'h' == key:
                keywords['help'] = True
                if value in temp_action:
                    keywords['sub_help'] = value
                    break

            keywords[key] = value
        except (KeyError, ValueError, IndexError):
            pass

    return keywords


def parse_denali_variables(denali_variables):
    """
    Parse the denali variables for the stuff that's important
    :param denali_variables: the variables that denali tracks
    :type denali_variables: dict
    :return: returns the parsed dict of denali variables
    :rtype: dict
    """
    denali = {}
    for cli in denali_variables.get('cliParameters'):
        if cli[0].__contains__('-o') or cli[0].__contains__('--out'):
            denali['out'] = cli[1].split(',')

        else:
            denali[cli[0].strip('-')] = cli[1]

    return denali


def hydrate_query_params(action, method, parameters, api_map, denali):
    """
    Attempts to populate the api_map query params with the provided user parameters
    :param action: Action to be performed
    :type action: str
    :param method: Method to be performed, one of the CRUD functions
    :type method: str
    :param parameters: The parameters passed in when denali is run
    :type parameters: dict
    :param api_map: The mapping of possible options for each possible scenario
    :type api_map: dict
    :return: nothing
    :rtype: None
    """
    # todo - if the parameter has "device" in the name or in the description then check if it's in the denali
    # todo - variables and shove it into the api_map

    # the initial pass to hydrate the api map with the passed in polaris parameters
    for param, par_val in parameters.items():
        try:
            # we also check for the single method paths and add it to query params
            if api_map.get(action).get('single_method'):
                for key in api_map[action]['methods'][method]['query_params'].keys():
                    api_map[action]['methods'][method]['query_params'][key]['value'] = action
                    break

            if param in api_map[action]['methods'][method]['query_params'].keys():
                api_map[action]['methods'][method]['query_params'][param]['value'] = par_val

        except KeyError:
            pass

    # this is going through the api map and filling in the query param device name if -h was passed into denali
    for key, value in api_map[action]['methods'][method]['query_params'].items():
        if 'device' in key:
            if not value.get('value'):
                try:
                    hosts = denali['hosts']
                    if hosts != '*':
                        api_map[action]['methods'][method]['query_params'][key]['value'] = hosts.split(',')[0]

                except KeyError:
                    pass


def hydrate_arguments(action, method, parameters, api_map, denali):
    """
    Attempts to populate the api_map dict with all the argument values needed
    :param action: Action to be performed
    :type action: str
    :param method: Method to be performed, one of the CRUD functions
    :type method: str
    :param parameters: The parameters passed in when denali is run
    :type parameters: dict
    :param api_map: The mapping of possible options for each possible scenario
    :type api_map: dict
    :return: nothing
    :rtype: None
    """
    for param, par_val in parameters.items():
        try:
            if param in ['action', 'method']:
                continue

            if param in api_map[action]['methods'][method]['arguments']['data']['arguments'].keys():
                api_map[action]['methods'][method]['arguments']['data']['arguments'][param]['value'] = par_val

        except KeyError:
            continue

    try:
        for key, value in api_map[action]['methods'][method]['arguments']['data']['arguments'].items():
            if 'device' in key or 'host' in key or 'device' in \
                    api_map[action]['methods'][method]['arguments']['data']['arguments'][key]['description'] or \
                    'host' in api_map[action]['methods'][method]['arguments']['data']['arguments'][key]['description']:
                if not value:
                    try:
                        hosts = denali['hosts']
                        if hosts != '*':
                            api_map[action]['methods'][method]['arguments']['data']['arguments'][key]['value'] = value

                    except KeyError:
                        continue

    except KeyError:
        pass


def create_request_data(action, method, api_map):
    """
    Generate the data required for any http method that's not a get
    :param action: Action to be performed
    :type action: str
    :param method: Method to be performed, one of the CRUD functions
    :type method: str
    :param api_map: The mapping of possible options for each possible scenario
    :type api_map: dict
    :return: returns the arguments used for the request
    :rtype: dict
    """
    # todo - need to check if there is any data object that is a host name. If so then look in hosts for it.
    # Todo - the only problem with this is what if params and arguments both have a device name and they need to be
    # todo - ^^ different, how will i know which one is which?

    # todo -- check if the terms host_name, hosts_name, host_names, hosts_names or device_name, devices_name,
    # todo -- device_names, devices_names is in the tree. if so then look through the denali host variables for it.
    arguments = {}
    try:
        if api_map.get(action).get('methods').get(method).get('arguments').get('data').get('arguments'):
            for key, value in api_map.get(action).get('methods').get(method).get('arguments').get('data').get(
                    'arguments').items():
                arguments[key] = value.get('value').encode("UTF-8")
    except (AttributeError, KeyError, ValueError, IndexError):
        pass

    return arguments


def check_missing_argument_data(action, method, api_map):
    """
    Attempts to populate the data field from api map dict with the provided user input
    :param action: Action to be performed
    :type action: str
    :param method: Method to be performed, one of the CRUD functions
    :type method: str
    :param api_map: The mapping of possible options for each possible scenario
    :type api_map: dict
    :return: nothing
    :rtype: None
    """

    for key, value in api_map[action]['methods'][method]['arguments']['data']['arguments'].items():
        new_val = value.get('value')
        if not new_val:
            print("\nLooks like we're updating something. I'll just need some more information.\n")
            while not new_val:
                new_val = raw_input("Enter the '" + key + "' : ")

            api_map[action]['methods'][method]['arguments']['data']['arguments'][key]['value'] = new_val


def check_missing_query_params(action, method, api_map):
    """
    Checks for any missing query params that are required for the function, then prompts for them
    :param action: the action we are performing
    :type action: str
    :param method: the method that we will be requesting ie. list, update, delete, etc...
    :type method: str
    :param api_map: the api_map of the ops api
    :type api_map: dict
    :return: returns nothing as we are editing the api_map itself
    :rtype: None
    """
    for key, value in api_map[action]['methods'][method]['query_params'].items():
        new_val = value.get('value')
        if not new_val:
            while not new_val:
                new_val = raw_input("Enter the '" + key + "' : ")

            api_map[action]['methods'][method]['query_params'][key]['value'] = new_val


# todo - I will need to either use some string manipulation to perform this or just remove sanitize action
def sanitize_action(action):
    """
    Sanitizes the given action input to something the program knows and allows for automation
    :param action: The action the user wants to run
    :type action: str
    :return: returns the sanitized computer known action
    :rtype: str
    """
    if action:
        return action


def sanitize_method(method):
    """
    Sanitizes the given method input to something the program knows and allows for automation
    :param method: The method the user wants to run
    :type method: str
    :return: returns the sanitized computer known CRUD method
    :rtype: str
    """
    if method == 'create' or method == 'post':
        return 'create'

    elif method == 'delete' or method == 'destroy':
        return 'destroy'

    elif method == 'get' or method == 'retrieve':
        return 'retrieve'

    elif method == 'list':
        return 'list'

    elif method == 'partial_update' or method == 'patch':
        return 'partial_update'

    elif method == 'update' or method == 'put':
        return 'update'

    else:
        print("\nI'm sorry, my responses are limited... You must ask the right questions. (I don't know "
              "method '{0}')\n\n".format(method))
        return ''


def print_help(api_map, help_option=None):
    """
    Prints out the list of commands they can run
    :param api_map: The api map of the ops api
    :type api_map: dict
    :param help_option: specific action the user may want help with
    :type help_option: str
    :return: A very large string to be printed to the command line
    :rtype: str
    """
    actions = [act for act in api_map.get('actions')]

    help_dict = {}
    help = """\

                                    The North Star
                        
Syntax:
    denali --pol action=core_dlcm_devices method=list
    
    
    -o  |  --out            Define terminal and file data outputs
    
                            The following formats are available
                                json     : json formatted output (default)
                                csv      : comma separated values
                                yaml     : yaml formatted output
                                xml      : xml formatted output
                                txt      : raw output **(only available for FILE output)
                                
                            Multiple output formats (the screen/stdout or file formats) can be combined
                            for the same query -- use the exact output format name defined above
                                -o json,csv             : Write json and csv formats to the screen
                                -o json,file.csv        : Write json to the screen and then write file.csv
                                -o john.json,jane.csv   : Output to files in json and csv
                                
                            Examples:
                                denali -o json,file.csv --pol action=core_dlcm_devices method=list
                                denali -o yaml --pol action=processing_rsid_actions method=list
                                
                            NOTES:
                                Polaris assumes a file if a file-like structure is used and the format output
                                is specified; i.e., -o devices.yaml assumes yaml output for a file.  If a file
                                like structure is not used, then screen output is assumed.
                                
    -h  |  --hosts          Define the host you want to work with
    
                            Examples:
                                denali -h db2272.sin2 --pol action=core_dlcm_devices method=retrieve
                                
                            NOTES:
                                This is an alternate way to pass in the host name for end points that require
                                a host name. 
                                The other way is to pass it in as a parameter. ie. device_name=db2272.sin2
                                 
    
Examples:
    denali --pol help                                                      |   Show this help
    denali --pol help=core_dlcm_devices                                    |   Show options for dlcm devices
    
    denali --pol action=core_dlcm_devices method=list                      |   List all dlcm devices 
    denali -h db2272.sin2 --pol action=core_dlcm_devices method=retrieve   |   Retrieve dlcm device
    
    ****** [NOTE] ******
        You can enter host names in two different ways, demonstrated below.
        
        ex.. denali --pol action=core_dlcm_devices method=retrieve device_name=db2272.sin2
        
        OR
        
        You can pass in the host name using the denali parameter -h / --hosts. 
        
        ex.. denali -h db2272.sin2 --pol action=core_dlcm_devices method=retrieve
        
    
Available sub-sections help for actions:

{0:>50}    |    {1}
""".format('all', 'Show help for all')
    actions.sort()
    for action in actions:
        act_len = 30 if len(action) > 30 else len(action)
        add_periods = '...' if len(action) > act_len else ''
        help += """\
{0:>50}    |    {1}{2}
""".format(action, 'Show help for {0}'.format(action[:act_len]), add_periods)
# todo - add action help for specific ones that are in processing_rsid_actions etc..

    help_dict['help'] = help

    for action, act_val in api_map.items():
        examples = []
        if action not in ['actions', 'timestamp']:
            create_action_help = """\

                                    The North Star

{0}:
    {1}
    
    Methods:
""".format(action, act_val.get('description'))
            for method, met_val in act_val.get('methods').items():
                append_example = True
                create_action_help += """\
        {0}:
            {1}
                
""".format(method, met_val.get('description'))
                if method == 'list':
                    examples.append('denali --pol action={0} method={1}'.format(action, method))

                # !!!!add query params if there are any
                if met_val.get('query_params') and not act_val.get('single_method'):
                    create_action_help += """\
            query_params:
"""

                    for arg, arg_val in met_val.get('query_params').items():
                        if append_example and 'device' not in arg:
                            examples.append('denali --pol action={0} method={1} {2}=...'.format(
                                action, method, arg))

                            append_example = False

                        if append_example and 'device' in arg:
                            examples.append('denali -h db2272.sin2 --pol action={0} method={1}'.format(
                                action, method, arg))

                            append_example = False

                        create_action_help += """\
                {0}:    {1}
""".format(arg, arg_val.get('description'))
                    create_action_help += "\n"

                # !!!! add arguments if any exist
                if met_val.get('arguments'):
                    create_action_help += """\
            arguments:
"""
                    for arg, arg_val in met_val.get('arguments').get('data').get('arguments').items():
                        create_action_help += """\
                {0:<25}:    {1}
                {2:<25}     Required -- {3}
""".format(arg, arg_val.get('description'), '', arg_val.get('required'))

            if not act_val.get('single_method'):
                create_action_help += """
    Examples:
"""
                ex_len = 2 if len(examples) > 2 else len(examples)
                for e in range(ex_len):
                    create_action_help += """\
        {0}
""".format(examples[e])
            create_action_help += "\n"
            help_dict[action] = create_action_help

    help_dict['all'] = help + "\n"
    for action in actions:
        help_dict['all'] += "\n\n{0}".format(help_dict.get(action))

    if help_option:
        print(help_dict.get(help_option))
        sys.exit(0)

    else:
        print(help)
        sys.exit(0)


def get_syfy_quote():
    large_list = [
        '- "Two possibilities exist: either we are alone in the Universe or we are not. Both are equally terrifying."'
        '\n -- Arthur C. Clarke',

        '- "How inappropriate to call this planet \'Earth\', when it is clearly \'Ocean\'."\n -- Arthur C. Clarke',

        '- "I don\'t believe in astrology; I\'m a Sagittarius and we\'re skeptical."\n -- Arthur C. Clarke',

        '- "..science fiction is something that could happen - but usually you wouldn\'t want it to. \n'
        'Fantasy is something that couldn\'t happen - though often you only wish that it could."\n -- Arthur C. Clarke',

        '- "A learning experience is one of those things that say, \'You know that thing you just did? Don\'t do '
        'that\'."\n -- Douglas Adams',

        '- "Let us think the unthinkable, let us do the undoable, let us prepare to grapple with the ineffable \n'
        '\t\titself, and see if we may not eff it after all."\n -- Douglas Adams',

        '- "I may not have gone where I intended to go, but I think I have ended up where I needed to be."'
        '\n -- Douglas Adams',

        '- "I love deadlines. I love the whooshing noise they make as they go by."\n -- Douglas Adams',

        '- "Driving a Porsche in London is like bringing a Ming vase to a football game."\n -- Douglas Adams',

        '- "The ships hung in the sky, much the way that bricks don\'t"\n -- Douglas Adams',

        '- "He attacked everything in life with a mix of extraordinary genius and naive incompetence, and it was \n'
        '\t\toften difficult to tell which was which."\n -- Douglas Adams',

        '- Time is an illusion. Lunchtime doubly so."\n -- Douglas Adams',

        '- "Individual science fiction stories may seem as trivial as ever to the blinder critics and philosophers \n'
        '\t\tof today - but the core of science fiction, its essence, the concept around which it revolves, has \n'
        '\t\tbecome crucial to our salvation if we are to be saved at all."\n -- Isaac Asimov',

        '- "But suppose we were to teach creationism. What would be the content of the teaching? Merely that a \n'
        '\t\tcreator formed the universe and all species of life ready-made? Nothing more? No details?"'
        '\n -- Isaac Asimov',

        '- "I do not fear computers. I fear the lack of them."\n -- Isaac Asimov',

        '- "Those people who think they know everything are a great annoyance to those of us who do."'
        '\n -- Isaac Asimov',

        '- "The saddest aspect of life right now is that science fiction gathers knowledge faster than\n'
        '\t\tsociety gathers wisdom."\n -- Isaac Asimov',

        '- "Any planet is \'Earth\' to those that live on it."\n -- Isaac Asimov',

        '- "Never let your sense of morals prevent you from doing what is right."\n -- Isaac Asimov',

        '- "Violence is the last refuge of the incompetent."\n -- Isaac Asimov',

        '- "We are an impossibility in an impossible universe."\n -- Ray Bradbury',

        '- "Insanity is relative. It depends on who has who locked in what cage."\n -- Ray Bradbury',

        '- "You don\'t have to burn books to destroy a culture. Just get people to stop reading."\n -- Ray Bradbury',

        '- "We need not to be let alone. We need to be really bothered once in a while. \n'
        '\t\tHow long is it since you were really bothered? About something important, about something real?"'
        '\n -- Ray Bradbury',

        '"Every morning I jump out of bed and step on a landmine. The landmine is me. \n'
        '\t\tAfter the explosion, I spent the rest of the day putting pieces together."\n -- Ray Bradbury',

        '- "So few want to be rebels anymore. And out of those few, most, like myself, scare easily."'
        '\n -- Ray Bradbury',

        '- "Science is no more than an investigation of a miracle we can never explain, \n'
        '\t\tand art is an interpretation of that miracle."\n -- Ray Bradbury',

        '- "If you think this Universe is bad, you should see some of the others."\n -- Philip K. Dick',

        '- "It really seems to me that in the midst of great tragedy, \n'
        '\t\tthere is always the possibility that something terribly funny will happen."\n -- Philip K. Dick',

        '- "The \'Net\' is a waste of time, and that\'s exactly what\'s right about it."\n -- William Gibson',

        '- "The future is not google-able"\n -- William Gibson',

        '- "Progress isn\'t made by early risers. It\'s made by lazy men trying to find easier ways to do something."'
        '\n -- Robert A. Heinlein',

        '- "Deep in the human unconscious is a pervasive need for a logical universe that makes sense. \n'
        '\t\tBut the real universe is always one step beyond logic."\n -- Frank Herbert',

        '- "If you ask \'Should we be in space?\' you ask a nonsense question. We are in space. We will be in space."'
        '\n -- Frank Herbert',

        '- "I must not fear. Fear is the mind-killer. Fear is the little-death that brings total obliteration."'
        '\n -- Frank Herbert',

        '- "Show me a completely smooth operation and I\'ll show you someone who\'s covering mistakes. '
        'Real boats rock."\n -- Frank Herbert',

        '- "You see, gentlemen, they have something to die for. They\'ve discovered they\'re a people. \n'
        '\t\tThey\'re awakening."\n -- Frank Herbert',

        '- "Emotions are the curse of logic."\n -- Frank Herbert',

        '- "Absolute power does not corrupt absolutely, absolute power attracts the corruptible."\n -- Frank Herbert',

        '- "The dinosaurs became extinct because they didn\'t have a space program. '
        '\t\tAnd if we become extinct because we don\'t have a space program, it\'ll serve us right!"\n -- Larry Niven',

        '- "Never fire a laser at a mirror."\n -- Larry Niven',

        '- "That\'s the thing about people who think they hate computers...What they really hate are lousy '
        'programmers."\n -- Larry Niven',

        '- "Here\'s a quick rule of thumb Don\'t annoy science fiction writers. \n'
        '\t\tThese are people who destroy entire planets before lunch. Think of what they\'ll do to you."'
        '\n -- John Scalzi',

        '- "If you want me to treat your ideas with more respect, get some better ideas."\n -- John Scalzi',

        '- "Science, my lad, is made up of mistakes, but they are mistakes which it is useful to make, \n'
        '\t\tbecause they lead little by little to the truth."\n -- Jules Verne',

        '- "The moon, by her comparative proximity, and the constantly varying appearances produced by her several '
        'phases,\n\t\thas always occupied a considerable share of the attention of the inhabitants of the Earth."'
        '\n -- Jules Verne',

        '- "Those who believe in telekinetics, raise my hand."\n -- Kurt Vonnegut',

        '- "Any reviewer who expresses rage and loathing for a novel is preposterous. \n'
        '\t\tHe or she is like a person who has put on full battle armor and attacked a hot fudge sundae."'
        '\n -- Kurt Vonnegut',

        '- "Dear future generations: Please accept our apologies. We were rolling drunk on petroleum."'
        '\n -- Kurt Vonnegut',

        '- "Science is magic that works."\n -- Kurt Vonnegut',

        '- "If your brains were dynamite there wouldn\'t be enough to blow your hat off."\n -- Kurt Vonnegut',

        '- "We are what we pretend to be, so we must be careful about what we pretend to be."\n -- Kurt Vonnegut',

        '- "Advertising is legalized lying."\n -- H.G. Wells',

        '- "Looking at these stars suddenly dwarfed my own troubles and all the gravities of terrestrial life."'
        '\n -- H.G. Wells',

        '- "Every time I see an adult on a bicycle, I no longer despair for the future of the human race."'
        '\n -- H.G. Wells',

        '- "The path of least resistance is the path of the loser."\n -- H.G. Wells'
    ]

    return large_list[random.randint(0, len(large_list) - 1)]


def build_polaris(api_map):
    functions = []
    method_map = {
        'create': 'post',
        'destroy': 'delete',
        'list': 'get',
        'partial_update': 'patch',
        'retrieve': 'get',
        'update': 'put'
    }
    for key, value in api_map.items():
        # key == function name / action name
        func = ''
        if key != 'timestamp' and key != 'actions':
            func = """
def {0}(self, **kwargs):
    class {1}(PolarisCrudAbstract):
        def __init__(self, headers, ops_api_url, ops_api_version):
            self.headers = headers
            self.ops_api_url = ops_api_url
            self.ops_api_version = ops_api_version

""".format(key, value.get('class_name'))
            for method, meth_value in value.get('methods').items():
                url = create_request_url(meth_value.get('uri'))
                # if method doesn't require data use this one else use the one below
                if method in ['retrieve', 'list', 'destroy']:
                    method_func = """\
        def {0}(self):
            res = requests.{1}('{2}, headers=self.headers, verify=False, allow_redirects=False)

            return self.json_loader(res)

""".format(method, method_map.get(method), url)

                else:
                    method_func = """\
        def {0}(self):
            data = kwargs.get('data', '')
            res = requests.{1}('{2}, data=json.dumps(data), headers=self.headers, verify=False, allow_redirects=False)

            return self.json_loader(res)

""".format(method, method_map.get(method), url)

                func += method_func
            func += """\
    return {0}(self.headers, self.ops_api_url, self.ops_api_version)

""".format(value.get('class_name'))
        functions.append(func)

    str_funcs = ''.join(functions)
    # with open('/home/jlonghurst/.denali/polaris_build.json', 'w') as f:
    #     f.write(str_funcs)

    # print(str_funcs)
    return str_funcs


def build_api_map():
    home_dir = os.getenv('HOME')
    now = datetime.datetime.now()
    today = '{0}-{1}-{2}'.format(now.year, now.month, now.day)

    with open('{0}/.denali/polaris_api_map.json'.format(home_dir), 'r') as api_file:
        try:
            api_map = json.loads(api_file.read())
            api_map_time = api_map.get('timestamp')
        except ValueError:
            api_map = {}
            api_map_time = ''

    if api_map_time and api_map_time == today:
        return api_map

    # i need the users token. By this point in the code the user should already have resolved the token so i can get
    # it from the file on disk
    with open('{0}/.denali/polaris.yaml'.format(home_dir), 'r') as f:
        token = yaml.load(f).get('opsapi', {}).get('token')

    api_map = {
        'timestamp': today,
        'actions': set()
    }

    api_data = requests.get('https://opsapi.adobe.net/swagger/?format=openapi', verify=False, allow_redirects=False)
    api = json.loads(api_data.content)

    for k1, v1 in api.get('paths').items():
        # Sanitizing the path to be something a method name could be ie /projects/ to projects
        action = k1.replace('/', '_')[1:len(k1) - 1].encode('UTF-8')
        while '{' in action:
            if '{' in action:
                first = action.find('{')
                last = action.find('}')

                action = action[:first - 1] + action[last + 1:]

        base = action.replace('_', '/')

        if action.endswith('_'):
            action = action[:len(action) - 1]

        if action.startswith('an'):
            action = action[3:]

        api['paths'][k1]['action'] = action
        class_name = action.split('_')
        for i in range(len(class_name)):
            class_name[i] = class_name[i].capitalize()

        class_name = ''.join(class_name)

        desc = ''
        for tag in api.get('tags'):
            if tag.get('name') == base:
                desc = tag.get('description')
                break

        api_map[action] = {
            'methods': {},
            'class_name': class_name,
            'command': action,
            'description': desc.encode('UTF-8'),
            'single_method': False
        }

        api_map['actions'].add(action)

    for k1, v1 in api.get('paths').items():
        # The below is all information pertaining to a specific method ie. get, put, post etc...
        for k2, v2 in v1.items():
            if k2 == 'action' or k2 == 'parameters':
                continue

            # k2 is the method and v2 is the contents of that method
            if k2 == 'post':
                method = 'create'

            elif k2 == 'delete':
                method = 'destroy'

            elif k2 == 'get':
                if '{' in k1:
                    method = 'retrieve'

                else:
                    method = 'list'

            elif k2 == 'patch':
                method = 'partial_update'

            elif k2 == 'put':
                method = 'update'

            else:
                method = None

            if method:
                api_map[v1['action']]['methods'][method] = {
                    'uri': k1.encode('UTF-8'),
                    'description': v2.get('description'),
                    'query_params': parse_query_params(k1, v2.get('parameters')),
                    'arguments': {}
                }

                # The below will build the arguments dict from what the api has
                for param in v2.get('parameters'):
                    args = {}
                    if param.get('name') != 'data':
                        args[param.get('name')] = {
                            'value': '',
                            'description': param.get('description'),
                            'type': param.get('type'),
                            'required': param.get('required')
                        }

                    else:
                        ref = param.get('schema').get('$ref').split('/')
                        ref = ref[len(ref) - 1]
                        # load the data dict into the arguments
                        args[param.get('name')] = {
                            'schema_ref': ref.encode('UTF-8'),
                            'arguments': {}
                        }
                        for def_key, def_val in api.get('definitions').items():
                            # args[param.get('name')]['required'] = [i.encode('UTF-8') for i in
                            #                                        def_val.get('required')]
                            if def_key == ref:
                                required = def_val.get('required')  # this is a list of required properties
                                # Going through the schema definitions properties to grab what is required
                                for prop_key, prop_val in def_val.get('properties').items():
                                    args[param.get('name')]['arguments'][prop_key.encode('UTF-8')] = {
                                        'description': prop_val.get('description', '').encode('UTF-8'),
                                        'type': prop_val.get('type', '').encode('UTF-8'),
                                        'value': '',
                                        'required': True if prop_key in required else False
                                    }

                        api_map[v1['action']]['methods'][method]['arguments'] = args

    api_map = create_secondary_api_map(api_map, token)

    with open('{0}/.denali/polaris_api_map.json'.format(home_dir), 'w') as api_file:
        api_map['actions'] = list(api_map['actions'])
        api_file.write(json.dumps(api_map))

    return api_map


def create_secondary_api_map(api_map, token):
    """
    Creates new fake endpoints for the cli based on functions whose update is all that really matters
    :param api_map: Api map with the paths, endpoints and parameters
    :type api_map: dict
    :param token: Users opsapi bearer token used in requests
    :type token: str
    :return: returns the api map back to the original function
    :rtype: dict
    """

    for action, act_val in api_map.items():
        if action in ['actions', 'timestamp']:
            continue

        # todo -- this is the only piece that will truly require manual intervention because idk what things
        # todo - are important to only update
        # if not token:
        #     with open('{0}/.denali/polaris.yaml'.format(os.getenv('HOME')), 'r') as f:
        #         token = yaml.load(f).get('opsapi').get('token')

        if 'processing' in action:
            update = False
            get = False
            for method, meth_val in act_val.get('methods').items():
                if method == 'update':
                    update = meth_val

                if method == 'list':
                    get = True

            if update and get:
                # verify that the uri only has one query parameter
                if len(act_val.get('methods').get('update').get('query_params').keys()) <= 1:
                    url = 'https://opsapi.adobe.net/api/v1{0}'.format(act_val.get('methods').get('list').get('uri'))
                    headers = {'Authorization': 'Bearer {0}'.format(token)}
                    res = requests.get(url, headers=headers)
                    if res.status_code in [200, 201, 202, 204]:
                        items = json.loads(res.content)
                        for entry in items:
                            name = entry.get('name')
                            class_name = name.split('_')
                            class_name = [i.capitalize() for i in class_name]
                            api_map[name] = {
                                'class_name': ''.join(class_name),
                                'command': name,
                                'description': entry.get('description'),
                                'methods': {
                                    'update': update
                                },
                                'single_method': True
                            }
                            api_map['actions'].add(name)

                else:
                    pass
                    # print(res)
                    # print(res.content)

    return api_map


def parse_query_params(string, parameters):
    """
    String will be in format /core/{name}/lib/{other_command}/, also adds the parameter description
    :param parameters: the api parameters for the given
    :type parameters:
    :param string: the uri to format
    :type string: str
    :return: returns all the query parameters for the specific method. ie. get should have at least one query param
    :rtype: dict
    """
    params = {}
    string = string.encode('UTF-8').split('/')
    string = [s for s in string if s]
    string = [s for s in string if s.__contains__('{')]
    string = [s.strip('{').strip('}') for s in string]
    for s in string:
        desc = ''
        for param in parameters:
            if param.get('name') == s and param.get('required'):
                desc = param.get('description')
                if 'name' in s and 'device' in desc:
                    s = 'device_' + s

                elif 'name' in s and 'action' in desc:
                    s = 'action_' + s

                break

        params[s] = {
            'value': '',
            'description': desc
        }

    return params


def create_request_url(uri):
    """
    Creates the request url to be used in an HTTP request
    :param uri: the appending uri for the specific method call
    :type uri: str
    :return: returns the url string to be used in the request
    :rtype: str
    """
    url = '{0}/{1}/'  # this equates to the base url plus the api version number ie. https://opsapi.adobe.com/api/v1

    uri = uri.encode('UTF-8').split('/')
    uri = [u for u in uri if u]
    # uri = ['core', 'dlcm', 'devices', '{parent_lookup_name}', 'actions', '{name}']
    uri_map = {}
    index = 2
    for i in range(len(uri)):
        if uri[i].__contains__('{'):
            uri[i] = uri[i].strip('{').strip('}')
            if 'name' in uri[i]:
                if 'device' in uri[i - 1]:
                    uri_map[index] = 'device_' + uri[i]

                elif 'action' in uri[i - 1]:
                    uri_map[index] = 'action_' + uri[i]

            else:
                uri_map[index] = uri[i]

            url += '{' + str(index) + '}' + '/'
            index += 1

        else:
            url += uri[i] + '/'

    format_str = "'.format(self.ops_api_url, self.ops_api_version"
    for i in range(2, index):
        format_str += ", kwargs.get('query_params').get('{0}').get('value')".format(uri_map[i])

    format_str += ')'

    url += format_str
    return url


class PolarisCrudAbstract:
    __metaclass__ = abc.ABCMeta

    def json_loader(self, res):
        """
        Takes the result and attempts to load it as json if it can. otherwise it just returns the content
        :param res: the result from the request
        :type res: requests.Response
        :return: returns either a json object or just the response content
        :rtype: json or dict
        """
        self.check_errors(res)
        content = res.content
        try:
            return json.loads(content)
        except ValueError:
            return content

    @staticmethod
    def handle_errors(status_code):
        """
        Handles errors and gives back a pretty message rather than an ugly html encoded one
        :param status_code: the response status code
        :type status_code: int
        :return: returns a string
        :rtype: str
        """
        status_code_dict = {
            200: 'we got an ok',
            201: 'it was created',
            202: 'it was accepted',
            204: 'there is no content, or we just deleted something :)',
            301: 'that address was moved permanently',
            304: 'nothing was modified',
            400: 'a bad request',
            401: 'you are not authorized to use that command',
            402: 'payment is required',
            403: 'that is forbidden, like Romeo and Juliet',
            404: 'we still haven\'t found what we\'re looking for',
            405: 'that method isn\'t allowed',
            406: 'that is unacceptable',
            409: 'there is a conflict',
            500: 'there was an internal server error',
            501: 'that is not implemented yet',
            502: 'we found a bad gateway',
            503: 'the service is temporarily unavailable, could be some maintenance?',
            504: 'the gateway timed out'
        }
        message = status_code_dict.get(status_code, "something wen't wrong. Please try again.")

        return "\nIt looks like {0}. aka HTTP {1}\n".format(message, status_code)

    def check_errors(self, res):
        """
        Check if there are errors, if there is it will print out the pretty message then exit
        :param res: the response object from the request call
        :type res: requests.Response
        :return: nothing
        :rtype: None
        """
        if res.status_code in [301, 304, 400, 401, 402, 403, 404, 405, 406, 409, 500, 501, 502, 503, 504]:
            print(self.handle_errors(res.status_code))
            sys.exit(1)

    def create(self):
        return "I'm sorry, I do not know how to create the item(s)."

    def destroy(self):
        return "I'm sorry, I do not know how to delete the item(s)."

    def list(self):
        return "I'm sorry, I do not know how to list the item(s)."

    def partial_update(self):
        return "I'm sorry, I do not know how to patch the item(s)."

    def retrieve(self):
        return "I'm sorry, I do not know how to get the item(s)."

    def run(self, method):
        return getattr(self, method)()

    def update(self):
        return "I'm sorry, I do not know how to update the item(s)."


class Functions(Credentials):
    def __init__(self, headers, ops_api_url, ops_api_version):
        self.headers = headers
        self.ops_api_url = ops_api_url
        self.ops_api_version = ops_api_version
        super(Functions, self).__init__()

    api_map = build_api_map()
    exec (build_polaris(api_map))


class Polaris(Functions):
    def __init__(self, header_accept='application/json'):
        self.ops_api_url = 'https://opsapi.adobe.net/api'
        self.ops_api_version = 'v1'
        self.headers = {
            'Authorization': 'Bearer {0}'.format(self.__load_token()),
            'Content-Type': 'application/json',
            'accept': header_accept
        }
        super(Polaris, self).__init__(self.headers, self.ops_api_url, self.ops_api_version)

    @staticmethod
    def __load_token():
        with open('{0}/.denali/polaris.yaml'.format(os.getenv('HOME')), 'r') as f:
            token = yaml.load(f).get('opsapi').get('token')

        return token
