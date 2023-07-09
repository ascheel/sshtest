#! /usr/bin/env python


#############################################
#
# denali_update.py
#
#############################################
#
#   This module contains the code to allow updates to CMDB to occur.
#   The first version of the updater works with the DeviceDao only.
#

import denali
import os
import csv
import sys
import datetime, time
import denali_analytics
import denali_commands
import denali_search
import denali_utility

from denali_tty import colors

# global variable for batch mode processing of server updates (if an update
# file is used
BATCH_MODE  = False

# if BATCH_MODE is True, this variable specified the number of hosts
# used for each update batch/run.
batch_count = 1000

# global variable for file contents
file_data = None


# This List of Lists stores the update keys and the translated name (if applicable)
# for CMDB.  Some update keys have different name in CMDB ...

cmdb_update_keys = [
                        # Update Key                CMDB Alias                      CMDB Name
                        [ "name",                   "name",                         "name"                                  ],
                        [ "label",                  "label",                        "label"                                 ],
                        [ "device_service",         "device_service",               "device_service.full_name"              ],
                        [ "device_role",            "device_role",                  "device_role.full_name"                 ],
                        [ "asset_tag",              "asset_tag",                    "asset_id",                             ],
                        [ "serial",                 "serial",                       "serial"                                ],
                        [ "device_state",           "device_state",                 "device_state.full_name"                ],
                        [ "device_state_notes",     "device_state_notes",           "device_state_notes"                    ],
                        [ "environment",            "environment",                  "environment.full_name"                 ],
                        [ "install_date",           "install_date",                 "install_date"                          ],
                        [ "notes",                  "notes",                        "notes"                                 ],
                        [ "ownership",              "ownership",                    "ownership"                             ],
                        [ "model",                  "model",                        "model.name"                            ],
                        [ "vendor_supplier",        "vendor_supplier",              "vendor_supplier.name"                  ],

                        [ "primary_ip",             "primary_ip_address",           "primary_ip_address.ip_address"         ],
                        [ "secondary_ip",           "secondary_ip_address",         "secondary_ip_address.ip_address"       ],
                        [ "ilo_ip",                 "ilo_ip_address",               "ilo_ip_address.ip_address"             ],
                        [ "ilo_ad_auth",            "ilo_ad_auth",                  "ilo_ad_auth"                           ],
                        [ "mac_addr",               "mac",                          "mac_addr"                              ],
                        [ "int_dns_name",           "int_dns_name",                 "int_dns_name"                          ],
                        [ "ext_dns_name",           "ext_dns_name",                 "ext_dns_name"                          ],
                        [ "ad_domain",              "ad_domain",                    "ad_domain"                             ],

                        [ "customer.billing_id",    "customer.billing_id",          "customer.billing_id"                   ],
                        [ "assigned_to_user",       "assigned_to_user",             "assigned_to_user"                      ],

                        [ "disks",                  "disks",                        "disk"                                  ],
                        [ "cpu",                    "cpu",                          "cpu"                                   ],
                        [ "cpu_cores",              "cpu_cores",                    "cpu_cores"                             ],
                        [ "memory",                 "memory",                       "memory"                                ],
                        [ "num_attached_storage",   "num_attached_storage",         "num_attached_storage"                  ],
                        [ "num_power_supplies",     "num_power_supplies",           "num_power_supplies"                    ],

                        [ "location_status",        "location_status",              "location_status"                       ],
                        [ "rack",                   "rack_name",                    "rack.name"                             ],
                        [ "rack_position",          "rack_facing",                  "rack_position"                         ],
                        [ "rack_unit",              "rack_number",                  "rack_unit"                             ],
                        [ "location_notes",         "location_notes",               "location_notes"                        ],
                        [ "enclosure_slot",         "enclosure_slot",               "enclosure_slot"                        ],

                        [ "operating_system",       "os_name",                      "operating_system.display_name"         ],
                        [ "kernel",                 "kernel",                       "kernel"                                ],

                        [ "software_version",       "software_version",             "software_version.version"              ],

                        [ "insight_dataset",        "insight_dataset",              "insight_dataset"                       ],
                        [ "dop_version",            "dop_version",                  "dop_version"                           ],
                        [ "dop_path",               "dop_path",                     "dop_path"                              ],
                   ]


#
#   Valid keys for updating CMDB
#

update_keys = [
                # Base Device Information
                "name", "label", "device_service", "asset_tag", "serial", "device_state", "device_state_notes",
                "device_role", "environment", "install_date", "notes", "ownership", "model", "vendor_supplier",

                # Network Settings
                "primary_ip", "secondary_ip", "ilo_ip", "ilo_ad_auth", "mac_addr", "int_dns_name", "ext_dns_name",
                "ad_domain",

                # Assignment Information
                "customer.billing_id", "assigned_to_user",

                # Hardware Settings
                "disks", "cpu", "cpu_cores", "memory", "num_attached_storage", "num_power_supplies",

                # Location Information
                "location_status", "rack", "rack_position", "rack_unit", "location_notes",

                    # Required "rack" information (all 3 required):
                    # "rack": { "name": "103", "cage.name": "52200", "cage.location.name": "VA5" }

                # Operating System Settings
                "operating_system", "kernel",

                # Software Version Settings
                "software_version",

                    # Require "software_version" information:
                    # "software_version" : [ {
                    #                           "software.name": "Apache",
                    #                           "version": "2.2.6",
                    #                        },
                    #                        {  "software.name": "MySQL",
                    #                           "version": "5.0.90",
                    #                        },
                    #                      ],

                # Insight-specific fields
                "insight_dataset", "dop_version", "dop_path"
              ]


# list of hosts (in the update scope) that have been found to be either
# 'good' (to update) or 'bad' (no update allowed).
hostsGood   = []
hostsRemove = []


##############################################################################
#
# replaceUpdateAbbreviations(denaliVariables, argument)
#
#   Return True if a change was made
#   Return False if no change was made
#

def replaceUpdateAbbreviations(denaliVariables, argument):

    replace_dictionary = {
                            'device_state': {
                                                'odis' : 'On Duty - In Service',
                                                'odr'  : 'Off Duty - Reserved',
                                                'ods'  : 'On Duty - Standby',
                                                'pds'  : 'Provisioning - Deploying Software',
                                                'pic'  : 'Provisioning - Image Complete',
                                                'ppc'  : 'Provisioning - Pending Config',
                                                'poh'  : 'On Duty - Poweroff Hold',
                                            }
                         }

    arg = argument.split('=')

    # if statements to determine the update key and value with possible short-cut replacements
    if arg[0].strip().lower() == "state" or arg[0].strip().lower() == "device_state":
        replacement = replace_dictionary['device_state'].get(arg[1].strip().lower(), None)
        if replacement is not None:
            argument = arg[0].strip().lower() + '=' + replacement
            return (True, argument)

    return (False, None)



##############################################################################
#
# organizeOverriddenAttributes(denaliVariables)
#

def organizeOverriddenAttributes(denaliVariables):

    override_found  = False
    debug           = False
    attribute_names = []

    # (1) Craft the correct query language ... leaving any submitted parameters alone.
    #     Submit the correct fields to query on (hostname, attribute name, attribute value, attribute override)
    field_list = 'name,attribute_data.attribute.name,attribute_data.value,attribute_data.overrides_attribute_data_id'

    # (2) Retrieve the server list from the passed in command line arguments.
    #     This call validates that all hosts returned are in SKMS before any
    #     attribute updates are done against them.
    ccode = denali_utility.createServerListFromArbitraryQuery(denaliVariables, 'DeviceDao', field_list)
    if ccode == False:
        # no devices found -- exit out
        return False

    # Turn the sql query parameters into a proper string to use.  Without this, a List of Lists
    # is sent through, and buildHostQuery chokes on that.
    denaliVariables["sqlParameters"] = denali_utility.validateSQL(denaliVariables)

    # (3) At this point, the entire responseDictionary is in denaliVariables['responseDictionary'].
    #     Operate on the response dictionary and determine which attribute(s) qualify as an override.
    #     With that information, create a data structure to be used with the displaying and clearing
    #     of the data.

    # currentFields   = ['RAID_SETTINGS', 'COBBLER_PROFILE']
    # displayValues   = ['5', 'techops-7-an']
    # newPrintData    = {u'db8204.or1': [u'db8204.or1', 'techops-7-an', '5'], u'db8064.or1': [u'db8064.or1', 'techops-7-an', '5']}
    # printData       = [[u'db8064.or1', u'techops-7-an', u'10'], [u'db8204.or1', u'techops-7-an', u'10']]

    if debug == True:
        print "server list = [%i] :: %s" % (len(denaliVariables['serverList']), denaliVariables['serverList'])
        print

    for host_record in denaliVariables['responseDictionary']['data']['results']:
        for attribute_data in host_record['attribute_data']:
            if attribute_data['overrides_attribute_data_id'] != '0':
                # store the name in attribute_names
                if attribute_data['attribute']['name'] not in attribute_names:
                    attribute_names.append(attribute_data['attribute']['name'])

                # found an overridden attribute
                a_name  = attribute_data['attribute']['name']
                a_value = attribute_data['value']

                # this stores the current (override) value with the attribute name (equal sign separator)
                if host_record['name'] not in denaliVariables['updateParameters']:
                    denaliVariables['updateParameters'].update({host_record['name']:[a_name + '=' + a_value]})
                else:
                    denaliVariables['updateParameters'][host_record['name']].append(a_name + '=' + a_value)

                if debug == True:
                    if override_found == False:
                        print host_record['name'] + " :: %s" % a_name,
                        override_found = True
                    else:
                        print ", %s" % a_name,

        if host_record['name'] in denaliVariables['updateParameters']:
            attribute_list = denaliVariables['updateParameters'][host_record['name']]
            attribute_list.sort()
            denaliVariables['updateParameters'][host_record['name']] = attribute_list
        else:
            denaliVariables['updateParameters'].update({host_record['name']:[]})
            attribute_list = []

        if debug == True:
            if override_found == False:
                print host_record['name'] + " :: No attribute overrides found"
            else:
                override_found = False
                print

    # put the name list in the update parameters dictionary
    attribute_names.sort()
    denaliVariables['updateParameters'].update({'attribute_names':attribute_names})

    if debug == True:
        print
        print "dvup = %s" % denaliVariables['updateParameters']

    # make sure at least one device has overridden attributes
    # multiple ways to check and ensure there are hosts in the data structure
    if 'attribute_names' in denaliVariables['updateParameters']:
        if len(denaliVariables['updateParameters']['attribute_names']) == 0:
            print "Denali:  No hosts with attribute overrides found"
            return False

        for host in denaliVariables['updateParameters']:
            if len(denaliVariables['updateParameters'][host]):
                break
        else:
            # no hosts found
            print "Denali:  No hosts with attribute overrides found"
            return False
    else:
        # attribute_names key was not created -- no attributes in the list -- fail
        print "Denali:  No hosts with attribute overrides found"
        return False

    return True



##############################################################################
#
# organizeUpdateParameters(denaliVariables)
#

def organizeUpdateParameters(denaliVariables, host, argList):

    argList    = argList.split(',')
    newArgList = []
    tempArg    = ''

    squareBrackets   = 0
    squigglyBrackets = 0

    # Combine elements together (if they don't have an equal sign in the
    # argument --> copy it to the end of the previous element.  Then go
    # back through the list again and delete all elements that don't have
    # an equal sign.
    for (index, arg) in enumerate(argList):
        if arg.find('=') == -1:
            if (index - 1) < 0:
                # problem -- non-equal sign parameter at location 0?
                # that's not right
                print "Denali update syntax error:  First parameter doesn't have an equal sign."
                print "Execution stopped."
                return False

            # find the previous marker with an equal sign (search to -1 as it will stop at the 0 index)
            for revIndex in range(index, -1, -1):
                if argList[revIndex].find('=') != -1:
                    break
                else:
                    continue

            argList[revIndex] += ',' + arg

    # copy over the fixed update parameters
    for arg in argList:
        if arg.find('=') != -1:
            newArgList.append(arg)

    # copy them back to the original data store
    argList    = newArgList[:]
    newArgList = []

    # Check for an update of the key and other data at the same time:
    # Denali will not allow a device to be updated while at the same time
    # updating other data variables for the host which includes the specific
    # device identifier (hostname, device_id, etc.).  Pick one -- either the
    # host by itself, or the data by itself.  This effectively means that if
    # a host and data need to be updated, it has to be done twice.
    if denaliVariables["updateMethod"] == "file":
        update_key = denaliVariables["updateKey"][0]
        update_key_column = denaliVariables["updateKey"][2]
    else:
        update_key = "name"
        update_key_column = "Host Name"

    for arg in argList:
        if arg.startswith(update_key) and len(argList) > 1:
            print
            print "Syntax Error:"
            print "Denali does not allow a device specified by its %s to also update" % update_key_column
            print "its %s at the same time.  If you wish to update the %s," % (update_key_column, update_key_column)
            print "do that in a separate update session."
            print
            print "  Device %s: %s" % (update_key, host)
            for arg in argList:
                if arg.startswith(update_key):
                    print " !==> host data update --> %s <==!" % arg
                else:
                    print "      host data update --> %s" % arg
            return False

    # count brackets '[ and ]' and '{ and }'
    for arg in argList:
        if '[' in arg:
            squareBrackets   += arg.count('[')
        if '{' in arg:
            squigglyBrackets += arg.count('{')
        if ']' in arg:
            squareBrackets   -= arg.count(']')
        if '}' in arg:
            squigglyBrackets -= arg.count('}')

    if squareBrackets != 0 or squigglyBrackets != 0:
        if squareBrackets != 0:
            print "Denali update syntax error:  Opening/Closing square brackets do not match."
        else:
            print "Denali update syntax error:  Opening/Closing squiggly brackets do not match."

        print "Execution stopped."
        return False

    openBracket = 0

    for arg in argList:
        openCount  = (arg.count('[') + arg.count('{'))
        closeCount = (arg.count(']') + arg.count('}'))

        # check for single item
        if openCount == closeCount:
            # In this instance the open brackets ([{) match in number to
            # the close brackets (]}).  This means a single valued update
            # surrounded by brackets -- just add it to the List.
            newArgList.append(arg)

        # multiple items
        else:
            if openBracket == 0:
                if openCount > 0:
                    openBracket = openCount
                    tempArg = arg

                else:
                    newArgList.append(arg)

            else:
                if openCount > 0:
                    openBracket += openCount
                elif closeCount > 0:
                    openBracket -= closeCount

                tempArg = tempArg + ',' + arg

                if openBracket == 0:
                    newArgList.append(tempArg)

        if len(newArgList):
            # handle any abbreviations/short-cuts submitted
            ccode, argument = replaceUpdateAbbreviations(denaliVariables, newArgList[-1])
            if ccode == True:
                newArgList[-1] = argument

    if host not in denaliVariables['updateParameters']:
        denaliVariables["updateParameters"].update({host:newArgList})
    else:
        print "Denali update file syntax error:  Two or more hosts of the same name [%s] are specified in the file." % host
        print "Execution stopped."
        return False

    return True



##############################################################################
#
# useUpdateAliasesForFieldNames(fieldCategories)
#

def useUpdateAliasesForFieldNames(fieldCategories):

    aliasedFields = []

    for field in fieldCategories:
        for alias in cmdb_update_keys:
            if field in alias:
                aliasedFields.append(alias[0])
                break

    return aliasedFields



##############################################################################
#
# findKeyAlias(denaliVariables, key)
#
#   This function is passed in an update key (column name).  It may come in
#   as an alias or not.  The code will search the current alias list in the
#   denali_search code, and see if it exists.  If it does, it will pull over
#   the "cmdb" name to use as the key, instead of whatever was submitted.
#
#   Also included is if the entered key is a Column Title (not an alias).
#   This will find that and convert it as well (saw this issue with a previous
#   use-case where it confused the user).
#
#   lineEntry[0] is the cmdb alias
#   lineEntry[1] is the cmdb data name (what should be used)
#   lineEntry[2] is the column name (in English)
#
#   This will only search through the DeviceDao -- and leave everything else
#   as submitted.
#

def findKeyAlias(denaliVariables, key):

    cmdb_keys = denali_search.cmdb_defs
    new_key   = ''

    for lineEntry in cmdb_keys["DeviceDao"]:
        #if denaliVariables["updateDebug"] == True:
        #    print "  devicedao line entry = %s" % lineEntry
        if lineEntry[0] == key or lineEntry[2] == key:
            if denaliVariables["updateDebug"] == True:
                print "  Found a match:  %s" % lineEntry[1]
                print "  DeviceDAO line entry = %s" % lineEntry
            new_key = lineEntry[1]

            # For searching, a relationship matters ilo_ip_address.ip_address
            # For updating, a relationship can _NOT_ be specified
            # -- remove any "dot" relationship
            location = new_key.find(".")
            if location == -1:
                return new_key
            else:
                return new_key[:location]
    else:
        return key



##############################################################################
#
# validateParameterSyntax(denaliVariables, key, key_data, parameter)
#
#   This function does a basic syntax check on the data given to it before it
#   is sent off to CMDB for analysis.  This is not an exhaustive check by any
#   means; the full validity check is left to CMDB to enact.  However, Denali
#   can catch basic mistakes before any queries are sent to CMDB needlessly.
#
#   key       = name of the value to be updated
#   key_data  = data for the key to be updated
#   parameter = entire data line submitted
#
#       <key>            <key_data>
#       device_service : SiteCatalyst - Frag - Production
#       parameter = "device_service=SiteCatalyst - Frag - Production"
#

def validateParameterSyntax(denaliVariables, key, key_data, parameter):

    # verify that the submitted key is in the list of available keys to use
    #if key.strip() not in cmdb_update_keys:
    for updateKey in cmdb_update_keys:
        if key.strip() in updateKey:
            break
    else:
        # the key wasn't found -- add it dynamically to the List
        # and allow SKMS to catch it (if invalid)
        key = key.strip()
        newList = [ key, key, key ]
        cmdb_update_keys.extend([newList])

        if denaliVariables["updateDebug"] == True:
            print
            print "Unrecognized Key submitted [\"%s\"]" % key

            key = findKeyAlias(denaliVariables, key)
            print "Key returned: %s" % key

        #print "Invalid Syntax:  Invalid key (%s) submitted." % key
        #return False

    if key == "name":
        if key_data.startswith(' ') == True or key_data.endswith(' ') == True:
            # problem -- hostname cannot have a leading or trailing space
            # strip it -- just to make sure
            key_data.strip()
            return True
        else:
            return True

    # review specific keys for correct usage (brackets, squigglys, etc.)
    elif key == "device_service" or key == "device_role":
        if (key_data.count('[') == 1 and
            key_data.count(']') == 1):

            return True

        if (key_data.count('[') == 0 and
            key_data.count(']') == 0):

            data = key_data.split(',')
            if len(data) > 1:
                print "Denali invalid syntax: Multi-value Device Service requires array brackets."
                print "Submitted: %s" % parameter
                print "Expected : device_service=[<device service1>,<device service2>, ... ]"
                return False
            else:
                return True

        else:
            print "Denali invalid syntax"
            print "Submitted: %s" % parameter
            print "Expected : device_service=[<device service1>,<device service2>, ... ]"
            return False

    elif key == "rack":
        if key_data.count('{') == 1 and key_data.count('}') == 1:
            if (key_data.find("name") != -1 and
                key_data.find("cage.name") != -1 and
                key_data.find("cage.location.name") != -1):

                return True

            else:
                print "Denali invalid syntax"
                print "Submitted: %s" % parameter
                print "Expected : rack={name=<name1>,cage.name=<name2>,cage.location.name=<name3>}"
                return False
        else:
            print "Denali invalid syntax"
            print "Submitted: %s" % parameter
            print "Expected : rack={name=<name1>,cage.name=<name2>,cage.location.name=<name3>}"
            return False

    elif key == "software_version":
        if (key_data.count('[') == 1 and
            key_data.count(']') == 1):

            if (key_data.count('{') == 0 and
                key_data.count('}') == 0 and
                len(key_data) == 2):

                # empty array?  to delete existing entries?
                pass

            else:

                if (key_data.find("software.name") != -1 and
                    key_data.find("version") != -1):

                    return True

                else:
                    print "Denali invalid syntax"
                    print "Submitted: %s" % parameter
                    print "Expected : software_version=[{software.name=<name1>,version=<version1>},{...}]"
                    return False
        else:
            print "Denali invalid syntax"
            print "Submitted: %s" % parameter
            print "Expected : software_version=[{software.name=<name1>,version=<version1>},{...}]"
            return False

    # basic key/value pair
    else:
        return True



##############################################################################
#
# generateKeyData(key_data)
#

def generateKeyData(key_data):

    key_dict_array = []
    key_dict = {}
    key_list = []

    #print "key_data = %s" % key_data

    if key_data.startswith("[{"):
        # an array of dictionaries -- "software_version" is likely
        array    = []
        key_dict = {}

        dataList = key_data[1:-1].split(',')
        #print "  **dataList = %s" % dataList

        length = len(dataList)
        #print "length = %s" % length

        for index in range(0, length, 1):
        #for (index, item) in enumerate(dataList):

            item = dataList[index]

            #key_dict = {}
            #print "**item = %s" % item

            key_value = item.split('=')

            for (count, key) in enumerate(key_value):
                key_value[count] = key_value[count].replace('{', '')
                key_value[count] = key_value[count].replace('}', '')

            #print "+kv-0 : kv-1 == %s : %s" % (key_value[0], key_value[1])

            #print "current dict = %s" % key_dict
            #print "update with  = %s:%s" % (key_value[0], key_value[1])

            if key_value[0] in key_dict or key_value[1] in key_dict:
                array.append(key_dict)
                key_dict = {}

            key_dict.update({key_value[0]:key_value[1]})
            #print "updated dict = %s\n" % key_dict

        array.append(key_dict)
        #print "array = %s\n" % array

        data = array

    elif key_data[0] == '{' or key_data[0] == '[':
        dataList = key_data[1:-1].split(',')
        #print "  **dataList = %s" % dataList

        if len(dataList) == 1 and len(dataList[0]) == 0:
            # this code path can be used to delete all software items
            # for a host (--update="software_version=[]")
            data = []
        else:

            for (index, item) in enumerate(dataList):
                temp_dict = {}
                if '=' in item:
                    #print "  (D) Add data to Dictionary"
                    #print "      data => %s" % item

                    key_value = item.split('=')
                    if key_value[0] in key_dict:
                        temp_dict.update = ({key_value[0].strip():key_value[1].strip()})
                    else:
                        key_dict.update({key_value[0].strip():key_value[1].strip()})
                    data = key_dict

                else:
                    key_list.append(item.strip())
                    data = key_list

    else:
        data = str(key_data)

    return data



##############################################################################
#
# createAttributeUpdateDictionary(denaliVariables, hostname)
#

def createAttributeUpdateDictionary(denaliVariables, hostname):

    attributeData = {}

    if denaliVariables["updateDebug"] == True:
        print "dvUpdateParameters = %s" % denaliVariables["updateParameters"]
        print "Server List        = %s" % denaliVariables["serverList"]
        #print "Hostname           = %s" % device

    # By default, every server in the list gets the same update; this should
    # make the update dictionary fairly easy to put together
    #
    # Only the data portion ("attribute" in the setAttributes method for the
    # DeviceDao) is needed
    if denaliVariables['clearOverrides'] == True:
        host_identifier = hostname
    else:
        host_identifier = 'all'

    if len(denaliVariables["updateParameters"]) == 0:
        # the update parameters are empty -- this is wrong
        print "Denali syntax error:  Attribute updateParameters are empty."
        return False

    for attributePair in denaliVariables["updateParameters"][host_identifier]:
        # Allow single (empty) quotes to be a substitute for nothing behind
        # the equal sign.  This syntax will clear the current attribute value
        # allowing an inherited value to take its place.  If the string has
        # any length (something inside the quotation marks), this code will
        # be ignored.
        if attributePair.endswith("=''"):
            attributePair = attributePair[:-2]

        # find the lowest string index where the equal sign is located
        locEqual = attributePair.find('=')
        if locEqual == -1:
            print "Denali syntax error:  Equal sign in attribute updateParameter problem (doesn't exist)."
            return False

        # create a List of 2 items and then populate it
        attribute    = [None] * 2
        attribute[0] = attributePair[:locEqual]
        attribute[1] = attributePair[(locEqual + 1):]

        # any attribute with this flag set is being cleared
        if denaliVariables['clearOverrides'] == True:
            attribute[1] = ''

        # clear out the extra spaces
        attribute[0] = attribute[0].strip()
        if len(attribute[0]) < 2:
            print "Denali syntax error:  Length of attribute name in updateParameter is invalid [%s]." % attribute[0]
            return False

        attribute[1] = attribute[1].strip()

        # informational message -- maybe this will clear out an attribute, so don't stop processing
        # upon discovery of this
        if len(attribute[1]) == 0 and denaliVariables["updateDebug"] == True:
            print "Denali attribute message:  Empty value for attribute [%s] submitted." % attribute[0]

        attributeData.update({attribute[0]:attribute[1]})

    if denaliVariables["updateDebug"] == True:
        print "attributeData (parameterData) = %s" % attributeData


    return attributeData



##############################################################################
#
# createUpdateDictionary(denaliVariables, device)
#

def createUpdateDictionary(denaliVariables, device):

    param_dict  = {}
    device_data = {}

    if len(denaliVariables["updateParameters"]) == 1 and denaliVariables["updateMethod"] == "console":
        device = "all"

    updateParameters = denaliVariables["updateParameters"][device]
    deviceList       = denaliVariables["serverList"]
    #updateParameters = updateParameters[device]

    for device in deviceList:
        for parameter in updateParameters:
            equalLocation = parameter.find('=')
            key = parameter[:equalLocation]
            key_data = parameter[(equalLocation + 1):]

            if len(key_data) == 0:
                key_data = "''"

            # check the parameter syntax
            ccode = validateParameterSyntax(denaliVariables, key, key_data, parameter)
            if ccode == False:
                if denaliVariables["updateDebug"] == True:
                    print "validateParameterSyntax() failed for host %s" % device
                return False

            cmdb_key_alias = findKeyAlias(denaliVariables, key)
            if cmdb_key_alias != '':
                # as long as the return key isn't empty, set it.
                # this will be the cmdb data value (which should work).
                key = cmdb_key_alias

            key_data = generateKeyData(key_data)
            if key_data == "''":      # empty data-set, request is to clear the value
                key_data = ''
                #print "key_data = <empty>"
            else:
                pass
                #print "key_data = %s" % key_data

            if key == "name":
                if key_data.startswith(' ') == True or key_data.endswith(' ') == True:
                    if denaliVariables["updateDebug"] == True:
                        print
                        print "Denali info message: Update code found a host with leading and/or trailing whitespace -- automatically addressed."
                        print "                     Host: %s" % key_data

                    key_data = key_data.strip()

            if isinstance(key_data, str):
                device_data.update({key:key_data.strip()})
            else:
                # "add" [default behavior] will keep any existing entries
                #       and will add a new one (or set)
                # "remove" will remove the specified data entries
                # "replace" will replace all of them with what is specified
                if denaliVariables["updateDefault"] == "add":
                    device_data.update({key: {"add":key_data}})
                elif denaliVariables["updateDefault"] == "remove":
                    device_data.update({key: {"remove": key_data}})
                elif denaliVariables["updateDefault"] == "replace":
                    device_data.update({key:key_data})

    return device_data



##############################################################################
#
# savePreviewData(denaliVariables, previewData)
#
#   previewData is the printData coming in as a List of Lists, with each List
#               representing a single row in the output (a full host's data)
#
#   This function will take this data and turn it into a dictionary keyed by
#   host name, stored as a list of the remaining column values.  When done,
#   this data arrangement will be stored in denaliVariables["updatePreviewData"]
#
#   This function is called every time the preview is generated/displayed so
#   as to ensure that it has up to date data.
#

def savePreviewData(denaliVariables, previewData):

    updatePreviewData = {}

    for row in previewData:
        host = row[0].strip()

        tempRow = []
        for column in row:
            tempRow.append(column.strip())

        updatePreviewData.update({host:tempRow[1:]})

    denaliVariables["updatePreviewData"] = updatePreviewData

    return True



##############################################################################
#
# populateSORDictionary(denaliVariables, printData)
#
#   This function has a number of functions; all of which revolve around the
#   source of record information for a specific host in CMDB.
#
#   Function #1:
#       Copy the source of record data from printData to a separate dictionary
#       for later use.
#
#   Function #2:
#       Delete the column in printData if it wasn't specifically asked to be
#       printed (meaning, there is not an update to it, so don't show it).
#
#   Function #3:
#       Count the number of "columns of interest" to be updated.  Only specific
#       columns fit in this category.  For instance, if a host source of record
#       is a SIS database, and Denali asks to update its device_state, SKMS
#       will fail this request.  The same host can have its hostname updated.
#       Thus, "device_state" is a column of interest.  Count all of these as
#       they will potentially cause a host update to fail.
#

def populateSORDictionary(denaliVariables, printData):

    removeData = ''
    coi        = 0

    # If this is a group attribute update, no SOR data will exist.
    # Just fill it out as 'CMDB' (DeviceGroups are CMDB-only anyway)
    # and then return
    if denaliVariables['attributeUpdate'] == True:
        for group in denaliVariables['serverList']:
            denaliVariables['updateSOR'].update({group:'CMDB'})
        return True

    # Columns that SIS will not let be updated via CMDB (for fear of a future
    # SIS synchronization to CMDB overwriting any update data)
    columnsOfInterest = ["device_state", "device_state.full_name"]

    if denaliVariables["updateSOR"]["sorColumn"] == True:
        # sorColumn is True; meaning it was requested to be shown/updated
        # copy the data into the updateSOR dictionary and leave the printData alone
        removeData = False
    else:
        # sorColumn is False; meaning it was not requested to be shown or updated
        # copy the data into the updateSOR dictionary, and remove the column from printData
        removeData = True

    # turn the fields variable into List
    columnNames = denaliVariables["fields"].split(',')
    for (index, column) in enumerate(columnNames):
        if column == "source_or_record.name" or column == "source_name":
            # found it -- 'index' has the location
            break

    # see if a "column of interest" is included in the update schedule
    for column in columnNames:
        if column in columnsOfInterest:
            coi += 1

    # store the coi count in the dictionary (coi = columns of interest)
    denaliVariables["updateSOR"].update({"coi_count":coi})

    # copy the data and delete the SOR column (if necessary)
    for (rIndex, row) in enumerate(printData):
        # get the source of record data
        hostname = row[0].strip()
        sorDB    = row[index].strip()

        # store the data in the dictionary for future use
        denaliVariables["updateSOR"].update({hostname:sorDB})

        # remove the data (if it wasn't asked to be included)
        if removeData == True:
            del printData[rIndex][index]

    if denaliVariables['debug'] == True:
        print "source of record = %s" % denaliVariables['updateSOR']

    # Return the correct code (true/false) depending on data removal
    if removeData == True:
        return True
    else:
        return False



##############################################################################
#
# separateMultiValuedParameter(parameter)
#
#   The update method from SKMS supports multi-valued parameters.  This piece
#   of code does a separation on them so they can be displayed in a semi-nice
#   looking manner.
#

def separateMultiValuedParameter(parameter):

    mvParameter = []
    eqLocation  = parameter.find('=')
    mvParameter.append(parameter[:eqLocation])

    # Determine the type of multi-valued parameter being passed in
    if parameter.find('[') and parameter.find('{'):
        # List of Dictionaries
        endLocation = parameter.rfind('}')
        mvParameter.append(parameter[(eqLocation+2):(endLocation+1)])
    elif parameter.find('{'):
        # Dictionary
        endLocation = parameter.rfind('}')
        mvParameter.append(parameter[(eqLocation+1):(endLocation+1)])
    #elif parameter.find('['):
        # List -- for future inclusion.  Fill out the code when there
        # is a good example to work with

    return mvParameter



##############################################################################
#
# collectOriginalDataValues(denaliVariables)
#

def collectOriginalDataValues(denaliVariables):

    newRows       = []
    newPrintData  = {}
    displayFields = []      # a combined set of column headers / attributes to update (carries forward all entries)
    currentFields = []      # the current set of column headers / attributes to update (reset after each host)
    displayValues = []      # attribute values to be updated

    EMPTY_CELL    = "---"
    sqlAttribute  = ''

    for host in denaliVariables["serverList"]:
        newRows.append([host])

    if denaliVariables["updateMethod"] == "file":
        # This for loop allows for a dynamic set of columns based upon each server potentially
        # having a different set of attributes to update.
        for (index, hostname) in enumerate(denaliVariables["updateParameters"]):

            parameters = denaliVariables["updateParameters"][hostname]

            # Turn the updateParameters into a "--fields" command.
            # Add all fields requested to be updated on any server
            # found in the list.
            for field in parameters:
                keyName = field.split('=')

                # only add a new column _IF_ it doesn't already exist
                if keyName[0].strip() not in displayFields:
                    displayFields.append(keyName[0].strip())

                currentFields.append(keyName[0].strip())
                displayValues.append(keyName[1].strip())

            host = newRows[index][0]
            newPrintData.update({hostname:[]})

            for (cIndex, column) in enumerate(displayFields):
                for (fIndex, field) in enumerate(currentFields):
                    if column == field:
                        newPrintData[hostname].append(displayValues[fIndex])
                        break
                    else:
                        if cIndex > len(newPrintData[hostname]):
                            newPrintData[hostname].append(EMPTY_CELL)

            # clear the display values/currentFields for the next loop iteration
            displayValues = []
            currentFields = []

        # put the EMPTY_CELL text in every unoccupied column cell
        count = len(displayFields) + 1
        for host in denaliVariables["serverList"]:

            # add the host name at the beginning of the host data
            newPrintData[host].insert(0, host)

            if len(newPrintData[host]) < count:
                diff = (count - len(newPrintData[host]))

                for i in range(diff):
                    newPrintData[host].append(EMPTY_CELL)

    elif denaliVariables["updateMethod"] == "console":
        for (index, parameter) in enumerate(denaliVariables["updateParameters"]["all"]):
            # if this is a List or dictionary, separate it as needed
            if parameter.find('[') != -1 or parameter.find('{') != -1:
                keyName = separateMultiValuedParameter(parameter)
            else:
                keyName = parameter.split('=')

            # only add a new column _IF_ it doesn't already exist
            if keyName[0].strip() not in displayFields:
                displayFields.append(keyName[0].strip())

            currentFields.append(keyName[0].strip())
            displayValues.append(keyName[1].strip())

        for host in denaliVariables["serverList"]:
            if len(displayValues) == len(currentFields):
                # if a host value doesn't exist, insert it
                displayValues.insert(0, host)
            else:
                # if a host value exists, just change it
                displayValues[0] = host

            tempDV = displayValues[:]
            newPrintData.update({host:tempDV})

    elif denaliVariables["updateMethod"] == "attribute":
        # the attribute gathering still needs SOR data
        ccode = getAttributeSORData(denaliVariables)
        if ccode == False:
            # problem collecting the source of record data
            return (False, False)

        (printData, newPrintData) = getOriginalUpdateAttributeData(denaliVariables)
        if printData == False:
            # problem collecting the attribute data
            return (False, False)


    # prep the manipulated variables for a basic denali query
    # (how else would the original values for comparison be obtained?)

    if denaliVariables["updateMethod"] != "attribute":
        # add the correct identifier column name -- (name, serial, asset, etc.)
        if denaliVariables["updateMethod"] == "file":
            column1_name = denaliVariables["updateKey"][0]
        else:
            column1_name = denaliVariables["updateKey"]

        if column1_name in displayFields:
            displayFields.remove(column1_name)

        if len(displayFields) == 0:
            denaliVariables["fields"] = column1_name + ',' + column1_name + ' '
        else:
            displayFields = ','.join(displayFields)
            denaliVariables["fields"] = column1_name + ',' + displayFields

        # see if the source of record DeviceDao data attribute was declared (to be updated)
        if denaliVariables["fields"].find("source_name") == -1 and denaliVariables["fields"].find("source_of_record.name") == -1:
            # no, it wasn't -- add it in as an extra column for data gathering
            denaliVariables["fields"] += ",source_name"
            denaliVariables["updateSOR"].update({"sorColumn":False})
        else:
            # yes, it was declared on the command line or in an update file
            denaliVariables["updateSOR"].update({"sorColumn":True})

        denaliVariables["updateCategories"] = denaliVariables["fields"].split(',')

        (modFields, denaliVariables["columnData"]) = denali_search.determineColumnOrder(denaliVariables)
        (sqlQuery, wildcard) = denali_search.buildGenericQuery(denaliVariables, column1_name)
        sqlQuery = "DeviceDao" + ':' + sqlQuery

        printData = denali_utility.sqlQueryConstructionResponse(denaliVariables, sqlQuery)
        if printData == False:
            # the reason this would fail is a bad query
            print "Denali Error: (1) SQL Query for comparison data failed.  Denali exiting."
            api = denaliVariables["api"]
            if str(api.get_error_type()) == "validation":
                print colors.bold + colors.fg.yellow + "       SKMS error message : " + colors.reset,
                print "%s" % api.get_error_message()
            return (False, False)


        # depending on denaliVariables["updateSOR"], do one of the following:
        #   if true:   do not remove the column just populate the dictionary with it
        #   if false:  remove the column and populate the dictionary with it
        ccode = populateSORDictionary(denaliVariables, printData)
        if ccode == True:
            for (index, column) in enumerate(denaliVariables["columnData"]):
                if column[1] == "source_of_record.name":
                    del denaliVariables["columnData"][index]
                    break

    #
    # save the original data for inclusion in the rollback log
    # all update methods use this function (file/console/attribute)
    #

    ccode = savePreviewData(denaliVariables, printData)
    if ccode == False:
        # problem saving the data -- this means the rollback log will fail
        return (False, False)


    return (printData, newPrintData)



##############################################################################
#
# organizeAttributeData(denaliVariables, response_dict)
#

def organizeAttributeData(denaliVariables, response_dict):

    columnFields = ''
    rowData      = []
    printData    = []

    EMPTY_VALUE  = "VALUELESS"

    # set up the columns for printing the attributes

    if denaliVariables['attributeUpdate'] == False:
        identifier = "devices"
        device_id  = "device_id"
    else:
        identifier = "device_groups"
        device_id  = "device_group_id"

    # use the first server's list of attributes (in whatever order they are in
    # the dictionary) to generate the columnFields string
    if "attributes" not in response_dict[identifier][0]:
        # problem -- no attribute return?
        print "Denali getAttributes() error.  The return dictionary does not have an \"attributes\" key."
        return False

    for (index, host) in enumerate(response_dict[identifier]):
        if len(host["attributes"]) < len(denaliVariables["updateParameters"]["all"]):

            # The number of attributes reported by CMDB is less than that in the
            # requested update from the user (i.e., 3 requested attribute updates,
            # CMDB reports only 1 in the dictionary).
            #
            # Note:
            # All devices/hosts have access to all attributes in CMDB, so a missing
            # attribute key:value in the return dictionary means the attribute has
            # no value for this device/host.
            #
            # This code "fills in the blanks" with missing attributes.

            if denaliVariables["updateDebug"] == True:
                print "(b) response_dict[attributes] = %s" % host["attributes"]

            # find the attribute(s) in the response dictionary and add them in
            for updateAttribute in denaliVariables["updateParameters"]["all"]:
                updateAttribute = updateAttribute.split('=')
                updateAttribute = updateAttribute[0].strip()

                for responseAttribute in host["attributes"]:
                    responseAttribute = responseAttribute["name"].strip()
                    if updateAttribute == responseAttribute:
                        break
                else:
                    # updateAttribute not found in the response dictionary
                    newDict = {"name":updateAttribute,"value":EMPTY_VALUE}
                    response_dict[identifier][index]["attributes"].append(newDict)

            if denaliVariables["updateDebug"] == True:
                print "(a) response_dict[attributes] = %s" % response_dict[identifier][index]["attributes"]

    for attribute in response_dict[identifier][0]["attributes"]:
        if len(columnFields) == 0:
            columnFields = attribute["name"]
        else:
            columnFields += ',' + attribute["name"]

    # put the host name first, and then the attributes
    columnFields = "name," + columnFields

    # copy the data to the fields location
    denaliVariables["fields"] = columnFields[:]

    # turn it into a list for easy searching
    columnFields = columnFields.split(',')

    # denaliVariables["columnData"]  --  data insertion
    # this is just the host name and column attributes, so it shouldn't
    # be too complicated
    denaliVariables["columnData"] = []
    nameColumn = ["name", "name", "Host Name", 20]
    denaliVariables["columnData"].append(nameColumn)

    for (index, column) in enumerate(columnFields):
        # skip the first one -- the host name (already included above)
        if index == 0:
            continue
        if len(column) > 23:
            COLUMN_WIDTH = len(column) + 2
        else:
            COLUMN_WIDTH = 25

        tempColumn = [column, column, column, COLUMN_WIDTH]
        denaliVariables["columnData"].append(tempColumn)


    # fill out the row data -- so inserts are easy
    for column in columnFields:
        rowData.append('')


    for host in response_dict[identifier]:
        tempData = []
        hostname = host["name"]
        deviceid = host[device_id]
        attrs    = host["attributes"]

        # insert the host name
        rowData[0] = hostname

        # insert the attribute value in the correct row position
        for attribute in attrs:
            attribute_name  = attribute["name"]
            attribute_value = attribute["value"]

            # find the index in columnFields where the attribute_name is located
            index = columnFields.index(attribute_name)
            rowData[index] = attribute_value

        tempData = rowData[:]
        printData.append(tempData)


    if len(printData) == 0:
        # problem with printData generation
        print "Denali attribute printData has a length of zero."
        return False

    return printData



##############################################################################
#
# getAttributeSORData(denaliVariables)
#

def getAttributeSORData(denaliVariables):

    denaliVariables["fields"] = "name,source_name"
    denaliVariables["updateSOR"].update({"sorColumn":False})

    #denaliVariables["updateCategories"] = denaliVariables["fields"].split(',')

    (modFields, denaliVariables["columnData"]) = denali_search.determineColumnOrder(denaliVariables)

    # run a denali query to display the data
    (sqlQuery, wildcard) = denali_search.buildHostQuery(denaliVariables)

    sqlQuery = "DeviceDao" + ':' + sqlQuery

    printData = denali_utility.sqlQueryConstructionResponse(denaliVariables, sqlQuery)
    if printData == False:
        # the reason this would fail is a bad query
        print "Denali Error: (2) SQL Query for comparison data failed.  Denali exiting."
        api = denaliVariables["api"]
        if str(api.get_error_type()) == "validation":
            print colors.bold + colors.fg.yellow + "       SKMS error message : " + colors.reset,
            print "%s" % api.get_error_message()
        return False

    ccode = populateSORDictionary(denaliVariables, printData)

    return True



##############################################################################
#
# getOriginalOverrideAttributeData(denaliVariables)
#

def getOriginalOverrideAttributeData(denaliVariables):

    newPrintData = {}
    printData    = []
    debug        = False

    attribute_columns = denaliVariables['updateParameters'].pop('attribute_names', None)
    if debug == True:
        print "dv update parms = %s" % denaliVariables['updateParameters']
        print "ac = %s" % attribute_columns

    host_list = denaliVariables['updateParameters'].keys()
    host_list.sort()
    for (h_index, host) in enumerate(host_list):
        if debug == True:
            print "host name = %s" % host
            print "host data = %s" % denaliVariables['updateParameters'][host]

        # temporary host data list
        temp_host_data     = []
        temp_host_new_data = []

        # host attribute index counter (reset to zero for each host)
        host_attr_index    = 0

        # build the column of data to print in the preview
        for (a_index, attribute) in enumerate(attribute_columns):
            try:
                host_attribute      = denaliVariables['updateParameters'][host][host_attr_index].split('=')[0]
                host_attribute_data = denaliVariables['updateParameters'][host][host_attr_index].split('=')[1]
            except:
                # no more attributes -- fill out the rest of the host list with blanks
                host_attribute      = ''
                host_attribute_data = 'N/A'

            if debug == True:
                print "column attribute = %s" % attribute
                print "host attribute   = %s" % host_attribute

            if host_attribute == attribute:
                if debug == True:
                    print "  found a match at index #%i" % a_index
                host_attr_index += 1
            else:
                if debug == True:
                    print "  NOT a match at index #%i" % a_index
                host_attribute_data = 'N/A'

            if host not in temp_host_data:
                # printData
                temp_host_data.append(host)
                temp_host_data.append(host_attribute_data)

                # newPrintData
                temp_host_new_data.append(host)
                temp_host_new_data.append('')
            else:
                # printData
                temp_host_data.append(host_attribute_data)

                # newPrintData
                temp_host_new_data.append('')

        # merge the temp_host_data Lists with the printData  newPrintData Lists
        printData.append(temp_host_data)
        newPrintData.update({host:temp_host_new_data})

    # create denaliVariables['columnData'] for printing the preview
    denaliVariables["columnData"] = [["name", "name", "Host Name", 20]]

    for (index, column) in enumerate(attribute_columns):
        if len(column) > 23:
            COLUMN_WIDTH = len(column) + 2
        else:
            COLUMN_WIDTH = 25

        tempColumn = [column, column, column, COLUMN_WIDTH]
        denaliVariables["columnData"].append(tempColumn)

    # create the 'all' section of denaliVariables['updateParameters']
    denaliVariables['updateParameters'].update({'all':[]})
    for attribute in attribute_columns:
        change_string = "%s=" % attribute
        denaliVariables['updateParameters']['all'].append(change_string)

    if debug == True:
        print "RESULTS:"
        print "printData    = %s" % printData
        print "newPrintData = %s" % newPrintData

    return (printData, newPrintData)



##############################################################################
#
# getOriginalUpdateAttributeData(denaliVariables)
#

def getOriginalUpdateAttributeData(denaliVariables):

    currentFields = []
    displayValues = []
    newPrintData  = {}
    printData     = []

    # build the update payload according to the type of update
    if denaliVariables['attributeUpdate'] == True:
        updateDao  = 'DeviceGroupDao'
        identifier = 'device_groups'
    else:
        updateDao  = 'DeviceDao'
        identifier = 'devices'

    # data from an attribute override is massaged differently than that from a normal attribute update
    if denaliVariables['clearOverrides'] == True:
        (printData, newPrintData) = getOriginalOverrideAttributeData(denaliVariables)
        return (printData, newPrintData)

    for (index, parameter) in enumerate(denaliVariables["updateParameters"]["all"]):

        # old method -- using split on the equal sign(s)
        #keyName = parameter.split('=')
        #currentFields.append(keyName[0].strip())
        #displayValues.append(keyName[1].strip())

        # new method -- just in case an attribute uses an equal sign in its text
        locEqual   = parameter.find('=')

        if locEqual == -1:
            print "Denali syntax error:  Equal sign in an attribute updateParameter problem (doesn't exist)."
            return False

        keyName    = [None] * 2
        keyName[0] = parameter[:locEqual]
        keyName[1] = parameter[(locEqual + 1):]
        currentFields.append(keyName[0].strip())
        displayValues.append(keyName[1].strip())

    parameterDictionary = { "attribute_names" : currentFields,
                            identifier        : denaliVariables["serverList"] }

    if denaliVariables["updateDebug"] == True:
        print "parameterDictionary = %s" % parameterDictionary

    # copy the parameter dictionary -- it will be updated by the api call below
    # and cause issues in the analytics push
    copy_parmDictionary = dict(parameterDictionary)

    api          = denaliVariables["api"]
    request_type = "Attribute Comparison"

    # record start time for analytics
    denaliVariables["analyticsSTime"] = time.time()

    # just plug the method get/receive in right here, instead of circling back to
    # the denali_search module code (does this break the normal work-flow?)
    #if api.send_request("DeviceDao", "getAttributes", parameterDictionary) == True:
    ccode = api.send_request(updateDao, "getAttributes", parameterDictionary)
    if ccode == True:
        response_dict = api.get_data_dictionary()

        if denaliVariables["analytics"] == True:
            elapsed_time = time.time() - denaliVariables["analyticsSTime"]
            denali_analytics.createProcessForAnalyticsData(denaliVariables, request_type, copy_parmDictionary, "DeviceDao", "getAttributes", 1, elapsed_time)
            denaliVariables["analyticsSTime"] = 0.00

        # verify the response dictionary is correct
        if (identifier in response_dict and "attributes" in response_dict[identifier][0]):

            # data successfully retrieved (good format) -- now operate/organize it correctly.
            printData = organizeAttributeData(denaliVariables, response_dict)
            if printData == False:
                return (False, False)

        else:
            print "Denali getAttributes() error.  Return dictionary format is unexpected."
            return (False, False)

    else:
        print "\nERROR:"
        print "   STATUS: " + api.get_response_status()
        print "   TYPE: " + str(api.get_error_type())
        print "   MESSAGE: " + api.get_error_message()
        print
        return (False, False)

    # printData has successfully returned (and column alignment)
    # generate the new print data based on the

    # currentFields has the column name (and correct order for itself)
    # displayValues has the column data (and correct order for itself)

    # do not trust the currentFields order to match the denaliVariables["fields"]
    # order.

    # {hostname1 : [hostname2, column1, column2, ...], hostname2 : [hostname2, ... }

    for hostname in denaliVariables["serverList"]:

        tempDisplayValues = []

        if len(currentFields) == 0:
            # uh oh -- problem
            print "Denali error.  currentFields for attributes is empty."
            return (False, False)

        # clear out a temporary variable (with a set number of fields) -- add 1 for hostname
        for item in range(len(currentFields) + 1):
            tempDisplayValues.append('')

        tempDisplayValues[0] = hostname

        # copy denaliVariables["fields"] to a List
        dvFields = denaliVariables["fields"].split(',')

        for (index, field) in enumerate(dvFields):
            if index == 0:
                # skip the host name
                continue

            # collect the matching field data index
            colIndex = currentFields.index(field)

            # insert the data
            tempDisplayValues[index] = displayValues[colIndex]

        tempDV = tempDisplayValues[:]
        newPrintData.update({hostname:tempDV})


    if denaliVariables["updateDebug"] == True:
        print "currentFields   = %s" % currentFields
        print "displayValues   = %s" % displayValues
        print "newPrintData    = %s" % newPrintData
        print "printData       = %s" % printData
        print
        print "responseDictionary = %s" % response_dict

    return (printData, newPrintData)



##############################################################################
#
# showPreviewOfUpdate(denaliVariables)
#
#   Show a preview of the data being updated.
#
#   For the basic mode, it will show a count of the number of devices being
#   updated.
#
#   For the advanced mode, it will show a listing of all devices being changed
#   with their current data and the data after the change (if completed).
#

def showPreviewOfUpdate(denaliVariables):

    NO_CHANGES = getattr(colors.fg, denaliVariables["updateColorNo"])
    CHANGES    = getattr(colors.fg, denaliVariables["updateColorYes"])

    if denaliVariables["updateViewCount"] == -1:
        # If '-1', it means a complete refresh of the data.  This is typically done on the first
        # time through this loop to print all hosts.  There's no need to collect the data again
        # if it was already retrieved previously (cut down on the # of queries sent to the database).

        # get the original data and new data (save it for the rollback log)
        (printData, newPrintData) = collectOriginalDataValues(denaliVariables)
        if printData == False:
            # the reason this would fail is a bad query
            return False

        # save this off in case there are refreshes (view with a number) requested
        denaliVariables["updatePrintData"] = [printData,newPrintData]
    else:
        # pull the saved data for use
        printData = denaliVariables["updatePrintData"][0][:]
        newPrintData = denaliVariables["updatePrintData"][1].copy()

    printData  = denali_utility.addUpdatePrintRows(denaliVariables, printData, newPrintData)
    if printData == False:
        print "Error: The preview failed to generate output data; comparison data not available."
        return False

    # Check for multihost name update signal and change as appropriate
    # The signal is "<hostname>" in the change name portion of the request

    # This code turns a flag (on or off) depending on if the user requested a multi-host
    # hostname update to be made.
    if 'all' in denaliVariables['updateParameters']:
        for parameter in denaliVariables["updateParameters"]["all"]:
            if parameter.startswith("name=") and parameter.find('<hostname>') != -1:
                hostname_update_flag = True
                break
        else:
            hostname_update_flag = False

        # replace <hostname> with the actual hostname so the display is not generic
        for update_item in printData:
            if len(update_item) == 2 and hostname_update_flag == True:
                if update_item[1] == '':
                    # this is the original hostname
                    hostname_orig = update_item[0]

                if update_item[0] == '+' and hostname_orig != '':
                    # this is the name change location
                    update_item[1] = update_item[1].replace('<hostname>', hostname_orig)

    # empty list -- no devices found
    if len(printData) == 0:
        print "No devices found for the query submitted (5)."
        print "Server Query List: %s" % hostsGood
    else:
        print
        print "  :: Update Preview of CMDB Data to be Modified ::"
        print
        print "Each host has two lines; the current values (in white) along with an additional"
        print "line in color to identify if a change to the data is pending.  The colors for"
        print "identifying changes are as follows:"
        print
        print colors.bold + NO_CHANGES + " [   Unchanged   ] " + colors.reset + " =  No changes for the host."
        print colors.bold + CHANGES    + " [ Data Modified ] " + colors.reset + " =  One or more data items will be modified for this host."
        print

        ccode = calculateUpdateSummary(denaliVariables, printData)
        if ccode == False:
            # problem calculating update summary?
            # set the counts to reasonable numbers?
            showStats = False
        else:
            showStats = True

        (printData, overflowData) = denali_search.wrapColumnData(denaliVariables, printData)
        denali_search.prettyPrintData(printData, overflowData, {}, denaliVariables)

        if showStats == True:
            print
            if denaliVariables["updateViewCount"] == -1:
                print "Update summary counts:"
            else:
                print "[Partial View] Update summary counts:"
            print "  Number of hosts that will be modified     : %d" % denaliVariables["updateSummary"]["updateDevices"]
            print "  Number of hosts that will not be modified : %d" % denaliVariables["updateSummary"]["unchangedDevices"]
            print "  Total count of hosts reviewed             : %d" % denaliVariables["updateSummary"]["totalDevices"]

            print "  Source of Record Counts                   : [ SIS = %d ][ CMDB = %d ][ Unknown = %d ]" % (
                                                                 denaliVariables["updateSummary"]["sisHostsSORCount"],
                                                                 denaliVariables["updateSummary"]["cmdbHostsSORCount"],
                                                                 denaliVariables["updateSummary"]["unknownHostsSORCount"])
            # display the update method being used (add/remove/replace)
            print "  Update Entry Method                       : %s" % denaliVariables["updateDefault"].upper()

        else:
            print
            print "Total count of hosts : %d" % len(denaliVariables["serverList"])


    return True



##############################################################################
#
# updateListOfServers(denaliVariables)
#

def updateListOfServers(denaliVariables):

    updateParameters = denaliVariables["updateParameters"]
    deviceList       = denaliVariables["serverList"]


    if denaliVariables["autoConfirm"] == False:
        # autoconfirm is disabled (default); therefore, show the preview
        ccode = showPreviewOfUpdate(denaliVariables)
        if ccode == False:
            # there's a problem with the retrieval/display of the preview
            # data.  Must exit out
            return False

    else:
        # autoconfirm is enabled
        # collect the original data (but no preview of it)
        ccode = collectOriginalDataValues(denaliVariables)
        if ccode == False:
            # problem with the data collection -- rollback log will fail
            # do not proceed any further
            return False

    # refresh the host list after running through the preview (hosts may have been added/subtracted)
    deviceList = denaliVariables["serverList"]
    for (index, device) in enumerate(deviceList):
        confirmUpdate = "loop"

        # only reset the device if there was a full refresh of the list.
        if denaliVariables["updateViewCount"] == -1:
            denaliVariables["updateDevice"] = device
        else:
            if device == denaliVariables["updateDevice"]:
                denaliVariables["updateViewCount"] = -1
            else:
                continue

        if '*' in device or '?' in device or '%' in device:
            if denaliVariables["updateMethod"] == "file":
                # no wildcard updates are allowed from an update file.
                print "Syntax Error: No wildcard updates are allowed from an update file."
                print "Device filter: %s" % device
                return False

        else:
            # build the parameter dictionary that will be used for the update
            if denaliVariables["updateMethod"] == "console":        # easy   : Each host has the same update data
                hostNumber = 0
                device_data = createUpdateDictionary(denaliVariables, device)

            elif denaliVariables["updateMethod"] == "file":
                hostNumber = index
                device_data = createUpdateDictionary(denaliVariables, device)

            elif denaliVariables["updateMethod"] == "attribute":
                device_data = createAttributeUpdateDictionary(denaliVariables, device)

            else:
                # how did we get here?
                return False

            if device_data == False:
                # bail out of this function / do not continue to the
                # next (potential) device.
                #continue
                if denaliVariables["updateDebug"] == True:
                    print "createUpdateDictionary() failed for host %s" % device
                return False

            # fill out the parameter dictionary for the update method
            if denaliVariables["updateMethod"] == "attribute":
                if denaliVariables['attributeUpdate'] == True:
                    # Device Group attribute update
                    identifier = "device_groups"
                else:
                    # Host attribute update
                    identifier = "devices"

                if denaliVariables["autoConfirm"] == True:
                    # do all servers in one fell-swoop if the automatic
                    # confirmation switch was used.
                    param_dict = { "attributes"      : device_data,
                                   identifier        : denaliVariables["serverList"] }
                else:
                    # default -- one server at time.
                    param_dict = { "attributes"      : device_data,
                                   identifier        : [device] }
            else:
                param_dict = { "key_value"       : device,
                               "field_value_arr" : device_data }

            # Check for multiple hostname updates and adjust the parameter dictionary
            # as needed to handle this
            if 'field_value_arr' in param_dict and 'key_value' in param_dict and 'name' in param_dict['field_value_arr']:
                if param_dict['field_value_arr']['name'].find('<hostname>') != -1:
                    host_name_string = param_dict['field_value_arr']['name']
                    host_name_string = host_name_string.replace('<hostname>', param_dict['key_value'])
                    param_dict['field_value_arr']['name'] = host_name_string

            if denaliVariables["updateDebug"] == True:
                print "device parameter dictionary: %s" % param_dict

            # check the autoConfirm variable ("--yes" command-line switch setting)
            if denaliVariables["autoConfirm"] == False:

                # If the "loop" setting is set, do not advance the device in the 'for' loop;
                # just re-display the same one again.
                while confirmUpdate == "loop":
                    confirmUpdate = confirmRecordUpdate(denaliVariables, denaliVariables["updateDevice"], param_dict)
                    if confirmUpdate == "Failed Write":
                        # The rollback log failed to successfully write -- not good.
                        # stop everything here.
                        return False

        if confirmUpdate == True or denaliVariables["autoConfirm"] == True or denaliVariables["autoConfirm"] == "accept_all":
            # create a rollback log for the updates being done
            if denaliVariables["rollbackWritten"] == False:
                ccode = createUpdateRollbackLog(denaliVariables)
                if ccode == False:
                    # creation of the rollback log failed (in function error messages)
                    # stop the updates
                    return "Failed Write"

            if denaliVariables["updateDebug"] == True:
                print "%s (#debug-message#) ==> %s" % (device, param_dict)

            # perform the CMDB update
            ccode = updateCMDBRecord(denaliVariables, param_dict)
            #ccode = True
            #
            # ccode == True:   single host update succeeded
            # ccode == False:  single host update failed
            #
            # On failure, do not stop the process.  The update happens one host at a
            # time; therefore, it is possible that one host can fail because of bad
            # passed in parameters, and the next host will succeed (better parameters).
            #
            # The information on which succeeded or failed is recorded in the update
            # function, not here.  However, the True/False return could be used for
            # some kind of "user entertainment" while the update happens, if desired.
            #

            # reset the confirmation setting for the next server (if necessary)
            #confirmUpdate = False

            # This "if ccode == False:" and "return False" are currently disabled.  If the '#'
            # hash marks are removed, it means any update failure causes an immedate stop to
            # processing further updates.
            if ccode == "quit":
                return "quit"
            elif ccode == False and denaliVariables["updateDebug"] == True:
                # if the update failed and --updatedebug is used, print the SKMS error(s):
                api = denaliVariables["api"]
                print "\nERROR:"
                print "   STATUS: "  + api.get_response_status()
                print "   TYPE: "    + str(api.get_error_type())
                print "   MESSAGE: " + api.get_error_message()
                print
                # don't put "return False" here or all updates will stop after the first failure.

                # evaluate the returning error message to try and simplify it for human consumption
                evaluateSKMSErrorMessage(denaliVariables)

        elif confirmUpdate == "quit":
            # user requested all updates stop
            return "quit"

        elif confirmUpdate == "refresh":
            # refresh the list of servers
            return "refresh"

        # if --updateattr is used, and auto-confirmation enabled, and the update was successful,
        # then just quit out -- everything is finished at this point because autoConfirm puts all
        # servers through the update process in one command (for attributes only).
        #
        # this stops the 'for loop' from executing on the next host; which is unnecessary at this
        # point because all of them were done at the same time.
        if (denaliVariables["autoConfirm"]  == True and
            denaliVariables["updateMethod"] == "attribute" and
            ccode == True):
            return "quit"

    return True



##############################################################################
#
# evaluateSKMSErrorMessage(denaliVariables)
#

def evaluateSKMSErrorMessage(denaliVariables):

    api = denaliVariables["api"]
    message_status = api.get_response_status()
    message_type   = str(api.get_error_type())
    message        = api.get_error_message()

    if message.startswith("The ") and message.endswith(" must be set."):
        location   = message.find(" must be set.")
        cmdb_field = message[4:location]
        needed_field = findKeyAlias(denaliVariables, cmdb_field)
        if needed_field != cmdb_field:
            # found a field in the device dao table to use -- show it.
            if denaliVariables["updateDebug"] == True:
                print colors.bold + colors.fg.yellow + "  Best guess of what to use for " + colors.reset,
                print "[\"",
                print colors.bold + colors.fg.red + "\b%s" % cmdb_field + colors.reset,
                print "\b\"]  ==> ",
                print colors.bold + colors.fg.blue + "%s" % needed_field + colors.reset
                print "  See SKMS Web API documentation for further help."
            else:
                #print "         Best guess of what to use for [\"%s\"]:  %s" % (cmdb_field, needed_field)
                print colors.bold + colors.fg.yellow + "         Best guess of what to use for " + colors.reset,
                print "[\"",
                print colors.bold + colors.fg.red + "\b%s" % cmdb_field + colors.reset,
                print "\b\"]  ==> ",
                print colors.bold + colors.fg.blue + "%s" % needed_field + colors.reset
                print "         See SKMS Web API documentation for further help."
        else:
            if denaliVariables["updateDebug"] == True:
                print "  Cannot find \"%s\" in the defined list of fields; therefore, no suggestion is given."
                print "  Search CMDB objects manually in SKMS for additional help."
            else:
                print "         Cannot find \"%s\" in the defined list of fields; therefore, no suggestion is given."
                print "         Search CMDB objects manually in SKMS for additional help."

    return



##############################################################################
#
# sisUpdateConfirmation(denaliVariables)
#
#   This function just asks for a confirmation before proceeding with a CMDB
#   update that will change SIS mappings.
#

def sisUpdateConfirmation(denaliVariables):

    message = "Continue with SIS mapping changes for this device (y/n), all devices with the same set of changes (a), or quit (y/n/a/q): "

    print
    response = raw_input(message)
    if response.lower() == 'y' or response.lower() == 'yes':
        return True
    elif response.lower() == 'q' or response.lower() == 'quit':
        print "Remaining updates have been cancelled."
        return "quit"
    elif response.lower() == 'a':
        return "auto_confirm"
    else:
        return False



##############################################################################
#
# retrieveSISChanges(denaliVariables, response_dict)
#
#   Gather the SIS changes into a single variable for easy comparison
#

def retrieveSISChanges(denaliVariables, response_dict):

    data_changes = {}

    # verify that a SIS change element is in the dictionary
    if (
        'messages' in response_dict and
        'error_data' in response_dict['messages'][0] and
        'sis_changes' in response_dict['messages'][0]['error_data']
        ):

        # potential items in response dictionary -- the list, and the title to print if it exists
        sis_item_list = ['potential_sis_service_mappings' , 'reverse_sync_warnings']

        for sis_item in sis_item_list:
            if sis_item in response_dict['messages'][0]['error_data'] and len(response_dict['messages'][0]['error_data'][sis_item]) > 0:
                data_changes.update({sis_item:response_dict['messages'][0]['error_data'][sis_item]})

        data_changes.update({'sis_changes':response_dict['messages'][0]['error_data']['sis_changes']})

    return data_changes



##############################################################################
#
# saveSISChanges(denaliVariables, data_changes)
#

def saveSISChanges(denaliVariables, data_changes):

    # store the data (a Dictionary within a List)
    if len(denaliVariables['updateSISData']) == 0:
        denaliVariables['updateSISData'].append(data_changes)
    else:
        for existing_sis_changes in denaliVariables['updateSISData']:
            if data_changes == existing_sis_changes:
                break
        else:
            denaliVariables['updateSISData'].append(data_changes)

    return True



##############################################################################
#
# compareSISChanges(denaliVariables, sis_data_changes)
#
#   Compare the existing set of changes stored in denaliVariables with the
#   new set of changes (sis_data_changes).  If they are the same, return
#   "True".  If they are not the same, return "False".
#

def compareSISChanges(denaliVariables, sis_data_changes):

    for (index, sis_changes) in enumerate(denaliVariables['updateSISData']):
        if sis_data_changes == sis_changes:
            return True

    return False



##############################################################################
#
# displaySISChanges(denaliVariables, response_dict, device)
#

def displaySISChanges(denaliVariables, response_dict, device):

    if denaliVariables['updateDebug'] == True:
        print "response dictionary = %s" % response_dict

    # if the accept all switch was issued -- return true and do all of the
    # updates without further prompting
    if denaliVariables['autoConfirmAllSIS'] == True:
        return True

    # If the user has accepted the last fingerprint for SIS, check if this host
    # has a match, and auto-accept if it does.
    # If it does not, display the change dialog and wait for user input
    if denaliVariables['autoConfirmSIS']    == True:
        sis_data_changes = retrieveSISChanges(denaliVariables, response_dict)
        ccode            = compareSISChanges(denaliVariables, sis_data_changes)

        if denaliVariables['updateSISAccepted'] == True and ccode == True:
            # Return True here if auto-accepting the same set of SIS changes
            # for a different CMDB device.
            return True

    # verify that a SIS change element is in the dictionary
    if (
        'messages' in response_dict and
        'error_data' in response_dict['messages'][0] and
        'sis_changes' in response_dict['messages'][0]['error_data']
        ):

        # Show the device name/id so as to remove questions to what is happening
        # to what host/device
        print
        print "*** SIS mapping modification detected for [ %s ].  Review changes and confirm if correct ***" % device
        print "SIS Change Fingerprint [%d]" % (len(denaliVariables['updateSISData']) + 1)

        # potential items in response dictionary -- the list, and the title to print if it exists
        sis_item_list  = ['potential_sis_service_mappings' , 'reverse_sync_warnings']
        sis_item_title = ['Potential SIS Service Mappings:',
                          'Reverse Sync Warnings         :']

        for (item_index, sis_item) in enumerate(sis_item_list):
            if sis_item in response_dict['messages'][0]['error_data']:
                if len(response_dict['messages'][0]['error_data'][sis_item]) > 0:
                    print sis_item_title[item_index]
                    for (info_index, sis_information) in enumerate(response_dict['messages'][0]['error_data'][sis_item]):
                        print "%d. %s" % ((info_index + 1), sis_information)
                else:
                    if denaliVariables['updateDebug'] == True:
                        print " %s  No data" % sis_item_title[item_index]

        # reassign the sis_change data to a separate variable
        sis_changes = response_dict['messages'][0]['error_data']['sis_changes']

        # display the remaining data -- there's a potential for multiple items here
        sis_change_labels = sis_changes.keys()

        # spin through each of them, and display the contents
        for sis_label in sis_change_labels:
            sis_label_items_list = sis_changes[sis_label].keys()

            # hopefully stable field names -- to use everywhere
            potential_fields = ['field_label', 'new_value', 'old_value']
            if 'field_label' in sis_changes[sis_label]:
                print "%s:" % sis_changes[sis_label]['field_label']
                field_label = sis_changes[sis_label]['field_label']
            else:
                print "Data item(s) changing:"
                field_label = "value"
            if 'old_value' in sis_changes[sis_label]:
                print "  Old %s: %s" % (field_label, sis_changes[sis_label]['old_value'])
            if 'new_value' in sis_changes[sis_label]:
                print "  New %s: %s" % (field_label, sis_changes[sis_label]['new_value'])

            # search for extra field names (not listed above)
            for sis_label_item in sis_label_items_list:
                if sis_label_item in potential_fields:
                    continue
                print "    %s: %s" % (sis_label_item, sis_changes[sis_label][sis_label_item])

            if denaliVariables['updateDebug'] == True:
                print "sis_label_items = %s" % sis_label_items_list

        ccode = sisUpdateConfirmation(denaliVariables)
        if ccode == 'quit':
            return 'quit'
        elif ccode == 'auto_confirm':
            denaliVariables['autoConfirmSIS'] = True
            denaliVariables['updateSISAccepted'] = True

            # for all auto-confirmed entries -- add in their change vector
            sis_data_changes = retrieveSISChanges(denaliVariables, response_dict)
            ccode            = saveSISChanges(denaliVariables, sis_data_changes)

        elif ccode == False:
            return False
        elif denaliVariables['autoConfirmSIS'] == True:
            # If 'y' or 'yes' was entered and auto confirm SIS is enabled
            # make sure the update variable is modified to reflect this.
            denaliVariables['updateSISAccepted'] = True

    else:
        # no SIS changes ... then why are we in this function?
        pass

    return True



##############################################################################
#
# update_error_handling_routines(denaliVariables, kva, method)
#
#   This funciton handles some resubmits for data updates if needed.
#   1.  CSRF resubmit:  This happens if the CSRF token isn't populated in the
#       session file.  A simple resubmit of the data/update will cause the
#       update to succeed (because the first update request populates the CSRF)
#       data in the session file -- unfortunately that is too late for the update
#       to succeed -- so a resubmit works.
#
#   2.  Confirmation code:  This happens if a change is made that will affect
#       a SIS mapping.  We want to make sure that the user/administrator knows
#       that SIS will be affected, so they are questioned about this, and then
#       the confirmation code is sent back to SKMS, and the update is done.
#

def update_error_handling_routines(denaliVariables, kva, method):

    if len(method) == 0:
        return False

    api = denaliVariables['api']

    error_message = api.get_error_message()
    if error_message.startswith("The CSRF token is either missing or invalid"):
        # call update again if the failure is CSRF missing/invalid token
        if denaliVariables['updateDebug'] == True:
            print "error_handling: csrf error"
        ccode = api.send_request("DeviceDao", method, kva)
        if ccode == True:
            return True
        else:
            error_message = api.get_error_message()

    if error_message.startswith("A confirmation code is required"):
        # handle SIS two-way sync confirmation code update(s)
        if denaliVariables['updateDebug'] == True:
            print "error_handling: confirmation code required"
        response_dict = api.get_response_dictionary()

        if denaliVariables['updateDebug'] == True:
            print
            print "response_dict = %s" % response_dict
            print "kva           = %s" % kva
            print

        # get the response code (if it exists)
        if ('messages' in response_dict and
            len(response_dict['messages']) > 0 and
            'error_data' in response_dict['messages'][0] and
            'confirmation_code' in response_dict['messages'][0]['error_data']):
            confirm_code = response_dict['messages'][0]['error_data']['confirmation_code']
        else:
            # cannot find confirmation code -- fail the update request
            print "Denali: Update error.  Confirmation code not found."
            return False

        # display the changes to SIS
        ccode = displaySISChanges(denaliVariables, response_dict, kva['key_value'])
        if ccode == "quit":
            return "quit"
        elif ccode == False:
            return "rejected"

        # include the received confirmation code in the parameter dictionary to resend
        kva['field_value_arr'].update({'confirmation_code':confirm_code})
        if denaliVariables['updateDebug'] == True:
            print "kva = %s" % kva

        # resend the updated dictionary to do the update (again)
        ccode = api.send_request("DeviceDao", method, kva)
        if ccode == False:
            return False
        else:
            return True

    else:
        return False



##############################################################################
#
# updateCMDBRecord(denaliVariables, param_dict)
#
#   This function calls the WebAPI and performs the update as requested.
#

def updateCMDBRecord(denaliVariables, param_dict):

    api          = denaliVariables["api"]
    message      = ''
    request_type = "Update"

    if denaliVariables['attributeUpdate'] == True:
        # DeviceGroup update
        updateDao = 'DeviceGroupDao'
        update_id = 'device_groups'
    else:
        updateDao = 'DeviceDao'
        update_id = 'devices'

    if denaliVariables["updateMethod"] != "attribute":
        hostName = param_dict["key_value"]
    else:
        hostName = param_dict[update_id][0]

    #NO_CHANGES = getattr(colors.fg, denaliVariables["updateColorNo"])
    #CHANGES    = getattr(colors.fg, denaliVariables["updateColorYes"])

    # record start time for analytics
    denaliVariables["analyticsSTime"] = time.time()

    if denaliVariables["updateMethod"] == "attribute":
        ccode = api.send_request(updateDao, "setAttributes", param_dict)
        if ccode == False:
            ccode = update_error_handling_routines(denaliVariables, param_dict, "setAttributes")
            if ccode == "quit":
                return "quit"
        if ccode == True:
            data_dict = api.get_data_dictionary()

            if denaliVariables['updateDebug'] == True:
                print "data dictionary = %s" % data_dict

            if denaliVariables["analytics"] == True:
                elapsed_time = time.time() - denaliVariables["analyticsSTime"]
                denali_analytics.createProcessForAnalyticsData(denaliVariables, request_type, param_dict, updateDao, "setAttributes", 1, elapsed_time)
                denaliVariables["analyticsSTime"] = 0.00

            if "attribute" in data_dict and update_id in data_dict:
                # successful update
                success_failure = "SUCCESSFUL"

                if len(data_dict[update_id]) > 1:
                    for host in data_dict[update_id].keys():
                        if denaliVariables["autoConfirm"] != True:
                            print "  %-25s  :  " % data_dict[update_id][host],
                            print colors.bold + colors.fg.lightgreen + success_failure + colors.reset

                        ccode = amendUpdateLog(denaliVariables, data_dict[update_id][host], success_failure, message, param_dict)
                else:
                    if denaliVariables["autoConfirm"] != True:
                        print "  %-25s  :  " % hostName,
                        print colors.bold + colors.fg.lightgreen + success_failure + colors.reset

                    ccode = amendUpdateLog(denaliVariables, hostName, success_failure, message, param_dict)

                return True

            else:
                # failure
                cmdbUpdateFailureMessage(denaliVariables, data_dict, param_dict, hostName)
                return False
        elif ccode == "rejected":
            print "  %-25s  :  " % param_dict['key_value'],
            print colors.bold + colors.fg.lightcyan + "CANCELLED" + colors.reset
        else:
            # failure
            data_dict = ""
            cmdbUpdateFailureMessage(denaliVariables, data_dict, param_dict, hostName)
            return False

    else:
        ccode = api.send_request("DeviceDao", "updateRecord", param_dict)
        if ccode == False:
            ccode = update_error_handling_routines(denaliVariables, param_dict, "updateRecord")
            if ccode == "quit":
                return "quit"
        if ccode == True:
            data_dict = api.get_data_dictionary()

            if denaliVariables['updateDebug'] == True:
                print "data dictionary = %s" % data_dict

            if denaliVariables["analytics"] == True:
                elapsed_time = time.time() - denaliVariables["analyticsSTime"]
                denali_analytics.createProcessForAnalyticsData(denaliVariables, request_type, param_dict, "DeviceDao", "updateRecord", 1, elapsed_time)
                denaliVariables["analyticsSTime"] = 0.00

            if "primary_key_arr" in data_dict and "device_id" in data_dict["primary_key_arr"]:
                # successful update
                success_failure = "SUCCESSFUL"
                if denaliVariables["autoConfirm"] != True:
                    print "  %-25s  :  " % hostName,
                    print colors.bold + colors.fg.lightgreen + success_failure + colors.reset

                ccode = amendUpdateLog(denaliVariables, hostName, success_failure, message, param_dict)

                return True

            else:
                # failure
                cmdbUpdateFailureMessage(denaliVariables, data_dict, param_dict, hostName)
                return False
        elif ccode == "rejected":
            print "  %-25s  :  " % param_dict['key_value'],
            print colors.bold + colors.fg.lightcyan + "CANCELLED" + colors.reset
        else:
            # failure
            data_dict = ""
            cmdbUpdateFailureMessage(denaliVariables, data_dict, param_dict, hostName)
            return False



##############################################################################
#
# cmdbUpdateFailureMessage(denaliVariables, data_dict, param_dict, hostName)
#

def cmdbUpdateFailureMessage(denaliVariables, data_dict, param_dict, hostName):

    if denaliVariables['attributeUpdate'] == True:
        # DeviceGroup update
        update_id = 'device_groups'
    else:
        # Host update
        update_id = 'devices'

    api = denaliVariables["api"]
    success_failure = "FAILURE"
    if str(api.get_error_type()).strip() == "validation" or str(api.get_error_type()).strip() == "permission" or str(api.get_error_type()).strip() == "unknown":
        message = api.get_error_message()
    else:
        if denaliVariables["updateDebug"] == False:
            message = "Run Denali again with the \"--updatedebug\" switch for additional output"
        else:
            message = ""

    if len(data_dict) > 0 and update_id in data_dict:
        if len(data_dict[update_id]) > 1:
            # multi-host failed update (attributes most likely)
            for host in data_dict[update_id].keys():
                if denaliVariables["autoConfirm"] != True:
                    print "  %-25s  :  " % data_dict[update_id][host],
                    print colors.bold + colors.fg.lightgreen + success_failure + colors.reset

                if denaliVariables["updateDebug"] == False and denaliVariables["autoConfirm"] != True:
                    print colors.bold + colors.fg.yellow + "         SKMS Failure Reason : " + colors.reset,
                    print " %s" % message
                    evaluateSKMSErrorMessage(denaliVariables)
                ccode = amendUpdateLog(denaliVariables, data_dict[update_id][host], success_failure, message, param_dict)

            return

    # failed update - single host
    if denaliVariables["autoConfirm"] != True:
        print "  %-25s  :  " % hostName,
        print colors.bold + colors.fg.red + success_failure + colors.reset

    if denaliVariables["updateDebug"] == False and denaliVariables["autoConfirm"] != True:
        print colors.bold + colors.fg.yellow + "         SKMS Failure Reason : " + colors.reset,
        print " %s" % message
        evaluateSKMSErrorMessage(denaliVariables)
    ccode = amendUpdateLog(denaliVariables, hostName, success_failure, message, param_dict)

    return



##############################################################################
#
# confirmRecordUpdate(denaliVariables, device, param_dict)
#
#   This function is the last step/stage before an update to a CMDB record
#   is requested.  It simply prints the information that will be updated and
#   asks the user if this is what they want (yes/no).  If they answer 'yes',
#   the update is completed.  If they answer 'no', then the update is skipped
#   and control is returned to the calling function (to loop through to another
#   device, or finish).
#

def confirmRecordUpdate(denaliVariables, device, param_dict):

    global hostsRemove
    global hostsGood

    # basic preview before the update -- to be replaced by the preview function
    #print "Device Name:  %s" % device
    #print "Update Data:  %s" % param_dict

    #
    # Display the menu and collect a response
    #
    answer = displayUpdateMenu(denaliVariables, device)

    # Accept this host to update
    if answer == 'y' or answer == "yes":
        print "  [",
        print colors.bold + colors.fg.lightgreen + "%s" % device,
        print colors.reset,
        print "\b] host will be updated"
        return True

    # Reject this host from being updated
    elif answer == 'n' or answer == "no":
        print "  [",
        print colors.bold + colors.fg.red + "%s" % device,
        print colors.reset,
        print "\b] host update is skipped"
        return False

    # Accept _ALL_ hosts to be updated (no more prompts -- be careful)
    elif answer == 'a' or answer == "all":
        # I've pressed 'a' a few times accidentally when testing this code, so for
        # now, a double check is a good idea (I think) before turning the dogs loose
        # and potentially causing harm (even accidentally) to the database.
        # (Better safe than sorry).
        print colors.bold + colors.fg.red + "  Allow CMDB update for all devices? (y/n):" + colors.reset,
        answer = raw_input("")
        answer = answer.lower()

        # User must answer 'y' or "yes" to make this work -- any other character or <ENTER> will cancel
        # the "accept everything and do the update" request.
        if answer == 'y' or answer == "yes":
            # when 'yes' is accepted here, the rest of the updates will just roll through
            # automatically.
            denaliVariables["autoConfirm"] = "accept_all"
            return True

        else:
            print "Update of all submitted devices cancelled -- host list refreshed."
            denaliVariables["updateViewCount"] = -1
            denaliVariables["updateDevice"] = ''
            return "refresh"

    # Print a list of hostname (column aligned to look nice)
    elif answer.startswith('h') or answer.startswith("host"):
        return printHostnames(denaliVariables, answer)

    # Refresh the list (from the top of all hosts)
    elif answer == 'l' or answer == "list":
        denaliVariables["updateViewCount"] = -1
        denaliVariables["updateDevice"] = ''
        return "refresh"

    # Show a specific number of hosts starting at the current host
    elif answer.startswith('v') or answer.startswith("view"):
        if answer == 'v' or answer == "view":
            denaliVariables["updateViewCount"] = 1
            return "refresh"

        return skipOrViewHost(denaliVariables, answer)

    # Exit out of the update code -- don't do any more updates
    elif answer == 'q' or answer == "quit":
        print "CMDB record updates for all remaining devices have been cancelled."
        return "quit"

    # Insert a host (or hosts if comma separated) to be updated.  Only enabled in "console" mode.
    elif (answer == 'i' or answer == "insert") and denaliVariables["updateMethod"] == "console":
        #goodList = []
        goodList = raw_input("  Enter a list of servers to insert (comma separated): ")
        goodList = goodList.split(',')

        # What this essentially means is that the user has modified the main list
        # of servers to do updates on.  Add on the server(s) to this list.  Make
        # sure that the new server isn't already there -- use a "set" to do this.

        # grab the current list
        hostList = set(denaliVariables["serverList"])

        # add the new host(s) to the list
        for host in goodList:
            hostList.add(host)

        hostList = list(hostList)
        hostList.sort()

        # assign the master list to this update list
        denaliVariables["serverList"] = hostList

        if len(denaliVariables["serverList"]) > 0:
            # after an insert, the host list needs to be completely refreshed
            denaliVariables["updateViewCount"] = -1
            denaliVariables["updateDevice"] = ''#denaliVariables["serverList"][0]
        else:
            # If the host list is empty -- there's nothing to do.  Exit.
            print "Program Exit:  The host list is empty; there is nothing to do."
            return "quit"

        if denaliVariables["updateDebug"] == True:
            print "refreshed serverList = %s" % denaliVariables["serverList"]

        return "refresh"

    # Remove a host (or hosts) from the list of hosts to update (works in both "console" and "file" mode)
    elif answer == 'r' or answer == "remove":
        removeList = []
        removeList = raw_input("  Enter a list of servers to remove (comma separated): ")
        removeList = removeList.split(',')
        for host in removeList:
            hostsRemove.append(host.strip())

        # What this essentially means is that the user has provided a list of hosts
        # to remove from the serverList.
        hostList = set(denaliVariables["serverList"])

        for host in hostsRemove:
            try:
                hostList.remove(host)
            except:
                # requested host isn't present in current list
                pass

        # take the remaining servers and put them back in the list
        hostList = list(hostList)
        hostList.sort()
        denaliVariables["serverList"] = hostList

        if len(denaliVariables["serverList"]) > 0:
            # after a remove, the host list needs to be completely refreshed
            denaliVariables["updateViewCount"] = -1
            denaliVariables["updateDevice"] = ''#denaliVariables["serverList"][0]
        else:
            # If the host list is empty -- there's nothing to do.  Exit.
            print "Program Exit:  The host list is empty.  All hosts have been removed; there is nothing to do."
            return "quit"

        if denaliVariables["updateDebug"] == True:
            print "refreshed serverList = %s" % denaliVariables["serverList"]

        return "refresh"

    else:
        # catch-all:  in case something slips through, just cancel the update for it.
        print "  CMDB record update for [",
        print colors.bold + colors.fg.red + "%s" % device,
        print colors.reset,
        print "\b] has been cancelled."
        return False

    return False



##############################################################################
#
# displayUpdateMenu(denaliVariables, device)
#

def displayUpdateMenu(denaliVariables, device):

    # state variable for the menu loop
    answer = "loop"

    updateConsole = ['y', "yes", 'n', "no", 'a', "all", 'q', "quit", 'h', "host", 'l', "list", 'v', "view", 'i', "insert", 'r', "remove", '?', '']
    updateFile    = ['y', "yes", 'n', "no", 'a', "all", 'q', "quit", 'h', "host", 'l', "list", 'v', "view", 'r', "remove", '?', '']


    while answer == "loop":

        if denaliVariables["updateMenuShow"] == True:
            denaliVariables["updateMenuShow"] = False

            if len(denaliVariables["serverList"]) > 1:
                print
                print "  [ yes    ] - Accept a single host update [",
                print colors.bold + colors.fg.red + "%s" % device,
                print colors.reset,
                print "\b] -- ask again on the next host"

                print "  [ no     ] - Reject a single host update [",
                print colors.bold + colors.fg.red + "%s" % device,
                print colors.reset,
                print "\b] -- ask again on the next host"

            else:
                print
                print "  [ yes    ] - Accept this single host update [",
                print colors.bold + colors.fg.red + "%s" % device,
                print colors.reset,
                print "\b]"

                print "  [ no     ] - Reject this single host update [",
                print colors.bold + colors.fg.red + "%s" % device,
                print colors.reset,
                print "\b]"

            print "  [ all    ] - Accept all host updates (no further prompts)"
            print "  [ hosts  ] - Print the host names only / \"h<#>\" to print multiple hosts"
            print "  [ list   ] - Show the full host list and reset the update device to the first host"
            print "  [ view   ] - View the next host / \"v<#>\" to view multiple hosts / \"v <host>\" to jump to a specific host"

            if denaliVariables["updateMethod"] == "console":
                print "  [ insert ] - Insert one or more hosts into the host list (comma delimited list)"

            print "  [ remove ] - Remove one or more hosts from the host list (comma delimited list)"
            print "  [ quit   ] - Cancel remaining host updates and exit Denali immediately"
            print "  [ ?      ] - Display this menu"

        print
        print "Device to update: ",

        if denaliVariables["serverList"][-1] == device:
            print colors.bold + colors.fg.lightgreen + "%s" % device,
            print colors.reset + "  (last host)"
        else:
            print colors.bold + colors.fg.lightgreen + "%s" % device,
            print colors.reset

        try:
            sys.stdin = open("/dev/tty")
            if denaliVariables["updateMethod"] == "console":
                answer = raw_input("Proceed with device update? (y/[n]/a/h/l/v/i/r/q/?): ")
                answer = answer.lower()
                if answer.startswith('v') or answer.startswith("view") or answer.startswith('h') or answer.startswith("host"):
                    pass
                elif answer not in updateConsole:
                    answer = "loop"
            else:
                answer = raw_input("Proceed with device update? (y/[n]/a/h/l/v/r/q/?): ")
                answer = answer.lower()
                if answer.startswith('v') or answer.startswith("view") or answer.startswith('h') or answer.startswith("host"):
                    pass
                elif answer not in updateFile:
                    answer = "loop"

        except EOFError:
            print "Denali stdin EOF error:  stdin redirection not owned by the console, could not redirect."
            print "Exiting Denali"
            return "quit"

        if answer == '':
            answer = 'n'

        if answer == '?':
            answer = "loop"
            denaliVariables["updateMenuShow"] = True

    return answer



##############################################################################
#
# skipOrViewHost(denaliVariables, answer)
#

def skipOrViewHost(denaliVariables, answer):

    loop = True
    loop_counter = 0

    #
    # If "answer" has a [space] in it, assume a host name was provided.
    # If the host path is taken, assume the hostname will be 5 characters or larger.
    # If the number of character < 5, assume a number path (bad syntax)
    #
    # If "answer" has no [space] in it, assume a number was provided.
    # If the number path is taken, assume the number will be 4 digits or less.
    # if the number of digits is > 4, assume a host path (bad syntax)
    #

    while loop == True:

        loop_counter += 1

        if loop_counter > 5:
            # something's wrong -- refresh the entire list (which is better than
            # stopping everything and giving up)
            print "Denali:  skip/view infinite loop break [%s]" % answer
            denaliVariables["updateViewCount"] = -1
            return "refresh"

        # v/view [space] host ("v db2255.oak1" or "view db2255.oak1")
        if answer.count(' ') > 0:
            # process an assumed hostname to view or skip to

            hostname = answer.split(' ')
            hostname = hostname[1].strip()

            # check the length
            if len(hostname) > 4:

                # see if the hostname exists in the server list
                for (index, host) in enumerate(denaliVariables["serverList"]):
                    if hostname == host:
                        # found it -- it exists.
                        denaliVariables["updateDevice"] = hostname
                        denaliVariables["updateViewCount"] = 1
                        return "refresh"

                print "Hostname: \"%s\" is not found in the current server list to update" % hostname
                denaliVariables["updateViewCount"] = -1
                return "refresh"

            else:
                # remove the space to prep "answer" for "number" processing
                while answer.count(' ') > 0:
                    answer = answer.replace(' ', '')

        else:
            # process an assumed number to view or skip to
            # v/view combined with a number ("v5" or "view5")

            if answer.startswith("view"):
                hostnumber = answer[4:]
                if len(hostnumber) > 4:
                    # assume a hostname -- add a space and then continue
                    answer = answer[:4] + ' ' + answer[4:]
                    continue
            else:
                hostnumber = answer[1:]
                if len(hostnumber) > 4:
                    # assume a hostname -- add a space and then continue
                    answer = answer[:1] + ' ' + answer[1:]
                    continue

            # push the value into the updateViewCount storage location
            # (use try/except to catch problems)
            try:
                denaliVariables["updateViewCount"] = int(hostnumber.strip())
            except ValueError:
                print "Non-Integer value submitted for host count to view (\"%s\")" % hostnumber

                # refresh the entire list -- penalty for a typo
                denaliVariables["updateViewCount"] = -1

            return "refresh"



##############################################################################
#
# hostCommandParse(denaliVariables, cliCommand)
#

def hostCommandParse(denaliVariables, cliCommand):

    # The logic for this function is very similar what is found in the
    # skip/view function above.

    loop          = True
    loop_counter  = 0
    hostnameCount = 0

    while loop == True:

        loop_counter += 1

        if loop_counter > 5:
            # something's wrong -- refresh the entire list (which is better than
            # stopping everything and giving up)
            print "Denali:  host print infinite loop break [%s]" % cliCommand
            denaliVariables["updateViewCount"] = -1

            return True

        # h/host [space] host ("h db2255.oak1" or "host db2255.oak1")
        if cliCommand.count(' ') > 0:
            # process an assumed hostname to starting printing from

            hostname = cliCommand.split(' ')

            if len(hostname) > 2:
                try:
                    hostnameCount = int(hostname[2])
                except ValueError:
                    print "Non-Integer value submitted for host count to view (\"%s\")" % hostname[2]

            hostname = hostname[1].strip()

            # check the length
            if len(hostname) > 4:

                # see if the hostname exists in the server list
                for (index, host) in enumerate(denaliVariables["serverList"]):
                    if hostname == host:
                        # found it -- it exists.
                        denaliVariables["updateDevice"] = hostname

                        if hostnameCount > 0:
                            denaliVariables["updateViewCount"] = hostnameCount
                        else:
                            denaliVariables["updateViewCount"] = (len(denaliVariables["serverList"]) - index)

                        return True

                print "Hostname: \"%s\" is not found in the current server list to update" % hostname
                #denaliVariables["updateViewCount"] = -1
                return True

            else:
                # remove the space to prep "cliCommand" for "number" processing
                while cliCommand.count(' ') > 0:
                    cliCommand = cliCommand.replace(' ', '')

        else:
            # process an assumed number to view or skip to
            # h/host combined with a number ("h5" or "host5")

            if cliCommand.startswith("host"):
                hostnumber = cliCommand[4:]
                if len(hostnumber) > 4:
                    # assume a hostname -- add a space and then continue
                    cliCommand = cliCommand[:4] + ' ' + cliCommand[4:]
                    continue
            else:
                hostnumber = cliCommand[1:]
                if len(hostnumber) > 4:
                    # assume a hostname -- add a space and then continue
                    cliCommand = cliCommand[:1] + ' ' + cliCommand[1:]
                    continue

            # push the value into the updateViewCount storage location
            # (use try/except to catch problems)
            try:
                if len(hostnumber) > 0:
                    denaliVariables["updateViewCount"] = int(hostnumber.strip())
                else:
                    denaliVariables["updateViewCount"] = len(denaliVariables["serverList"])

            except ValueError:
                print "Non-Integer value submitted for host count to view (\"%s\")" % hostnumber

                # refresh the entire list -- penalty for a typo
                denaliVariables["updateViewCount"] = -1

            return True


    return True



##############################################################################
#
# printHostnames(denaliVariables, cliCommand)
#

def printHostnames(denaliVariables, cliCommand):

    NO_CHANGES = getattr(colors.fg, denaliVariables["updateColorNo"])
    CHANGES    = getattr(colors.fg, denaliVariables["updateColorYes"])

    HOST_PRINT_WIDTH = 125

    cliCommand = cliCommand.lower()

    if (cliCommand == "hall" or cliCommand == "h all" or cliCommand == "hostall" or
        cliCommand == "host all" or cliCommand == "h" or cliCommand == "host"):

        # reset the variables to show the entire list
        denaliVariables["updateViewCount"] == -1

        # first server in the list
        denaliVariables["updateDevice"] = denaliVariables["serverList"][0]


    ccode = hostCommandParse(denaliVariables, cliCommand)
    #print "ccode  = %s" % ccode
    #print "dv uvc = %s" % denaliVariables["updateViewCount"]
    #print "dv ud  = %s" % denaliVariables["updateDevice"]


    # print the host name(s) for a "console" based update
    # make a table of the list of hosts where the update happened -- make it look semi-nice.
    maxlength    = 0
    hostCount    = 0
    foundHost    = False
    maxHostCount = denaliVariables["updateViewCount"]

    if maxHostCount == -1:
        maxHostCount = len(denaliVariables["serverList"])

    for hostname in denaliVariables["serverList"]:
        if hostname == denaliVariables["updateDevice"] and foundHost == False:
            foundHost = True
        elif foundHost == True:
            pass
        else:
            continue

        hostCount += 1
        if hostCount <= maxHostCount:
            if len(hostname) > maxlength:
                maxlength = len(hostname)
        else:
            break

    # padding between each host printed
    maxlength += 4

    # number of hosts to print across the screen on a single line
    numHosts = HOST_PRINT_WIDTH / maxlength

    print "List of hosts submitted for updating:"
    print colors.bold + NO_CHANGES + "  [   Unchanged   ] " + colors.reset + " =  No changes for the host."
    print colors.bold + CHANGES    + "  [ Data Modified ] " + colors.reset + " =  One or more data items will be modified for this host."
    print

    hostCount    = 0
    hostsPerLine = 0
    foundHost    = False
    print "  ",

    for hostname in denaliVariables["serverList"]:

        if hostname == denaliVariables["updateDevice"] and foundHost == False:
            foundHost = True
        elif foundHost == True:
            pass
        else:
            continue

        if hostname in denaliVariables["updateHostsYes"]:
            hostColor = CHANGES
        else:
            hostColor = NO_CHANGES

        if hostname == denaliVariables["updateDevice"]:
            # put [x] in front of the current device -- to identify it easily in a large list.
            print "\b\b\b[x]",
            print colors.bold + hostColor + "\b%s " % hostname.ljust(maxlength),
            print colors.reset,
        else:
            print colors.bold + hostColor + "%s " % hostname.ljust(maxlength),
            print colors.reset,

        # increment the host count printed on a single line (check for max number)
        hostsPerLine += 1
        if hostsPerLine >= numHosts:
            print "\n  ",
            hostsPerLine = 0

        # increment the host count (total) printed
        hostCount += 1
        if hostCount >= maxHostCount:
            break

    # only print an extra line (for spacing) if the host last printed
    # isn't the last one on that specific line; otherwise, two lines
    # are printed
    if hostsPerLine != 0:
        print

    return "loop"



##############################################################################
#
# updateCMDBWithFile(denaliVariables, file_path)
#

def updateCMDBWithFile(denaliVariables, file_path):

    global BATCH_MODE
    global file_data
    global hostsGood
    global hostsRemove

    hostCount      = 0
    hostUpdateData = None

    hostName       = ''
    hostData       = ''

    bracketList = [ '[', '{' , ',' ]

    CHECK_COUNT     = True
    CHECK_SYNTAX    = True

    '''
    def readInChunks(fileObj, chunkSize=2048):
        """
        Lazy function to read a file piece by piece.
        Default chunk size: 2kB.
        """
        while True:
            data = fileObj.read(chunkSize)
            if not data:
                break
            yield data

    f = open('bigFile')
    for chuck in readInChunks(f):
        do_something(chunk)
    '''

    if file_path.endswith(".csv"):
        file_path = file_path[:-4] + ".yaml"

    if denaliVariables["updateDebug"] == True:
        print "Updating CMDB with file:  %s" % file_path

    # read the data in
    if BATCH_MODE == False:

        try:
            updateFile = open(file_path, 'r')   # open the file for reading
            file_data = updateFile.read()       # read in the entire file contents
            updateFile.close()                  # close the file
        except:
            print "File access of %s failed." % file_path
            return False

    else:
        # No host counting done.  Syntax checks will be in-line during the update
        # routine above
        #
        #   !!! More work to do here !!!
        #
        #
        return True

    # put the file data in "lines" for easier handling
    file_data = file_data.splitlines()
    #print "file_data = %s" % file_data

    #
    #   All that needs to happen here is to loop through the file data and gather
    #   each host and each host's update data.  Store those pieces of data inside
    #   denaliVariables and then call updateListOfServers(denaliVariables) to
    #   handle the rest of the process.
    #

    # The serverList for denali should be empty.  It will be added to as the
    # update file is parsed.
    denaliVariables["serverList"] = []
    update_key = denaliVariables["updateKey"]

    # Loop through every line in the file, to separate host data and update CMDB
    # with it.
    for line in file_data:

        # Check #1: Is the hostname in the list of bad hosts?  If so, skip it
        #           and move on to the next host to process
        if hostName not in hostsRemove:

            # Check #2: See if the file's line starts with "host".  If so, it means
            #           a new host's data is about to be read.
            #
            #           Aside:  This means that the last host found in the file
            #                   isn't written to the database -- so check for the
            #                   count at the end to flush the data found.
            if (line.startswith(update_key[0]) or
                line.startswith(update_key[1]) or
                line.startswith(update_key[2])):

                # Check #6: If the hostData variable has data, it means the data
                #           from the previous host has completed, write it out
                #           and get this new host's data ready.
                if len(hostData) > 0:

                    # remove the trailing comma
                    if hostData[-1] == ',':
                        hostData = hostData[:-1]

                    # remove colons for MAC address
                    hostDataItems = hostData.split(',')
                    for (itemIndex, item) in enumerate(hostDataItems):
                        if item.lower().startswith("mac"):
                            item = item.replace(':', '')
                            hostDataItems[itemIndex] = item

                    # put it back together
                    hostData = ','.join(hostDataItems)
                    hostData = hostData.replace(':', '=')

                    if denaliVariables["updateDebug"] == True:
                        print "hostName = %s" % hostName
                        print "hostData = %s" % hostData

                    ccode = organizeUpdateParameters(denaliVariables, hostName, hostData)
                    if ccode == False:
                        # failure to massage the parameters
                        return False

                    denaliVariables["serverList"].append(hostName)

                    # decrement the host counter (meaning: the data has been written)
                    hostCount -= 1

                    # clear out the temporary data storage holder
                    hostData   = ''

                # process the hostname (put it correctly in the data)
                if ':' in line:
                    hostLine = line.split(':')
                elif '=' in line:
                    hostLine = line.split('=')

                hostName = hostLine[1].strip()

                # increment the host counter
                hostCount   += 1
                bracketCount = 0

            # Check #3: See if the line read in starts with a hash/pound sign
            #           or is completely empty.  In either case, completely ignore it.
            elif line.startswith('#') or len(line.strip()) == 0:
                continue

            # Check #4: See if the line starts with a space (or more)
            #           This means that it is indented and from a server host
            #           already found -- add the line's data to the variable
            #           to store it for later use.
            elif line.startswith(' ') or line.startswith('\t'):
                line = line.strip()

                # make sure any in-line comments on this line are removed
                if '#' in line:
                    hashLocation = line.find('#')
                    line = line[:hashLocation]

                    # if the comment was the entire line (with leading spaces), don't include it
                    if len(line.strip()) == 0:
                        continue

                # strip the line and remove unnecessary spaces
                line = line.strip()
                line = line.replace(" : ", ":")
                line = line.replace("  ", '')
                line = line.replace(" [", "[")
                line = line.replace("] ", "]")
                line = line.replace(" {", "{")
                line = line.replace("} ", "}")

                # add the line to the existing data (if there is any)
                if hostData == '' and line.count(':') > 0:
                    line = line.replace(":", "=")
                    hostData = line
                else:
                    if len(line) < 6:       # small length because []{} characters come on single
                                            # lines sometimes -- which is what this if -- then is
                                            # looking for
                        if hostData[-1] == ',' and line[0] not in bracketList:
                            # If the last character in the saved data is a comma _AND_ the first
                            # character in the new data isn't a bracket (or comma), then remove
                            # the comma from the saved data before putting new data on the end.
                            #
                            # This helps the data to be correctly presented so it can be turned
                            # into a proper dictionary for CMDB updates to understand.
                            hostData = hostData[:-1]

                    if line.count(':') == 1:
                        line = line.replace(":", "=")

                    elif line.count(':') > 1:
                        # multiple colons (IPv6 address?) -- only put quotes around the first colon
                        line = line.replace(":", "=", 1)

                    hostData += line

                # count the brackets -- for insertion of commas in the proper place(s)
                bracketCount += line.count('[')
                bracketCount += line.count('{')
                bracketCount -= line.count('}')
                bracketCount -= line.count(']')

                if bracketCount == 0 or hostData[-1] not in bracketList:
                    hostData += ','

            # Check #5: If all else fails, it means one of the following:
            #             - The line doesn't start with "host"
            #             - The line isn't a comment or empty
            #             - The line isn't indented for host data
            #           Most likely this is some kind of syntax error.
            #           Mark the host as bad.
            else:
                hostsRemove.append(hostName)

                if hostName in hostsGood:
                    hostsGood.remove(hostName)

    # Clear out the remaining host with a CMDB flush
    if hostCount > 0:
        hostData = hostData[:-1]

        # remove the trailing comma
        if hostData[-1] == ',':
            hostData = hostData[:-1]

        # remove colons for MAC address
        if denaliVariables["updateDebug"] == True:
            print "hostData (b) = %s" % hostData

        hostDataItems = hostData.split(',')
        for (itemIndex, item) in enumerate(hostDataItems):
            if item.lower().startswith("mac"):
                item = item.replace(':', '')
                hostDataItems[itemIndex] = item

        # put it back together
        hostData = ','.join(hostDataItems)
        hostData = hostData.replace(':', '=')

        if denaliVariables["updateDebug"] == True:
            print "hostData (a) = %s" % hostData

        # do the actual CMDB update
        ccode = organizeUpdateParameters(denaliVariables, hostName, hostData)
        if ccode == False:
            # failure to massage the parameters
            return False

        denaliVariables["serverList"].append(hostName)

        # set this to true -- for the initial pass
        refresh = True

        # loop through this if servers are removed -- refresh the "to do" serer list
        while (refresh == True):
            refresh = False
            ccode = updateListOfServers(denaliVariables)
            if ccode == False:
                (hostsGood, hostsRemove) = updateBadHost(hostName, hostsGood, hostsRemove)
                if denaliVariables["updateDebug"] == True:
                    api = denaliVariables["api"]
                    print "\nERROR:"
                    print "   STATUS: " + api.get_response_status()
                    print "   TYPE: " + str(api.get_error_type())
                    print "   MESSAGE: " + api.get_error_message()
                    print
                return False
            elif ccode == "refresh":
                refresh = True
                denaliVariables["updatePreview"] = True
            elif ccode == "quit":
                return False
            else:
                # update was successful
                pass

        hostCount -= 1
        hostData   = ''

    return True



##############################################################################
#
# convertCSVToYaml(denaliVariables, file_path)
#
#   This function converts a CSV file to YAML-like format to allow the denali
#   update functionality to work with it.
#
#   There are two things happening here:
#       (1) Creation of a data store (List) with the file contents to enable
#           the syntax checking to proceed.
#       (2) Creation of a yaml file with the csv file contents.
#

def convertCSVToYAML(denaliVariables, file_path):

    csvList    = []
    yaml_data  = ''
    key_column = ''

    with open(file_path) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            csvList.append(row)

    csvfile.close()

    if denaliVariables["updateMethod"] == "file":
        update_key = denaliVariables["updateKey"][0]
    else:
        update_key = denaliVariables["updateKey"]

    # determine the name of the key column
    for row in csvList:
        for key in row.keys():
            if update_key == "name":
                # The update_key will be "name" by default and it is possible that the
                # hostname column will be named "name" or "Host Name".  Account for that.
                if key.lower().startswith("host") or key.lower().startswith("name"):
                    key_column = key
                    break
            else:
                if key.lower().startswith(update_key):
                    key_column = key
                    break
        if len(key_column) > 0:
            break
    else:
        # no host-like name was found -- not good.
        print "Denali Syntax Error: \"%s\" column data required for the update file to function" % update_key
        return False

    # using the "key" column, organize and output the data
    # in a yaml-like format
    #
    # create a new file -- same name, different extension (.yaml) with the
    # newly organized YAML data that the update method wants to operating with

    # remove the csv extension, put yaml extension on
    file_path_new = file_path[:-4] + ".yaml"

    yamlFile=open(file_path_new, 'w')

    for (index, row) in enumerate(csvList):
        # write the "key" column out first
        yaml_data   += "%s : %s\n" % (key_column, csvList[index][key_column])
        yamlFile.write("%s : %s\n" % (key_column, csvList[index][key_column]))

        # write the data columns out now
        for item in row:
            if item != key_column:
                yaml_data   += "    %s : %s\n" % (item, csvList[index][item])
                yamlFile.write("    %s : %s\n" % (item, csvList[index][item]))

        yaml_data   += "\n"
        yamlFile.write("\n")

    yamlFile.close()

    return yaml_data



##############################################################################
#
# returnKeyAliasAndColumnName(denaliVariables, key)
#

def returnKeyAliasAndColumnName(denaliVariables, key):

    cmdb_keys = denali_search.cmdb_defs
    new_key   = ''

    for lineEntry in cmdb_keys["DeviceDao"]:
        #if denaliVariables["updateDebug"] == True:
        #    print "  devicedao line entry = %s" % lineEntry

        # determine if the key is equal to either the alias (lineEntry[0])
        # or the column print header (lineEntry[2])
        if lineEntry[0] == key or lineEntry[2] == key:
            if denaliVariables["updateDebug"] == True:
                print "\n  Found a match:  %s" % lineEntry[1]
                print "  DeviceDAO line entry = %s" % lineEntry
            new_key = [lineEntry[0], lineEntry[1], lineEntry[2]]

            # For searching, a relationship matters ilo_ip_address.ip_address
            # For updating, a relationship can _NOT_ be specified
            # -- remove any "dot" relationship
            location = new_key[1].find(".")
            if location == -1:
                return new_key
            else:
                new_key[1] = lineEntry[1][:location]
                return new_key[:location]
    else:
        return key



##############################################################################
#
# findKeyHostAlias(denaliVariables)
#

def findKeyHostAlias(denaliVariables):

    allowed_update_keys = [ 'name', 'serial', 'asset_id', 'device_id' ]

    key = returnKeyAliasAndColumnName(denaliVariables, denaliVariables["updateKey"])

    if key[0] not in allowed_update_keys:
        print
        print "Key submitted [%s], is not valid.  Use one of the following:" % key
        print allowed_update_keys
        return False

    # If a hostname is updated, make it easy by changing one of the first two columns
    # to say "host" instead of "name".  This will allow the documentation concerning
    # using an update file to continue to work as expected.
    if key[0] == "name" and key[1] == "name" and key[2] == "Host Name":
        key[1] = "host"

    # make sure the correct update key identifier is saved here
    denaliVariables["updateKey"] = key

    return True



##############################################################################
#
# validateUpdateFile(denaliVariables, file_path)
#
#   In this function the code checks the "update" file for a few things:
#       (1) Existance of the file
#       (2) File size
#           The code will see if the file size is large (> 64 MB).  If so the
#           code will use the count (#3 below) and determine the best "batch"
#           set of hosts to send in for updates (i.e., 1000 at a time?)
#       (3) Host count
#           The code will count the number of hosts in the file.
#       (4) Syntax
#           If there are quotation marks it will remove them.
#           If there are lines not indented correctly, it will throw a
#           syntax error and stop execution (identifying the line number
#           where the problem is located in the file).

def validateUpdateFile(denaliVariables, file_path):

    global BATCH_MODE
    global file_data
    global hostsGood
    global hostsRemove

    hostCount      = 0
    hostUpdateData = None

    hostName       = ''
    sqlParameter   = ''

    bracketList    = [ '[', '{' , ',' ]

    userEntertainment = [ '\\', '|', '/', '-', '.' ]        # '.' at the end in case it runs over
    userEntCounter    = 0

    # only turn one to "True", not both (happens only when debug is enabled)
    userEntSpinner    = False       # spinning cursor |/-\|, etc.
    userEntCounter    = False       # in-place counters for good/bad hosts

    # disable one (or more) of these to reduce time to check the file
    # this could come into play if the update file is _very_ large and
    # there is a significant delay going through the file to check the
    # syntax, etc. (syntax is the most time-consuming check)

    CHECK_EXISTANCE = True
    CHECK_FILE_SIZE = True
    CHECK_COUNT     = True
    CHECK_SYNTAX    = True

    if denaliVariables["updateDebug"] == True:
        print "Validating updates file:  %s" % file_path

    # check for the update_key - populate appropriate data locations
    ccode = findKeyHostAlias(denaliVariables)
    update_key = denaliVariables["updateKey"]
    if ccode == False:
        return False

    # Check #1:  existance
    if CHECK_EXISTANCE == True:
        if denaliVariables["updateDebug"] == True:
            print "  [1] - File existance check : ",

        if os.path.isfile(file_path) == False:
            if denaliVariables["updateDebug"] == True:
                print "Failed"

            print "File path (%s) not found" % file_path
            return False
        else:
            if denaliVariables["updateDebug"] == True:
                print "Succeeded"

    # Check #2:  file size
    if CHECK_FILE_SIZE == True:
        if denaliVariables["updateDebug"] == True:
            print "  [2] - File size check      : ",

        fileSize = os.path.getsize(file_path)

        if denaliVariables["updateDebug"] == True:
            print "Succeeded"

        if fileSize > 67108864:      # 64 MB
            # With a file size of 64 MB, and _if_ each host were updating everything
            # in the database at the same time, the approximate number of hosts here
            # would be 32,768 requesting to be updated at the same time (wow!  why
            # so many?)

            # Break up the file into managable chucks for updating
            # the CMDB in batches (chunks of 1000 per run?)
            BATCH_MODE = True
        else:
            # should already be False, but set it anyway
            BATCH_MODE = False

    # read the data in to be able to count the hosts; however, only count the
    # hosts if BATCH_MODE is False
    if CHECK_COUNT == True and BATCH_MODE == False:
        if denaliVariables["updateDebug"] == True:
            print "  [3] - Host count check     : ",

        try:
            updateFile = open(file_path, 'r')   # open the file for reading
            file_data = updateFile.read()       # read in the entire file contents
            updateFile.close()                  # close the file
        except:
            if denaliVariables["updateDebug"] == True:
                print "Failed"

            print "File access of %s failed." % file_path
            return False

        if denaliVariables["updateDebug"] == True:
            print "Succeeded"

    else:
        # No host counting done.  Syntax checks will be in-line during the update
        # routine above
        return True

    # if the file asked to be input is a CSV, change it to YAML format and then
    # write it back out with the same name, but with a .yaml
    if file_path.endswith(".csv"):
        file_data = convertCSVToYAML(denaliVariables, file_path)
        if file_data == False:
            return False


    # put the file data in "lines" for easier handling
    # Check #3 and #4:  host count/syntax
    if CHECK_SYNTAX == False:
        # only the count check is done
        file_data = file_data.splitlines()
        for (index, line) in enumerate(file_data):
            if line.startswith("host"):                 # check #3
                hostCount += 1

    else:
        if denaliVariables["updateDebug"] == True:
            if userEntCounter == True or userEntSpinner == True:
                print "  [4] - File syntax check    : "
            else:
                print "  [4] - File syntax check    : ",

        # count and syntax checks are done
        file_data = file_data.splitlines()

        # loop through every line in the file
        for line in file_data:
            if denaliVariables["updateDebug"] == True:
                if userEntCounter == True:
                    gLength = len(hostsGood)
                    bLength = len(hostsRemove)
                    print "\rGood hosts:  %d   Bad hosts:  %d" % (gLength, bLength),

            # Check and see if the host was marked 'bad' -- if so, skip the
            # rest of the syntax verification process for it
            if hostName not in hostsRemove:
                # get the hostname (if it's the first line)
                if (line.startswith(update_key[0]) or
                    line.startswith(update_key[1]) or
                    line.startswith(update_key[2])):

                    # host (:/=) hostname
                    if ':' in line:
                        hostLine = line.split(':')
                    elif '=' in line:
                        hostLine = line.split('=')

                    hostName = hostLine[1].strip()

                    if denaliVariables["updateKey"][0] != 'name':
                        originalDataName = "--" + denaliVariables["updateKey"][0]
                        # put this data on the end of the sql modified list(s)
                        # it will automatically be manipulated into the sql search parameter set.
                        if len(sqlParameter) == 0:
                            sqlParameter = hostName
                        else:
                            sqlParameter += ' OR %s' % hostName

                    # increment the host counter
                    hostCount += 1

                    # clear out the temporary storage holders
                    hostData     = ''
                    hostSubData  = None
                    bracketCount = 0

                # check for a full line of comments (ignore the whole line)
                # check for empty lines .. ignore them as well
                elif line.startswith('#') or len(line.strip()) == 0:
                    continue

                # see if the line starts with spaces
                elif line.startswith(' ') or line.startswith('\t'):
                    # replace all tabs with spaces
                    if line.startswith('\t'):
                        line.replace('\t', ' ')

                    # Make sure any in-line comments on this line are removed
                    # There are some identifiers (Column Names) that legitimately
                    # have a hash in them -- in those cases use the alias name to
                    # avoid having the line yanked.
                    if '#' in line:
                        hashLocation = line.find('#')
                        line = line[:hashLocation]

                        # if the comment was the entire line, don't include it
                        if len(line.strip()) == 0:
                            continue

                    bracketCount += line.count('[')
                    bracketCount += line.count('{')
                    bracketCount -= line.count('}')
                    bracketCount -= line.count(']')

                    # add the line to the existing data (if there is any)
                    hostData += ' ' + line

                    if bracketCount == 0:
                        # completed with attribute analysis (all gathered in a single line)

                        if hostSubData != None:
                            # multi-lined attributes/values
                            hostSubData += line.strip()
                            hostData = hostSubData
                            hostSubData = None
                        else:
                            # single-line attribute/value
                            hostData = line

                        #print "completed line = %s" % hostData

                        # find the colon
                        colonLocation = hostData.find(':')
                        key = hostData[:colonLocation].strip()
                        key_data = hostData[(colonLocation + 1):].strip()

                        ccode = validateParameterSyntax(denaliVariables, key, key_data, hostData)

                        if denaliVariables["updateDebug"] == True and userEntSpinner == True:
                            #print "%s" % userEntertainment[userEntCounter],
                            #sys.stdout.write("\r%s \x1b[K" % userEntertainment[userEntCounter])
                            #sys.stdout.write("%s\r" % userEntertainment[userEntCounter])
                            #sys.stdout.flush()
                            print "%s\r" % userEntertainment[userEntCounter],
                            userEntCounter += 1

                            if userEntCounter >= 4:
                                userEntCounter = 0

                        if ccode == False:
                            # parameter put in not validated -- mark the host as bad
                            hostsRemove.append(hostName)

                            # if the hostName is in the good list, remove it
                            if hostName in hostsGood:
                                hostsGood.remove(hostName)

                        else:
                            if hostName not in hostsGood:
                                hostsGood.append(hostName)

                    else:
                        # additional line(s) to add to the current data
                        if hostSubData == None:
                            hostSubData = line.strip()
                        else:
                            if hostSubData[-1] in bracketList or len(line.strip()) < 5:
                                hostSubData += ' ' + line.strip()
                            else:
                                hostSubData += ',' + line.strip()
                else:
                    # - not a host started line
                    # - not a comment line
                    # - not a space started line
                    # This line is most likely a syntax error.  Mark this host as bad.
                    if len(hostName) == 0:
                        if line.find(':') != -1:
                            hostName = line.split(':')[1].strip()
                        else:
                            hostName = 'Unknown'
                    hostsRemove.append(hostName)
                    if hostName in hostsGood:
                        hostsGood.remove(hostName)

                    # At this point, all further checks will fail -- which is a litte
                    # ugly, but ...
                    # The summary at the end will print only one host -- the one
                    # found with the syntax error.  This means that if there are multiple
                    # hosts with errors, they will have to be addressed one at a time
                    # before denali will allow the list through.  Painful.
                    if denaliVariables["updateDebug"] == True:
                        print
                        print "Denali Error: A initial hostname or device was not found to start with the submitted"
                        print "              update key [%s].  For that reason, Denali has stopped execution." % denaliVariables["updateKey"][0]
                        print

    # add hosts to sql parameters
    if len(sqlParameter) > 0:
        denaliVariables["sqlParameters"].append([originalDataName,sqlParameter])
        denaliVariables["sqlParameters"] = denali_utility.processSQLParameters(denaliVariables)

    if denaliVariables["updateDebug"] == True and userEntCounter == False and userEntSpinner == False:
        if len(hostsRemove) > 0:
            print "Failed"
        else:
            print "Succeeded"

    if denaliVariables["updateDebug"] == True:
        gHosts = len(hostsGood)
        bHosts = len(hostsRemove)

        print "Number of Hosts Checked = %d" % hostCount
        print "  Bad Hosts  (%4d) = %s" % (bHosts, hostsRemove)
        print "  Good Hosts (%4d) = %s\n" % (gHosts, hostsGood)

    if len(hostsRemove) > 0:
        return False

    return True



##############################################################################
#
# updateBadHost(hostName, hostsGood, hostsRemove)
#
#   This function takes a host (hostName) off the good list and puts it on
#   the bad list.  It then returns both lists.
#

def updateBadHost(hostName, hostsGood, hostsRemove):

    for (index, host) in enumerate(hostsGood):
        if host == hostName:
            hostsGood.pop(index)
            hostsRemove.append(hostName)
            break

    return (hostsGood, hostsRemove)



##############################################################################
#
# validateRollbackDirectory(denaliVariables)
#

def validateRollbackDirectory(denaliVariables):

    home_directory = denali_utility.returnHomeDirectory(denaliVariables)

    # check if environment variables are accessible
    if home_directory == '' or home_directory is None:
        # problem accessing environment variables -- set it to /tmp
        denaliVariables['rbLocation'] = "/tmp"
        return True
    else:
        rollback_directory = home_directory + "/.denali/rollback"

    if denaliVariables["rbLocation"] == '':
        # set it to default
        denaliVariables["rbLocation"] = rollback_directory
    else:
        rollback_directory = denaliVariables["rbLocation"]

    # validate the directory exists
    if os.path.exists(rollback_directory) == False:
        # failure -- the directory doesn't exist; try creating it
        try:
            os.makedirs(rollback_directory)
        except:
            # There is a possible condition here where the directory is created just after the
            # check and just before the creation code line.  This code does not take that into
            # account -- hopefully it doesn't happen (that would be weird).
            print "Error:  The rollback directory [ %s ] doesn't exist and can not be created." % rollback_directory
            return False

    # validate the directory is writable
    if os.access(rollback_directory, os.W_OK | os.X_OK | os.R_OK) == False:
        # failure -- the directory isnt writable
        print "Error:  The rollback directory [ %s ] isn't writable." % rollback_directory
        return False

    return True



##############################################################################
#
# createUpdateRollbackLog(denaliVariables)
#

def createUpdateRollbackLog(denaliVariables):

    # set the state variable for the log being written
    # it should only be written once -- this should take care of that
    if denaliVariables["rollbackWritten"] == False:
        denaliVariables["rollbackWritten"] = True
    else:
        return True

    current_time = datetime.datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
    date_time = datetime.datetime.now().strftime("%m-%d-%Y @ %H:%M:%S")

    rollbackFileName = denaliVariables["rbLocation"] + "/rollback_%s.rbl" % current_time

    count = 0
    while os.path.isfile(rollbackFileName) == True:
        # sleep for 1 second (to advance time and make the file name unique -- hopefully)
        time.sleep(1)
        current_time = datetime.datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
        rollbackFileName = denaliVariables["rbLocation"] + "/rollback_%s.rbl" % current_time
        count += 1

        # avoid a deadlock here -- if the count > 5, break out.
        if count > 5:
            # we've waited 5 seconds to create a unique name -- it hasn't happened; give up
            print "Error: Cannot create unique rollback log file -- time stamp conflicts."
            return False

    try:
        rbFile = open(rollbackFileName, 'w')
    except:
        print "Error:  Cannot open %s for writing." % rollbackFileName
        return False

    try:
        rbFile.write("############################   Denali CMDB Rollback Log File   ############################\n")
        rbFile.write("##\n")
        rbFile.write("##  Date / Time : %s\n" % date_time)
        rbFile.write("##\n")
        rbFile.write("##  Filename    : %s\n" % rollbackFileName)
        rbFile.write("##\n")
        rbFile.write("##  Below is a formatted update log file for Denali.  It shows the\n")
        rbFile.write("##  original settings of the database before the update was executed.\n")

        if denaliVariables["updateMethod"] != "attribute":
            rbFile.write("##  This file can be used to move the data back to its original\n")
            rbFile.write("##  value(s) should the need arise.\n")
            rbFile.write("##\n")
        else:
            rbFile.write("##  Attribute updates by file are not implemented in Denali as of the\n")
            rbFile.write("##  current time.\n")
            rbFile.write("##\n")
            rbFile.write("##  Because the attribute method of updating was used, this file\n")
            rbFile.write("##  can _NOT_ be used and is only useful as far as documenting the\n")
            rbFile.write("##  state of the attributes before the update was completed.\n")
            rbFile.write("##\n")

        rbFile.write("##  This log is written BEFORE the data is pushed to CMDB.  This is a preview of the\n")
        rbFile.write("##  possible changes that could happen if all updates are successfully recorded.\n")
        rbFile.write("##\n")
        rbFile.write("##\n")
        rbFile.write("##  Values submitted to Denali (to change CMDB with):\n")
        rbFile.write("##\n")

        # print out the hosts/values submitted for updating
        hostkeys = denaliVariables["updateParameters"].keys()
        if len(hostkeys) == 1 and hostkeys[0] == "all":
            # print the host name(s) for a "console" based update
            # make a table of the list of hosts where the update happened -- make it look semi-nice.
            maxlength = 0
            for hostname in denaliVariables["serverList"]:
                if len(hostname) > maxlength:
                    maxlength = len(hostname)

            maxlength += 2
            numHosts = 90 / maxlength

            hostCount = 0
            rbFile.write("##  ")
            for hostname in denaliVariables["serverList"]:
                rbFile.write("%s " % hostname.ljust(maxlength))
                hostCount += 1
                if hostCount > numHosts:
                    rbFile.write("\n##  ")
                    hostCount = 0

            rbFile.write("\n##\n")
            rbFile.write("##    Parameters submitted: %s\n" % denaliVariables["updateParameters"]["all"])
            rbFile.write("##\n##\n######\n")

        else:
            # print the host name for a "file" based update
            for hostname in hostkeys:
                rbFile.write("##        %s : %s\n" % (hostname, denaliVariables["updateParameters"][hostname]))

        rbFile.write("##\n")
        rbFile.write("##\n")
        rbFile.write("##  Original values (shown below) to reset CMDB to its prior state:\n")
        rbFile.write("##\n")

    except:
        print "Error:  Cannot write header information to %s" % rollbackFileName
        return False

    # print out the original values (before the update) -- a YAML-like format
    for host in denaliVariables["serverList"]:

        # get the dictionary keys (hostnames) for each parameter "set"
        hostKeys = denaliVariables["updateParameters"].keys()

        # (re)set the state variable for a hostname update
        hostnameUpdated = False

        # See if the hostname was updated -- if so, it takes special handling
        # to create the rollback log correctly.
        if len(hostKeys) == 1 and hostKeys[0] == "all":
            for (pIndex, parameter) in enumerate(denaliVariables["updateParameters"]["all"]):
                if parameter.startswith("name="):
                    hostnameUpdated = True
                    host_name = parameter[5:]
                    break
        else:
            for parameter in denaliVariables["updateParameters"][host]:
                if parameter.startswith("name="):
                    hostnameUpdated = True
                    host_name = parameter[5:]
                    break

        # put the hostname "line" together
        if hostnameUpdated == True:
            hostName = "\nhost : %s\n" % host_name
        else:
            hostName = "\nhost : %s\n" % host.strip()


        # write the data out to the rbl file
        try:
        #if True:
            rbFile.write(hostName)

            if (len(hostKeys) == 1 and hostKeys[0] == "all") or denaliVariables['clearOverrides'] == True:
                if denaliVariables["updateMethod"] != "attribute":
                    # console method for creating the rollback log
                    for (pIndex, parameter) in enumerate(denaliVariables["updateParameters"]["all"]):
                        parameter = parameter.split('=')

                        if parameter[0] == "name": # and hostnameUpdated == True:
                            data = "    name : %s\n" % host.strip()
                        else:
                            index = denaliVariables["updateCategories"].index(parameter[0].strip())
                            data = "    %s : %s\n" % (parameter[0], denaliVariables["updatePreviewData"][host][pIndex])

                        rbFile.write(data)
                else:
                    # Attribute method for creating the rollback log
                    #
                    # This is a little different than the normal rollback entry.  It contains the YAML-like
                    # syntax as in the other method(s); however, additionally the file will contain a denali
                    # command (in a comment) to attempt and make attribute rollbacks as easy as possible.
                    attributeData = ''

                    if denaliVariables['clearOverrides'] == True:
                        host_index = host
                    else:
                        host_index = "all"

                    for (pIndex, parameter) in enumerate(denaliVariables["updateParameters"][host_index]):
                        # Create a denali CLI command to reset this data (there might be a whole slew
                        # of them, if the update scope was large; but it is what it is).  Something here
                        # is better than nothing.  Perhaps the set of denali commands could be scripted
                        # one after the other (shell script) -- that would make the rollback easier.
                        if denaliVariables['clearOverrides'] == True:
                            attribute_dict = {}
                            for attribute in denaliVariables['updateParameters'][host]:
                                attribute = attribute.split('=')
                                attribute_dict.update({attribute[0]:attribute[1]})

                            parameter = parameter.split('=')
                            data = "    %s : %s\n" % (parameter[0], attribute_dict[parameter[0]])

                            rbFile.write(data)

                            if len(attributeData) == 0:
                                attributeData  = "%s=%s" % (parameter[0], attribute_dict[parameter[0]])
                            else:
                                attributeData += ",%s=%s" % (parameter[0], attribute_dict[parameter[0]])
                        else:
                            # default attribute method
                            parameter = parameter.split('=')
                            data = "    %s : %s\n" % (parameter[0], denaliVariables["updatePreviewData"][host][pIndex])

                            rbFile.write(data)

                            if len(attributeData) == 0:
                                attributeData  = "%s=%s" % (parameter[0], denaliVariables["updatePreviewData"][host][pIndex])
                            else:
                                attributeData += ",%s=%s" % (parameter[0], denaliVariables["updatePreviewData"][host][pIndex])

                    rbFile.write("##\n")
                    rbFile.write("## Denali command to reset this host to its original state:\n")
                    data       = "##    denali.py --hosts=%s --updateattr=\"%s\"\n" % (host, attributeData)
                    rbFile.write(data)
                    rbFile.write("##\n")

            else:
                # file method for creating the rollback log
                for parameter in denaliVariables["updateParameters"][host]:
                    parameter = parameter.split('=')

                    if parameter[0] == "name": # and hostnameUpdated == True:
                        data = "    name : %s\n" % host.strip()
                    else:
                        index = denaliVariables["updateCategories"].index(parameter[0].strip())
                        if host in denaliVariables['updatePreviewData']:
                            data = "    %s : %s\n" % (parameter[0], denaliVariables["updatePreviewData"][host][(index - 1)])
                        else:
                            data = "    %s : Host not found in CMDB\n" % parameter[0]

                    rbFile.write(data)

        except:
            print "Denali rollback log error:  Cannot write original CMDB data to %s" % rollbackFileName

            # ?maybe? the file can be closed to preserve what (little) data was actually written
            rbFile.close()
            return False

    rbFile.close()

    return True



##############################################################################
#
# amendUpdateLog(denaliVariables, device, success_failure, message, param_dict)
#

def amendUpdateLog(denaliVariables, device, success_failure, message, param_dict):

    param_dict_modified = {}

    current_time = datetime.datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
    date_time = datetime.datetime.now().strftime("%m-%d-%Y @ %H:%M:%S")

    updateFileName = denaliVariables["rbLocation"] + "/denali_updateLog.log"

    try:
        # see if the file exists.  Yes?  Append.  No?  Create and write.
        if os.path.isfile(updateFileName) == True:
            ulFile = open(updateFileName, 'a')
        else:
            ulFile = open(updateFileName, 'w')
    except:
        print "Error:  Cannot open %s for writing." % updateFileName
        return False


    if denaliVariables['attributeUpdate'] == True:
        device_id = "device_groups"
    else:
        device_id = "devices"

    # the parameter_dictionary comes back from SKMS full of other information
    # before printing it -- strip it off to just the host and the data submitted
    if denaliVariables["updateMethod"] == "attribute":
        param_dict_modified.update({"devices":param_dict[device_id]})
        param_dict_modified.update({"attributes":param_dict["attributes"]})
    else:
        param_dict_modified.update({"key_value":param_dict["key_value"]})
        param_dict_modified.update({"field_value_arr":param_dict["field_value_arr"]})


    # see if the file has been written to for this round of updates.
    # No?  Put a demarkation line in the file (to help visually allow a log review
    # to know where the last update started (the logs are messy).
    if denaliVariables["updateLogWrite"] == False:
        denaliVariables["updateLogWrite"] = True
        ulFile.write("[%s] ==============================[Update Log Beginning of Session]==============================\n" % date_time)



    # update log file format for
    # time : success/failure : [hostname] : error message (if applicable)
    # time : success/failure : [hostname] : dictionary with update data

    if len(message) > 0:
        ulFile.write("%s : %s : [%s] : %s\n" % (current_time, success_failure, device.strip(), message))
    else:
        ulFile.write("%s : %s : [%s]\n"      % (current_time, success_failure, device.strip()))

    ulFile.write("%s : %s : [%s] : %s\n" % (current_time, success_failure, device.strip(), param_dict_modified))
    ulFile.close()


    return True



##############################################################################
#
# calculateUpdateSummary(denaliVariables, printData)
#

def calculateUpdateSummary(denaliVariables, printData):

    totalDevices     = 0
    updateDevices    = 0
    unchangedDevices = 0

    for row in printData:

        host = row[0].strip()

        if host[0] == '=':
            unchangedDevices += 1
            totalDevices     += 1
        elif host[0] == '+':
            updateDevices    += 1
            totalDevices     += 1

    # update the denaliVariables data
    denaliVariables["updateSummary"].update({"totalDevices":totalDevices})
    denaliVariables["updateSummary"].update({"updateDevices":updateDevices})
    denaliVariables["updateSummary"].update({"unchangedDevices":unchangedDevices})

    return True



##############################################################################
#
# wildcardWarning(denaliVariables, hostName)
#
#   If the submitted device filter contains an asterisk, this routine is run
#   to warn the user of the potential consequences.
#

def wildcardWarning(denaliVariables, hostName):

    if denaliVariables['autoConfirm'] == True:
        print "All automated console script updates must be done without a wildcard."
        print "Cancelling remaining updates."
        return False

    print
    print colors.bold + colors.fg.yellow + "!!    " + colors.reset,
    print colors.bold + colors.fg.red    + "WARNING :" + colors.reset,
    print colors.bold + colors.fg.yellow + "                                                 !!" + colors.reset
    print colors.bold + colors.fg.yellow + "!!    " + colors.reset,
    print colors.bold + colors.fg.red    + "A request to update CMDB device data with a wildcard      " + colors.reset,
    print colors.bold + colors.fg.yellow + "!!" + colors.reset
    print colors.bold + colors.fg.yellow + "!!    " + colors.reset,
    print colors.bold + colors.fg.red    + "was issued.  This is potentially extremely dangerous to   " + colors.reset,
    print colors.bold + colors.fg.yellow + "!!" + colors.reset
    print colors.bold + colors.fg.yellow + "!!    " + colors.reset,
    print colors.bold + colors.fg.red    + "the database.                                             " + colors.reset,
    print colors.bold + colors.fg.yellow + "!!" + colors.reset
    print

    if hostName == '*':
        print "Device filter submitted:  %s" % hostName,
        if len(denaliVariables["sqlParameters"]) > 0:
            print "(All hosts with a filter --> %s" % denaliVariables["sqlParameters"]
        else:
            print "  (All network devices)"
    else:
        print "Device filter submitted:",
        if len(denaliVariables["sqlParameters"]) > 0:
            print "(All %s hosts with a filter --> %s" % (hostName, denaliVariables["sqlParameters"])
        else:
            print "  (All network devices)"
    print

    if denaliVariables["updateMethod"] == "console":
        print "Press <ENTER> to exit out of this process"
        stdin_backup = sys.stdin
        sys.stdin    = open("/dev/tty")
        answer       = raw_input("Enter 'I Agree' to proceed with the device update command: ")
        sys.stdin    = stdin_backup
        if answer != "I Agree":
            print "Update to all devices cancelled."
            return False
        else:
            # "I Agree" was typed -- do the command
            return True

    elif denaliVariables["updateMethod"] == "file":
        print "All file updates must be done on an individual server basis."
        print "Cancelling remaining updates."
        return False

    return False



##############################################################################
#
# doSourceOfRecordUpdate(denaliVariables)
#
#  _parameters: {"device_key"               : {"device_id":"61732"},
#                "new_source_of_record_key" : {"source_of_record_id":"1"},
#                "_object"                  : "DeviceDao",
#                "_method"                  : "changeSourceOfRecord",
#               }

def doSourceOfRecordUpdate(denaliVariables):

    red = colors.bold + colors.fg.lightred

    maxHostWidth   = 0
    sor_submitted  = int(denaliVariables['sorUpdateTo'])
    parameter_dict = {
                      'device_key'               : {},
                      'new_source_of_record_key' : {'source_of_record_id': ''}
                     }

    destinationString = denali_utility.sorTranslate(denaliVariables, sor_submitted, returnString=True)

    print ("\nDevices that will have their Source of Record Updated to " + red + "%s" % destinationString + colors.reset + ":\n")
    ccode = denali_commands.printGroupedHostnamesInColumns(denaliVariables, denaliVariables['serverList'])

    # get the maximum host width
    for host in denaliVariables['serverList']:
        hostWidth = len(host)
        if hostWidth > maxHostWidth:
            maxHostWidth = hostWidth

    maxHostWidth += 3

    if denaliVariables["autoConfirm"] == False:
        ccode = sorWarningMessage(denaliVariables, sor_submitted)
        if ccode == False:
            return False
    else:
        print

    api = denaliVariables["api"]

    for device in denaliVariables['serverList']:
        # build the parameter_dictionary
        parameter_dict['device_key'].update({'name' : device})
        parameter_dict['new_source_of_record_key'].update({'source_of_record_id' : int(sor_submitted)})

        print "%s: " % device.ljust(maxHostWidth),

        ccode = api.send_request("DeviceDao", "changeSourceOfRecord", parameter_dict)
        if ccode == True:
            # success
            print (colors.bold + colors.fg.lightgreen + "SUCCESS" + colors.reset)
        else:
            if api.get_error_message() == "Source of record for device is already CMDB.":
                print (colors.bold + colors.fg.lightred + "FAILURE" + colors.reset + "  (Source of record for device is already CMDB)")
            else:
                print (colors.bold + colors.fg.lightred + "FAILURE" + colors.reset)
                print "SKMS ERROR:"
                print "   STATUS  : "  + api.get_response_status()
                print "   TYPE    : "  + str(api.get_error_type())
                print "   MESSAGE : "  + api.get_error_message()
                print

    return True



##############################################################################
#
# sorWarningMessage(denaliVariables, sor)
#

def sorWarningMessage(denaliVariables, sor):

    red = colors.bold + colors.fg.lightred

    print
    print (red + "!! Warning !!" + colors.reset)

    if sor == 1:
        print "You are about to make a change that will delete database records from one or more SIS"
        print "databases.  This action is PERMANENT and cannot be undone.  Please confirm below that"
        print "you want to delete SIS records and change the Source of Record to CMDB."
    else:
        print "You are about to make a change that will add database records to a SIS Database.  Please"
        print "confirm below that you acknowledge the Source of Record change will occur."

    print
    print ("Enter '" + red + "I Agree" + colors.reset + "' to proceed with the SOR update process")
    print

    stdin_backup = sys.stdin
    sys.stdin    = open("/dev/tty")
    answer       = raw_input("   ==> ")
    sys.stdin    = stdin_backup

    print
    if answer != "I Agree":
        print "Update to all devices canceled."
        return False
    else:
        # "I Agree" was typed -- execute the command procedure
        return True
