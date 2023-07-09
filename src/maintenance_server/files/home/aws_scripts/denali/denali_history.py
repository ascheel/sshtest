#! /usr/bin/env python


#############################################
#
# denali_history.py
#
#############################################
#
#   This module contains the code to allow queries to retrieve CMDB
#   history for multiple devices.
#
#   Typically this type of logic would be handled in an external module for
#   denali.  However, it is included with a switch of its own to make it
#   feel more integrated.
#
#   This module is a little "weird" because it accepts all of the normal SQL
#   statements; however they are slightly modified with a leading "hist_".
#   The history search is done in two separate searches (all from the same
#   set of command line parameters):
#       (1) Device IDs
#       (2) History for the device IDs found
#
#   What this means is that all sql modifiers on a search will initially be
#   used to search for the device IDs (the hosts).  They are then tossed out
#   and completely ignored by the history search.  To get a command line
#   parameter through to the history search, it must be preceeded by the
#   text: "hist_".  For example, a normal sort is --sort=name.  However, for
#   sorting the history it is --hist_sort=name.  With the "hist_" denali will
#   assume it is meant directly for history search and pass it on to be used
#   and manipulated in this module's code.  It will be completely ignored for
#   the device ID search.  The same idea goes with any history searching.
#   If something in the details is wanted, "--hist_details=<something>" would
#   be the syntax used to pass it through the second search.
#

import denali
import denali_search
import denali_utility

import datetime

from denali_tty import colors

##############################################################################
##############################################################################
#
# getLongestHostname(serverList)
#
#   This function determines the character length of the largest hostname
#

def getLongestHostname(serverList):

    hostLength = 0

    # determine the character count of the longest hostname
    for host in serverList:
        length = len(host)

        if length > hostLength:
            hostLength = length

    return hostLength



##############################################################################
#
# archiveHistoryDaoUse(denaliVariables, sqlParameters)
#
#   This function examines the sql parameter variable(s) submitted to determine
#   if a date older than 30 days was requested.
#
#   If date older than 30 days requested:  return True.
#   If date less than or equal to 30 days requested:  return False.
#

def archiveHistoryDaoUse(denaliVariables, sqlParameters):

    # get the current date
    currentDate = (datetime.datetime.now().strftime("%Y-%m-%d")).split('-')
    year        = int(currentDate[0])
    month       = int(currentDate[1])
    day         = int(currentDate[2])
    currentDate = datetime.date(year, month, day)

    # Roll through each of the sql parameters and see if any are named
    # 'datetime'.  If so, look at the date associated with it and then
    # do a delta time operation to determine the number of days between
    # the specified date and the current date.
    #
    # If the delta between dates is > 30 days, then set the return flag
    # from this function to "True" so the code will access
    # the SkmsArchiveHistoryDao during its search process.
    # during its search run.
    for parameter in sqlParameters:
        if parameter[0] == "datetime":
            hist_date = parameter[1]
            # remove any unnecessary characters for this check
            if hist_date[0] == '>' or hist_date[0] == '<' or hist_date[0] == '=':
                hist_date = hist_date[1:]

            # determine if the month/day was used
            hist_date_check = hist_date.split('-')
            if len(hist_date_check) == 1:
                # year only -- add "-01-01" to it (January 1)
                hist_date += "-01-01"
            elif len(hist_date_check) == 2:
                # year-month -- add "-01" to it (1st day of the month)
                hist_date += "-01"

            hist_date_check = hist_date.split('-')
            hist_year       = int(hist_date_check[0])
            hist_month      = int(hist_date_check[1])
            hist_day        = int(hist_date_check[2])
            hist_date       = datetime.date(hist_year, hist_month, hist_day)
            delta_days      = (currentDate - hist_date).days

            # if the delta between dates is > 30 days, then set
            # the switch to access to the archive history dao
            if delta_days > 30:
                return True

    return False



##############################################################################
#
# buildGenericHistorySQL(denaliVariables)
#

def buildGenericHistorySQL(denaliVariables):

    sqlParameters  = []
    daoDateData    = {}     # MRASEREQ-41538
    dateSQLElement = None

    if len(denaliVariables["historySQLQuery"]) > 0:
        # add the history sql to the sql parameters
        for histsql in denaliVariables["historySQLQuery"]:
            if histsql[0] == "sort":
                denaliVariables["sqlSort"] = histsql[1]
                continue
            sqlParameters.append(histsql)

    #
    # Massage date range - if it exists
    # MRASEREQ-41538:  work out any DAO date ranges before the main loop
    dao_date_ranges = ['history_datetime', 'datetime']
    for parameter in sqlParameters:
        # Check for DAO start date with 'day', 'week', 'month', or 'year' in it -- translate appropriately
        if parameter[0] in dao_date_ranges:
            if len(daoDateData) == 0:
                daoDateData.update({'date1':parameter[1]})
            else:
                daoDateData.update({'date2':parameter[1]})

    # MRASEREQ-41538
    if len(daoDateData):
        (ccode, dateSQLElement) = denali_utility.daoTimeMethodMassage(denaliVariables, daoDateData, parameter[0])
        if ccode == False:
            return False

    if dateSQLElement is None:
        dateSQLElement = sqlParameters

    return dateSQLElement



##############################################################################
#
# executeHistoryQuery(denaliVariables, deviceDict, history_dao, previousItemCount, savedTruncate, savedWrap)
#

def executeHistoryQuery(denaliVariables, deviceDict, history_dao, previousItemCount, savedTruncate, savedWrap):

    toggleHeaders = False

    if previousItemCount > 0 and denaliVariables["showHeaders"] == True:
        toggleHeaders = True
        denaliVariables["showHeaders"] = False

    #
    # step 6:
    #   Manually build the sql query
    # not exactly awesome here -- the query is built by hand
    # this is a little restrictive in that the code doesn't allow "any" field to be selected/printed
    # hopefully the set below is comprehensive enough.  omnitool restricts output as well -- maybe this will be "understood"
    sqlQuery  = "%s:SELECT %s " % (history_dao, denaliVariables["fields"])
    sqlQuery += "WHERE subject_type_label.value = 'Device'" + denaliVariables["sqlParameters"]

    # handle sorting -- if nothing specified, sort decreasing, by date/time
    if denaliVariables["sqlSort"] == '':
        # default sort -- descending by date
        sqlQuery += " ORDER BY history_datetime DESC"
    else:
        sqlQuery += denaliVariables["sqlSort"]

    if denaliVariables["debug"] == True:
        print "history sql query = %s" % sqlQuery

    #
    # step 7:
    #   Send the query off, get the retrieved data and print the results
    respDictionary = denali_search.constructSQLQuery(denaliVariables, sqlQuery, False)
    (printData, overflowData) = denali_search.generateOutputData(respDictionary, denaliVariables)

    # new data is probably larger than the columns -- wrap it and then print it (unless nowrap was specified)
    denaliVariables["textTruncate"] = savedTruncate
    denaliVariables["textWrap"]     = savedWrap

    # swap out the current host's device id for the host's hostname
    printData = swapDeviceIDForHostName(printData, deviceDict)

    # because the history feature acts like an external module, the code must do
    # everything manually -- including limiting the number of rows printed
    if denaliVariables["limitCount"] > 0:
        printData = limitDisplayRowPrinting(denaliVariables, printData, previousItemCount)

    (printData, overflowData) = denali_search.wrapColumnData(denaliVariables, printData)
    itemCount = len(printData) + previousItemCount
    denali_search.prettyPrintData(printData, overflowData, respDictionary, denaliVariables)

    if toggleHeaders == True:
        denaliVariables["showHeaders"] = True

    return (itemCount, sqlQuery)



##############################################################################
#
# deviceHistoryRequest(denaliVariables, queryData)
#
#   Main delegative function to handle history queries against CMDB.
#   Received from the caller is denaliVariables and the response data from the
#   query.  This queryData will contain two columns:  device name, device id,
#   for each device submitted.
#

def deviceHistoryRequest(denaliVariables, queryData):

    if queryData == False:
        print "History:  Device ID queryData is empty; history search not implemented."
        return False

    #
    # step 1:
    # Pull out the device IDs -- store them in a dictionary
    (deviceDict, hostListDict) = pullDeviceIDsFromQueryData(queryData)
    if deviceDict == False:
        if denaliVariables["debug"] == True:
            print "History query responseDictionary is empty"
        return False

    if "deviceCount" not in deviceDict or deviceDict["deviceCount"] == 0:
        print "History device count is zero."
        return False

    #
    # step 2:
    #   Set up the basic query variables
    #   denali --dao=HistoryDao --fields=subject_id,datetime,user_id,action,details,field_label,old_value,new_value
    #          --subject_type_label.value="Device" --subject_id=6692 --limit=30 --sort=datetime:d
    savedTruncate = denaliVariables["textTruncate"]
    savedWrap     = denaliVariables["textWrap"]

    denaliVariables["textTruncate"]   = False
    denaliVariables["textWrap"]       = False
    denaliVariables["searchCategory"] = "HistoryDao"
    denaliVariables["method"]         = "search"

    if denaliVariables["historyFields"] == "long":
        denaliVariables["fields"] = "subject_id,datetime,user.full_name,action,details,field_label,old_value,new_value"
    else:
        denaliVariables["fields"] = "subject_id,datetime,user.full_name,action,details"

    # build the generic sql parameters for this search(es)
    sqlParameters = buildGenericHistorySQL(denaliVariables)

    # early determination (based on sql parameters) if the SkmsArchiveHistoryDao
    # needs to be consulted for data
    access_archived_data = archiveHistoryDaoUse(denaliVariables, sqlParameters)

    #
    # step 3:
    # Create a sorted device_id list based upon the host list sort.  This will allow
    # multi-host history queries to show the host's history in host-sorted order (a -> z)
    hostList = hostListDict.keys()
    hostList.sort()

    deviceIDList = []
    for host in hostList:
        deviceIDList.append(hostListDict[host])

    for subject_id in deviceIDList:
        if subject_id == "deviceCount":
            continue

        #
        # step 4:
        # Build the sql query (from the original parameter(s) and modified history query)
        # this keeps the original "hist_*" sql modifier query item(s) and adds to it the
        # subject type and id for proper history searching
        denaliVariables["sqlParameters"] = [["--subject_id", str(subject_id)]]
        denaliVariables["sqlParameters"].extend(sqlParameters)

        #
        # step 5:
        #   Add in the sorting statement(s)
        if denaliVariables["sqlSort"] != '':
            # replace any aliased name(s) in the sort statement with the proper cmdb name(s)
            denaliVariables["sqlSort"] = denali_search.replaceAliasedNames(denaliVariables, "sqlSort")

            # create the SQL statement from the sort data passed in
            denaliVariables["sqlSort"] = denali_utility.createSortSQLStatement(denaliVariables["sqlSort"])

        # change the sql variables into SQL statement/query language (return variable
        # stores the result, but "historySQL" isn't used because denaliVariables is
        # updated automatically with this function call and used just below)
        historySQL = denali_utility.processSQLParameters(denaliVariables)

        # step 6/7: do the query -- get the data and print it
        (itemCount, sqlQuery) = executeHistoryQuery(denaliVariables, deviceDict, "HistoryDao", 0, savedTruncate, savedWrap)

        #
        # If the archive history dao is needed -- query it.
        #
        if access_archived_data == True or itemCount < denaliVariables["limitCount"]:
            (itemCount, sqlQuery) = executeHistoryQuery(denaliVariables, deviceDict, "SkmsArchiveHistoryDao", itemCount, savedTruncate, savedWrap)

        if denaliVariables["multiHostHeader"] == False:
            denaliVariables["showHeaders"] = False

        if denaliVariables["showsql"] == True or denaliVariables["summary"] == True:
            if denaliVariables["showsql"] == True:
                denali_utility.showSQLQuery(sqlQuery, denaliVariables)
            if denaliVariables["summary"] == True:
                denali_utility.printSummaryInformation(denaliVariables, itemCount, False)
        elif itemCount > 0:
            denaliVariables["historyCount"] += itemCount
            if denaliVariables["multiHostHeader"] == False:
                denaliVariables["showHeaders"] = False
            else:
                print

    # reset the dao to device dao -- for printing the showsql message
    # reset the summary to false -- is printed here
    denaliVariables["searchCategory"] = "DeviceDao"
    denaliVariables["summary"]        = False

    return itemCount



##############################################################################
#
# pullDeviceIDsFromQueryData(queryData)
#

def pullDeviceIDsFromQueryData(queryData):

    deviceIDDict = {}
    hostListDict = {}

    if queryData == False:
        return (False, False)

    # validate the dictionary -- make sure it is formatted correctly and can be used
    if "status" in queryData and queryData["status"] == "success" and "data" in queryData and "results" in queryData["data"]:
        if len(queryData["data"]["results"]) == 0:
            # History returned no devices/records
            return (False, False)

        # looks good -- pull the deviceIDs out
        deviceData = queryData["data"]["results"]

        for (index, device) in enumerate(deviceData):
            deviceIDDict.update({deviceData[index]["device_id"]:deviceData[index]["name"]})
            hostListDict.update({deviceData[index]["name"]:deviceData[index]["device_id"]})

        # store the number of hosts in the dictionary (index + 1) because the index is zero-based
        deviceIDDict.update({"deviceCount":(index + 1)})

    else:
        # does not look good, return (False, False) for failure.
        return (False, False)

    return (deviceIDDict, hostListDict)



##############################################################################
#
# swapDeviceIDForHostName(printData, deviceDict):
#

def swapDeviceIDForHostName(printData, deviceDict):

    for (index, row) in enumerate(printData):
        printData[index][0] = deviceDict[row[0].strip()]

    return printData



##############################################################################
#
# limitDisplayRowPrinting(denaliVariables, printData, previousItemCount)
#
#   Manual implementation of a row limiting feature.
#

def limitDisplayRowPrinting(denaliVariables, printData, previousItemCount):

    limitCount = int(denaliVariables["limitCount"])
    limitCount -= previousItemCount
    if limitCount < 1:
        return printData

    if len(printData) > limitCount:
        printData = printData[:limitCount]

    return printData



##############################################################################
#
# buildArrayToSend(denaliVariables, host, updateString)
#
#   This function builds the array to send in to update the history with
#

def buildArrayToSend(denaliVariables, host, updateString):

    key_array = {'key_value_arr': host,
                 'note'         : updateString}

    return key_array



##############################################################################
#
# verifyHistoryUpdate(denaliVariables, response_dict)
#
#   This function verifies if the history update was done correctly.  It does
#   this by looking at the returned dictionary from SKMS.
#

def verifyHistoryUpdate(denaliVariable, response_dict):

    if 'history_id_arr' in response_dict and response_dict['history_id_arr']:
        return True
    else:
        return False



##############################################################################
#
# sendHistoryUpdateRequest(denaliVariables, key_value_array, category='DeviceDao')
#
#   Send the request off to update the history for the hosts specified
#

def sendHistoryUpdateRequest(denaliVariables, key_value_array, category='DeviceDao'):

    api = denaliVariables["api"]

    if denaliVariables["debug"] == True:
        print
        print "api                : %s" % api
        print "category           : %s" % category
        print "method             : %s" % 'addNotes'
        print "parameterDictionary: %s" % key_value_array

    ccode = api.send_request(category, 'addNotes', key_value_array)
    if ccode == True:
        response_dict = api.get_data_dictionary()

        # check to make sure the history was updated correct
        ccode = verifyHistoryUpdate(denaliVariables, response_dict)
        if ccode == False:
            return False
    else:
        return False

    return True



##############################################################################
#
# csrfWorkAround(denaliVariables, kva, category='DeviceDao')
#

def csrfWorkAround(denaliVariables, kva, category='DeviceDao'):

    api = denaliVariables['api']

    # call recursively if failure is CSRF missing/invalid token
    message = api.get_error_message()
    if message.startswith("The CSRF token is either missing or invalid"):
        ccode = sendHistoryUpdateRequest(denaliVariables, kva, category)
        if ccode == False:
            return False
        else:
            return True

    return False



##############################################################################
#
# addHistoryToHostList(denaliVariables)
#
#   Add a note to the history for each host specified
#

def addHistoryToHostList(denaliVariables, updateString, print_result=True):

    host_buffer       = 7
    update_success    = colors.fg.lightgreen
    update_failure    = colors.fg.lightred
    successful_buffer = ' ' * host_buffer + colors.bold + update_success + "SUCCESSFUL" + colors.reset
    failure_buffer    = ' ' * host_buffer + colors.bold + update_failure + "FAILURE"    + colors.reset

    max_host_length   = getLongestHostname(denaliVariables["serverList"])

    if denaliVariables["singleUpdate"] == True:
        # all updates done in a single request (all hosts -- the entire group -- at the same time)
        key_value_array = buildArrayToSend(denaliVariables, denaliVariables["serverList"], updateString)
        ccode = sendHistoryUpdateRequest(denaliVariables, key_value_array)
        if ccode == False:
            ccode = csrfWorkAround(denaliVariables, key_value_array)
        if ccode == False:
            api = denaliVariables["api"]
            print colors.bold + update_failure + "\nSKMS ERROR" + colors.reset,
            print "adding history note on group of hosts"
            print "\nERROR:"
            print "   STATUS  : " + api.get_response_status()
            print "   TYPE    : " + str(api.get_error_type())
            print "   MESSAGE : " + api.get_error_message()
            print
            return False
        else:
            if denaliVariables["autoConfirm"] == False and print_result == True:
                print "All hosts updated " + colors.bold + update_success + "SUCCESSFULLY" + colors.reset
                print
    else:
        # all updates done one host at a time
        for host in denaliVariables["serverList"]:
            key_value_array = buildArrayToSend(denaliVariables, host, updateString)
            ccode = sendHistoryUpdateRequest(denaliVariables, key_value_array)
            if ccode == False:
                ccode = csrfWorkAround(denaliVariables, key_value_array)
            if ccode == False:
                api = denaliVariables["api"]
                print "%s : " % host.ljust(max_host_length) + failure_buffer
                print "\nERROR:"
                print "   STATUS  : " + api.get_response_status()
                print "   TYPE    : " + str(api.get_error_type())
                print "   MESSAGE : " + api.get_error_message()
                print
                return False
            else:
                if denaliVariables["autoConfirm"] == False and print_result == True:
                    print "%s : " % host.ljust(max_host_length) + successful_buffer

    return True



##############################################################################
#
# addHistoryToGroup(denaliVariables, updateString, print_result=True)
#
#   Add a note to the history for each group specified
#

def addHistoryToGroup(denaliVariables, updateString, print_result=True):

    group_buffer      = 7
    update_success    = colors.fg.lightgreen
    update_failure    = colors.fg.lightred
    successful_buffer = ' ' * group_buffer + colors.bold + update_success + "SUCCESSFUL" + colors.reset
    failure_buffer    = ' ' * group_buffer + colors.bold + update_failure + "FAILURE"    + colors.reset

    max_group_length   = getLongestHostname(denaliVariables["serverList"])

    if denaliVariables["singleUpdate"] == True:
        # all updates done in a single request (all hosts -- the entire group -- at the same time)
        key_value_array = buildArrayToSend(denaliVariables, denaliVariables['groupList'], updateString)
        ccode = sendHistoryUpdateRequest(denaliVariables, key_value_array, 'DeviceGroupDao')
        if ccode == False:
            ccode = csrfWorkAround(denaliVariables, key_value_array, 'DeviceGroupDao')
        if ccode == False:
            api = denaliVariables["api"]
            print colors.bold + update_failure + "SKMS ERROR" + colors.reset,
            print "adding history note on group(s)"
            print "\nERROR:"
            print "   STATUS  : " + api.get_response_status()
            print "   TYPE    : " + str(api.get_error_type())
            print "   MESSAGE : " + api.get_error_message()
            print
            return False
        else:
            if denaliVariables["autoConfirm"] == False and print_result == True:
                print "All group(s) updated " + colors.bold + update_success + "SUCCESSFULLY" + colors.reset
                print
    else:
        # all updates done one host at a time
        for group in denaliVariables['groupList']:
            key_value_array = buildArrayToSend(denaliVariables, group, updateString)
            ccode = sendHistoryUpdateRequest(denaliVariables, key_value_array, 'DeviceGroupDao')
            if ccode == False:
                ccode = csrfWorkAround(denaliVariables, key_value_array, 'DeviceGroupDao')
            if ccode == False:
                api = denaliVariables["api"]
                print "%s : " % group.ljust(max_group_length) + failure_buffer
                print "\nERROR:"
                print "   STATUS  : " + api.get_response_status()
                print "   TYPE    : " + str(api.get_error_type())
                print "   MESSAGE : " + api.get_error_message()
                print
                return False
            else:
                if denaliVariables["autoConfirm"] == False and print_result == True:
                    print "%s : " % group.ljust(max_group_length) + successful_buffer

    return True

##############################################################################
##############################################################################
##############################################################################


if __name__ == '__main__':
    # do nothing
    pass
