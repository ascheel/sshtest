#! /usr/bin/env python

import os
from sys import stdout
import getpass
import datetime
import copy
import time
import math
import re
from shutil import copy
import struct
import socket

from multiprocessing import Process, Queue, Lock, Pipe, Value

import denali_arguments
import denali_authenticate
import denali_commands
import denali_location
import denali_search
import denali_update
import SKMS

from denali_tty import colors

#
# Utility module
#




##############################################################################
#
# debugOutput(denaliVariables, outputString)
#

def debugOutput(denaliVariables, outputString):

    if denaliVariables['debug'] == True:
        print outputString

    if denaliVariables['debugLog'] == True:
        # get the current date/time
        time     = datetime.datetime.now().strftime("%m/%d/%Y_%H:%M:%S%P")
        fileName = denaliVariables['debugLogFile']
        with open(fileName, "a") as logfile:
            logfile.write(time + " : " + outputString + '\n')



##############################################################################
#
# natural_sort(list_of_hosts, direction)
#
#   This is hopefully a good enough natural sort algorithm for use with denali.
#   Right now only the "-c sort" command makes use of it.
#

def natural_sort(list_of_hosts, direction):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ]
    return sorted(list_of_hosts, key = alphanum_key, reverse=direction)



##############################################################################
#
# pullOutHostsFromPrintData(denaliVariables, printData)
#

def pullOutHostsFromPrintData(denaliVariables, printData):

    oStream    = denaliVariables['stream']['output']
    columnData = denaliVariables['columnData']
    hostnames  = []

    for (cIndex, column) in enumerate(columnData):
        if column[1] == 'name':
            hostname_column = cIndex
            break
    else:
        # no hostname column found -- cannot report on hosts
        oStream.write("\nError: Problem finding hostnames in segmented printData.")
        return False

    for (rIndex, row) in enumerate(printData):
        hostnames.append(row[cIndex].strip())

    denaliVariables['serverList'] = hostnames

    return



##############################################################################
#
# covertPrintDataToResponseDictionary(denaliVariables, printData)
#

def covertPrintDataToResponseDictionary(denaliVariables, printData):

    oStream    = denaliVariables['stream']['output']
    columnData = denaliVariables['columnData']
    results    = []

    for (rIndex, row) in enumerate(printData):
        rowDict = {}
        for (cIndex, column) in enumerate(columnData):
            rowDict.update({column[1]:row[cIndex].strip()})
        results.append(rowDict)

    if len(results) == 0:
        # problem -- results need to be here to work
        oStream.write("\nError: Problem populating results dictionary.")
        return False

    host_count = len(denaliVariables['serverList'])
    respDict1  = {'status':'success', 'messages':[], 'error_type':'', 'data':{'results':[]}}
    respDict2  = {'paging_info':{'last_page':1, 'current_page':1, 'items_per_page':host_count, 'item_count':host_count}}

    respDict1['data'].update(respDict2)
    respDict1['data']['results'] = results

    return respDict1



##############################################################################
#
# validateSQL(denaliVariables)
#

def validateSQL(denaliVariables):

    # build a temporary list to send in to the validator
    tempObjects  = []
    tempValues   = []
    tempCombined = []

    # validate the SQL parameters are valid (object name/value combination)
    for parm in denaliVariables["sqlParameters"]:
        if parm[0].startswith("--"):
            tempObjects.append(parm[0])

            if len(parm) > 1:
                tempValues.append(parm[1])
            else:
                print "Denali Syntax Error: SQL parameter value is empty for [\"%s\"]" % parm[0]
                print "                     Parameter is dropped from sql modifier list."
                # if the corresponding object isn't removed, then it creates a scenario where the
                # entirety of the CMDB is searched through (all objects) -- which is like _not_
                # what the user asked for.  In this case, it just removes a single modifier and
                # does the query without it.
                tempObjects.pop()
        else:
            # MRASEREQ-41586
            if denaliVariables['debug'] == True:
                print "Denali Syntax Error: SQL parameter name entered without double dash [\"%s\"]" % parm[0]

    # This is not a perfect check.  It makes sure there are objects and that the
    # number of sql objects matches the number of sql object values.  These could
    # be empty if there are syntax errors passed through the command line.
    #
    # The downside here is that a carefully crafted command line with multiple
    # syntax errors in it could cause unexpected data returns ("wait, I didn't ask
    # for that -- why did that show up?").  That's why the above messages will be
    # displayed when these types of errors are identified (hope the user pays close
    # attention).
    if len(tempObjects) > 0 and (len(tempObjects) == len(tempValues)):
        # load the tempObject list into the variable definition
        denaliVariables["sqlParameters"] = tempObjects

        # send it off to be validated and un-aliased
        denaliVariables["sqlParameters"] = (denali_arguments.validateSQLParameters(denaliVariables)).split(',')

        # reshuffle the objects and values together into the List of Lists
        for (index, parm) in enumerate(denaliVariables["sqlParameters"]):
            if parm == "location_id":
                tempValues[index] = denali_search.locationDataReturn(denaliVariables, tempValues[index])
                if tempValues[index] == False:
                    return False

            tempCombined.append([parm, tempValues[index]])

        # assign the fixed up list back to the denaliVariables location
        denaliVariables["sqlParameters"] = tempCombined
        denaliVariables["sqlParameters"] = denali_search.buildSqlParmQuery(denaliVariables)
    else:
        denaliVariables["sqlParameters"] = ''

    return denaliVariables['sqlParameters']



##############################################################################
#
# createServerListFromArbitraryQuery(denaliVariables, searchDao='DeviceDao', fields='name')
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

def createServerListFromArbitraryQuery(denaliVariables, searchDao='DeviceDao', fields='name'):

    origDeviceList = denaliVariables["serverList"]

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
    #denaliVariables["defaults"]       = True
    denaliVariables["method"]         = "search"
    denaliVariables["fields"]         = fields
    denaliVariables["searchCategory"] = searchDao
    denaliVariables["textTruncate"]   = False
    denaliVariables["textWrap"]       = False

    if len(denaliVariables["sqlParameters"]) > 0:
        denaliVariables["sqlParameters"] = validateSQL(denaliVariables)
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

        # save the response dictionary
        if len(denaliVariables['responseDictionary']):
            denaliVariables['responseDictionary']['data']['results'].extend(respDictionary['data']['results'])
        else:
            denaliVariables['responseDictionary'] = respDictionary

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
        denaliVariables["serverList"] += deviceList

    # STEP 4: reset to the original state
    denaliVariables["defaults"]       = saveDefault
    denaliVariables["method"]         = saveMethod
    denaliVariables["fields"]         = saveFields
    denaliVariables["searchCategory"] = saveDao
    denaliVariables["textTruncate"]   = saveTrunc
    denaliVariables["textWrap"]       = saveWrap
    denaliVariables["sqlParameters"]  = saveSQLMod

    if len(denaliVariables["serverList"]) == 0:
        # no viable devices/hosts found
        return False

    return True



##############################################################################
#
# expandServerList(denaliVariables)
#

def expandServerList(denaliVariables):

    if denaliVariables["debug"] == True:
        print "(b) expandServerList -- serverList = %s" % denaliVariables["serverList"]

    for device in denaliVariables["serverList"]:
        if ('*' in device or '?' in device or '%' in device) and denaliVariables["updateMethod"] == "console":
            # wildcard updates are allowed from the console (interactive) session
            # after agreeing to a warning message to continue
            ccode = denali_update.wildcardWarning(denaliVariables, device)
            if ccode == False:
                return False
            # it is possible that multiple comma separated hosts have wildcards
            # after the first, don't ask again, assume they are all accepted
            break

    # clean up the server list -- remove any garbage characters before processing
    for (index, device) in enumerate(denaliVariables["serverList"]):
        device = device.replace(' ', '')
        device = device.replace('\b', '')
        denaliVariables["serverList"][index] = device

    # assign the updated list to the serverList variable
    origDeviceList = denaliVariables["serverList"]

    # STEP 1: save the current state
    saveMethod = denaliVariables["method"]
    saveFields = denaliVariables["fields"]
    saveDao    = denaliVariables["searchCategory"]
    saveTrunc  = denaliVariables["textTruncate"]
    saveWrap   = denaliVariables["textWrap"]
    saveSQLMod = denaliVariables["sqlParameters"]

    # STEP 2: set the values to do this query
    denaliVariables["method"]         = "search"
    denaliVariables["fields"]         = "name"
    denaliVariables["searchCategory"] = "DeviceDao"
    denaliVariables["textTruncate"]   = False
    denaliVariables["textWrap"]       = False

    if len(denaliVariables["sqlParameters"]) > 0:

        # build a temporary list to send in to the validator
        tempObjects  = []
        tempValues   = []
        tempCombined = []

        for parm in denaliVariables["sqlParameters"]:
            tempObjects.append(parm[0])
            tempValues.append(parm[1])

        # load the tempObject list into the variable definition
        denaliVariables["sqlParameters"] = tempObjects

        # send it off to be validated and un-aliased
        denaliVariables["sqlParameters"] = denali_arguments.validateSQLParameters(denaliVariables).split(',')

        # reshuffle the objects and values together into the List of Lists
        for (index, parm) in enumerate(denaliVariables["sqlParameters"]):
            if parm == "location" or parm == "location_id":
                tempValues[index] = denali_search.locationDataReturn(denaliVariables, tempValues[index])
            tempCombined.append([parm, tempValues[index]])

        # assign the fixed up list back to the denaliVariables location
        denaliVariables["sqlParameters"] = tempCombined
        denaliVariables["sqlParameters"] = denali_search.buildSqlParmQuery(denaliVariables)

    else:
        denaliVariables["sqlParameters"] = ''

    dao = "DeviceDao"

    # STEP 3: build the sql query with the given hosts, and get the results
    (sqlQuery, wildcard) = denali_search.buildHostQuery(denaliVariables)
    sqlQuery = dao + ':' + sqlQuery
    respDictionary = denali_search.constructSQLQuery(denaliVariables, sqlQuery, False)
    if respDictionary == False:
        return False

    (printData, overflowData) = denali_search.generateOutputData(respDictionary, denaliVariables)
    if printData == False:
        return False

    # STEP 3a: pull the "good server names" out of the structure and put it in a list
    deviceList = []
    for row in printData:
        if len(row[0].strip()) > 0:
            deviceList.append(row[0].strip())

    denaliVariables["serverList"] = deviceList

    # STEP 4: reset to the original state
    denaliVariables["method"]         = saveMethod
    denaliVariables["fields"]         = saveFields
    denaliVariables["searchCategory"] = saveDao
    denaliVariables["textTruncate"]   = saveTrunc
    denaliVariables["textWrap"]       = saveWrap
    #denaliVariables["sqlParameters"]  = saveSQLMod

    if denaliVariables["debug"] == True:
        print "(a) expandServerList -- serverList = %s" % denaliVariables["serverList"]
        print "(a) len(serverList) = %d" % len(denaliVariables["serverList"])

    return True



##############################################################################
#
# retrieveAPIAccess(denaliVariables)
#

def retrieveAPIAccess(denaliVariables):

    # If a user hasn't specified the username in a .denali/config file, it is
    # likely this variable will be empty.  Assume the logged in user, and continue
    if len(denaliVariables['userName']) == 0:
        denaliVariables['userName'] = getpass.getuser()

    api = SKMS.WebApiClient(denaliVariables['userName'], '', denaliVariables['apiURL'], True)
    denali_authenticate.customizeSKMSClientStrings(denaliVariables, api)
    api.disable_ssl_chain_verification()
    denaliVariables["api"] = api



##############################################################################
#
# determineHostAlias(denaliVariables)
#
#   (1) See what hosts in the submitted list are valid (CMDB has them)
#   (2) From the ones that do not have a CMDB entry, see if they have a
#       valid alias.
#   (3) Combine the valid + alias lists into one
#

def determineHostAliases(denaliVariables):

    # only use the auto alias replacement if the host list size is < denaliVariables
    # 'aliasHostCount'.
    if len(denaliVariables['serverList']) > denaliVariables['aliasHostCount']:
        return

    # If the 'api' variable is None, it means that the SKMS library hasn't been
    # accessed yet.  Do that now so validateDeviceList will succeed.
    if denaliVariables['api'] is None:
        retrieveAPIAccess(denaliVariables)

    validateDeviceList(denaliVariables, '')

    # because this is a pre-cursor to the actual search, set it back to 'None'
    # so the code can properly work
    denaliVariables['api'] = None

    host_aliases = denali_commands.processArguments(denaliVariables, 'host', {})

    host_name_keys = host_aliases.keys()
    for host_name in host_name_keys:
        if host_aliases[host_name] != '':
            location = denaliVariables['serverList'].index(host_name)
            denaliVariables['serverList'][location] = host_aliases[host_name]

    return



##############################################################################
#
# validateDeviceList(denaliVariables, initialFields)
#
#   This function expects only to be passed the denaliVariables variable as a
#   parameter.
#
#   A list of hosts/devices is given and that list is validated.  There are devices
#   in CMDB that do not exist (db2257.oak1, for example).  If that host is specifically
#   listed for an attribute query, then the entire query will fail.  In other words,
#   the hosts must be validated before submission (for some query types).
#
#   This function will do a "search" query against a list of hosts, returning only
#   the names of hosts that exist in the database.  That will be the validated list.
#
#   As a side note, this data can be used to answer a question posed a few times
#   about Denali:  44 devices are returned from a query where 60 were submitted; which
#   devices were not found?
#
#   The function does the following:
#       (1) Save the current query state
#       (2) Set the values for this interim query
#       (3) Execute the interim query (retrieve the data)
#           (a) Extract the viable host names (all that are included)
#           (b) Store this list of hosts names in denaliVariables["serverList"]
#       (4) Reset the query variables to their initial values
#       (5) Store the "host is not found" list in denaliVariables
#

def validateDeviceList(denaliVariables, initialFields):

    if denaliVariables['debug'] == True:
        print "\n++Entered validateDeviceList\n"

    origDeviceList = denaliVariables["serverList"]

    # PRE-STEP: Eliminate any wildcard-ed hosts from this check;
    #           only check hosts that were specifically named.

    returnedDevices    = []
    updatedDeviceList  = []
    wildcardDeviceList = []
    for (index, host) in enumerate(origDeviceList):
        if '*' not in host and '?' not in host:
            updatedDeviceList.append(host)
        else:
            wildcardDeviceList.append(host)

    # MRASETEAM-40488
    # This first check is used for secret store queries where the sql parameter(s)
    # length (and host) will be zero, so it returns without doing the query.
    if denaliVariables["getSecrets"] == True:
        if len(updatedDeviceList) == 0 and len(denaliVariables["sqlParameters"]) == 0:
            return True
    elif len(updatedDeviceList) == 0:
        # This part of the check applies to everything else: if there is no list of
        # hosts to query, just return.
        return True

    # STEP 1: save the current state
    saveDefault = denaliVariables["defaults"]
    saveMethod  = denaliVariables["method"]
    saveFields  = denaliVariables["fields"]
    saveDao     = denaliVariables["searchCategory"]
    saveTrunc   = denaliVariables["textTruncate"]
    saveWrap    = denaliVariables["textWrap"]
    saveSQLMod  = denaliVariables["sqlParameters"]
    saveServer  = denaliVariables["serverList"]

    # assign the updated list to the serverList variable
    # copy it -- or variable referencing will create problems
    denaliVariables["serverList"] = updatedDeviceList[:]


    # STEP 2: set the values to do this query
    # remove default setting (showing or not 'decommissioned' hosts) -- leave as set
    # in the submitted query
    #denaliVariables["defaults"]       = True
    denaliVariables["method"]         = "search"
    denaliVariables["fields"]         = "name"
    denaliVariables["searchCategory"] = "DeviceDao"
    denaliVariables["textTruncate"]   = False
    denaliVariables["textWrap"]       = False
    denaliVariables["sqlParameters"]  = processSQLParameters(denaliVariables)

    dao = "DeviceDao"

    # STEP 3: build the sql query with the given hosts, and get the results
    if len(updatedDeviceList) > 0:
        (sqlQuery, wildcard) = denali_search.buildHostQuery(denaliVariables)
    else:
        (sqlQuery, wildcard) = denali_search.buildGenericQuery(denaliVariables)

    sqlQuery = dao + ':' + sqlQuery

    counter = 0
    loop    = True

    while loop == True:
        respDictionary = denali_search.constructSQLQuery(denaliVariables, sqlQuery, False)
        if respDictionary == False:
            # no data returned from SKMS
            # without this, a python stack results (cannot iterate a 'bool' variable)
            denaliVariables["defaults"]       = saveDefault
            denaliVariables["method"]         = saveMethod
            denaliVariables["fields"]         = saveFields
            denaliVariables["searchCategory"] = saveDao
            denaliVariables["textTruncate"]   = saveTrunc
            denaliVariables["textWrap"]       = saveWrap
            denaliVariables["sqlParameters"]  = saveSQLMod
            denaliVariables["serverList"]     = saveServer

            return False

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
        #denaliVariables["serverList"] = deviceList + wildcardDeviceList
        denaliVariables["serverList"] += deviceList
        returnedDevices               += deviceList

    # STEP 4: reset to the original state
    denaliVariables["defaults"]       = saveDefault
    denaliVariables["method"]         = saveMethod
    denaliVariables["fields"]         = saveFields
    denaliVariables["searchCategory"] = saveDao
    denaliVariables["textTruncate"]   = saveTrunc
    denaliVariables["textWrap"]       = saveWrap
    denaliVariables["sqlParameters"]  = saveSQLMod
    denaliVariables["serverList"]     = saveServer

    # STEP 5: store the "not found" host list
    if len(updatedDeviceList) > 0:
        #invalidList = list(set(updatedDeviceList) - set(denaliVariables["serverList"]))
        invalidList = list(set(updatedDeviceList) - set(returnedDevices))
    else:
        invalidList = ''

    if denaliVariables["debug"] == True:
        print "orig device list     = Len(%d) : %s" % (len(origDeviceList), origDeviceList)
        print "wildcard device list = Len(%d) : %s" % (len(wildcardDeviceList), wildcardDeviceList)
        print "updated device list  = Len(%d) : %s" % (len(updatedDeviceList), updatedDeviceList)
        print "new device list      = Len(%d) : %s" % (len(deviceList), deviceList)
        print "invalid list         = Len(%d) : %s" % (len(invalidList), invalidList)
        print "\"serverList\"         = Len(%d) : %s" % (len(denaliVariables["serverList"]), denaliVariables["serverList"])

    if len(invalidList) > 0:
        # sort the list -- it looks ugly otherwise -- and store it
        invalidList.sort()
        denaliVariables["devicesNotFound"] = invalidList

        if denaliVariables["validateData"] == True:
            ccode = fillInDNFData(denaliVariables, initialFields)
            return True

    if len(invalidList) == len(updatedDeviceList) and len(deviceList) == 0:
        # no viable devices/hosts found
        return False

    return True



##############################################################################
#
# repopulateHostList(denaliVariables, printData, responseDictionary)
#
#   This function is meant to strip off the host names from a query, and put
#   them back into denaliVariables["serverList"].  This is needed with some
#   external queries (like nagios) because they only know of the hosts they're
#   given and cannot do wildcard searches.  In this case, SKMS does the search,
#   then those hosts are passed into the monitoring API for results.
#

def repopulateHostList(denaliVariables, printData, responseDictionary):

    host_column_number  = -1
    state_column_number = -1
    host_list           = []

    #print "responseDictionary = %s" % responseDictionary

    # save the response dictionary across skms queries
    if not denaliVariables['jsonResponseDict']:
        denaliVariables['jsonResponseDict'] = dict(responseDictionary)
    else:
        denaliVariables['jsonResponseDict']['data']['results'].extend(responseDictionary['data']['results'])

    # determine which column the hostname is in
    for (count, column) in enumerate(denaliVariables["columnData"]):
        if column[2] == 'Host Name' and host_column_number == -1:
            host_column_number = count
        if column[2] == 'Device State' and state_column_number == -1:
            state_column_number = count

    # pull the hostname from the row data already generated
    for row in printData:
        # If attributes are searched for, the hostname (except for the first attribute), will
        # be a zero-length string.  This empty-string is where the hostname normally would be
        # but isn't displayed if multiple attributes are shown.  So ... don't add zero-length
        # strings.
        if len(row[host_column_number].strip()):
            host_list.append(row[host_column_number].strip())

    # save the searched hostlist back in denaliVariables
    if denaliVariables['serverList'][-1] == 'denali_host_list':
        denaliVariables['serverList'].remove('denali_host_list')
        denaliVariables['serverList'].extend(host_list)
    else:
        denaliVariables['serverList'] = host_list

    # Add a marker on the end to know when to keep a list, or not.
    # Normally the serverList will come populated with whatever
    # the user has supplied (which could be wild-carded or ranged
    # hosts in among legitimate hosts).  This list should be ignore
    # completely and replaced by the SKMS returned host list.  This
    # marker is put on the end of a searched out list.  It is up to
    # the calling function to remove the final entry to use it
    # properly.
    denaliVariables['serverList'].append('denali_host_list')

    return



##############################################################################
#
# fillInDNFData(denaliVariables)
#
#   This function takes the list of DNFs (Devices Not Found) and makes row and
#   columns for them exactly as needed for printing (text, csv, etc.).  This
#   will only be used when --validate is entered as a commandline parameter.
#
#   The list of hosts is found here :  denaliVariables["devicesNotFound"]
#   The DNF data will be stored here:  denaliVariables["dnfPrintList"]
#

def fillInDNFData(denaliVariables, initialFields):

    columnData = []
    NOT_FOUND  = "N/A"

    denaliVariables["fields"] = denali_arguments.fieldSubstitutionCheck(denaliVariables, initialFields)
    (modFields, columnData)   = denali_search.determineColumnOrder(denaliVariables)

    for hostname in denaliVariables["devicesNotFound"]:
        data = []
        for column in columnData:
            left_justify_value = column[3]
            if column[2] == "Host Name":
                data.append(hostname.ljust(left_justify_value))
            else:
                data.append(NOT_FOUND.ljust(left_justify_value))
        denaliVariables["dnfPrintList"].append(data)

    return True



##############################################################################
#
# narrowHostListByDeviceService(denaliVariables)
#
#   The purpose of this function is to take a list of hosts presented, and
#   narrow them down to a single host from each device service.
#
#   The plan right now is for this function only to be called when the
#   getSecrets method is used -- to narrow in on hosts based on their device
#   service only.
#

def narrowHostListByDeviceService(denaliVariables):

    # Modify denaliVariables["serverList"] in this function and then
    # return true/false depending upon the result(s)

    # STEP 1: save the current state
    saveMethod = denaliVariables["method"]
    saveFields = denaliVariables["fields"]
    saveDao    = denaliVariables["searchCategory"]
    saveTrunc  = denaliVariables["textTruncate"]
    saveWrap   = denaliVariables["textWrap"]
    saveSQLMod = denaliVariables["sqlParameters"]

    # STEP 2: set the values to do this query
    denaliVariables["method"]         = "search"
    denaliVariables["fields"]         = "name,device_service.full_name"
    denaliVariables["searchCategory"] = "DeviceDao"
    denaliVariables["textTruncate"]   = False
    denaliVariables["textWrap"]       = False
    denaliVariables["sqlParameters"]  = processSQLParameters(denaliVariables)

    dao = "DeviceDao"

    # STEP 3: build the sql query with the given hosts, and get the results
    (sqlQuery, wildcard) = denali_search.buildHostQuery(denaliVariables)

    sqlQuery = dao + ':' + sqlQuery
    respDictionary = denali_search.constructSQLQuery(denaliVariables, sqlQuery, False)
    (printData, overflowData) = denali_search.generateOutputData(respDictionary, denaliVariables)

    if printData == False:
        return False

    # STEP 4: pull the "good server names" out of the structure and put it in a list

    # clear out the serverList and getSecretsDict (making them new here)
    denaliVariables["getSecretsDict"] = {}
    denaliVariables["serverList"]     = []

    for row in printData:
        if row[1].strip() not in denaliVariables["getSecretsDict"]:
            # store this in the dict like this:  device_service : hostname
            denaliVariables["getSecretsDict"].update({row[1].strip():row[0].strip()})

    # STEP 5: pull out the host name from the dictionary
    for device_service in denaliVariables["getSecretsDict"]:
        denaliVariables["serverList"].append(denaliVariables["getSecretsDict"][device_service])

    # STEP 6: reset to the original state
    denaliVariables["method"]         = saveMethod
    denaliVariables["fields"]         = saveFields
    denaliVariables["searchCategory"] = saveDao
    denaliVariables["textTruncate"]   = saveTrunc
    denaliVariables["textWrap"]       = saveWrap
    denaliVariables["sqlParameters"]  = saveSQLMod

    return True



##############################################################################
#
# separateDevicesByType(denaliVariables, deviceList, responseDictionary)
#
#   This function takes the serverList and returns a dictionary with each
#   device assigned to a specific separation.  For example, if the separation
#   is the location, then each device will be found within a dictionary key
#   of that location.
#

def separateDevicesByType(denaliVariables, deviceList, responseDictionary):

    debug             = False
    mod_deviceList    = []
    dl_dictionary     = {}
    dpc_separator     = ['dpc', 'name', 'host', 'hostname']
    separator_count   = (denaliVariables['pdshSeparate']['separator'].count(',') + 1)

    if debug == True:
        print "separator_count = %s" % separator_count

    # Allow only a single separator (one comma), reject multiple commas separators
    if separator_count > 2:
        # A single comma means 2 separators categories, two commas
        # means 3 categories, etc.
        print "Separation method [%s] currently not supported." % denaliVariables['pdshSeparate']['separator']
        return False

    # store the separator_count -- ensures the code uses the proper level of
    # indirection to send in the data
    denaliVariables['pdshSeparate'].update({'separator_count':separator_count})

    # Loop through the deviceList and put it in the correct format
    # for the next 'for' loop to process.  This part of the 'if' statement
    # is specifically for DPC separation.  Any CMDB data separation will
    # happen automatically via a query response (the 'else' associated with
    # the 'if' here)
    if denaliVariables['pdshSeparate']['separator'].lower() in dpc_separator:
        for device in deviceList:
            if device.endswith('.omniture.com') or device.endswith('.adobe.net'):
                device_short = device.rsplit('.', 2)[0]
            else:
                device_short = device

            if device_short.count('.') == 1:
                device_dpc = device_short.split('.')[1]
            elif device_short.count('.') == 2 and device.endswith('.ut1'):
                # make sure and handle any UT1 devices successfully (2 periods
                # with the dpc identifier at the end)
                device_dpc = 'ut1'
            else:
                # error condition -- need to see the device name to handle it
                print "pdsh separate device name error: %s" % device
                continue

            mod_deviceList.append([device, device_dpc])
    elif denaliVariables['pdshSeparate']['separator'].lower() == '_single_':
        # This identifier asks the code to put each host in a separate
        # category all by itself.  This was designed to work with the
        # --host_command switch because each host could potentially have
        # a separate command (or commands) to run (in parallel w/ PDSH).

        host_list = denaliVariables['hostCommands'].keys()
        for (index, host) in enumerate(host_list):
            # The category must be a string (.strip() is used against it)
            # In this case, it's just a counter, but that works too.
            if host == "active":
                continue
            mod_deviceList.append([host, str(index + 1)])
    else:
        # The array returned from generateOutputData is already correct
        # Just make sure it doesn't wrap (or it could alter the segments
        # needed -- improperly)
        denaliVariables["textWrap"]    = False
        (mod_deviceList, overflowData) = denali_search.generateOutputData(responseDictionary, denaliVariables)

        # If --verify is used, 4 columns are, by default, included.  This
        # will cause the 'for' loop below to have issues because that code
        # expects mod_deviceList to supply it ONLY the hostname and separator
        # column data.  Remove the extra columns here so that this function
        # works as expected.
        if denaliVariables['devServiceVerify']:
            name_column = None
            sep_column1 = None
            sep_column2 = None

            # Separator cannot be short-cuts/aliases, it must match
            separator = denaliVariables['pdshSeparate']['separator']

            # This feels a little unusual.  This is creating a new item in
            # denaliVariables as a single-use data storage location to meet
            # the input criteria for the alias function below.
            denaliVariables.update({'sep_data':separator})
            separator = denali_search.replaceAliasedNames(denaliVariables, 'sep_data')

            # find the 'name' column and separator column indexes
            for (index, column) in enumerate(denaliVariables['columnData']):
                if column[0] == 'name':
                    name_column = index
                    continue
                sep_dataList = separator.split(',')

                for sep_data in sep_dataList:
                    # With --verify, compare against the actual CMDB name, because
                    # any aliases will have been turned into these from just above.
                    if column[1].startswith(sep_data):
                        if sep_column1 is None:
                            sep_column1 = index
                            sep_dataList = sep_dataList[-1]
                            break
                        else:
                            sep_column2 = index
                            break

            # All specific separate data column index values need to populated for
            # the function to work correctly.  Check and make sure they are.  If not,
            # fail the request with debugging data to help.
            if (name_column is None or sep_column1 is None or
               (denaliVariables['pdshSeparate']['separator_count'] == 2 and sep_column2 is None)):
                print "Denali Error: Separator metadata problem. Execution stopped."
                print "  Debugging data for this issue:"
                print "    separator md = %s" % denaliVariables['pdshSeparate']
                print "    separator    = %s" % separator
                print "    name column  = %s" % name_column
                print "    sep column1  = %s" % sep_column1
                print "    sep column2  = %s" % sep_column2
                print "    columnData   = %s" % denaliVariables['columnData']
                return False

            # remake each data line to include only the name and separator column data
            for (index, host) in enumerate(mod_deviceList):
                if denaliVariables['pdshSeparate']['separator_count'] == 1:
                    new_hostData = [host[name_column], host[sep_column1]]
                elif denaliVariables['pdshSeparate']['separator_count'] == 2:
                    new_hostData = [host[name_column], host[sep_column1], host[sep_column2]]
                mod_deviceList[index] = new_hostData

    # At this point the List/array contains entries like this:
    #    [ ['hostname1', 'category1'], ['hostname2', 'category2'], ...]
    #
    # The first item in each set is always the device name.
    # The second item in each set is always the device separator category.
    #
    # Take the deviceList (in this format), and put it into a dictionary
    # of categories.

    # For a two item separator [hostname, category1, category2]:
    # The order of cat1, cat2 matters.  This means that cat1 is processed
    # first, and then cat2 is part of cat1.  If this needs to be changed,
    # then the order of the separator input needs to be swapped.

    # Single separator code -- easy, and straight-forward (keep this for now)
    #for item in mod_deviceList:
    #    if item[1].strip() in dl_dictionary:
    #        dl_dictionary[item[1].strip()].append(item[0].strip())
    #    else:
    #        dl_dictionary.update({item[1].strip():[item[0].strip()]})

    if debug == True:
        print "mod_deviceList  = %s" % mod_deviceList

    # Multi-separator code (for 1 or 2 separators in the list)
    for (mIndex, item_list) in enumerate(mod_deviceList):
        for (cIndex, category) in enumerate(item_list):
            # strip the category -- it comes straight from generateOutput
            # with spaces for printing built-in
            category = category.strip()

            # the separator_count doesn't have a -1 here because the hostname
            # wasn't added to the count -- so it is already -1.
            if cIndex < separator_count:
                # middle category
                write_host = False
            else:
                # final category
                write_host = True

            if cIndex == 0:
                # hostname -- assign it and move along
                hostname = category
                continue

            elif cIndex == 1:
                if write_host == True:
                    if category in dl_dictionary:
                        dl_dictionary[category].append(hostname)
                    else:
                        dl_dictionary.update({category:[hostname]})
                else:
                    # without a hostname to write, just verify that the
                    # category exists and move to the next one
                    if category not in dl_dictionary:
                        dl_dictionary.update({category:{}})
                if debug == True:
                    print "(1) dl_dictionary = %s" % dl_dictionary

            elif cIndex == 2:
                prevCategory = item_list[cIndex - 1].strip()
                if write_host == True:
                    if category in dl_dictionary[prevCategory]:
                        dl_dictionary[prevCategory][category].append(hostname)
                    else:
                        dl_dictionary[prevCategory].update({category:[hostname]})
                else:
                    # without a hostname to write, just verify that the
                    # category exists and move to the next one
                    if category not in dl_dictionary[prevCategory]:
                        dl_dictionary[prevCategory].update({category:{}})
                if debug == True:
                    print "(2) dl_dictionary = %s" % dl_dictionary

            else:
                # skip whatever this is
                continue

    if debug == True:
        print "dl_dictionary   = %s" % dl_dictionary

    return dl_dictionary



##############################################################################
#
# extractAttributeColumn(listData, columnNumber)
#

def extractAttributeColumn(listData, columnNumber):

    returnColumn = ''

    for row in listData:
        if returnColumn == '':
            returnColumn = row[columnNumber]
        else:
            returnColumn += "," + row[columnNumber]

    return returnColumn



##############################################################################
#
# genericColumnInsert(printData, denaliVariables, insertColumnNumber, newColumnData)
#

def genericColumnInsert(printData, denaliVariables, insertColumnNumber, newColumnData):

    addColumnData = denaliVariables["addColumnData"]

    columnWidth = newColumnData[3]

    for (index, row) in enumerate(printData):
        printData[index].insert(insertColumnNumber, addColumnData[index].ljust(columnWidth))

    # Column is inserted.
    # Merge the column header information (inside newColumnData) with
    # denaliVariables["columnData"]

    denaliVariables["columnData"].insert(insertColumnNumber, newColumnData)

    return printData



##############################################################################
#
# keyColumnInsert(printData, denaliVariables, insertColumnNumber, newColumnData, cKey="default")
#

def keyColumnInsert(printData, denaliVariables, insertColumnNumber, newColumnData, cKey="default"):

    addColumnData = denaliVariables["addColumnData"]
    columnWidth = newColumnData[3]

    for (index, row) in enumerate(printData):
        if cKey == "default":
            # the key is row[0], the default
            columnKey = row[0].strip()
        else:
            # the key is whatever column number is passed in
            columnKey = row[cKey].strip()

        if columnKey in addColumnData:
            printData[index].insert(insertColumnNumber, addColumnData[columnKey].ljust(columnWidth))
        else:
            printData[index].insert(insertColumnNumber, ''.ljust(columnWidth))

    # Column is inserted.
    # Merge the column header information (inside newColumnData) with
    # denaliVariables["columnData"]

    denaliVariables["columnData"].insert(insertColumnNumber, newColumnData)

    return printData



##############################################################################
#
# removeColumn(denaliVariables, printData, columnNumber)
#

def removeColumn(denaliVariables, printData, columnNumber):

    for row in printData:
        row.pop(columnNumber)

    denaliVariables["columnData"].pop(columnNumber)

    return printData



##############################################################################
#
# addUpdatePrintRows(denaliVariables, existingData, newData)
#
#   currentData is a List of Lists.  Each sub-List is a row of data to print
#   newData is a dictionary of Lists, keyed by hostName to make lookup easy.
#
#   This function takes the newData and inserts it into currentData with each
#   hostName coming after the currentData hostName.
#
#   This function was introduced with the --update/file switches so as to
#   provide a comparison of before/after data when an update is requested,
#   and as such, showing the data in tabular format (current server, and
#   updated server) seemed appropriate.
#
#   A "plus sign" is added to the host name if there is a difference between
#   the original data, and this new data
#
#   If the updated data doesn't change the original server's data, then an
#   "equal sign" is added.
#

def addUpdatePrintRows(denaliVariables, existingData, newData):

    combinedData  = []
    currentData   = []
    adjustedData  = []
    hostsToUpdate = []

    # counts for source of record information
    sisHosts   = 0
    cmdbHosts  = 0
    unkHosts   = 0

    #denaliVariables["updateHostsYes"] = []
    #denaliVariables["updateHostsNo"]  = []

    currentHostCount = 0
    deviceFound      = False

    # use copies of the data -- not the original data
    existingDataCopy = existingData[:]
    newDataCopy      = newData.copy()

    # modify the existing data by adding a space in front of the host name
    # this is for the '+' (update will happen) and '=' (no update/same data)
    for row in existingDataCopy:
        tempRow = []

        host = row[0].strip()
        host = ' ' + host

        for (index, column) in enumerate(row):
            if index == 0:      # host name location
                tempRow.append(host)
            else:
                tempRow.append(column.strip())

        currentData.append(tempRow)

    # compare the existingData with the newData to determine if a row
    # is different (changes requested) or not
    for (rowIndex, row) in enumerate(existingDataCopy):
        compareRow = []
        newRow     = []

        if denaliVariables["updateViewCount"] != -1 and len(denaliVariables["updateDevice"]) > 0:
            # user requested a device "view" from the current device (updateDevice)
            # once the outer loop reaches the current host, then start using the data
            if row[0].strip() != denaliVariables["updateDevice"] and deviceFound == False:
                continue
            else:
                # set the state variable to True (so the code doesn't skip other devices)
                deviceFound = True

                # increment the host counter
                currentHostCount += 1

        host = row[0].strip()

        # get the SOR data
        sorDB = denaliVariables["updateSOR"][host]

        # increment the counters for SOR
        if sorDB.find("SIS") != -1:
            sisHosts += 1
        elif sorDB.find("CMDB") != -1:
            cmdbHosts += 1
        else:
            # catch-all for everything else
            unkHosts += 1

        # put all column data in a list for comparison
        for column in row:
            compareRow.append(column.strip())

        if host in newDataCopy:
            # save the name before it is modified
            origHost = host

            # search the row for an empty string -- so it can be displayed properly
            if "''" in newDataCopy[host] or '""' in newDataCopy[host] or '' in newDataCopy[host]:
                for (dIndex, item) in enumerate(newDataCopy[host]):
                    if item == "''" or item == '""' or len(item) == 0:
                        newDataCopy[host][dIndex] = ""
                        emptyString = True
            else:
                emptyString = False

            if compareRow == newDataCopy[host]:
                # the rows are equivalent; no change affected
                hostsToUpdate.append(host)

                # add the host name on the "no" update list -- only for a full refresh
                if denaliVariables["updateViewCount"] == -1:
                    denaliVariables["updateHostsNo"].append(host)

                host = '='
            else:
                # the rows are different -- DB will be updated if approved
                hostsToUpdate.append(host)

                # add the host name on the "yes" update list -- only for a full refresh
                if denaliVariables["updateViewCount"] == -1:
                    denaliVariables["updateHostsYes"].append(host)

                host = '+'

            if emptyString == True:
                emptyString = False

                for (iIndex, item) in enumerate(newDataCopy[origHost]):
                    if len(item) == 0:
                        newDataCopy[origHost][iIndex] = "[EMPTY STRING]"

            for (index, column) in enumerate(newDataCopy[origHost]):
                if index == 0:      # modified host name (=/+) -- don't use origHost
                    newRow.append(host)
                else:
                    newRow.append(column)

            adjustedData.append(currentData[rowIndex])
            adjustedData.append(newRow)
        else:
            adjustedData.append(row)


        # only put the data together for as many devices as requested
        # in the update UI (typical is all devices)
        if denaliVariables["updateViewCount"] != -1:
            if currentHostCount >= denaliVariables["updateViewCount"]:
                break

    # Update the summary counters for source of record information
    denaliVariables["updateSummary"].update({"sisHostsSORCount":sisHosts})
    denaliVariables["updateSummary"].update({"cmdbHostsSORCount":cmdbHosts})
    denaliVariables["updateSummary"].update({"unknownHostsSORCount":unkHosts})

    return adjustedData



##############################################################################
#
# sorTranslate(denaliVariables, sorDestination, returnString=False)
#

def sorTranslate(denaliVariables, sorDestination, returnString=False):

    sor_records = {       '1'  : 'CMDB',
                          '4'  : 'DALLAS SIS',
                          '5'  : 'LONDON SIS',
                          '7'  : 'SINGAPORE SIS',
                          '8'  : 'OREGON SIS (PNW)',
                          '26' : 'ACC SIS',
    }

    sor_record_values = { 'CMDB'      : '1',
                          'DAL'       : '4',
                          'DA2'       : '4',
                          'DALLAS'    : '4',
                          'LON'       : '5',
                          'LON5'      : '5',
                          'LONDON'    : '5',
                          'SIN'       : '7',
                          'SIN2'      : '7',
                          'SINGAPORE' : '7',
                          'PNW'       : '8',
                          'OR1'       : '8',
                          'OREGON'    : '8',
                          'ACC'       : '26',
                          'VA7'       : '26',
    }

    sorDestination = str(sorDestination).upper()

    if sorDestination in sor_records:
        if returnString == False:
            return sorDestination
        else:
            return sor_records[str(sorDestination)]

    if sorDestination in sor_record_values:
        if returnString == False:
            return sor_record_values[sorDestination]
        else:
            return sor_records[sor_record_values[sorDestination]]

    print "Denali Error: Source of Record [%s] not found in SOR table.  Exiting." % sorDestination

    return -1



##############################################################################
#
# parsePowerNewlineFile(fileName)
#

def parsePowerNewlineFile(fileName):

    newlineDictionary = {}
    keys   = []
    values = []

    if os.path.isfile(fileName) != True:
        return False

    newlineFile = open(fileName, 'r')

    for (count, line) in enumerate(newlineFile):
        # assume line #0 is the key, and line #1+ contains the value(s)
        if count == 0:
            keys = line.strip().split(',')
        else:
            values.append(line.strip().split(','))

    newlineFile.close()
    newlineDictionary = dict(zip(keys, *values))

    return newlineDictionary



##############################################################################
#
# parseNewlineFile(fileName, columnCount)
#

def parseNewlineFile(fileName, columnCount):

    newlineDictionary = {}
    values = []

    if os.path.isfile(fileName) != True:
        return False

    newlineFile = open(fileName, 'r')

    columnIndex = 0

    for line in newlineFile:
        # the first column will be the dictionary 'key'
        if columnIndex == 0:
            key = line.strip()
        else:
            values.append(line.strip())

        columnIndex += 1

        if columnIndex > (columnCount - 1):
            columnIndex = 0
            newlineDictionary.update({key:values})
            values = []

    newlineFile.close()

    return newlineDictionary



##############################################################################
#
# processSQLParameters(denaliVariables)
#

def processSQLParameters(denaliVariables):

    if len(denaliVariables["sqlParameters"]) > 0:

        # build a temporary list to send in to the validator
        tempObjects  = []
        tempValues   = []
        tempCombined = []

        for parm in denaliVariables["sqlParameters"]:
            tempObjects.append(parm[0])
            tempValues.append(parm[1])

        # load the tempObject list into the variable definition
        denaliVariables["sqlParameters"] = tempObjects

        # send it off to be validated and un-aliased
        denaliVariables["sqlParameters"] = (denali_arguments.validateSQLParameters(denaliVariables)).split(',')

        # reshuffle the objects and values together into the List of Lists
        for (index, parm) in enumerate(denaliVariables["sqlParameters"]):
            tempCombined.append([parm, tempValues[index]])

        # assign the fixed up list back to the denaliVariables location
        denaliVariables["sqlParameters"] = tempCombined
        denaliVariables["sqlParameters"] = denali_search.buildSqlParmQuery(denaliVariables)
    else:
        denaliVariables["sqlParameters"] = ''

    return denaliVariables["sqlParameters"]



##############################################################################
#
# getDenaliResponse(denaliVariables, select, where, device)
#

def getDenaliResponse(denaliVariables, select, where, device, generic_response):

    PID         = os.getpid()
    time        = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    fileName    = '/tmp/denali-tmp-%s-%s.newline' % (PID, time)
    denaliVariables["tmpFilesCreated"].append(fileName)
    scriptLoc   = denaliVariables["denaliLocation"]

    authenticationParm = denali_arguments.returnLoginCLIParameter(denaliVariables)

    if authenticationParm == False:
        # punt?  How did we get this far then?  Manual authentication?
        return False

    try:
        os.remove(fileName)
    except:
        pass

    authenticationParm = authenticationParm[0] + '=' + authenticationParm[1]

    denali_call="%s %s --sql=\"DeviceDao:SELECT %s WHERE %s = '%s'\" -o %s --noheaders" % \
                 (scriptLoc, authenticationParm, select, where, device, fileName)

    os.system(denali_call)

    if generic_response == True:
        # count the columns submitted
        columnCount = select.count(',')
        columnCount += 1
        returnDict = parseNewlineFile(fileName, columnCount)
    else:
        returnDict = parsePowerNewlineFile(fileName)

    try:
        os.remove(fileName)
    except:
        pass

    return returnDict



##############################################################################
#
# returnHomeDirectory(denaliVariables)
#

def returnHomeDirectory(denaliVariables):

    home_directory = os.getenv("HOME")

    # If the home directory call returns nothing, there is a good chance this
    # is a rundeck execution.  In this case, assign the home directory to the
    # /tmp directory.

    if home_directory == '' or home_directory is None:
        home_directory = "/tmp/denali/"

        # create the directory
        # if the create fails, an exception will be thrown
        if not os.path.exists(home_directory):
            os.makedirs(home_directory)

    return home_directory



##############################################################################
#
# saveProfileDataItem(denaliVariables, daoDictionary, profile, profile_line)
#

def saveProfileDataItem(denaliVariables, daoDictionary, profile, profile_line):

    if len(profile) == 0:
        # bogus profile
        return daoDictionary

    daoline     = profile_line.split(':', 1)    # only the first ':'
    dao         = daoline[0].strip()
    value       = daoline[1].strip()
    value_split = value.split('=')              # only the first '='
    field       = value_split[0].strip()
    field       = field.replace('"', '')
    field       = field.replace("'", "")
    data_value  = value_split[1].strip()
    data_value  = data_value.replace('"', '')
    data_value  = data_value.replace("'", "")

    # Is the profile in the dictionary?  If not, add it in.
    if profile not in daoDictionary:
        daoDictionary.update({profile:{dao:{field:['', data_value]}}})
    else:
        # Is the dao in the dictionary?  If not, add it in.
        if dao not in daoDictionary[profile]:
            daoDictionary[profile].update({dao:{field:['', data_value]}})
        else:
            daoDictionary[profile][dao].update({field:['', data_value]})

    # Replace aliased name with cmdb value from denali_search.cmdb_defs[]
    # if an alias isn't found -- this means denali doesn't have a definition
    # for it, not that it doesn't exist in CMDB.  Trust the user at this point.
    if dao in denali_search.cmdb_defs:
        for line_item in denali_search.cmdb_defs[dao]:
            if line_item[0] == field:
                # alias found, assign the full CMDB data value
                if dao in daoDictionary[profile]:
                    daoDictionary[profile][dao].update({field:[line_item[1],data_value]})
                else:
                    daoDictionary[profile].update({dao:{field:[line_item[1],data_value]}})
                break
            elif line_item[1] == field:
                # cmdb data attribute found, assign the alias value
                if dao in daoDictionary[profile]:
                    daoDictionary[profile][dao].update({field:[line_item[0],data_value]})
                else:
                    daoDictionary[profile].update({dao:{field:[line_item[0],data_value]}})
                break

    return daoDictionary



##############################################################################
#
# configFile_debugOutput(file_attribute, file_value)
#

def configFile_debugOutput(file_attribute, file_value):

    print "%s : %s" % (file_attribute, file_value)



##############################################################################
#
# loadConfigFile(denaliVariables, denali_location, user_submitted=False)
#
#   denali_location is the [0] argument in argv -- the script execution path.
#

def loadConfigFile(denaliVariables, denali_location, user_submitted=False):

    # add timing data for config file read
    addElapsedTimingData(denaliVariables, 'loadConfigFile_start', time.time())

    genericVariable = []
    daoDictionary   = {}
    profile         = ''

    colorList = [
                    "black",      "red",
                    "green",      "orange",
                    "blue",       "purple",
                    "cyan",       "lightgrey",
                    "darkgrey",   "lightred",
                    "lightgreen", "yellow",
                    "lightblue",  "pink",
                    "lightcyan"
                ]

    if user_submitted == True:
        fileName = denali_location
    else:
        home_directory = returnHomeDirectory(denaliVariables)
        fileName = "%s/.denali/config" % home_directory
        dirName  = "%s/.denali" % home_directory

    if os.path.isfile(fileName) == True:

        # file exists, parse it for information
        for configLine in open(fileName):
            origConfigLine = configLine[:]
            configLine     = configLine.strip()

            if configLine.startswith('#') or configLine.strip() in ['\n', '\r\n']:
                # ignore the line
                continue

            if configLine.find('=') != -1:
                genericValue = configLine.split('=')
                genericValue[0] = genericValue[0].strip()
                genericValue[1] = genericValue[1].strip()
            elif configLine.startswith('profile') and configLine.find(':') != -1:
                # Any profile definition-start line will not have an equal sign
                # in it -- so this will work fine.
                profile = configLine.split(':')[1]
                continue
            else:
                continue

            # see if there are any spaces in the value
            spaceLocation = genericValue[1].find(' ')

            # look for profile data and store it in the daoDictionary
            # Example line:
            # DeviceDao:device_state="On Duty - In Service"
            if (origConfigLine.startswith('  ')    and
                origConfigLine.find('Dao') != -1   and
                origConfigLine.find(':')   != -1):
                daoDictionary = saveProfileDataItem(denaliVariables, daoDictionary, profile, origConfigLine)
                continue

            if genericValue[0].startswith("user"):
                if spaceLocation == -1:
                    denaliVariables["userName"] = genericValue[1]
                    if denaliVariables['debug'] == True:
                        configFile_debugOutput('user', genericValue[1])
                else:
                    # oops -- a space in the user name -- not correct
                    print
                    print "An invalid username was found (with a space character embedded)"
                    print "in the denali configuration file: %s" % fileName
                    print
                    print "Execution of Denali will be stopped."
                    return -1
                continue

            # MRASEREQ-41388
            if genericValue[0].startswith("cred"):
                # store the filename in the creds variable
                denaliVariables['credsFileUsed'] = genericValue[1].strip()
                if denaliVariables['debug'] == True:
                    configFile_debugOutput('creds', genericValue[1].strip())
                continue

            if genericValue[0].startswith("session_path"):
                if spaceLocation == -1:
                    denaliVariables["sessionPath"] = genericValue[1]
                    if denaliVariables['debug'] == True:
                        configFile_debugOutput('session_path', genericValue[1])

                else:
                    # oops -- a space in the session path was found -- not correct
                    print
                    print "An invalid session path was found (with a space character embedded)"
                    print "in the denali configuration file: %s" % fileName
                    print
                    print "Execution of Denali will be stopped."
                    return -1
                continue

            if genericValue[0].startswith("aliases_path"):
                if spaceLocation == -1:
                    denaliVariables["aliasLocation"] = genericValue[1]
                    if denaliVariables['debug'] == True:
                        configFile_debugOutput('aliases_path', genericValue[1])

                else:
                    # oops -- a space in the alias file path was found -- not correct
                    print
                    print "An invalid alias file path was found (with a space character embedded)"
                    print "in the denali configuration file: %s" % fileName
                    print
                    print "Execution of Denali will be stopped."
                    return -1
                continue

            if genericValue[0].startswith("log_path"):
                if spaceLocation == -1:
                    # strip off a trailing slash if present
                    if genericValue[1][-1] == '/':
                        genericValue[1] = genericValue[1][:-1]
                    denaliVariables['logPath'] = genericValue[1]
                    if denaliVariables['debug'] == True:
                        configFile_debugOutput('log_path', genericValue[1])

                else:
                    # oops -- a space in the log file path was found -- not correct
                    print
                    print "An invalid log file path was found (with a space character embedded)"
                    print "in the denali configuration file: %s" % fileName
                    print
                    print "Execution of Denali will be stopped."
                    return -1
                continue

            if genericValue[0].startswith("quiet_info") or genericValue[0].startswith("info_messages"):
                if spaceLocation == -1:
                    if genericValue[1].lower() == 'true':
                        genericValue[1] = True
                    elif genericValue[1].lower() == 'false':
                        genericValue[1] = False
                    else:
                        # default to 'True' -- show the messages
                        genericValue[1] = True
                    denaliVariables['showInfoMessages'] = genericValue[1]

                    if denaliVariables['debug'] == True:
                        configFile_debugOutput('showInfoMessages', genericValue[1])
                continue

            if genericValue[0].startswith("strip_hosts"):
                if spaceLocation == -1:
                    domains = genericValue[1].split(',')

                    for domain in domains:
                        domain = domain.replace("'", "")
                        domain = domain.replace("\"", "")
                        domain = domain.strip()
                        genericVariable.append(domain)

                    denaliVariables["domainsToStrip"] = genericVariable
                    if denaliVariables['debug'] == True:
                        configFile_debugOutput('strip_hosts', genericValue[1])

                else:
                    # oops -- a space in the alias file path was found -- not correct
                    print
                    print "An invalid domain strip syntax was found (with a space character embedded)"
                    print "in the denali configuration file: %s" % fileName
                    print
                    print "Execution of Denali will be stopped."
                    return -1
                continue

            if genericValue[0].startswith("api_url"):
                if spaceLocation == -1:
                    api_url = genericValue[1].strip()
                    api_url = api_url.replace("\"", "")
                    api_url = api_url.replace("'", "")
                    denaliVariables["apiURL"] = genericValue[1]
                    if denaliVariables['debug'] == True:
                        configFile_debugOutput('api_url', genericValue[1])
                    else:
                        if genericValue[1] != 'api.skms.adobe.com':
                            if genericValue[1].find('test') != -1 or genericValue[1].find('stage') != -1:
                                print "Non-production SKMS end-point requested: %s" % genericValue[1]

                else:
                    print
                    print "An invalid SKMS API URL was found (with a space character embedded)"
                    print "in the denali configuration file: %s" % fileName
                    print
                    print "Execution of Denali will be stopped."
                    return -1
                continue

            if genericValue[0].startswith("rollback_location"):
                if spaceLocation == -1:
                    denaliVariables["rbLocation"] = genericValue[1].strip()
                    if denaliVariables['debug'] == True:
                        configFile_debugOutput('rollback_location', genericValue[1])
                else:
                    print
                    print "An invalid path for rollback_location was given in the denali configuration"
                    print "file: %s" % fileName
                    print
                    print "Execution of Denali will be stoppped."
                    return -1
                continue

            if genericValue[0].startswith("rollback_days"):
                if spaceLocation == -1:
                    try:
                        denaliVariables["rbDaysToKeep"] = int(genericValue[1].strip())
                        if denaliVariables['debug'] == True:
                            configFile_debugOutput('rollback_days', genericValue[1])

                    except ValueError:
                        print
                        print "An invalid value for rollback_days was given (value not converted to interger)"
                        print "in the denali configuration file: %s" % fileName
                        print
                        print "Execution of Denali will be stopped."
                        return -1
                else:
                    print
                    print "An invalid value for rollback_days was given (with a space character embedded)"
                    print "in the denali configuration file: %s" % fileName
                    print
                    print "Execution of Denali will be stopped."
                    return -1
                continue

            if genericValue[0].startswith("update_change_color"):
                if spaceLocation == -1:
                    if genericValue[1].strip() in colorList:
                        denaliVariables["updateColorYes"] = genericValue[1].strip()
                        if denaliVariables['debug'] == True:
                            configFile_debugOutput('update_change_color', genericValue[1].strip())
                    else:
                        print "Color requested that wasn't in the list."
                        print "Accepted colors: %s" % colorList
                else:
                    print
                    print "An invalid color designation was given in the denali configuration"
                    print "Default colors will be used."
                    print
                continue

            if genericValue[0].startswith("update_nochange_color"):
                if spaceLocation == -1:
                    if genericValue[1].strip() in colorList:
                        denaliVariables["updateColorNo"] = genericValue[1].strip()
                        if denaliVariables['debug'] == True:
                            configFile_debugOutput('update_nochange_color', genericValue[1].strip())
                    else:
                        print "Color requested that wasn't in the list."
                        print "Accepted colors: %s" % colorList
                else:
                    print
                    print "An invalid color designation was given in the denali configuration"
                    print "Default colors will be used."
                    print
                continue

            if genericValue[0].startswith("monitor_ok_color"):
                if spaceLocation == -1:
                    if genericValue[1].strip() in colorList:
                        denaliVariables["mon_ok"] = genericValue[1].strip()
                        if denaliVariables['debug'] == True:
                            configFile_debugOutput('monitor_ok_color', genericValue[1].strip())
                    else:
                        print "Color requested that wasn't in the list."
                        print "Accepted colors: %s" % colorList
                else:
                    print
                    print "An invalid color designation was given in the denali configuration"
                    print "Default colors will be used."
                    print
                continue

            if genericValue[0].startswith("monitor_critical_color"):
                if spaceLocation == -1:
                    if genericValue[1].strip() in colorList:
                        denaliVariables["mon_critical"] = genericValue[1].strip()
                        if denaliVariables['debug'] == True:
                            configFile_debugOutput('monitor_critical_color', genericValue[1].strip())
                    else:
                        print "Color requested that wasn't in the list."
                        print "Accepted colors: %s" % colorList
                else:
                    print
                    print "An invalid color designation was given in the denali configuration"
                    print "Default colors will be used."
                    print
                continue

            if genericValue[0].startswith("monitor_warning_color"):
                if spaceLocation == -1:
                    if genericValue[1].strip() in colorList:
                        denaliVariables["mon_warning"] = genericValue[1].strip()
                        if denaliVariables['debug'] == True:
                            configFile_debugOutput('monitor_warning_color', genericValue[1].strip())
                    else:
                        print "Color requested that wasn't in the list."
                        print "Accepted colors: %s" % colorList
                else:
                    print
                    print "An invalid color designation was given in the denali configuration"
                    print "Default colors will be used."
                    print
                continue

            if genericValue[0].startswith("monitor_unknown_color"):
                if spaceLocation == -1:
                    if genericValue[1].strip() in colorList:
                        denaliVariables["mon_unknown"] = genericValue[1].strip()
                        if denaliVariables['debug'] == True:
                            configFile_debugOutput('monitor_unknown_color', genericValue[1].strip())
                    else:
                        print "Color requested that wasn't in the list."
                        print "Accepted colors: %s" % colorList
                else:
                    print
                    print "An invalid color designation was given in the denali configuration"
                    print "Default colors will be used."
                    print
                continue

            if genericValue[0].startswith("monitor_notfound_color"):
                if spaceLocation == -1:
                    if genericValue[1].strip() in colorList:
                        denaliVariables["mon_notfound"] = genericValue[1].strip()
                        if denaliVariables['debug'] == True:
                            configFile_debugOutput('monitor_notfound_color', genericValue[1].strip())
                    else:
                        print "Color requested that wasn't in the list."
                        print "Accepted colors: %s" % colorList
                else:
                    print
                    print "An invalid color designation was given in the denali configuration"
                    print "Default colors will be used."
                    print
                continue

            if genericValue[0].startswith("monitor_host_separator"):
                if spaceLocation == -1:
                    denaliVariables["mon_output"] = genericValue[1].strip()
                    if denaliVariables['debug'] == True:
                        configFile_debugOutput('monitor_host_separator', genericValue[1].strip())
                else:
                    print
                    print "An invalid Monitor Host Separator was submitted [%s]." % genericValue[1].strip()
                    print "Default value of comma will be used."
                    print
                continue

            # MRASEREQ-42389
            if genericValue[0].startswith("monitor_default_display"):
                if spaceLocation == -1:
                    possibleValues = ['simple', 'simplified', 'basic', 'detail', 'details', 'summary']
                    if genericValue[1].lower() in possibleValues:
                        suppliedValue = genericValue[1].lower()
                        # assign the variable
                        if suppliedValue.startswith('simp') or suppliedValue.startswith('basic'):
                            denaliVariables['monitoring_default'] = 'simple'
                        elif suppliedValue.startswith('detail'):
                            denaliVariables['monitoring_default'] = 'details'
                        else:
                            denaliVariables['monitoring_default'] = 'summary'
                        if denaliVariables['debug'] == True:
                            configFile_debugOutput('monitor_default_display', denaliVariables['monitoring_default'])
                continue

            if genericValue[0].startswith("skms_rows"):
                if spaceLocation == -1:
                    if int(genericValue[1]) > denaliVariables['maxSKMSRowReturn'] or int(genericValue[1]) < 1:
                        genericValue[1] = denaliVariables['maxSKMSRowReturn']
                    denaliVariables["maxSKMSRowReturn"] = int(genericValue[1])
                    if denaliVariables['debug'] == True:
                        configFile_debugOutput('skms_rows', int(genericValue[1]))
                else:
                    print
                    print "An invalid number of skms_rows was specified in the denali configuration"
                    print "file: %s" % fileName
                    print
                    print "Execution of Denali will be stoppped."
                    return -1
                continue

            if genericValue[0].startswith("mfa_auto_push"):
                if spaceLocation == -1:
                    if genericValue[1].lower() == 'true':
                        genericValue[1] = True
                    elif genericValue[1].lower() == 'false':
                        genericValue[1] = False
                    else:
                        genericValue[1] = False
                    denaliVariables['mfa_auto_push'] = genericValue[1]

                    if denaliVariables['debug'] == True:
                        configFile_debugOutput('mfa_auto_push', genericValue[1])
                continue

            # MRASEREQ-41495
            if genericValue[0].startswith("skms_monapi_auth"):
                if spaceLocation == -1:
                    if genericValue[1].lower() == 'true':
                        genericValue[1] = True
                    elif genericValue[1].lower() == 'false':
                        genericValue[1] = False
                    else:
                        genericValue[1] = False
                    denaliVariables['skms_monapi_auth'] = genericValue[1]
                    if denaliVariables['debug'] == True:
                        configFile_debugOutput('skms_monapi_auth', genericValue[1])
                continue

            if genericValue[0].startswith("pdsh_show_dual_status"):
                if spaceLocation == -1:
                    if genericValue[1].lower() == 'true':
                        genericValue[1] = True
                    elif genericValue[1].lower() == 'false':
                        genericValue[1] = False
                    else:
                        # if they use this switch, turn it on by default
                        genericValue[1] = True
                    denaliVariables["pdshFailSucceedHosts"] = genericValue[1]
                    if denaliVariables['debug'] == True:
                        configFile_debugOutput('pdsh_show_dual_status', genericValue[1])
                continue

            if genericValue[0].startswith("verification_host"):
                if spaceLocation == -1:
                    denaliVariables["testHost"] = genericValue[1].strip()
                    if denaliVariables['debug'] == True:
                        configFile_debugOutput('verification_host', genericValue[1].strip())
                else:
                    print
                    print "An invalid verification host was submitted [%s]." % genericValue[1].strip()
                    print "Default host will be used."
                    print
                continue

            if genericValue[0].startswith("dm_username"):
                if spaceLocation == -1:
                    denaliVariables['dm_username'] = genericValue[1].strip()
                    if denaliVariables['debug'] == True:
                        configFile_debugOutput('dm_username', genericValue[1].strip())
                continue

            if genericValue[0].startswith("dm_password"):
                if spaceLocation == -1:
                    denaliVariables['dm_password'] = genericValue[1].strip()
                    if denaliVariables['debug'] == True:
                        configFile_debugOutput('dm_password', genericValue[1].strip())
                continue

            if genericValue[0].startswith("debug_log"):
                if spaceLocation == -1:
                    if genericValue[1].lower() == 'true':
                        denaliVariables['debugLog'] = True
                        if denaliVariables['debug'] == True:
                            configFile_debugOutput('debug_log', genericValue[1])

                        # populate the filename/location
                        home_directory = returnHomeDirectory(denaliVariables)
                        if home_directory == '':
                            # environment didn't return a result -- store in /tmp
                            denaliVariables['debugLogFile'] = "/tmp/" + denaliVariables['debugLogFile']
                        else:
                            # The only way to activate this feature is with the config file,
                            # and that only exists in the .denali directory -- so this
                            # assumption should be fine.
                            denaliVariables['debugLogFile'] = home_directory + "/.denali/" + denaliVariables['debugLogFile']
                        continue

            if genericValue[0].startswith("column_auto_resize"):
                if spaceLocation == -1:
                    if genericValue[1].lower() == 'true':
                        denaliVariables["autoColumnResize"] = True
                        if denaliVariables['debug'] == True:
                            configFile_debugOutput('column_auto_resize', genericValue[1])
                    continue

    elif user_submitted == False:
        # if this path is entered with a user-supplied config file, just break out

        # The config file doesn't exist in ~/.denali
        # This means that either the directory doesn't exist, or the directory
        # does exist but the file isn't there.
        #
        # Make .denali if it doesn't exist and copy in the generic config
        # file for use.  The user has rights to create a directory in their
        # home directory, and copy in files, so this set of commands should
        # not have any permission issues.
        try:
            os.stat(dirName)
        except:
            # check again -- just in case
            if os.path.isdir(dirName) == False:
                os.mkdir(dirName)

        # See if the config file exists, if not, copy it in
        # Copy in the default config file to ~/.denali
        file_dir  = denali_location.rsplit('/',1)[0].strip()

        # The filename assumes an RPM installation where the 'denali_config'
        # directory will exist.  If this is a local installation, then this
        # code will silently fail, and that's ok because any local installations
        # presupposes that the user knows what they are doing.

        file_name  = '/usr/share/doc/packages/denali/config'    # new config location
        file_name1 = file_dir + '/denali_config/' + 'config'    # old config location
        if os.path.exists(file_name) == True:
            try:
                copy(file_name, dirName)
            except:
                pass
                #print "copy(%s, %s) failed" % (file_name, dirName)
        elif os.path.exists(file_name1) == True:
            try:
                copy(file_name1, dirName)
            except:
                pass
                #print "copy(%s, %s) failed" % (file_name, dirName)
        return False

    # store the daoDictionary
    denaliVariables['daoDictionary'] = daoDictionary

    return True



##############################################################################
#
# fillOutHostCommandList(denaliVariables, serverList)
#
#   This function assumes each host in 'serverList' has a command associated
#   with it delineated by a colon separator; e.g., server1:uptime
#
#   The code will pull out the host name/command and store it in denaliVariables
#   under the hostCommands key, and will return just the server list from
#   this function.
#

def fillOutHostCommandList(denaliVariables, serverList):

    newServerList = []

    for server in serverList:
        if server.count(':') > 0:
            server_split   = server.split(':')
            server_name    = server_split[0]
            server_command = server_split[1]

            if server_name.endswith('.com') == False and server_name.endswith('.net') == False:
                server_name += '.omniture.com'

            # If multiple commands are requested/supplied, put them in a List
            # for easy iteration
            if server.count(';') > 0:
                server_command = server_command.split(';')
            else:
                server_command = [server_command]
            newServerList.append(server_name)
            denaliVariables['hostCommands'].update({server_name:server_command})
        else:
            # server doesn't have an associated command
            newServerList.append(server)

    return newServerList



##############################################################################
#
# stripServerName(serverList, denaliVariables)
#
#   serverList comes in as a List of hostnames, and the function removes any
#   domain values that match the domainsToStrip variable stored.
#

def stripServerName(serverList, denaliVariables):

    updatedServerList = []
    strip_domains = denaliVariables["domainsToStrip"]

    if len(strip_domains) == 0:
        return serverList

    for server in serverList:
        for domain in strip_domains:
            if domain in server:
                server = server.replace(domain, '')
                updatedServerList.append(server)
                break
        else:
            updatedServerList.append(server)

    return updatedServerList



##############################################################################
#
# loadAliasesFile(denaliVariables)
#

def loadAliasesFile(denaliVariables):

    # add timing data for aliases file read
    addElapsedTimingData(denaliVariables, 'loadAliasesFile_start', time.time())

    aliasDictionary = {}

    alias_path = denaliVariables["aliasLocation"]
    if alias_path != '':
        fileName = alias_path
        # check whether the path name includes a file or not ... try and resolve here
        if os.path.isfile(alias_path) == False and os.path.isdir(alias_path) == True:
            if fileName[-1] == '/':
                fileName += 'aliases'
            else:
                fileName += '/aliases'
    else:
        home_directory = returnHomeDirectory(denaliVariables)
        fileName = "%s/.denali/aliases" % home_directory

    if os.path.isfile(fileName) == True:
        try:
            aliasFile = open(fileName, 'r')
        except:
            return False

        for line in aliasFile:
            line = line.strip()
            if line.lower().startswith("alias ") and line.find('=') != -1:
                alias = line[(line.find(' ') + 1):]
                alias = alias.split('=')

                if (alias[0].startswith("_DEFAULT") or
                    alias[0].startswith("_POWER")   or
                    alias[0].startswith("_RACK")    or
                    alias[0].startswith("_SWITCH")
                   ):

                    # An underscore character is reserved for currently 4 potential
                    # uses with aliases:
                    #
                    # (1) _DEFAULT -- to replace the default search fields
                    # (2) _POWER   -- to replace the default power search fields
                    # (3) _RACK    -- to replace the default rack search fields
                    # (4) _SWITCH  -- to replace the default switch search fields

                    aliasDictionary.update({alias[0]:alias[1]})
                    aliasDictionary.update({alias[0][1:]:alias[1]})

                elif alias[0].startswith('_'):

                    print
                    print "Alias syntax error:"
                    print "An alias definition was found that starts with an underscore"
                    print "character.  With the exception of the following reserved names,"
                    print
                    print "  [ _DEFAULT, _POWER, _RACK, _SWITCH ]"
                    print
                    print "no user-defined alias name can start with an underscore."
                    print
                    print "\"%s\" is not allowed to be used." % alias[0]
                    print "Execution of Denali has stopped."
                    print
                    return -1

                aliasDictionary.update({alias[0]:alias[1]})

    else:
        return False

    return aliasDictionary



##############################################################################
#
# separateSortElements(sortItems)
#

def separateSortElements(sortItem):

    # potential directional sort (ascending or descending) specified
    sortElements = sortItem.split(':')

    sortColumn = sortElements[0]
    sortDirection = sortElements[1].lower()

    if (sortDirection == 'descending' or
        sortDirection == 'descend' or
        sortDirection == 'desc' or
        sortDirection == 'down' or
        sortDirection == 'd'
       ):
        sortDirection = ' DESC'

    else:
        # assume "ascending" or normal sort order
        sortDirection = ''


    sortReturn = sortColumn + sortDirection + ', '

    return sortReturn


##############################################################################
#
# createSortSQLStatement(sortColumn)
#

def createSortSQLStatement(sortColumn):

    # split the sorting information by comma first (to get each individual
    # sort request.  Then split the information by colon (to get the order
    # of the sort -- ascending [ASC] or descending [DESC])

    ORDER_BY = " ORDER BY "

    if ',' in sortColumn:
        sortReqs = sortColumn.split(',')

        for sortItem in sortReqs:
            if ':' in sortItem:
                ORDER_BY += separateSortElements(sortItem)
            else:
                # no direction given, just add it to the command
                ORDER_BY += sortItem + ', '
    else:
        if ':' in sortColumn:
            ORDER_BY += separateSortElements(sortColumn)
        else:
            # no direction given, just add it to the command
            ORDER_BY += sortColumn


    ORDER_BY = ORDER_BY.rstrip()

    #print "sql sort command = %s" % ORDER_BY

    if ORDER_BY[-1:] == ',':
        return ORDER_BY[:-1]
    else:
        return ORDER_BY



##############################################################################
#
# showSQLQuery(sqlQuery, denaliVariables)
#

def showSQLQuery(sqlQuery, denaliVariables):

    print
    print " SQL Query Submitted:"
    print "========================="
    print "CMDB Dao Method : %s" % denaliVariables["method"]
    print "CMDB Dao        : %s" % denaliVariables["searchCategory"]
    if denaliVariables['profileAdded'] == True:
        print "Profile Used    : %s" % denaliVariables['profile']
    print "%s" % sqlQuery
    print



##############################################################################
#
# gatherProcess(denaliVariables, item, whereQuery, q, lock, count)
#

def gatherProcess(denaliVariables, item, whereQuery, q, lock, count):

    dao        = denaliVariables["searchCategory"]
    identifier = item.pop(0)

    denaliVariables["serverList"] = item

    # build the sql query
    (sqlQuery, wildcard) = denali_search.buildGenericQuery(denaliVariables, whereQuery)

    #print "sql query = %s" % sqlQuery
    #exit()

    # add the appropriate dao to the query (at the front)
    sqlQuery = dao + ':' + sqlQuery

    # With this query built, the code can now call denali to ask it to execute it.
    # The "False" parameter means to return the data in dictionary format from the query.
    respDictionary = denali_search.constructSQLQuery(denaliVariables, sqlQuery, False)

    if respDictionary == False:
        with lock:
            print "SQL Query failed."

            if denaliVariables["showsql"] == True:
                showSQLQuery(sqlQuery, denaliVariables)

            api = denaliVariables["api"]
            print "\nERROR:"
            print "   STATUS: " + api.get_response_status()
            print "   TYPE: " + str(api.get_error_type())
            print "   MESSAGE: " + api.get_error_message()

        count.value -= 1
        denali_search.cleanUp(denaliVariables)
        exit(1)

    # put the retrieved information on the queue
    q.put([identifier, respDictionary])

    # this process is completed -- decrement the overall thread count
    count.value -= 1



##############################################################################
#
# watcherProcess(rcvData, lock, pipe)
#

def watcherProcess(rcvData, lock, pipe):

    retDictionary = {}

    while True:
        # this call will block until data arrives
        tempData = rcvData.get()

        # if the main thread signals all watchers have finished,
        # then break out of the while loop
        if tempData == "FINISHED":
            break

        # update the dictionary
        retDictionary.update({tempData[0]:tempData[1]["data"]["results"]})

    # send the completed dictionary to the main thread for processing and
    # close the pipe connection
    pipe.send(retDictionary)
    pipe.close()



##############################################################################
#
# multiQueryResponse(denaliVariables, queryList, whereQuery)
#

def multiQueryResponse(denaliVariables, queryList, whereQuery):

    # This function assumes that the method is "search".
    # If a non-search method is wanted, use: multiQueryMethodResponse()

    # user entertainment
    user_entertainment      = 0
    total_processes_created = 0

    # maximum threads to spin up at any one time -- to *hopefully* prevent problems
    # "50" is just a nice round number chosen; perhaps the host can handle more?
    MAX_THREAD_COUNT = 50

    procList        = []
    rcvData         = Queue()
    lock            = Lock()
    retDictionary   = {}

    # get the pipe configured
    (parentP, listenP) = Pipe()

    # create a shared memory variable -- for the number of gatherProcesses created
    # and running at a single instance
    threads_created = Value('i', 0)

    watcher = Process(target=watcherProcess, args=(rcvData, lock, listenP))
    watcher.start()

    for item in queryList:
        while threads_created.value >= MAX_THREAD_COUNT:
            # if the maximum number of gatherProcesses have been created; wait (checks done every
            # 1/2-second) until it drops below the threshold value, and then allow a new one to be
            # created.
            time.sleep(0.5)

        p = Process(target=gatherProcess, args=(denaliVariables, item, whereQuery, rcvData, lock, threads_created))
        threads_created.value += 1
        total_processes_created += 1

        if denaliVariables["debug"] == True or user_entertainment == 1:
            stdout.write("\rProcesses created = %d" % total_processes_created)

        p.start()
        procList.append(p)

    # wait until all of the gather processes have exited
    for p in procList:
        p.join()

    # signal the watcherProcess to stop / collect the completed dictionary
    rcvData.put("FINISHED")
    retDictionary = parentP.recv()

    # close out the watcherProcess / close out the parent pipe
    watcher.join()
    parentP.close()

    #if denaliVariables["debug"] == True or user_entertainment == 1:
    #    stdout.write("\rTotal processes created = %d" % total_processes_created)
    #    pressEnter = raw_input("\nPress <ENTER> to continue:")

    return retDictionary



##############################################################################
#
# multiQueryMethodResponse(denaliVariables, queryList)
#

def multiQueryMethodResponse(denaliVariables, queryList):

    # user entertainment
    user_entertainment      = 0
    total_processes_created = 0

    # maximum threads to spin up at any one time -- to *hopefully* prevent problems
    # "50" is just a nice round number chosen; perhaps the host can handle more?
    MAX_THREAD_COUNT = 50

    procList        = []
    rcvData         = Queue()
    lock            = Lock()
    retDictionary   = {}

    # get the pipe configured
    (parentP, listenP) = Pipe()

    # create a shared memory variable -- for the number of gatherProcesses created
    # and running at a single instance
    threads_created = Value('i', 0)

    watcher = Process(target=methodWatcherProcess, args=(rcvData, lock, listenP))
    watcher.start()

    for item in queryList:
        while threads_created.value >= MAX_THREAD_COUNT:
            # if the maximum number of gatherProcesses have been created; wait (checks done every
            # 1/2-second) until it drops below the threshold value, and then allow a new one to be
            # created.
            time.sleep(0.5)

        p = Process(target=methodGatherProcess, args=(denaliVariables, item, rcvData, lock, threads_created))
        threads_created.value += 1
        total_processes_created += 1

        if denaliVariables["debug"] == True or user_entertainment == 1:
            stdout.write("\rProcesses created = %d" % total_processes_created)

        p.start()
        procList.append(p)

    # wait until all of the gather processes have exited
    for p in procList:
        p.join()

    # signal the watcherProcess to stop / collect the completed dictionary
    rcvData.put("FINISHED")
    retDictionary = parentP.recv()

    # close out the watcherProcess / close out the parent pipe
    watcher.join()
    parentP.close()

    #if denaliVariables["debug"] == True or user_entertainment == 1:
    #    stdout.write("\rTotal processes created = %d" % total_processes_created)
    #    pressEnter = raw_input("\nPress <ENTER> to continue:")

    return retDictionary



##############################################################################
#
# methodGatherProcess(denaliVariables, item, q, lock, count)
#

def methodGatherProcess(denaliVariables, item, q, lock, count):

    identifier = item
    denaliVariables["serverList"] = item

    queryItem = {"device_key": item}
    respDictionary = executeMethodQuery(denaliVariables, queryItem)

    if respDictionary == False:
        with lock:
            print "SQL Query failed."

            api = denaliVariables["api"]
            print "\nERROR:"
            print "   STATUS: " + api.get_response_status()
            print "   TYPE: " + str(api.get_error_type())
            print "   MESSAGE: " + api.get_error_message()

        count.value -= 1
        denali_search.cleanUp(denaliVariables)
        exit(1)

    # put the retrieved information on the queue
    q.put([identifier, respDictionary])

    # this process is completed -- decrement the overall thread count
    count.value -= 1



##############################################################################
#
# methodWatcherProcess(rcvData, lock, pipe)
#

def methodWatcherProcess(rcvData, lock, pipe):

    retDictionary = {}

    while True:
        # this call will block until data arrives
        tempData = rcvData.get()

        # if the main thread signals all watchers have finished,
        # then break out of the while loop
        if tempData == "FINISHED":
            break

        #print "tempData = %s" % tempData
        # update the dictionary
        retDictionary.update({tempData[0]:tempData[1]})

    # send the completed dictionary to the main thread for processing and
    # close the pipe connection
    pipe.send(retDictionary)
    pipe.close()



##############################################################################
#
# executeMethodQuery(api, category, method, queryItem)
#

def executeMethodQuery(denaliVariables, queryData={}):

    api      = denaliVariables["api"]
    method   = denaliVariables["method"]
    category = denaliVariables["searchCategory"]


    # Put the built query into dictionary format for the API to use

    #print "api                : %s" % api
    #print "category           : %s" % category
    #print "method             : %s" % method
    #print "parameterDictionary: %s" % data

    if api.send_request(category, method, queryData) == True:
        response_dict = api.get_data_dictionary()
    else:
        print "ERROR:"
        print "   STATUS: " + api.get_response_status()
        print "   TYPE: " + str(api.get_error_type())
        print "   MESSAGE: " + api.get_error_message()
        return False

    return response_dict



##############################################################################
#
# sqlQueryConstructionResponse(denaliVariables, sqlQuery)
#

def sqlQueryConstructionResponse(denaliVariables, sqlQuery):

    subQueries = denali_search.separateSQLQueries(sqlQuery, denaliVariables)
    subData = ''

    #numDevices = len(denaliVariables["serverList"])
    #if numDevices > 1000:
    #    denali.deviceLimitError(numDevices)
    #    return False

    for (index, query) in enumerate(subQueries):
        numOfQueries = len(subQueries)

        denaliVariables["searchCategory"] = query[0]
        sqlQuery = query[1]

        findSELECT = sqlQuery.find("SELECT")
        findWHERE  = sqlQuery.find("WHERE")
        where = sqlQuery[findWHERE:].strip()
        denaliVariables["fields"] = sqlQuery[(findSELECT + 7):(findWHERE - 1)].strip()

        (modFields, denaliVariables["columnData"]) = denali_search.determineColumnOrder(denaliVariables)

        sqlQuery = "SELECT " + modFields + " " + where
        if "[#]" in sqlQuery:
            sqlQuery = sqlQuery.replace("[#]", subData)

        if "PAGE" not in sqlQuery:
            PAGE = " PAGE 1, %d" % denaliVariables["maxSKMSRowReturn"]
            sqlQuery += PAGE

        (compiledData, itemCount) = getSQLResponse(denaliVariables, sqlQuery, index, numOfQueries)

    #
    #if denaliVariables["summary"] == True:
    #    print
    #    print " Total Items Displayed: %d" % itemCount

    #if denaliVariables["showsql"] == True:
    #    showSQLQuery(sqlQuery, denaliVariables)
    #

    return compiledData



##############################################################################
#
# getSQLResponse(denaliVariables, sqlQuery, index, numOfQueries)
#

def getSQLResponse(denaliVariables, sqlQuery, index, numOfQueries):

    subData     = ''
    next_page   = True
    page_number = 0
    completeData = []

    while next_page == True:
        page_number += 1

        # put the current page number in the output type individual lists.  This is a
        # state for the file write routine to check and see if an append needs to be
        # done (page >= 2) or to just open the file for writing initially (page = 1).
        for item in denaliVariables['outputTarget']:
            item.append = page_number > 1

        responseDictionary = denali_search.executeWebAPIQuery(denaliVariables, sqlQuery)
        #print "rd = %s" % responseDictionary

        if denaliVariables["debug"] == True:
            print "\nresponseDictionary = %s" % responseDictionary

        if responseDictionary != False:
            method = denaliVariables["method"]
            if method == "search":
                # check the item count -- need another page?
                (pageInfo, item_count) = denali_search.checkItemCount(denaliVariables, responseDictionary)
            elif method == "count" or method == "getAttributes":
                pageInfo = False
                item_count = "count"

            if (index + 1) == numOfQueries:
                # output the information
                (printData, overflowData) = denali_search.generateOutputData(responseDictionary, denaliVariables)
                if denaliVariables["debug"] == True:
                    print "len(printData) = %s" % len(printData)
                    print "(B) len(completeData) = %s" % len(completeData)

                completeData.extend(printData)

                if denaliVariables["debug"] == True:
                    print "(A) len(completeData) = %s" % len(completeData)
                #denali_search.prettyPrintData(printData, overflowData, responseDictionary, denaliVariables)

            else:
                # sub-query data handling
                # don't print sub-query data
                # just gather the data for later use
                subData = denali_search.gatherSearchedData(responseDictionary, denaliVariables)

            # clean up the data --- remove 'nones'
            responseDictionary = denali_search.clearUpNones(responseDictionary)

            if pageInfo != False:      # new pages to query for
                sqlQuery = denali_search.modifyQueryPageSetting(sqlQuery, pageInfo)
            else:
                next_page = False

        else:
            next_page = False
            return False, False

    return (completeData, item_count)



##############################################################################
#
# resetOutputTarget(denaliVariables)
#
#   If a combined data gather was used, then the output targets will be wrong
#   and not print headers (if requested).  Reset the numbers back to one (1)
#   so the headers can print.
#

def resetOutputTarget(denaliVariables):
    for target in denaliVariables["outputTarget"]:
        target.append = False



##############################################################################
#
# removeClosedJIRA(denaliVariables, responseDictionary)
#

def removeClosedJIRA(denaliVariables, responseDictionary):


    for (dev_index, device) in enumerate(responseDictionary["data"]["results"]):

        # remove unneeded data from dictionary
        responseDictionary["data"]["results"][dev_index].pop("jira_issue")

        # get status list ("Closed" or not) and the dictionaryKeys
        jiraStatus = responseDictionary["data"]["results"][dev_index]["jira_issue.status"]
        jiraKeys   = responseDictionary["data"]["results"][dev_index].keys()

        for (status_index, status) in enumerate(jiraStatus):
            if status == "Closed" or status == "Resolved":
                for (key_index, key_name) in enumerate(jiraKeys):
                    if key_name.startswith("jira_issue"):
                        if (len(responseDictionary["data"]["results"][dev_index][key_name])-1) >= status_index:
                            responseDictionary["data"]["results"][dev_index][key_name][status_index] = ''

        jiraList = []
        for (status_index, status) in enumerate(jiraStatus):
            for (key_index, key_name) in enumerate(jiraKeys):
                if key_name.startswith("jira_issue"):
                    for dataValue in responseDictionary["data"]["results"][dev_index][key_name]:
                        if len(dataValue) > 0:
                            jiraList.append(dataValue)
                    responseDictionary["data"]["results"][dev_index][key_name] = jiraList
                    jiraList = []

    for (index, cData) in enumerate(denaliVariables["columnData"]):
        if cData[0] == "jira_status":
            denaliVariables["columnData"].pop(index)

    return responseDictionary



##############################################################################
#
# calculatePercentage(overall_time, elapsed_time)
#
#   Calculate the current elapsed time percentage of the overall time.
#   Used with the --time parameter.
#

def calculatePercentage(overall_time, elapsed_time):

    if overall_time == 0:
        return '100%'

    percentage = (elapsed_time / overall_time) * 100
    if percentage < 0.01:
        return '<0.01%'
    if percentage < 10:
        percentage = ' ' + str(round(percentage,2)) + '%'
    else:
        percentage = str(round(percentage,2)) + '%'

    # add trailing zero to align percentages
    if len(percentage[percentage.find('.'):]) < 4:
        percentage = percentage[:-1] + '0%'
    return percentage



##############################################################################
#
# printTimeDifferences(denaliVariables, time_start_list, time_stop_list, printString, overall=0, function_count=1)
#

def printTimeDifferences(denaliVariables, time_start_list, time_stop_list, printString, overall=0, function_count=1):

    category_width        = 40
    time_start_width      = 24
    time_stop_width       = 24
    time_difference_width = 22
    time_percentage_width = 10

    counter = 0
    elapsed = False

    #print "+Time category = %s" % printString
    #print "   time startl = %s" % time_start_list
    #print "   time stopl  = %s" % time_stop_list

    if function_count > 1:
        elapsed = True
    elif len(time_start_list) != len(time_stop_list):
        if printString.startswith('f_'):
            printString = 'Function: ' + printString[2:]
        print "%s time arrays have different counts" % printString
        print "Start: %s" % time_start_list
        print "Stop : %s" % time_stop_list
        return

    if len(time_start_list) == 0:
        return

    if elapsed == False:
        # single function timing data -- not combined -- no average displayed
        # should be good to go
        elapsed_time_final = 0

        for (start_value, stop_value) in zip(time_start_list, time_stop_list):
            counter += 1
            start_time          = datetime.datetime.fromtimestamp(start_value).strftime('%Y-%m-%d %H:%M:%S')
            stop_time           = datetime.datetime.fromtimestamp(stop_value).strftime('%Y-%m-%d %H:%M:%S')
            elapsed_time        = stop_value - start_value
            elapsed_time_final += elapsed_time
            percent_time        = calculatePercentage(overall, elapsed_time_final)

            # category
            if printString.startswith('f_'):
                printString = '(f) ' + printString[2:]

            stdout.write("%s" % printString.ljust(category_width))
            if printString == 'Denali Overall':
                overall = elapsed_time_final

            # start time / stop time
            stdout.write("%s" % start_time.ljust(time_start_width))
            stdout.write("%s" % stop_time.ljust(time_stop_width))

            # percentage of overall
            stdout.write('%s' % percent_time.ljust(time_percentage_width))

            # time difference
            if elapsed_time < 60:
                # 12 decimals displayed - no scientific notation
                # Require the '0' -- {0:.12f} because python v2.6.6 will produce an error without it
                #   ValueError: zero length field name in format
                print '{0:.12f}'.format(elapsed_time) + 's'
            else:
                seconds = elapsed_time % 60
                minutes = int(math.ceil((elapsed_time - seconds) / 60))
                print "%sm %s" % (minutes, '{0:.9f}'.format(seconds) + 's')

    else:
        # elapsed time data
        if printString.startswith('f_'):
            printString = printString[2:]

        elapsed_time = 0

        for time_value in range(function_count):
            start_value        = time_start_list[time_value]
            stop_value         = time_stop_list[time_value]
            start_time         = datetime.datetime.fromtimestamp(start_value).strftime('%Y-%m-%d %H:%M:%S')
            stop_time          = datetime.datetime.fromtimestamp(stop_value).strftime('%Y-%m-%d %H:%M:%S')
            elapsed_time      += (stop_value - start_value)
            elapsed_time_final = elapsed_time
            percent_time       = calculatePercentage(overall, elapsed_time_final)

        # category
        combined_data = "(f) %s [%d]" % (printString, function_count)
        stdout.write(combined_data.ljust(category_width))

        # start time / stop time
        stdout.write("%s" % start_time.ljust(time_start_width))
        stdout.write("%s" % stop_time.ljust(time_stop_width))

        # percentage of overall
        stdout.write('%s' % percent_time.ljust(time_percentage_width))

        # compute the elapsed time for the call
        if elapsed_time < 60:
            stdout.write("%s" % ('{0:.12f}'.format(elapsed_time) + 's').ljust(time_difference_width))
        else:
            seconds = elapsed_time % 60
            minutes = int(math.ceil((elapsed_time - seconds) / 60))
            stdout.write("%sm %s" % (minutes, ('{0:.9f}'.format(seconds) + 's').ljust(time_difference_width-3)))

        # compute the average each function call took
        if function_count > 1:
            elapsed_time_average = elapsed_time / function_count
            if elapsed_time_average < 60:
                print '{0:.12f}'.format(elapsed_time_average) + 's'
            else:
                seconds = elapsed_time_average % 60
                minutes = int(math.ceil((elapsed_time_average - seconds) / 60))
                print "%sm %s" % (minutes, ('{0:.9f}'.format(seconds) + 's').ljust(time_difference_width-3))

        stdout.flush()

    # store the elapsed time (if denali_overall), or subtract it from the total
    # to determine the unaccounted time (which a function call timing tag would
    # help understand)
    if printString == "Denali Overall":
        denaliVariables['time_unaccounted'] = elapsed_time_final
    else:
        if printString != "Monitoring API":
            current_time = denaliVariables['time_unaccounted']
            denaliVariables['time_unaccounted'] -= elapsed_time_final

    return overall



##############################################################################
#
# addTimingData(denaliVariables, stat_name, time)
#

def addTimingData(denaliVariables, stat_name, time):

    stat_name = 'f_' + stat_name

    if stat_name in denaliVariables['time']:
        denaliVariables['time'][stat_name].append(time)
    else:
        denaliVariables['time'].update({stat_name:[time]})



##############################################################################
#
# addElapsedTimingData(denaliVariables, stat_name, time)
#

def addElapsedTimingData(denaliVariables, stat_name, time):
    stat_name = 'f_' + stat_name
    if stat_name in denaliVariables['time']:
        if stat_name.endswith('_start'):
            denaliVariables['time'][stat_name][0] += 1
            denaliVariables['time'][stat_name].append(time)
            return
        else:
            denaliVariables['time'][stat_name].append(time)
    else:
        if stat_name.endswith('_stop'):
            denaliVariables['time'].update({stat_name:[time]})
        else:
            denaliVariables['time'].update({stat_name:[1,time]})



##############################################################################
#
# printTimingInformation(denaliVariables)
#

def printTimingInformation(denaliVariables):

    print

    if denaliVariables['debug'] == True or denaliVariables['monitoring_debug'] == True:
        print "Time status dictionary = %s" % denaliVariables['time']

    print "Timing Category                         Time Start              Time Stop               %         Time Difference       Average Run"
    print "==========================================================================================================================================="

    # capture the overall time differential for use in each subsequent run
    overall = printTimeDifferences(denaliVariables, denaliVariables['time']['denali_start'],
                                   denaliVariables['time']['denali_stop'], "Denali Overall")

    printTimeDifferences(denaliVariables, denaliVariables['time']['skms_auth_start'],
                         denaliVariables['time']['skms_auth_stop'], "SKMS Authentication", overall)

    printTimeDifferences(denaliVariables, denaliVariables['time']['skms_start'],
                         denaliVariables['time']['skms_stop'], "SKMS API Access", overall)

    if denaliVariables['monitoring'] == True:
        printTimeDifferences(denaliVariables, denaliVariables['time']['monitoring_start'],
                             denaliVariables['time']['monitoring_stop'], "Monitoring Overall", overall)

        printTimeDifferences(denaliVariables, denaliVariables['time']['monapi_start'],
                             denaliVariables['time']['monapi_stop'], "Monitoring API Access", overall)

    printTimeDifferences(denaliVariables, denaliVariables['time']['update_start'],
                         denaliVariables['time']['update_stop'], "SKMS Update", overall)

    time_keys = denaliVariables['time'].keys()
    time_keys.sort()
    for time_start in time_keys:
        count = 1
        if time_start.startswith('f_') and time_start.endswith('_start'):
            time_stop = time_start[:-3] + 'op'

            if len(denaliVariables['time'][time_start]) == len(denaliVariables['time'][time_stop]) + 1:
                if isinstance(denaliVariables['time'][time_start][0], int) == True:
                    count = denaliVariables['time'][time_start].pop(0)
            printTimeDifferences(denaliVariables, denaliVariables['time'][time_start],
                                 denaliVariables['time'][time_stop], time_start[:-6], overall, count)

    print
    #print "Time unaccounted for (function time not individually tracked): %fs" % denaliVariables['time_unaccounted']

    return



##############################################################################
#
# printOverallTimeToRun(denaliVariables)
#

def printOverallTimeToRun(denaliVariables):

    start_time = denaliVariables['time']['denali_start'][0]
    stop_time  = time.time()

    diff_time  = stop_time - start_time
    if denaliVariables['monitoring'] == False:
        print " Time to display queried results   : %fs" % diff_time
    else:
        print "  Total Query Time             : %fs" % diff_time
    return



##############################################################################
#
# printSummaryInformation(denaliVariables)
#
#   If --summary is specified, this function displays that information.
#   denaliVariables["limitCount"] stores the count for how many devices/records
#   were requested for display.
#

def printSummaryInformation(denaliVariables, itemCount, wildcard, count=0):

    hostsNotFound = len(denaliVariables["devicesNotFound"])
    serverList    = denaliVariables["serverList"]

    # If a search was done, and --summary submitted but the search was done on
    # behalf of monitoring or command execution, just return back out -- print nothing.
    if (denaliVariables['monitoring'] == True or
        denaliVariables['commandExecuting'] == True):
        return

    if (denaliVariables['method'] == 'count' and
        denaliVariables['batchDevices'] == True):
        if 'final_key' not in denaliVariables['batchDeviceList']:
            return

    if denaliVariables["method"] == "search":
        print
        if denaliVariables['limitCount'] > 0:
            print " Total limit of devices displayed  : %d  (--limit)" % denaliVariables['limitCount']
        elif 'definition' in denaliVariables['limitData']:
            summary = denaliVariables['limitData'].get('summary', 0)
            if summary > 0:
                print " Total limit of devices displayed  : %d  (--limit)" % denaliVariables['limitData']['summary']

        if denaliVariables["searchCategory"] == "DeviceDao":
            print " Total number of devices queried   : %d" % itemCount
        elif itemCount > 0:
            print " Total number of records queried   : %d" % itemCount
        else:
            printOverallTimeToRun(denaliVariables)
            return

        if wildcard == True:
            print " Total number of devices submitted : %d* (wildcard used)" % (len(serverList) + hostsNotFound)
        else:
            if denaliVariables["searchCategory"] == "HistoryDao":
                print " Total number of devices submitted : 1"
            else:
                if count == 0:
                    print " Total number of devices submitted : %d" % (itemCount + hostsNotFound)
                else:
                    print " Total number of devices displayed : %i" % count

        printOverallTimeToRun(denaliVariables)

        if hostsNotFound > 0:
            print " Total number of devices not found : %d" % hostsNotFound
            print "   Host not found list:"

            hostCount        = 0
            maxHostWidth     = 0
            printingMaxWidth = 80

            # determine the maximum width (num of characters) for the
            # largest host name; adjust the printing accordingly
            for host in denaliVariables["devicesNotFound"]:
                hostWidth = len(host)
                if hostWidth > maxHostWidth:
                    maxHostWidth = hostWidth

            maxHostWidth += 2
            hostsToPrint  = printingMaxWidth / maxHostWidth

            for host in denaliVariables["devicesNotFound"]:
                if hostCount == 0:
                    print "   ",
                print "%s" % host.ljust(maxHostWidth),
                hostCount += 1
                if hostCount > hostsToPrint:
                    hostCount = 0
                    print
        print

    elif denaliVariables["method"] == "count":
        print
        print " Total number of item categories   : %s" % denaliVariables["methodData"]
        printOverallTimeToRun(denaliVariables)
        print



##############################################################################
#
# convertFromEpochToDateTime(time_epoch, pattern='%Y-%m-%d %H:%M:%S')
#
#   MRASEREQ-41538
#

def convertFromEpochToDateTime(time_epoch, pattern='%Y-%m-%d %H:%M:%S'):

    date_time = time.strftime(pattern, time.localtime(time_epoch))
    return date_time



##############################################################################
#
# convertFromDateTimeToEpoch(time_string, pattern='%Y-%m-%d %H:%M:%S')
#
#   MRASEREQ-41538
#

def convertFromDateTimeToEpoch(time_string, pattern='%Y-%m-%d %H:%M:%S'):

    if len(time_string) == 0:
        print "Denali Syntax Error:  Time String has a length of zero"
        return False, False

    if time_string[0].strip().isdigit() is not True:
        time_string = time_string[1:]

    # if the hours:minutes:seconds were not included, it is midnight by default
    if time_string.find(' ') == -1:
        pattern = '%Y-%m-%d'
    elif time_string.count(':') == 1:
        pattern = '%Y-%m-%d %H:%M'

    try:
        time_epoch = int(time.mktime(time.strptime(time_string, pattern)))
    except ValueError:
        print "Denali Syntax Error:  Time format is %s (24-hour clock)" % pattern
        print "     Time submitted:  %s" % time_string
        return False, False

    return time_epoch, pattern



##############################################################################
#
# daoTimeMethodMassage(denaliVariables, daoDictionary, daoDateElement)
#
#   MRASEREQ-41538
#
#   This function takes english words and numbers and translates them into the
#   correct start and end times for a dao date window.
#
#   Delta term words supported:
#       day/days    week/weeks    month/months    year/years
#       The numbers used with this can have a '+' or '-' sign to indicate which
#       direction the delta is (adding or subtracting time from a given starting
#       point).
#
#   Current limitations:
#   (1) It is assumed that only the start time will be searched on.  This means
#       that if a week's worth of data is wanted, it is counted on start time of
#       the dao data, not an end time.  If an end time is specified, and it is a
#       'delta' english term, then it probably won't work as desired (potentially
#       showing something completely wrong).
#

def daoTimeMethodMassage(denaliVariables, daoDictionary, daoDateElement):

    date1             = None        # is the first date a delta (day/week/month)?
    date2             = None        # is the second date a delta (day/week/month)?
    delta_count       = ''          # if delta, how many are there (of d/w/m) -- change to int
    delta_term        = ''          # if delta, string of the type (day/week/month)
    delta_date        = ''          # storage of the full delta string (if it exists)
    real_date         = ''          # storage of the full real string (if it exists)
    add_time          = True        # if true, positive delta.  If false, negative delta
                                    #   Either add to or subtract from the other date submitted,
                                    #   or the current date/time (if only a delta submitted)
    delta_time        = 0           # if delta, the amount of seconds for that time delta;
                                    #   calculated by delta_count x (day/week/month multiplier)
    time_prefix_delta = '<'         # prefix to put on the delta time ('<', '>')
    time_prefix_real  = '>'         # prefix to put on the real time  ('<', '>')
    leap_year         = None        # whether or not the date logic should account for leap year

    # seconds in a ...
    day_multiplier  = 86400     # 24 hrs x 60 mins x 60 secs
    week_multiplier = 604800    # seconds in a day x 7 days

    if denaliVariables['debug'] == True:
        print "date data = %s" % daoDictionary

    # Determine which of the possible dates (two total) has a duration word
    # (or not) in it.
    if (daoDictionary['date1'].lower().find('day')   != -1 or
        daoDictionary['date1'].lower().find('week')  != -1 or
        daoDictionary['date1'].lower().find('month') != -1 or
        daoDictionary['date1'].lower().find('year')  != -1):
        date1 = True
    else:
        date1 = False

    if 'date2' in daoDictionary:
        if (daoDictionary['date2'].lower().find('day')   != -1 or
            daoDictionary['date2'].lower().find('week')  != -1 or
            daoDictionary['date2'].lower().find('month') != -1 or
            daoDictionary['date2'].lower().find('year')  != -1):
            date2 = True
        else:
            date2 = False

    if denaliVariables['debug'] == True:
        print "date1 = %s" % date1
        print "date2 = %s" % date2

    if date1 == False and date2 is None:
        # single real date object, just return
        if denaliVariables['debug'] == True:
            print "single real date object -- just return"
        return (True, True)
    elif date1 == True and date2 is None:
        # single delta date object, get the real date
        if denaliVariables['debug'] == True:
            print "single delta date object"
        delta_date = daoDictionary['date1']
        real_date  = time.strftime('%Y-%m-%d')      # get the current date for the 'real_date'
        # add a bogus character to the front (function expects one, or the year loses a character)
        real_date  = '-' + real_date
    elif (date1 == True  and date2 == False):
        # 2 date objects: d1 is delta, d2 is real
        if denaliVariables['debug'] == True:
            print "d1 is delta, d2 is real"
        delta_date = daoDictionary['date1']
        real_date  = daoDictionary['date2']
    elif (date1 == False and date2 == True):
        # 2 date objects: d1 is real, d2 is delta
        if denaliVariables['debug'] == True:
            print "d1 is real, d2 is delta"
        delta_date = daoDictionary['date2']
        real_date  = daoDictionary['date1']
    elif date1 == False and date2 == False:
        # 2 real date objects, just return
        if denaliVariables['debug'] == True:
            print "two real dates -- change nothing -- just return"
        return (True, True)

    # get the epoch for the real_date object
    (real_date_epoch, time_pattern) = convertFromDateTimeToEpoch(real_date)
    if real_date_epoch == False:
        return (False, False)

    if denaliVariables['debug'] == True:
        print "\nreal_date_epoch   = %s" % real_date_epoch

    # see if the user requested a subtraction (-) via delta time
    if delta_date.startswith('-'):
        add_time          = False
        delta_date        = delta_date[1:]
        time_prefix_delta = '>'
        time_prefix_real  = '<'

    # strip off the plus sign (+) if it exists
    if delta_date.startswith('+'):
        delta_date = delta_date[1:]

    # determine the count of days/weeks/months for the delta
    for character in delta_date:
        if character.isdigit():
            delta_count += character
        else:
            delta_term  += character

    # strip off spaces on the end of the multiplier term
    delta_term = delta_term.strip()

    if len(delta_count):
        delta_count = int(delta_count)
    else:
        # if just 'day' or 'week' or 'month' is specified, assume they mean one (1)
        delta_count = 1

    if delta_term.lower().startswith('day') or delta_term.lower().startswith('week'):
        if delta_term.lower().startswith('day'):
            delta_time = day_multiplier * delta_count
        elif delta_term.lower().startswith('week'):
            delta_time = week_multiplier * delta_count

        # adjust the 2nd date parameter value by the delta amount
        if add_time == True:
            real_date_epoch += delta_time
        else:
            real_date_epoch -= delta_time

        # get the second date in date_time format (pattern from above conversion)
        real_date_two = convertFromEpochToDateTime(real_date_epoch, time_pattern)

    else:
        if delta_term.lower().startswith('month') or delta_term.lower().startswith('year'):

            # months with 31 days
            month_days31 = [ 1, 3, 5, 7, 8, 10, 12 ]

            # get the second date in date_time format (pattern from above conversion)
            real_date_two = convertFromEpochToDateTime(real_date_epoch, time_pattern)
            date_split    = real_date_two.split('-')
            year          = int(date_split[0])
            month         = int(date_split[1])
            day           = int(date_split[2])

            if delta_term.lower().startswith('year'):
                if add_time == True:
                    year += delta_count
                else:
                    year -= delta_count

            elif delta_term.lower().startswith('month'):
                # months become years; handle, for example: 30 months
                if delta_count > 12:
                    year_modifier = delta_count / 12
                    delta_count   = delta_count - (year_modifier * 12)

                    if add_time == True:
                        year += year_modifier
                    else:
                        year -= year_modifier

                if add_time == True:
                    month += delta_count
                else:
                    month -= delta_count

                # Account for a year rollover (forward or back)
                if month > 12:      # next year
                    month   = month - 12
                    year   += 1     # increment the year
                elif month == 0:    # previous year
                    month   = 12    # set to December
                    year   -= 1     # decrement the year

                # Account for month differences (30/31 days) -- round down to '30' if necessary
                if day == 31 and month not in month_days31:
                    day = 30

                # determine if this is a leap year or not
                if year % 4 != 0:
                    leap_year = False
                elif year % 100 != 0:
                    leap_year = True
                elif year % 400 != 0:
                    leap_year = False
                else:
                    leap_year = True

                # Account for February -- 28 days (and leap year handling)
                # If there is a landing date > than the 28th, do a little subtraction
                # and make that the 'day' in March and then make the month '3' (March).
                if month == 2 and day > 28:
                    # handle leap year
                    if leap_year == True and day == 29:
                        # Feb 29th on a leap year is valid -- let it pass
                        pass
                    else:
                        day   = day - 28
                        month = 3

            # ok, now put it all back together (day, month, year, etc.)
            date_split[0] = str(year).zfill(4)
            date_split[1] = str(month).zfill(2)
            date_split[2] = str(day).zfill(2)
            real_date_two = '-'.join(date_split)

        else:
             print "Denali Syntax Error:  Delta term [%s] not recognized" % delta_term
             return (False, False)


    # put the prefixes on the dates
    real_date     = time_prefix_real  + real_date[1:]
    real_date_two = time_prefix_delta + real_date_two

    if denaliVariables['debug'] == True:
        print "delta_count       = %s" % delta_count
        print "delta_term        = %s" % delta_term

        if add_time == True:
            print "delta_time (secs) = +%d seconds" % delta_time
        else:
            print "delta_time (secs) = -%d seconds" % delta_time

        print "Date #1           = %s" % real_date
        print "Date #2           = %s" % real_date_two

    # now substitute the modified dates back into denaliVariables['sqlParameters']
    number_substituted = 0
    for (index, parameter) in enumerate(denaliVariables['sqlParameters']):
        if parameter[0] == daoDateElement:
            if number_substituted == 0:
                denaliVariables['sqlParameters'][index][1] = real_date
            else:
                denaliVariables['sqlParameters'][index][1] = real_date_two
            number_substituted += 1

    # create a separate data object to return with the needed information if wanted
    dateSQLElement = [[daoDateElement,real_date],[daoDateElement,real_date_two]]

    # if there was no second date submitted -- add it on to bracket the search window
    if number_substituted == 1:
        denaliVariables['sqlParameters'].append([daoDateElement, real_date_two])

    # Because there was likely a time/delta manipulation, print out the date range
    # that was calculated for the user as an informational aid (sort it with the lower
    # date first).
    if real_date[0] == '>':
        print "DAO search date range:  %s  |  %s" % (real_date, real_date_two)
    else:
        print "DAO search date range:  %s  |  %s" % (real_date_two, real_date)

    if denaliVariables['debug'] == True:
        print "denaliVariables['sqlParameters'] = %s" % denaliVariables['sqlParameters']

    return (True, dateSQLElement)



##############################################################################
#
# sortAttributeColumns(denaliVariables, nameList, valueList, inheritList)
#

def sortAttributeColumns(denaliVariables, nameList, valueList, inheritList):

    zippedList = []
    attrLists  = {}

    if len(nameList) > 0:
        zippedList.append(nameList)
    if len(valueList) > 0:
        zippedList.append(valueList)
    if len(inheritList) > 0:
        zippedList.append(inheritList)

    # combine the attributes in a tuple
    zipped = zip(*zippedList)

    # sort the combined attributes (by the name if it exists,
    # or by whatever column is in position #1 if it doesn't)
    zipped.sort()

    # un-combine the attributes -- in separate tuples
    zipLists = zip(*zipped)

    zLength = len(zipLists)
    for index in range(zLength):
        attrLists.update({'c' + str(index):list(zipLists[index])})

    listKeys = attrLists.keys()

    # if all three are specified, it's easy to identify columns
    # the columns are assigned name, value, inheritance, so c0
    # will be name, c1 is value, and c2 is inheritance.
    if len(listKeys) == 3:
        attrLists["attribute_name"]        = attrLists.pop("c0")
        attrLists["attribute_value"]       = attrLists.pop("c1")
        attrLists["attribute_inheritance"] = attrLists.pop("c2")
    else:
        if len(listKeys) == 1:
            (name, value, inherit) = getAttrColumns(denaliVariables)

            if name != -1:
                attrLists["attribute_name"] = attrLists.pop("c0")
            elif value != -1:
                attrLists["attribute_value"] = attrLists.pop("c0")
            else:
                attrLists["attribute_inheritance"] = attrLists.pop("c0")

        elif len(nameList) > 0:
            attrLists["attribute_name"] = attrLists.pop("c0")

            # assign the remaining column
            if len(valueList) > 0:
                attrLists["attribute_value"] = attrLists.pop("c1")
            else:
                attrLists["attribute_inheritance"] = attrLists.pop("c1")
        else:
            # if c0 isn't name, then the remaining two are ...
            attrLists["attribute_value"]       = attrLists.pop("c0")
            attrLists["attribute_inheritance"] = attrLists.pop("c1")

    return attrLists



##############################################################################
#
# translateAttributeIndex(indexList, masterList)
#

def translateAttributeIndex(indexList, masterList):

    returnList = []

    if len(indexList) > 0:
        for index in indexList:
            returnList.append(masterList[index])
    else:
        return False

    return returnList



##############################################################################
#
# attributeSearch(criteria, masterList)
#

def attributeSearch(criteria, masterList):

    # only four types of searches are currently supported
    #   (1)  *<search>
    #   (2)  <search>*
    #   (3)  *<search>*
    #   (4)  exact match (no asterisks are used)

    searchList = []

    asCount = criteria.count('*')

    if asCount == 0:
        # exact match requested
        # this criteria shouldn't ever get in this function, but check anyway
        # just to be safe
        return [criteria]

    if asCount > 2 or (criteria.startswith('*') == False and criteria.endswith('*') == False):
        # error -- too many asterisks defined
        print "Error:  Attribute search supports 2 asterisks maximum (positioned before or after text, not in-between characters)"
        return False

    if criteria.startswith('*') or criteria.endswith('*'):

        if criteria.startswith('*'):
            startswith = True
        else:
            startswith = False

        if criteria.endswith('*'):
            endswith   = True
        else:
            endswith   = False

        # remove all asterisks for character pattern matching
        criteria = criteria.replace('*', '')

        if startswith == True and endswith == True:
            for (index, name) in enumerate(masterList):
                if criteria in name:
                    searchList.append(index)

        elif startswith == True:
            for (index, name) in enumerate(masterList):
                if name.endswith(criteria):
                    searchList.append(index)

        else:
            for (index, name) in enumerate(masterList):
                if name.startswith(criteria):
                    searchList.append(index)

        return searchList

    else:
        print "Error:  Undefined problem with the attribute search criteria."
        return False



##############################################################################
#
# insertAttributeColumns(denaliVariables, attrLists, row)
#
#   This function takes the 'row' variable as the base starting point, and then
#   manipulates the attrLists dictionary.  Each attribute is assigned to a new
#   column for display.  Therefore, if the list of hosts has a combined 20
#   attributes, then there will be 20 additional columns (one per attribute).
#   Any host that doesn't have an attribute in an attribute column (all hosts
#   don't have all attributes), that row/column will be empty.
#
#   This assumes the following:
#
#       (1) The attribute_name and attribute_value are chosen for display.
#           If either of these is missing, this function will not work.
#           Previous code will catch this condition and reset the output
#           to display appropriately.
#       (2) The attribute_name will be the column header, with the
#           attribute_value being the column data.
#
#   There is a possibility (albeit, remote) that a set of 1000 servers will
#   have one (or potentially more) attributes that the next 1000 servers do
#   not have.  Hopefully that chances of that are extremely _remote_.
#
#   The first server analyzed will be the foundation for the attribute columns.
#   Every other server will check this first server's list and put the data
#   under the already established columns.  If a new attribute is found, it will
#   be added to the current list (at the end? and resorted later?) as the new
#   foundation for attribute columns.
#

def insertAttributeColumns(denaliVariables, attrLists, row):

    columnAppend = False

    attribute_column_width = 40

    # assign pertinent variables
    sqlParms     = denaliVariables["sqlParmsOriginal"]
    printColumns = denaliVariables["columnData"]

    # remove the attribute_name and attribute_value columns
    # they aren't needed in this display format
    if len(denaliVariables["attr_columns"]) == 0:
        # get attribute column numbers (zero-based)
        (nameColumn, valueColumn, inheritColumn) = getAttrColumns(denaliVariables)

        if nameColumn < valueColumn:
            printColumns.pop(nameColumn)
            printColumns.pop(valueColumn - 1)
            row.pop(nameColumn)                 # remove the "empty" row data
            row.pop(valueColumn - 1)            # to make room for inserts
        else:
            printColumns.pop(valueColumn)
            printColumns.pop(nameColumn - 1)
            row.pop(valueColumn)
            row.pop(nameColumn - 1)

    # see if there is any search criteria for this display format
    (attr_name, attr_value, attr_inheritance) = getSQLAttributeSearch(sqlParms)

    #
    # Step 1:  Build the column list for this row
    #

    # are we searching, or showing all attributes?
    if len(attr_name) == 0 and len(attr_value) == 0 and len(attr_inheritance) == 0:
        # show all attributes -- no search requested

        # see if the attributes in the list are already in the print columns variable
        # if not, add them in (at the end) -- use a 'set' difference to determine this
        missingAttributes = list(set(attrLists["attribute_name"]) - set(denaliVariables["attr_columns"]))
        missingAttributes.sort()

        if len(missingAttributes) > 0:
            for column in missingAttributes:
                columnAppend = True

                # column not found -- add it in (don't care about column order right now)
                # dv["ac"] -- stores just the attribute columns names/headers (for a quick look-up)
                # dv["cd"] -- stores the entire list of columns to be printed
                tempList = ["attr_" + column, "attr_" + column, column, attribute_column_width]
                denaliVariables["columnData"].append(tempList)
                denaliVariables["attr_columns"].append(column)

    else:
        # show specific attributes

        # attribute name search?
        if len(attr_name) > 0:

            for column in attr_name:
                if column[0] == True:               # wildcard search
                    wildList = attributeSearch(column[1], attrLists["attribute_name"])
                    if wildList == False:
                        return False                # improperly formated search; i.e., "*sc*mine*" <-- not allowed
                    else:
                        wildList = translateAttributeIndex(wildList, attrLists["attribute_name"])
                        if wildList == False:
                            continue                # not found; move to the next

                    missingAttributes = list(set(wildList) - set(denaliVariables["attr_columns"]))
                    missingAttributes.sort()

                    if len(missingAttributes) > 0:
                        for column in missingAttributes:
                            columnAppend = True

                            tempList = ["attr_" + column, "attr_" + column, column, attribute_column_width]
                            denaliVariables["columnData"].append(tempList)
                            denaliVariables["attr_columns"].append(column)
                else:
                    if column[2] not in denaliVariables["attr_columns"]:
                        columnAppend = True

                        tempList = ["attr_" + column[2], "attr_" + column[2], column[2], attribute_column_width]
                        denaliVariables["columnData"].append(tempList)
                        denaliVariables["attr_columns"].append(column[1])

        # attribute value search?
        if len(attr_value) > 0:

            for value in attr_value:
                if value[0] == True:                # wildcard search
                    wildList = attributeSearch(value[1], attrLists["attribute_value"])
                    if wildList == False:
                        return False                # improperly formated search; i.e., "*sc*mine*" <-- not allowed
                    else:
                        wildList = translateAttributeIndex(wildList, attrLists["attribute_name"])
                        if wildList == False:
                            continue                # not found; move to the next

                    missingAttributes = list(set(wildList) - set(denaliVariables["attr_columns"]))
                    missingAttributes.sort()

                    if len(missingAttributes) > 0:
                        for column in missingAttributes:
                            columnAppend = True

                            tempList = ["attr_" + column, "attr_" + column, column, attribute_column_width]
                            denaliVariables["columnData"].append(tempList)
                            denaliVariables["attr_columns"].append(column)
                else:
                    if value[2] in attrLists["attribute_value"]:
                        index = attrLists["attribute_value"].index(value[2])
                        columnName = attrLists["attribute_name"][index]
                        if columnName not in denaliVariables["attr_columns"]:
                            columnAppend = True

                            tempList = ["attr_" + columnName, "attr_" + columnName, columnName, attribute_column_width]
                            denaliVariables["columnData"].append(tempList)
                            denaliVariables["attr_columns"].append(columnName)

    #
    # Step 2: Add the data to the row in the proper column
    #

    for (index, column) in enumerate(denaliVariables["columnData"]):
        if column[0].startswith("attr_"):
            if column[2] in attrLists["attribute_name"]:
                attrIndex = attrLists["attribute_name"].index(column[2])

                if (len(row) - 1) < index:
                    row.append(attrLists["attribute_value"][attrIndex])
                else:
                    row[index] = attrLists["attribute_value"][attrIndex]
            else:
                # change this row's output to put a different text string in the cell
                # when attribute data isn't found; i.e. 'N/A' or '.' or '' <empty>

                # only update the cell's data if the index fits within the list length
                # -- otherwise there will be an IndexError.  With no update the column
                # will be empty.
                # query that will expose this problem (without the index check here):
                #  --hosts="*smurf*" -f name ATTRIBUTES --attribute_name="PUPPET_GIT_REPO OR PUPPET_GIT_SERVER" --attrcolumns
                # without "--attrcolumns", the query/display works fine.
                if index < len(row):
                    row[index] = ''

    # remove any remaining "None" data elements from the row
    #for (index, dataColumn) in enumerate(row):
    #    if dataColumn == None:
    #        row[index] = ''


    # if auto resize is enabled, check and see if attribute column sizes need to be adjusted
    # this is injecting straight into the column data ... so make sure it is correct or the
    # display will look terrible
    GUTTER_SIZE = 2
    if denaliVariables['autoColumnResize'] == True:
        for (cIndex, column) in enumerate(denaliVariables['columnData']):
            columnData_name = column[2]
            columnData_size = column[3]
            if columnData_name in denaliVariables['attributeColumnSizes']['columns']:
                asc_size = denaliVariables['attributeColumnSizes']['columns'][columnData_name]
                if asc_size < columnData_size:
                    denaliVariables['columnData'][cIndex][-1] = asc_size + GUTTER_SIZE

    return [row]



##############################################################################
#
# insertStackedAttributeColumns(denaliVariables, attrLists, row)
#
#   denaliVariables = system-wide data storage variables
#   attrLists       = dictionary containing the attribute data (name, value, inheritance)
#   row             = row data without attribute information inserted ... yet
#
#   This function takes the 'row' variable as the base starting point, and then
#   manipulates the attrLists dictionary and inserts it into the row.  It
#   creates multiple rows (as each attribute name requires its own row).  The
#   resulting set of rows is stored in 'rowData' and returned to the calling
#   function.
#

def insertStackedAttributeColumns(denaliVariables, attrLists, row):

    rowData = []
    rowTemp = []

    # set to "True" to show all attributes when searching for a specific one (or ones)
    showAllAttributes = False

    # assign pertinent variables
    sqlParms     = denaliVariables["sqlParmsOriginal"]
    printColumns = denaliVariables["columnData"]

    # get attribute column numbers
    (nameColumn, valueColumn, inheritColumn) = getAttrColumns(denaliVariables)

    # collect the sql search criteria for attributes
    (attr_name, attr_value, attr_inheritance) = getSQLAttributeSearch(sqlParms)

    # if no search criteria was entered -- show all of the attributes
    if len(attr_name) == 0 and len(attr_value) == 0 and len(attr_inheritance) == 0:
        showAllAttributes = True

    if showAllAttributes == True:
        # fill in the initial value (with other existing column data)
        for (index, column) in enumerate(printColumns):
            if column[0] in attrLists:
                row[index] = attrLists[column[0]][0]
            elif column[0] == 'attribute_overrides_id' and denaliVariables['attributeOverride'] == True:
                if attrLists['attribute_inheritance'][0] != '0':
                    row[index] = 'Yes'
                else:
                    row[index] = ''
            elif column[0] == 'attribute_inherited_id' and denaliVariables['attributeInherit'] == True:
                if attrLists['attribute_inheritance'][0] == '0':
                    row[index] = 'No'
                else:
                    row[index] = ''

                # actual attribute_data_id number ... not used for now
                # this is what should be used, but it needs to show the name of the owner of
                # the attribute, like the device service, or environment, etc.
                #row[index] = attrLists['attribute_inheritance'][0]

        rowData.append(row)

        # start on the second attribute because the first is integrated already
        rangeStart = 1
    else:
        rangeStart = 0

    # The only time this code (function) is executed is if two or three attribute
    # columns are requested for display.  Therefore, for the length of the column,
    # pick either the attribute_name column, or if it doesn't exist the
    # attribute_value column will.
    if "attribute_name" in attrLists:
        attrLength = len(attrLists["attribute_name"])
    else:
        attrLength = len(attrLists["attribute_value"])

    for item in range(rangeStart, attrLength):
        # blank row for the new data
        newRow = ['' for index in range(len(row))]

        for (index, column) in enumerate(printColumns):
            if column[0] in attrLists:
                newRow[index] = attrLists[column[0]][item]
            elif column[0] == 'attribute_overrides_id' and denaliVariables['attributeOverride'] == True:
                # Execute this code if the override id was requested:
                # attributes are attached to a single output, but have many lines, so any
                # alterations are done here (i.e., the 'yes' and blank outputs)
                if attrLists['attribute_inheritance'][item] != '0':
                    newRow[index] = 'Yes'
                else:
                    newRow[index] = ''
            elif column[0] == 'attribute_inherited_id' and denaliVariables['attributeInherit'] == True:
                if attrLists['attribute_inheritance'][item] == '0':
                    newRow[index] = 'No'
                else:
                    newRow[index] = ''

                # actual attribute_data_id number ... not used for now
                # this is what should be used, but it needs to show the name of the owner of
                # the attribute, like the device service, or environment, etc.
                #newRow[index] = attrLists['attribute_inheritance'][item]

        # if a specific search criteria for attributes was requested, the showAllAttributes
        # value will be 'False' -- meaning, only show some of the attributes (if found)
        if showAllAttributes == False:
            # Searching attributes here is a little odd.
            # The criteria entered in denali is put into an SQL statement.  The SQL statement
            # is not case-sensitive.  Once the host(s) is/are found that fulfill this query,
            # that host's data is then searched to see if its attributes match the criteria
            # (which now _is_ case-sensitive).  This means that the same search criteria is
            # effectively used twice (once for the host discovery, and secondly for the attribute
            # matching).

            # Attribute matching is also a little odd.
            # If a wilcard is specified it describes that ALL matches (beginning, middle, end) are
            # caught and shown as a valid match.  What this means is if a server is shown as
            # having the attribute pattern (sql search), and "*yum" is specified, it will match
            # all occurrences of the "yum" attribute name at the beginning, middle or end of the
            # name.  It will not honor the EXACT search criteria, just if that set of characters is
            # found anywhere in the attribute name/value, etc.  If an exact pattern match is wanted,
            # more code is needed to describe this functionality.

            if len(attr_name) != 0:
                #
                # Each attr_name stores two values  True/False, and the search criteria
                #   if "True" it means a wildcard search is requested
                #   if "False" it means no wildcard was used -- assume an exact match
                #   attribute_name: [ [True, 'oak1'], [False, 'lon5'], ... ]  etc.
                #
                # The search here is case sensitive.  YUM != yum.
                # Add .lower() to the "if" statements to change this functionality.
                #   e.g., if name[2] in newRow[nameColum].lower():
                #
                for name in attr_name:
                    if name[0] == True:
                        if name[2] in newRow[nameColumn]:      # wildcard match
                            rowTemp.append(newRow)
                    else:
                        if name[2] == newRow[nameColumn]:      # exact match
                            rowTemp.append(newRow)

            elif len(attr_value) != 0:
                for value in attr_value:
                    if value[0] == True:
                        if value[2] in newRow[valueColumn]:
                            rowTemp.append(newRow)
                    else:
                        if value[2] == newRow[valueColumn]:
                            rowTemp.append(newRow)

            elif len(attr_inheritance) != 0:
                for inherit in attr_inheritance:
                    if inherit[0] == True:
                        if inherit[2] in newRow[inheritColumn]:
                            rowTemp.append(newRow)
                    else:
                        if inherit[2] == newRow[inheritColumn]:
                            rowTemp.append(newRow)

        else:
            # value is True; show all attributes
            rowData.append(newRow)

    # Catch all :: In case something goes wrong with data filtering above
    # Better to error out (on purpose) than return a python error
    if showAllAttributes == False:
        if len(rowTemp) == 0:
            print "Error: No attribute data collected (search sql criteria)"
            denali_search.cleanUp(denaliVariables)
            exit(1)
    else:
        if len(rowData) == 0:
            print "Error: No attribute data collected (all attributes)"
            denali_search.cleanUp(denaliVariables)
            exit(1)

    # put the initial row together
    if showAllAttributes == False:
        # fill in the initial value (with other existing column data)

        for (index, column) in enumerate(printColumns):

            if column[0] in attrLists:
                row[index] = rowTemp[0][index]

        rowData.insert(0, row)

        # if there is more than one row identified in the search, include
        # the other rows (rowTemp) here
        if len(rowTemp) > 1:
            # remove row[0] -- it has already been used
            rowTemp.pop(0)

            for row in rowTemp:
                rowData.append(row)

    return rowData



##############################################################################
#
# stripUnicodeTrappings(data)
#

def stripUnicodeTrappings(data):

    # remove all unicode "trappings" from the response
    data = unicode(data).replace("{u'", "")
    data = unicode(data).replace("'}", "")
    data = unicode(data).replace("[u'", "")
    data = unicode(data).replace("', u'", ",")
    data = unicode(data).replace("', u\"", ",")
    data = unicode(data).replace("\"]", "")
    data = unicode(data).replace("']", "")
    data = unicode(data).replace("[]", "")
    data = unicode(data).replace(": u'", ": '")
    data = data.strip()

    return data



##############################################################################
#
# singleAttributeColumn(denaliVariables)
#

def singleAttributeColumn(denaliVariables):

    fieldColumns = denaliVariables["fields"].split(',')
    count        = 0

    for field in fieldColumns:
        if (field == "attribute_data.attribute.name" or
            field == "attribute_data.value" or
            field == "attribute_data.inherited_from_attribute.value"):

            count += 1

    if count == 1:
        return True
    else:
        return False



##############################################################################
#
# getAttrColumns(denaliVariables)
#

def getAttrColumns(denaliVariables):

    nameColumn    = -1
    valueColumn   = -1
    inheritColumn = -1

    for (index, field) in enumerate(denaliVariables["fields"].split(',')):

        if field == "attribute_name" or field == "attribute_data.attribute.name":
            nameColumn = index
        elif field == "attribute_value" or field == "attribute_data.value":
            valueColumn = index
        elif (field == "attribute_inheritance" or
              field == "attribute_data.inherited_from_attribute.value" or
              field == "attribute_data.inherited_attribute_data_id" or
              field == "attribute_data.overrides_attribute_data_id"):
            inheritColumn = index

    return (nameColumn, valueColumn, inheritColumn)



##############################################################################
#
# extractHostList(responseDictionary)
#
#   This function pulls out the list of hosts returned from the query and
#   plugs it into denaliVariables["serverList"]
#

def extractHostList(responseDictionary):
    host_list = []

    responseDictionary = responseDictionary["data"]["results"]

    for host_response in responseDictionary:
        host_list.append(host_response["name"])

    return host_list



##############################################################################
#
# dataItemIncrement(data_item, combined_count_dict, index, what_to_count)
#

def dataItemIncrement(data_item, combined_count_dict, index, what_to_count):

    newCount     = int(data_item[what_to_count])
    data         = combined_count_dict[index].split('::')
    data[1]      = str(int(data[1]) + newCount)
    combined_count_dict[index] = data[0] + '::' + data[1]

    return



##############################################################################
#
# dataItemMatch(data_item, combined_count_dict, what_to_count)
#
#   data_item           : single item from denaliVariables batch storage
#   combined_count_dict : dictionary with combined data in it
#   what_to_count       : what key in the dictionary stores the count
#

def dataItemMatch(data_item, combined_count_dict, what_to_count):

    match = False
    index = 0

    data_morphed = modifyData(data_item, what_to_count)
    data_morphed = data_morphed.split('::')
    data         = data_morphed[0]

    for combined_item in combined_count_dict:
        combined_morphed = combined_item.split('::')
        combined_data    = combined_morphed[0]

        if data == combined_data:
            match = True
            break
        else:
            index += 1
    else:
        return (False, 0)

    return (match, index)



##############################################################################
#
# modifyData(data_item, what_to_count)
#

def modifyData(data_item, what_to_count):

    modified_data = ''
    count         = 0

    data_keys = data_item.keys()
    data_keys.sort()

    for key in data_keys:
        if key == what_to_count:
            count = str(data_item[key])
            continue

        if len(modified_data) == 0:
            modified_data  = key + ':' + str(data_item[key])
        else:
            modified_data += ',' + key + ':' + str(data_item[key])

    modified_data += '::' + count

    return modified_data



##############################################################################
#
# combineCountedData(denaliVariables)
#

def combineCountedData(denaliVariables):

    combined_count_dict = []

    count_data = denaliVariables['methodData']
    count_data = count_data.split(':')

    what_to_count    = count_data[0]
    count_categories = count_data[1]

    for data_item in denaliVariables['batchDeviceData']['data']['results']:
        if len(combined_count_dict) == 0:
            # first item -- add it
            modified_data = modifyData(data_item, what_to_count)
            combined_count_dict.append(modified_data)
            continue

        (ccode, index) = dataItemMatch(data_item, combined_count_dict, what_to_count)
        if ccode == False:
            # item doesn't exist -- add it
            modified_data = modifyData(data_item, what_to_count)
            combined_count_dict.append(modified_data)
            continue
        else:
            # item exists -- increment the proper counter
            dataItemIncrement(data_item, combined_count_dict, index, what_to_count)

    # modify combined data to resemble the original dictionary
    reassembleDictionaryStructure(denaliVariables, combined_count_dict, what_to_count)



##############################################################################
#
# reassembleDictionaryStructure(denaliVariables, combined_count_dict, what_to_count)
#

def reassembleDictionaryStructure(denaliVariables, combined_count_dict, what_to_count):

    for (index, keys_values) in enumerate(combined_count_dict):
        combined_count_dict[index] = {}
        keys_values = keys_values.split(',')

        for kv_pair in keys_values:
            kv_pair = kv_pair.split(':')
            key     = kv_pair[0]
            value   = kv_pair[1]

            if len(kv_pair) > 2 and kv_pair[2] == '':
                key_count = what_to_count
                value_count = kv_pair[3]
                combined_count_dict[index].update({key_count:value_count})

            combined_count_dict[index].update({key:value})

    denaliVariables['batchDeviceData']['data']['results'] = combined_count_dict

    return True



##############################################################################
#
# batchedDeviceRequest(denaliVariables, subData)
#
#   Store in denaliVariables['batchDeviceData']
#

def batchedDeviceRequest(denaliVariables, subData):

    method = denaliVariables['method']

    if method == 'search' or method == 'count':
        if denaliVariables['batchDeviceData'] == {}:
            denaliVariables['batchDeviceData'] = subData
        else:
            denaliVariables['batchDeviceData']['data']['results'].extend(subData['data']['results'])
    else:
        print "Batch method = %s" % method

    if batchProcessingCompleted(denaliVariables) == True:
        # only combine counted data after it has all been retrieved (run the count routine once)
        if 'final_key' in denaliVariables['batchDeviceList'] and method == 'count':
            combineCountedData(denaliVariables)
            (printData, overflowData) = denali_search.generateOutputData(denaliVariables['batchDeviceData'], denaliVariables)
            denali_search.prettyPrintData(printData, overflowData, denaliVariables['batchDeviceData'], denaliVariables)

        elif 'final_key' in denaliVariables['batchDeviceList'] or denaliVariables['method'] != 'count':
            #(printData, overflowData) = denali_search.generateOutputData(denaliVariables['batchDeviceData'], denaliVariables)
            (printData, overflowData) = denali_search.generateOutputData(subData, denaliVariables)
            if denaliVariables['monitoring'] == False:
                # If monitoring was requested DO NOT print the output
                # Monitoring itself will make a call to output the data
                denali_search.prettyPrintData(printData, overflowData, denaliVariables['batchDeviceData'], denaliVariables)
        else:
            printData = []

    return len(printData)



##############################################################################
#
# batchProcessingCompleted(denaliVariables)
#

def batchProcessingCompleted(denaliVariables):

    # for the 'count' method, the number of hosts submitted will likely
    # never match the output rows, so just print what is there
    if denaliVariables['method'] == 'count':
        return True

    host_count  = denaliVariables['batchTotalCount']
    batch_count = len(denaliVariables['batchDeviceData']['data']['results'])

    if host_count == batch_count:
        return True
    else:
        if denaliVariables['debug'] == True:
            print "host_count  = %s" % host_count
            print "batch_count = %s" % batch_count

    return True



##############################################################################
#
# batchDeviceList(denaliVariables)
#
#   This function copies sets of devices/hsots from the existing list, and
#   cuts them up into groups of maxRows (whatever the setting is for the maximum
#   number of rows).
#

def batchDeviceList(denaliVariables):

    maxRows     = denaliVariables['maxSKMSRowReturn']
    total_count = len(denaliVariables['serverList'])

    denaliVariables['batchTotalCount'] = total_count

    # turn on batching mode, if appropriate
    if total_count > maxRows:
        denaliVariables['batchDevices'] = True
    else:
        return False

    # separate the hosts into batches of maxRows and store them in batchDeviceList
    count      = 0
    start      = 0
    interval   = maxRows

    while (True):
        start  = (interval * count)
        end    = (start + interval)
        count += 1

        # adjust start/end points of the devices
        if start >= total_count:
            break
        if end > total_count:
            end = total_count

        device_batch = denaliVariables['serverList'][start:end]
        denaliVariables['batchDeviceList'].update({count:device_batch})

    return True



##############################################################################
#
# combineBatchedDeviceNames(denaliVariables)
#
#   This function is run when a batched set of hosts has finished processing
#   and that group needs to be combined for further work (like a monitoring
#   query).

def combineBatchedDeviceNames(denaliVariables):

    combined_hostnames = []

    batch_keys = denaliVariables['batchDeviceList'].keys()
    for batch in batch_keys:
        if batch == 'final_key':
            continue
        combined_hostnames += denaliVariables['batchDeviceList'][batch]

    denaliVariables['serverList'] = combined_hostnames

    return True



##############################################################################
#
# getSQLAttributeSearch(sqlParms)
#
#   sqlParameters is a List of Lists.  Each List (inside the main List) describes
#   a specific search criteria.
#   Example:
#       --attribute_name="COBBLER_PROFILE OR *YUM* OR *MENT"
#           [ [False, 'COBBLER_PROFILE', 'COBBLER_PROFILE'], [True, '*YUM*', 'YUM'], [True, '*MENT', 'MENT'] ]
#
#       --attribute_name="PHP_VER" --attribute_value="5.4 OR SCREQ"
#           [ [False, '--attribute_name', 'PHP_VER'], [False, '--attribute_value', '5.4 OR SCREQ'], ... ]
#
#   The "True" and "False" indicate whether or not a wildcard is located in the search criteria.
#

def getSQLAttributeSearch(sqlParameters):

    # temporary storage dictionary for sql attribute search criteria
    sqlAttrValues = { "attr_name"   : [],
                      "attr_value"  : [],
                      "attr_inherit": []  }

    for sqlSearchValues in sqlParameters:

        if sqlSearchValues[0] == "--attribute_name":
            key = "attr_name"
        elif sqlSearchValues[0] == "--attribute_value":
            key = "attr_value"
        elif sqlSearchValues[0] == "--attribute_inheritance":
            key = "attr_inherit"
        else:
            continue

        if len(sqlSearchValues[1]) > 0:
            value = sqlSearchValues[1]

            if " AND " in value or " OR " in value or " NOT " in value:
                value = value.replace(" AND ", ' ')     # AND qualifier
                value = value.replace( " OR ", ' ')     # OR  qualifier
                value = value.replace(" NOT ", ' ')     # NOT qualifier
                value = value.replace("  ",    ' ')     # double spaces -> single

                # split the criteria according to spaces
                values = value.split(' ')
                for (index, item) in enumerate(values):
                    # create an empty List
                    sqlAttrValues[key].append([])

                    if '*' in item:
                        sqlAttrValues[key][index].append(True)
                    else:
                        sqlAttrValues[key][index].append(False)

                    sqlAttrValues[key][index].append(item.strip())
                    item = item.replace('*', '')
                    sqlAttrValues[key][index].append(item.strip())

            else:
                sqlAttrValues[key].append([])

                if '*' in value:
                    sqlAttrValues[key][0].append(True)
                else:
                    sqlAttrValues[key][0].append(False)

                sqlAttrValues[key][0].append(value.strip())
                value = value.replace('*', '')
                sqlAttrValues[key][0].append(value.strip())

        else:
            # if there is a bad/corrupted input value here, just skip it
            # and move on to the next one to process
            continue


    return (sqlAttrValues["attr_name"],
            sqlAttrValues["attr_value"],
            sqlAttrValues["attr_inherit"])



##############################################################################
#
# oooAuthentication(denaliVariables)
#
#   Out of Order authentication.  This is called when a user needs to authenticate
#   to SKMS in a different order than the default (which should take care of 99%
#   of the use-cases).  Currently the findServerIPHosts() ... just below ... uses
#   this function because the host list is built first (expansion, ranges, etc.)
#   before the user authenticates, which makes this call important; otherwise, the
#   query will fail.
#
#   This function will determine if the command line was given with a specified
#   username, or if a credentials file was provided.  In either case, the code
#   will properly handle that and authenticate as needed.
#

def oooAuthentication(denaliVariables):

    userAuth = False
    credAuth = False
    credFile = ''

    denaliVariables['time']['skms_auth_start'].append(time.time())

    for parameter in denaliVariables["cliParameters"]:
        if parameter[0] == "--user":
            userAuth = True
            break
        elif parameter[0] == "--creds":
            credAuth = True
            credFile = parameter[1]
            break

    if userAuth == False and credAuth == False:
        print "Denali Error:  Undetected method of authenticating against SKMS.  Execution halted."
        return False

    if userAuth == True:
        # username authentication
        ccode = denali_authenticate.authenticateAgainstSKMS(denaliVariables, "username")
    else:
        # credentials file authentication
        (username, password) = denali_authenticate.readCredentialsFile(credFile, denaliVariables)
        ccode = denali_authenticate.authenticateAgainstSKMS(denaliVariables, "credentials", username, password)

    denaliVariables['time']['skms_auth_stop'].append(time.time())

    if ccode == False:
        # authentication failed -- exit
        return False
    else:
        return True



##############################################################################
#
# findServerIPHosts(denaliVariables)
#
#   This function takes the submitted server list, and searches for IP Addresses
#   that may be included.  With that list of addresses, a query is made for the
#   hostnames (in the function createServerListFromArbitraryQuery), and then those
#   names are included with the original server list (minus ip addresses) to have
#   the final search done and output (or passed on to the command/monitoring
#   module).
#

def findServerIPHosts(denaliVariables):

    ipHostList    = []
    modServerList = []
    commandPing   = False

    for host in denaliVariables['serverList']:
        if host.count('.') == 3:
            host = host.split('.')
            value1 = host[0]
            value2 = host[1]
            value3 = host[2]
            value4 = host[3]
            # see if this is a CIDR address
            if value4.find('/') != -1 and value4.split('/')[1].isdigit() == True:
                # cidr address found ... expand it
                cidr_data = cidrAddressData(denaliVariables, '.'.join(host))
                if cidr_data == "False":
                    # error condition triggered -- ignore the error, and print what can
                    # be successfully processed
                    pass
                else:
                    ipHostList.extend(cidr_data['address_list'])
            elif value1.isdigit() and value2.isdigit() and value3.isdigit():
                ipHostList.append('.'.join(host))
            else:
                modServerList.append('.'.join(host))
        else:
            modServerList.append(host)

    modServerList = list(set(modServerList))

    # check for -c ping in the cliParameters
    for parameter in denaliVariables['cliParameters']:
        if (parameter[0] == '-c' or parameter[0] == '--command') and parameter[1].startswith('ping'):
            commandPing = True
            break

    if len(ipHostList) and commandPing == False:
        # take the IP list and add it to the sqlParameters with "--ip"
        # then do a CMDB query for all hostnames that match the submitted
        # ip addresses

        # enable the query to run
        if denaliVariables['api'] is None:
            # this could mean that it is the first time the user/creduser has run denali today,
            # and because of this they aren't configured with a session file yet.  take care of
            # that now.
            ccode = oooAuthentication(denaliVariables)
            if ccode == False:
                return "False"
            retrieveAPIAccess(denaliVariables)

        # this setting is so that the ip address(es) can match any hostname found
        denaliVariables['serverList'] = ['*']
        denaliVariables['sqlParameters'].append(['--ip_address', ' OR '.join(ipHostList)])
        ccode = createServerListFromArbitraryQuery(denaliVariables, searchDao='DeviceDao')
        if ccode == False:
            # No hosts found with ip addresses -- just take the original
            # hosts (if any) and query for them
            denaliVariables['serverList'] = modServerList
        else:
            # createServerListFromArbitraryQuery returns with the serverList populated.
            # Extend that list with whatever was given (other host names?).
            denaliVariables['serverList'].extend(modServerList)

        # remove the ip address sql parameter
        denaliVariables['sqlParameters'] = denaliVariables['sqlParameters'][:-1]

        # disable the api variable -- so the next query can run (the code looks for)
        # this and stops if it is on, thinking multiple queries are happening.
        denaliVariables['api'] = None

    return denaliVariables['serverList']



##############################################################################
#
# cidrAddressData(denaliVariables, cidrAddress)
#
#   This function takes an ip address in CIDR notation (x.x.x.x/##), and returns
#   a dictionary with data concerning that address.
#

def cidrAddressData(denaliVariables, cidrAddress):

    MAX_CIDR_VALUE  = 21
    ip_address_data = {}

    (addrString, cidrString) = cidrAddress.split('/')

    addr = addrString.split('.')
    cidr = int(cidrString)
    mask = [0, 0, 0, 0]
    net  = []

    # don't let someone go crazy and put in a '0' representing 4 billion addresses
    # that would be stupid.  limit this to 21 or greater.
    if cidr < MAX_CIDR_VALUE:
        print "CIDR value submitted [/%s] represents a larger network than supported." % cidr
        print "Value must be /%i or greater." % MAX_CIDR_VALUE
        return "False"

    for i in range(cidr):
        mask[i/8] = mask[i/8] + (1 << (7 - i%8))

    for i in range(4):
        net.append(int(addr[i]) & mask[i])

    broad  = list(net)
    brange = 32 - cidr

    for i in range(brange):
        broad[3 - i/8] = broad[3 - i/8] + (1 << (i%8))

    # Locate usable IPs
    hosts = {'first': list(net), 'last':list(broad)}
    hosts['first'][3]       # typically the first address (.0) is removed ( += 1 to do that)
    hosts['last'][3]        # typically the last address (.255) is removed ( -= 1 to do that)

    # Count the difference between first and last host IPs
    hosts['count'] = 0
    for i in range(4):
        hosts['count'] += (hosts['last'][i] - hosts['first'][i]) * 2**(8*(3-i))

    # assign the data to the dictionary
    ip_address_data.update({'cidr'         : '%s/%s' % (addrString, cidr)})
    ip_address_data.update({'address'      : addrString})
    ip_address_data.update({'netmask'      : '.'.join(map(str, mask))})
    ip_address_data.update({'network'      : '.'.join(map(str, net))})
    ip_address_data.update({'broadcast'    : '.'.join(map(str, broad))})
    ip_address_data.update({'host_range'   : '%s - %s' % ('.'.join(map(str, hosts['first'])), '.'.join(map(str, hosts['last'])))})
    ip_address_data.update({'host_count'   : hosts['count']})
    ip_address_data.update({'address_list' : []})

    # addresses in the range
    i = struct.unpack('>I', socket.inet_aton(addrString))[0]

    startAddress = (i >> brange) << brange
    endAddress   = startAddress | (1 << brange)

    if startAddress == endAddress:
        # Problem: start and end addresses are the same, so no addresses will be
        #          discovered.
        # This problem has been observed with /21 CIDR address (/22 works fine).
        # Fix for this is to manually calculate the ending address:
        #   (1) Decrease the brange by 1, bit-shifting to get the number of addresses
        #   (2) Multiply that value by two
        #   (3) Using basic addition, get the corrent ending address value
        diff = (1 << (brange-1))
        endAddress = startAddress + (diff * 2)

    for i in range(startAddress, endAddress):
        ip_address_data['address_list'].append("%s" % (socket.inet_ntoa(struct.pack('>I', i))))

    return ip_address_data



##############################################################################
#
# getDeltaTimeDifference(time1, time2)
#
#   Given two times, determine the difference between them with the result as
#   a string -- "1 day, 23:46:40", representing 1 day, 23 hr, 46 min, 40 secs.
#
#   time1 is the start time.
#   time2 is the ending time.
#
#   times are assumed to be in the format:  YYYY-MM-DD HH:MM:SS
#

def getDeltaTimeDifference(time1, time2):

    pattern = "%Y-%m-%d %H:%M:%S"

    # convert from datetime to epoch
    epoch1 = int(time.mktime(time.strptime(time1, pattern)))
    epoch2 = int(time.mktime(time.strptime(time2, pattern)))

    #            stop   - start
    difference = epoch2 - epoch1

    # epoch time to strftime
    #dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(epoch))

    delta = str(datetime.timedelta(seconds=difference))

    days_marker = delta.find('day')
    if days_marker != -1:
        days = int(delta[:(days_marker - 1)])
        if days == 1:
            delta = delta[:(days_marker - 1)] + 'd ' + delta[(days_marker + 5):]
        else:
            delta = delta[:(days_marker - 1)] + 'd ' + delta[(days_marker + 6):]

    hour_marker = delta.find(':')
    delta       = delta[:hour_marker] + 'h ' + delta[(hour_marker + 1):]
    min_marker  = delta.find(':')
    delta       = delta[:min_marker]  + 'm'

    return delta
