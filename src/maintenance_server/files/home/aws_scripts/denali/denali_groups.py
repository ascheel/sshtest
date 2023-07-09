#############################################
#
# denali_groups.py
#
#############################################
#
#   This module contains the code to allow queries to retrieve and update
#   CMDB device groups (DeviceGroupDao)
#
#   Typically this type of logic would be handled in an external module for
#   denali.  However, it is included with a switch of its own to make it
#   feel more integrated.
#

import denali
import denali_location
import denali_search
import denali_utility

import os
import copy
import datetime
import subprocess

from denali_tty import colors


DEBUG       = False
interactive = False

##############################################################################
##############################################################################
#
# csrfWorkAround(denaliVariables, method, kva)
#

def csrfWorkAround(denaliVariables, method, kva):

    api = denaliVariables['api']

    # call recursively if failure is CSRF missing/invalid token
    message = api.get_error_message()
    if message.startswith("The CSRF token is either missing or invalid"):
        (element, skip_count) = sendGroupUpdateRequest(denaliVariables, method, kva)
        if element == -1:
            return (-1, -1)
        else:
            return (element, skip_count)

    return (-1, -1)



##############################################################################
#
# modifyHostGroupList(denaliVariables, group_list, action, print_result=True)
#

def modifyHostGroupList(denaliVariables, group_list, action, print_result=True):

    update_success    = colors.fg.lightgreen
    update_failure    = colors.fg.lightred
    group_list        = group_list.split(',')
    nr_failures       = 0

    for group in group_list:
        if action   == 'addgroup' or action == 'ag':
            method   = 'addDevices'
            message  = 'Adding hosts to group: %s' % group
            skipped  = 'skipped = already in the device group'
        if action   == 'delgroup' or action == 'dg':
            method   = 'removeDevices'
            message  = 'Removing hosts from group: %s' % group
            skipped  = 'skipped = not in the device group'

        # build the key_value_array to send
        key_value_array = {'device_group_key' : group,
                           'device_keys'      : denaliVariables['serverList']}

        (element, skip_count) = sendGroupUpdateRequest(denaliVariables, method, key_value_array)
        if element == -1:
            (element, skip_count) = csrfWorkAround(denaliVariables, method, key_value_array)
        if element == -1:
            api = denaliVariables["api"]
            print colors.bold + update_failure + "SKMS ERROR: " + colors.reset,
            print message
            print "\nERROR:"
            print "   STATUS  : " + api.get_response_status()
            print "   TYPE    : " + str(api.get_error_type())
            print "   MESSAGE : " + api.get_error_message()
            print
            nr_failures += 1
        else:
            if denaliVariables["autoConfirm"] == False and print_result == True:
                print message
                print "  All hosts updated   : " + colors.bold + update_success + "SUCCESSFULLY" + colors.reset
                print "  Host number updated : %d" % element
                print "  Host number skipped : %d   [%s]" % (skip_count, skipped)
                print

    if nr_failures > 0:
        return False

    return True



##############################################################################
#
# verifyGroupUpdate(denaliVariables, response_dict, method)
#
#   This function verifies if the history update was done correctly.  It does
#   this by looking at the returned dictionary from SKMS.
#

def verifyGroupUpdate(denaliVariable, response_dict, method):

    if method   == 'addDevices':
        element  = 'added_cnt'
    elif method == 'removeDevices':
        element  = 'removed_cnt'
    else:
        return -1, -1

    if element in response_dict:
        return (response_dict[element], response_dict['skipped_cnt'])
    else:
        return -1, -1



##############################################################################
#
# sendGroupUpdateRequest(denaliVariables, method, key_value_array)
#
#   Send the request off to update the group name with the hosts specified
#

def sendGroupUpdateRequest(denaliVariables, method, key_value_array):

    api = denaliVariables["api"]

    if denaliVariables["debug"] == True:
        print
        print "api                : %s" % api
        print "category           : %s" % 'DeviceGroupDao'
        print "method             : %s" % method
        print "parameterDictionary: %s" % key_value_array

    ccode = api.send_request('DeviceGroupDao', method, key_value_array)
    if ccode == True:
        response_dict = api.get_data_dictionary()

        # check to make sure the group update succeeded
        (element, skip_count) = verifyGroupUpdate(denaliVariables, response_dict, method)
        return (element, skip_count)
    else:
        return -1, -1



##############################################################################
# Req's for new device group:  [ device_group_type ]
#   (1) Service Cluster
#       a. Name         : name
#       b. Description  : description
#       c. Service      : service_id
#       d. Location     : location_id
#       e. IP Address   : ip_address_id
#
#   (2) NAS Cluster / SAN Array / Static Group
#       a. Name         : name
#       b. Description  : description
#
#   (3) Virtual Cluster
#       a. Name         : name
#       b. Description  : description
#       c. Location     : location_id
#
#   (4) Dynamic Group -- filter required, will get to later if needed

device_group_type = {
                        # Static Group
                        1 : {
                               'name'           : None,
                               #'description'    : None,
                            },

                        # SAN Array
                        3 : {
                               'name'           : None,
                               #'description'    : None,
                            },

                        # NAS Cluster
                        4 : {
                               'name'           : None,
                               #'description'    : None,
                            },

                        # Virtual Cluster
                        5 : {
                               'name'           : None,
                               #'description'    : None,
                               #'location_id'    : None,
                            },

                        # Service Cluster
                        6 : {
                               'name'           : None,
                               #'description'    : None,
                               #'service_id'     : None,
                               #'location_id'    : None,
                               #'ip_address_id'  : None,
                            },
                    }


##############################################################################
#
# interactiveGroupCreator(denaliVariables)
#
#   This function is called to interactive create a group.  It will walk the
#   user through the needed pieces of data.

def interactiveGroupCreator(denaliVariables):

    group_kva_data = {'field_value_arr':{}}

    def getGroupName(group_kva_data):
        name = ''
        while len(name) == 0:
            name = raw_input('  Enter group Name         :  ')
        group_kva_data['field_value_arr'].update({'name':name})

    def getGroupDescription(group_kva_data):
        description = ''
        description = raw_input('  Enter group description  :  ')
        group_kva_data['field_value_arr'].update({'description':description})

    def getGroupService(group_kva_data):
        service = ''
        service = raw_input('  Enter group Service/ID   :  ')
        group_kva_data['field_value_arr'].update({'service_id':service})

    def getGroupLocation(group_kva_data):
        location = ''
        location = raw_input('  Enter group Location/ID  :  ')
        group_kva_data['field_value_arr'].update({'location':location})

    def getGroupIPAddress(group_kva_data):
        ipaddress = ''
        ipaddress = raw_input('  Enter group IP Address   :  ')
        group_kva_data['field_value_arr'].update({'ip_address_id':ipaddress})

    print "Interactive mode entered"

    # device_group_type
    print "Enter a device_group_type from the following:"
    print " (1) Static"
    print " (3) SAN Array"
    print " (4) NAS Cluster"
    print " (5) Virtual Cluster"
    print " (6) Service Cluster (typical selection)"
    print

    dgt = 0
    while (dgt == 0):
        dgt = raw_input("Enter a device_group_type: ")
        if dgt.isdigit() == True:
            if int(dgt) < 0 or int(dgt) > 6 or int(dgt) == 2:
                print "Select 1, 3, 4, 5, or 6."
                dgt = 0
        else:
            print "Select 1, 3, 4, 5, or 6."
            dgt = 0

    dgt = int(dgt)
    print

    if dgt == 1:
        print "Static:"
        group_kva_data['field_value_arr'].update({'device_group_type':dgt})
        getGroupName(group_kva_data)
        getGroupDescription(group_kva_data)
    elif dgt == 2:
        print "Dynamic:"
        print "Dynamic group settings do not work at the moment; exiting code"
        return False
        #group_kva_data['field_value_arr'].update({'device_group_type':dgt})
        #getGroupName(group_kva_data)
        #getGroupDescription(group_kva_data)

    elif dgt == 3:
        print "SAN Array:"
        group_kva_data['field_value_arr'].update({'device_group_type':dgt})
        getGroupName(group_kva_data)
        getGroupDescription(group_kva_data)

    elif dgt == 4:
        print "NAS Cluster:"
        group_kva_data['field_value_arr'].update({'device_group_type':dgt})
        getGroupName(group_kva_data)
        getGroupDescription(group_kva_data)

    elif dgt == 5:
        print "Virtual Cluster:"
        group_kva_data['field_value_arr'].update({'device_group_type':dgt})
        getGroupName(group_kva_data)
        getGroupDescription(group_kva_data)
        getGroupLocation(group_kva_data)

    elif dgt == 6:
        print "Service Cluster:"
        group_kva_data['field_value_arr'].update({'device_group_type':dgt})
        getGroupName(group_kva_data)
        getGroupDescription(group_kva_data)
        getGroupService(group_kva_data)
        getGroupLocation(group_kva_data)
        getGroupIPAddress(group_kva_data)

    print
    return group_kva_data



##############################################################################
#
# addNewHostGroup(denaliVariables, group_data)
#

def addNewHostGroup(denaliVariables, group_data):

    global interactive

    update_success    = colors.fg.lightgreen
    update_failure    = colors.fg.lightred

    group_kva         = {}
    device_group_type = False

    if group_data == "Waiting":
        interactive = True
        group_kva = interactiveGroupCreator(denaliVariables)
        if group_kva == False:
            return False
    else:
        # gather submitted data for syntax verification
        group_data = group_data.split(',')

        for item in group_data:
            item = item.replace(':', '=')
            item = item.split('=')

            # Catch any/all syntax errors or other problems too numerous to
            # code around.
            try:
                if item[1][0] == '\'' or item[1][0] == '\"':
                    item[1] = item[1][1:]
                if item[1][-1] == '\'' or item[1][-1] == '\"':
                    item[1] = item[1][:-1]

                item[0] = item[0].strip()
                item[1] = item[1].strip()

                if item[0] == 'device_group_type' and item[1].isdigit() == True:
                    item[1] = int(item[1])

                group_kva.update({item[0]:item[1]})
            except:
                print "New Group Syntax error.  Group information supplied is incomplete or invalid [%s]" % group_data
                print "Try without any parameters attached to --newgroup for interactive mode."
                return False

        group_kva = {'field_value_arr':group_kva}

    group_kva = verifyNewGroupSyntax(denaliVariables, group_kva)
    if group_kva == False:
        return False

    ccode = createNewGroupRecord(denaliVariables, group_kva)
    if ccode == False:
        api = denaliVariables["api"]
        print colors.bold + update_failure + "SKMS ERROR: " + colors.reset,
        print "\nERROR:"
        print "   STATUS  : " + api.get_response_status()
        print "   TYPE    : " + str(api.get_error_type())
        print "   MESSAGE : " + api.get_error_message()
        print
        return False

    return True



##############################################################################
#
# verifyNewGroupCreation(denaliVariables, response_dict)
#

def verifyNewGroupCreation(denaliVariables, response_dict):

    update_success    = colors.fg.lightgreen
    update_failure    = colors.fg.lightred

    if 'primary_key_arr' in response_dict:
        if 'device_group_id' in response_dict['primary_key_arr']:
            device_group_id = response_dict['primary_key_arr']['device_group_id']
            print "New Group Creation :  " + colors.bold + update_success + "SUCCESSFULL" + colors.reset
            print "Device Group ID    :  %s" % device_group_id
            return True
        else:
            return False
    else:
        return False

    return False



##############################################################################
#
# createNewGroupRecord(denaliVariables, group_kva)
#

def createNewGroupRecord(denaliVariables, group_kva):

    api = denaliVariables["api"]

    if denaliVariables["debug"] == True:
        print
        print "api                : %s" % api
        print "category           : %s" % 'DeviceGroupDao'
        print "method             : %s" % 'createRecord'
        print "parameterDictionary: %s" % group_kva

    ccode = api.send_request('DeviceGroupDao', 'createRecord', group_kva)
    if ccode == True:
        response_dict = api.get_data_dictionary()

        # check to make sure the group update succeeded
        ccode = verifyNewGroupCreation(denaliVariables, response_dict)
        if ccode == True:
            return True
        return False
    else:
        return False



##############################################################################
#
# verifyNewGroupSyntax(denaliVariables, group_kva)
#

def verifyNewGroupSyntax(denaliVariables, group_kva):

    # Location needed to potentially re-run the script to gather
    # specific items from CMDB
    denali_script_location = denaliVariables['denaliLocation']

    accepted_dgt = device_group_type.keys()
    accepted_dgt.sort()

    # this one works -- exactly as is
    #{'device_group_type': 6, 'ip_address_id': '10.84.9.75', 'location': 'OR1',
    # 'service_id': 'Ethos DMA Cluster', 'description': 'Another test group', 'name': 'MikeH-Test1'}

    orig_group_kva = copy.deepcopy(group_kva)

    # Make sure device_group_type is defined -- based on this, the rest of the
    # checks will be determined
    if 'device_group_type' not in group_kva['field_value_arr'] or group_kva['field_value_arr']['device_group_type'] not in accepted_dgt:
        print "New group creation requires 'device_group_type' to be assigned."
        print "Accepted values are:"
        for value in accepted_dgt:
            print "  %s " % value,
        print
        return False

    checks_to_run = device_group_type[group_kva['field_value_arr']['device_group_type']].keys()

    # name check
    if 'name' in checks_to_run:
        if 'name' not in group_kva['field_value_arr'] or len(group_kva['field_value_arr']['name']) == 0:
            print "Failed Name syntax check."
            print "Required: 'name' key/value parameter not found."
            return False
        if DEBUG == True:
            print "Passed 'name' check"

    # description check
    if 'description' in checks_to_run:
        if 'description' not in group_kva['field_value_arr'] or len(group_kva['field_value_arr']['description']) == 0:
            print "Failed Description syntax check."
            print "Required: 'description' key/value parameter not found."
            return False
        if DEBUG == True:
            print "Passed 'description' check"

    # service_id check
    if 'service_id' in checks_to_run:
        if 'service' not in group_kva['field_value_arr'] and 'service_id' not in group_kva['field_value_arr']:
            print "Failed Service syntax check."
            print "Required: 'service' or 'service_id' key/value parameter not found."
            return False
        if 'service' in group_kva['field_value_arr']:
            if len(group_kva['field_value_arr']['service']) == 0:
                print "Failed Service syntax check."
                print "Required: 'service' key/value parameter empty."
                return False

            # Only 'service_id' is accepted by the WebAPI.  See if the entry is all digits, if so
            # assume this is the service_id.  If not, do a lookup on the text given to translate
            # the service name into a service ID.
            service = group_kva['field_value_arr']['service']
            result = subprocess.Popen([denali_script_location, "--dao=ServiceDao", "--fields=service_id",
                                       "--name=%s" % service, "--noheaders", "-o", "newline"],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result.wait()
            service_id = result.stdout.read().strip()
            print "service_id = %s" % service_id
            if service_id.isdigit() == False:
                print "Denali could not determine the proper Service ID for %s" % service
                print "Message returned: %s" % service_id
                return False

            # remove the existing key (not to be used for the update)
            group_kva['field_value_arr'].pop('service', None)

            # add the new data into the dictionary
            group_kva['field_value_arr'].update({'service_id':service_id})

        else:
            if len(group_kva['field_value_arr']['service_id']) == 0:
                print "Failed Service syntax check."
                print "Required: 'service_id' key/value parameter empty."
                return False
        if DEBUG == True:
            print "Passed 'service/service_id' check"

    # location_id check
    if 'location_id' in checks_to_run:
        if 'location' not in group_kva['field_value_arr'] and 'location_id' not in group_kva['field_value_arr']:
            print "Failed Location syntax check."
            print "Required: 'location' or 'location_id' key/value parameter not found."
            return False
        if 'location' in group_kva['field_value_arr']:
            if len(group_kva['field_value_arr']['location']) == 0:
                print "Failed Location syntax check."
                print "Required: 'location' key/value parameter empty."
                return False
            else:
                location = group_kva['field_value_arr']['location']
                if location not in denali_location.dc_location:
                    print "Failed Location syntax check:  Location [%s] not found" % location
                    return False
            location_id = denali_location.dc_location.index(location)

        else:
            if len(group_kva['field_value_arr']['location_id']) == 0:
                print "Failed Location syntax check."
                print "Required: 'location_id' key/value parameter empty."
                return False
            else:
                location_id = group_kva['field_value_arr']['location_id']
                if location_id > len(denali_location.dc_location) or len(denali_location.dc_location[location_id]) == 0:
                    print "Failed Location syntax check."
                    print "Improper location_id [%s] entered." % location_id
                    return False
        if DEBUG == True:
            print "Passed 'location/location_id' check"

    # ip_address_id check
    if 'ip_address_id' in checks_to_run:
        if 'ip_address' not in group_kva['field_value_arr'] and 'ip_address_id' not in group_kva['field_value_arr']:
            print "Failed IP Address syntax check."
            print "Required: 'ip_address' or 'ip_address_id' key/value parameter not found."
            return False
        if 'ip_address' in group_kva['field_value_arr']:
            if len(group_kva['field_value_arr']['ip_address']) == 0:
                print "Failed IP Address syntax check."
                print "Required: 'ip_address' key/value parameter empty."
                return False

            # Only 'ip_address_id' is accepted by the WebAPI
            ip_address = group_kva['field_value_arr']['ip_address']
            result = subprocess.Popen([denali_script_location, "--dao=IpAddressDao", "--fields=ip_address_id",
                                       "--ip_address=%s" % ip_address, "--noheaders", "-o", "newline"],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result.wait()
            ip_address_id = result.stdout.read().strip()
            if ip_address_id.isdigit() == False:
                print "Denali could not determine the proper IP Address ID for %s" % ip_address
                print "Message returned: %s" % ip_address_id
                return False

            # remove the existing key (not to be used for the update)
            group_kva['field_value_arr'].pop('ip_address', None)

            # add the new data into the dictionary
            group_kva['field_value_arr'].update({'ip_address_id':ip_address_id})

        else:
            if len(group_kva['field_value_arr']['ip_address_id']) == 0:
                print "Failed IP Address syntax check."
                print "Required: 'ip_address_id' key/value parameter empty."
                return False
        if DEBUG == True:
            print "Passed 'ip_address/ip_address_id' check"

    if interactive == True:
        print
        print "Command line for non-interactive entry:"
        group_text = str(group_kva['field_value_arr'])
        group_text = group_text[1:-1]
        group_text = group_text.replace('\'','')
        print "  denali --newgroup=\"%s\"" % group_text
        print

        # make sure the user wants this to be committed
        user_verify = raw_input("Commit this group to SKMS (y/n)? ")
        if user_verify.lower() == 'y' or user_verify.lower() == 'yes':
            return group_kva
        else:
            print "Group data not committed.  Exiting."
            return False

    return group_kva



##############################################################################
#
# returnGroupList(denaliVariables)
#

def returnGroupList(denaliVariables):

    # enable the query to run
    if denaliVariables['api'] is None:
        # this could mean that it is the first time the user/creduser has run denali today,
        # and because of this they aren't configured with a session file yet.  take care of
        # that now.
        ccode = denali_utility.oooAuthentication(denaliVariables)
        if ccode == False:
            return False
        denali_utility.retrieveAPIAccess(denaliVariables)

    ccode = createServerListFromArbitraryQuery(denaliVariables, 'DeviceGroupDao')
    return ccode



##############################################################################
#
# createServerListFromArbitraryQuery(denaliVariables)
#
#   This function has one purpose -- take a generic query and create a list
#   of servers from it.  The return list will be placed in denaliVariables["serverList"]
#   for use by the calling function.  Typically external modules will call this
#   to get a list of hosts they will operate on with new queries or other text/data
#   manipulation.
#
#   The query submitted can have "*" for the host list or any arbitrary set of
#   SQL parameters designed to find specific hosts.
#

def createServerListFromArbitraryQuery(denaliVariables, searchDao='DeviceDao'):

    origDeviceList = denaliVariables["serverList"]

    # If the 'api' variable is None, it means that the SKMS library hasn't been
    # accessed yet.  Do that now so validateDeviceList will succeed.
    if denaliVariables['api'] is None:
        denali_utility.retrieveAPIAccess(denaliVariables)

    # STEP 1: save the current state
    saveDefault = denaliVariables["defaults"]
    saveMethod  = denaliVariables["method"]
    saveFields  = denaliVariables["fields"]
    saveDao     = denaliVariables["searchCategory"]
    saveTrunc   = denaliVariables["textTruncate"]
    saveWrap    = denaliVariables["textWrap"]
    saveSQLMod  = denaliVariables["sqlParameters"]
    saveServer  = denaliVariables["serverList"]

    # STEP 2: set the values to do this query
    # remove default setting (showing or not 'decommissioned' hosts) -- leave as set
    # in the submitted query
    #denaliVariables["defaults"] = True
    denaliVariables["method"]   = "search"

    if denaliVariables['attributeUpdate'] == True:
        denaliVariables["fields"] = "name"
    else:
        if searchDao == "DeviceGroupDao":
            denaliVariables["fields"] = "name,device.name"
        else:
            denaliVariables["fields"] = "name"

    denaliVariables["searchCategory"] = searchDao
    denaliVariables["textTruncate"]   = False
    denaliVariables["textWrap"]       = False

    if len(denaliVariables["sqlParameters"]) > 0:
        denaliVariables["sqlParameters"] = denali_utility.validateSQL(denaliVariables)
    else:
        denaliVariables["sqlParameters"] = ''

    #dao = "DeviceDao"
    dao = searchDao

    # STEP 3: build the sql query with the given hosts, and get the results
    (sqlQuery, wildcard) = denali_search.buildGenericQuery(denaliVariables)

    sqlQuery = dao + ':' + sqlQuery
    denaliVariables["serverList"] = []

    counter = 0
    loop    = True

    while loop == True:
        respDictionary = denali_search.constructSQLQuery(denaliVariables, sqlQuery, False)
        (printData, overflowData) = denali_search.generateOutputData(respDictionary, denaliVariables)

        # get the page number out
        if "paging_info" in respDictionary["data"]:
            currentPage  = respDictionary["data"]["paging_info"]["current_page"]
            lastPage     = respDictionary["data"]["paging_info"]["last_page"]
            itemsPerPage = respDictionary["data"]["paging_info"]["items_per_page"]

            if currentPage <= lastPage:
                currentPage += 1

            if currentPage > lastPage:
                loop = False

            pageLocation = sqlQuery.find("PAGE")
            if pageLocation == -1:
                loop = False
            else:
                sqlQuery = sqlQuery[:pageLocation] + "PAGE %s, %s" % (currentPage, itemsPerPage)

        # failsafe counter -- just in case something weird happens,
        # the app/search won't hang here
        counter += 1
        if counter > 40:
            # the loop is out of control, break out of it
            loop = False

        # STEP 3a: pull the "good server names" out of the structure and put it in a list
        deviceList = []
        for row in printData:
            if len(row[0].strip()) > 0:
                deviceList.append(row[0].strip())

        # STEP 3b: store the completed list back in denaliVariables for the program to use
        #          A wild card host is considered invalid by the getAttributes method.
        #          It must be a _specific_ host, not a generic one.  This realistically
        #          cannot be enabled until the input of more than 1000 hosts is allowed at
        #          scale by the AppDev team.
        #           9/3/2015 -- Up to 5000 hosts are allowed on return.
        if denaliVariables['attributeUpdate'] == False:
            if searchDao == "DeviceGroupDao":
                item_index = 1
            else:
                item_index = 0
            for (index, group) in enumerate(printData):
                if len(denaliVariables['serverList']) == 0:
                    denaliVariables['serverList'] = str(printData[index][item_index]).strip()
                else:
                    denaliVariables['serverList'] += ',' + str(printData[index][item_index]).strip()
        else:
            if len(denaliVariables['serverList']) == 0:
                denaliVariables['serverList']  = ','.join(deviceList)
            else:
                denaliVariables['serverList'] += ','.join(deviceList)

    # STEP 4: reset to the original state
    denaliVariables["defaults"]       = saveDefault
    denaliVariables["method"]         = saveMethod
    denaliVariables["fields"]         = saveFields
    denaliVariables["searchCategory"] = 'DeviceDao'
    denaliVariables["textTruncate"]   = saveTrunc
    denaliVariables["textWrap"]       = saveWrap
    denaliVariables["sqlParameters"]  = saveSQLMod

    if len(denaliVariables["serverList"]) == 0:
        # no viable devices/hosts found
        return False

    return True
