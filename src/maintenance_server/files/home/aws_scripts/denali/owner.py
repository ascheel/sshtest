
import denali_search
import denali_utility
import denali_arguments



##############################################################################
#
# getOwners(denaliVariables, *parameters)
#
#   Stub function definition that allows me to call "getOwner" or "getOwners"
#   and see the same result.

def getOwners(denaliVariables, *parameters):
    ccode = getOwner(denaliVariables, *parameters)
    return ccode



##############################################################################
#
# main(denaliVariables, *parameters)
#
#   Default call function

def main(denaliVariables, *parameters):
    ccode = getOwner(denaliVariables, *parameters)
    return ccode



##############################################################################
#
# checkFieldList(denaliVariables)
#

def checkFieldList(denaliVariables):

    host_name_column      = -1
    device_service_column = -1

    columnFields = denaliVariables["fields"].split(',')

    # search for the host name column
    for (index, field) in enumerate(columnFields):
        if field == "name":
            host_name_column = index
            break
    else:
        denaliVariables["fields"] += ",name"
        host_name_column = (index + 1)

    columnFields = denaliVariables["fields"].split(',')

    # search for the device service column
    for (index, field) in enumerate(columnFields):
        if field == "device_service" or field == "device_service.full_name":
            device_service_column = index
            break
    else:
        denaliVariables["fields"] += ",device_service.full_name"
        device_service_column = (index + 1)

    # Verify the necessary columns were added -- shouldn't be necessary if
    # the above code does its job correctly.
    if host_name_column == -1:
        print "Could not find host name in field list."
        denali_search.cleanUp(denaliVariables)
        exit(1)

    if device_service_column == -1:
        print "Could not find device service name in the field list."
        denali_search.cleanUp(denaliVariables)
        exit(1)

    return (host_name_column, device_service_column)



##############################################################################
#
# getOwner(denaliVariables, *parameters)
#

def getOwner(denaliVariables, *parameters):

    include_attributes = False
    dynamic_columns    = False
    page_number        = 0

    attr_columns = "DPO_RESERVATION"

    if len(parameters) > 0:
        if parameters[0].lower() == "all":
            dynamic_columns = True
        if parameters[0].lower() == "attribute":
            #include_attributes = True
            include_attributes = False

    # display owners in a single column or separated into multiple columns
    single_column_display = 0

    # The host name and device_service _MUST_ exist in the field list.  If it doesn't add it in.
    (hostNameColumn, deviceServiceColumn) = checkFieldList(denaliVariables)

    # build and execute the query
    denaliVariables["textWrap"]      = False
    denaliVariables["textTruncate"]  = False
    denaliVariables["sqlParameters"] = denali_utility.processSQLParameters(denaliVariables)

    (sqlQuery, wildcard) = denali_search.buildHostQuery(denaliVariables)
    sqlQuery = denaliVariables["searchCategory"] + ':' + sqlQuery
    printData = denali_utility.sqlQueryConstructionResponse(denaliVariables, sqlQuery)

    # only continue if the following conditions are not met
    if printData == False:
        print "There was a problem in the owner query.  Halting execution."
        denali_search.cleanUp(denaliVariables)
        exit(1)
    elif len(printData) == 0:
        print "No devices returned for the submitted query."
        denali_search.cleanUp(denaliVariables)
        exit(1)

    # get the master list of device services
    masterDict = masterList(denaliVariables, "list_only")
    if not len(masterDict):
        return {}

    # step 1: determine which device services are in the resultant data list
    devServiceData = set()

    for row in printData:
        devServiceData.add(row[deviceServiceColumn].strip())

    devServiceData = list(devServiceData)
    devServiceData.sort()

    # step 2: determine the needed columns to display
    if dynamic_columns == True:
        ownerGroups = set()

        for dev_service in devServiceData:
            dev_serv_list = dev_service.split(',')

            for device_service in dev_serv_list:
                if device_service in masterDict:
                    dsGroups = masterDict[device_service].keys()

                    if len(dsGroups) > 0:
                        for group in dsGroups:
                            ownerGroups.add(group)

        ownerGroups = list(ownerGroups)
        ownerGroups.sort(reverse=True)      # sort in descending order

        for (index, group) in enumerate(ownerGroups):
            if group == '':
                ownerGroups.pop(index)
                break

    else:
        # default run through -- look for 4 owner columns only
        #ownerGroups = ["System Engineering", "Operations", "Engineering", "Network Operations Center", "QE"]
        ownerGroups = ["System Engineering", "Operations", "Engineering"]

    # where to add the new column(s) -- at the end of the submitted field list
    columnNumber = len(denaliVariables["fields"])

    # step 3: loop on the column(s) to print (found/assigned in step #2)
    for group in ownerGroups:

        # step 4: collect column owners
        denaliVariables["addColumnData"] = collectDevServiceOwners(group, printData, masterDict, hostNameColumn,deviceServiceColumn)

        # step 5: insert column in printData
        columnTitle = group + " Owners"
        insertColumnNumber = columnNumber
        newColumnData      = ["", "", columnTitle, 35]
        printData = denali_utility.keyColumnInsert(printData, denaliVariables, insertColumnNumber, newColumnData, cKey=hostNameColumn)

        #
        #   Two options for column insertion -- with, or without a key (column key to identify with)
        #
        # (1)   ['item1','item2','item3',...]
        #printData = denali_utility.genericColumnInsert(printData, denaliVariables, insertColumnNumber, newColumnData)
        #
        # (2)  {'key1':'item1', 'key2':'item2', ...}
        #printData = denali_utility.keyColumnInsert(printData, denaliVariables, insertColumnNumber, newColumnData, cKey="default")

    # step 6: see if attributes were requested -- put them at the end
    if include_attributes == True:
        # backup the appropriate variables before using them differently
        saveFields  = denaliVariables["fields"]
        saveSort    = denaliVariables["sqlSort"]
        saveHosts   = denaliVariables["serverList"]
        saveColumns = denaliVariables["columnData"]
        saveSQL     = denaliVariables["sqlParameters"]
        saveDAO     = denaliVariables["searchCategory"]
        saveATTRS   = denaliVariables["attributesStacked"]
        saveSQL1    = denaliVariables["sqlParmsOriginal"]

        # set the data as needed
        denaliVariables["fields"]            = "name,attribute_name,attribute_value"
        denaliVariables["searchCategory"]    = "DeviceDao"
        denaliVariables["sqlParameters"]     = " AND (attribute_data.attribute.name LIKE '%s')" % attr_columns
        denaliVariables["sqlParmsOriginal"]  = [["--attribute_name", "%s" % attr_columns]]
        denaliVariables["attributesStacked"] = False

        # build the sql query with the given hosts
        (modFields, denaliVariables["columnData"]) = denali_search.determineColumnOrder(denaliVariables)
        (sqlQuery, wildcard) = denali_search.buildHostQuery(denaliVariables)
        sqlQuery = denaliVariables["searchCategory"] + ':' + sqlQuery

        attrPrintData = denali_utility.sqlQueryConstructionResponse(denaliVariables, sqlQuery)
        denali_utility.resetOutputTarget(denaliVariables)
        denaliVariables["columnData"] = saveColumns
        attr_list = attr_columns.split(',')

        for (columnKey, column) in enumerate(denaliVariables["columnData"]):
            if column[2] == "Host Name":
                break
        else:
            columnKey = 0

        for (column, attribute) in enumerate(attr_list):

            denaliVariables["addColumnData"] = collectRowData(attrPrintData, (column + 1))
            insertColumnNumber = 2
            newColumnData = ["attr_" + attribute, "attr_" + attribute, attribute, 35]
            printData = denali_utility.keyColumnInsert(printData, denaliVariables, insertColumnNumber, newColumnData, columnKey)

        # restore the variable backup(s)
        denaliVariables["fields"]            = saveFields
        denaliVariables["sqlSort"]           = saveSort
        denaliVariables["serverList"]        = saveHosts
        denaliVariables["sqlParameters"]     = saveSQL
        denaliVariables["searchCategory"]    = saveDAO
        denaliVariables["attributesStacked"] = saveATTRS

    # step 7: transform data back into JSON
    # MRASEREQ-40964
    json_data = transformToJSON(denaliVariables, printData)

    # step 8: print resultant data
    denaliVariables["textWrap"] = True
    (printData, overflowData) = denali_search.wrapColumnData(denaliVariables, printData)
    itemCount = len(printData)

    # MRASEREQ-40964 -- this toggle switch and 'json_data' in the printPrint call
    denaliVariables['jsonPageOutput'] = True
    denali_search.prettyPrintData(printData, overflowData, json_data, denaliVariables)

    if denaliVariables["summary"] == True:
        print
        print " Total Items Displayed: %d" % itemCount

    if denaliVariables["showsql"] == True:
        denali_utility.showSQLQuery(sqlQuery, denaliVariables)

    return True



##############################################################################
#
# transformToJSON(denaliVariables, printData)
#
#   MRASEREQ-40964:  Transform the printData structure back into a presentable
#                    JSON output so it can be analyzed after the data return.
#

def transformToJSON(denaliVariables, printData):
    json_data = {'results':[]}

    for row in printData:
        temp_dict = {}
        for (index, column) in enumerate(denaliVariables['columnData']):
            temp_dict.update({column[2]:row[index].strip()})
        json_data['results'].append(temp_dict)

    return json_data



##############################################################################
#
# masterList(denaliVariables, *parameters)
#

def masterList(denaliVariables, *parameters):

    # get all of the device services and their owners first -- store that in
    # a dictionary

    collect_all = "subset"
    ownerDictionaryMaster = {}

    # turn the tuple into a list
    parameters = list(parameters)
    #print "parameters = %s" % parameters

    if len(parameters) > 0:
        for parm in parameters:
            if parm.lower() == "all":
                collect_all = "all"
            elif parm.lower() == "summary":
                collect_all = "summary"
            elif parm == "list_only":
                collect_all = "list_only"
            elif parm.startswith("userSummary"):
                collect_all = "userListSummary"
            elif parm.startswith("user"):
                collect_all = "userList"
            elif parm.startswith("serviceSummary"):
                collect_all = "devServiceSummary"
            elif parm.startswith("service"):
                collect_all = "devService"

        # drop the first parameter
        parameters.pop(0)
    #print "collect_all = %s" % collect_all
    # save off the current state before this query modifies it
    saveFields  = denaliVariables["fields"]
    saveSort    = denaliVariables["sqlSort"]
    saveHosts   = denaliVariables["serverList"]
    saveColumns = denaliVariables["columnData"]
    saveSQL     = denaliVariables["sqlParameters"]
    saveDAO     = denaliVariables["searchCategory"]

    # build the custom query and then execute it
    denaliVariables["fields"] = "full_name,owner.owner_type.name,owner.owner_subject_type,owner_user.full_name,owner_team.full_name,owner.sort_order"
    #denaliVariables["sqlSort"]       = " ORDER BY full_name"
    denaliVariables["serverList"]     = "*"
    denaliVariables["sqlParameters"]  = " AND (active = '1')"       # assumption: 'inactive' device services aren't useful
    denaliVariables["searchCategory"] = "DeviceServiceDao"
    dao                               = "DeviceServiceDao"

    (modFields, denaliVariables["columnData"]) = denali_search.determineColumnOrder(denaliVariables, False)

    # if the master list is called, the columnData needs to be saved for later use
    dvColumnData = denaliVariables["columnData"]

    (sqlQuery, wildcard) = denali_search.buildGenericQuery(denaliVariables, "full_name")
    sqlQuery = dao + ':' + sqlQuery
    printData = denali_utility.sqlQueryConstructionResponse(denaliVariables, sqlQuery)
    if printData == False:
        print "Denali Error:  Owner masterList printData is 'False'.  Exiting program."
        return {}

    # reset the output target variables -- so it can print everything in one go
    denali_utility.resetOutputTarget(denaliVariables)

    # make a dictionary from the current print data to reference against -- so I don't have
    # to search CMDB for all 60,000+ devices and their owners.  Each will be referenced to a
    # device service, so this master list contains everything I need.

    for device_service in printData:
        ownerDictionaryMaster = populateGroupsIntoOwnerDict(ownerDictionaryMaster, device_service)

    # restore the previous query state
    denaliVariables["fields"] = saveFields
    denaliVariables["sqlSort"] = saveSort
    denaliVariables["serverList"] = saveHosts
    denaliVariables["columnData"] = saveColumns
    denaliVariables["sqlParameters"] = saveSQL
    denaliVariables["searchCategory"] = saveDAO

    # if this is called from another function, just return the master list
    if collect_all == "list_only":
        return ownerDictionaryMaster

    # make a sorted list (by device service name) to base this on.
    #dev_serv_list = ownerDictionaryMaster.keys()
    #dev_serv_list.sort()

    # check to see if just a list was requested (meaning, columnData is empty)
    if len(denaliVariables["columnData"]) == 0:
        denaliVariables["columnData"] = dvColumnData

    # remove the original columns (except the device service name)
    denali_utility.removeColumn(denaliVariables, printData, 1)     # owner.owner_type.name
    denali_utility.removeColumn(denaliVariables, printData, 1)     # owner.owner_subject_type
    denali_utility.removeColumn(denaliVariables, printData, 1)     # owner_user.full_name
    denali_utility.removeColumn(denaliVariables, printData, 1)     # owner_team.full_name

    if collect_all == "subset":
        # Put column definition for specific owner groups -- all of this is in the above dictionary
        #   #1: System Engineering
        #   #2: Operations
        #   #3: Engineering
        #   #4: QE

        ownerColumns = ["QE", "Engineering", "Operations", "System Engineering"]

        for column in ownerColumns:
            denaliVariables["addColumnData"] = collectColumnData(ownerDictionaryMaster, column)
            insertColumnNumber = 1
            column = column + " Owners"
            newColumnData = ["", "", column, 27]
            printData = denali_utility.keyColumnInsert(printData, denaliVariables, insertColumnNumber, newColumnData)

        (printData, overflowData) = denali_search.wrapColumnData(denaliVariables, printData)
        denali_search.prettyPrintData(printData, overflowData, {}, denaliVariables)

    elif collect_all == "all":
        # collect all of the data and get it organized
        organizeAllData(denaliVariables, ownerDictionaryMaster, printData)

    elif collect_all == "userList" or collect_all == "userListSummary":
        # a user (or users) assigned to what? device service(s) as owners.
        if collect_all == "userList":
            if len(parameters) > 0:
                parameters.insert(0, "user")
        else:
            if len(parameters) > 0:
                parameters.insert(0, "userSummary")

        # do the collect_all == "all" procedure, and then narrow it down by user(s)
        organizeAllData(denaliVariables, ownerDictionaryMaster, printData, parameters)

    elif collect_all == "devService" or collect_all == "devServiceSummary":
        # a device service (or services) has what user(s)/group(s) as owners.
        if collect_all == "devService":
            if len(parameters) > 0:
                parameters.insert(0, "service")
        else:
            if len(parameters) > 0:
                parameters.insert(0, "serviceSummary")

        # do the collect_all == "all" procedure, and then narrow it down by device services(s)
        organizeAllData(denaliVariables, ownerDictionaryMaster, printData, parameters)

    elif collect_all == "summary":
        # Collect a summary of the data (pass in the rest of the parameters)
        summaryData = collectSummaryData(ownerDictionaryMaster)
        ccode       = printSummaryData(summaryData, parameters)

    elif collect_all == "ascii":
        # draw an ASCII art representation of the device service structure
        pass

    if ownerDictionaryMaster == {}:
        return False
    else:
        return ownerDictionaryMaster



##############################################################################
#
# organizeAllData(denaliVariables, ownerDictionaryMaster, printData, searchList)
#

def organizeAllData(denaliVariables, ownerDictionaryMaster, printData, searchList):

    # location to save the rows where matches are found
    printDataNew = []

    # Place all of the groups in columns to print
    summaryData = collectSummaryData(ownerDictionaryMaster)
    ownerGroups = summaryData.keys()
    for (index, group) in enumerate(ownerGroups):
        if group == "Empty":
            ownerGroups.pop(index)
            break

    for column in ownerGroups:
        denaliVariables["addColumnData"] = collectColumnData(ownerDictionaryMaster, column)
        insertColumnNumber = 1
        column = column + " Owners"
        newColumnData = ["", "", column, 35]
        printData = denali_utility.keyColumnInsert(printData, denaliVariables, insertColumnNumber, newColumnData)

    '''
    # If more is done with this code, this may be the place to add it
    if searchList[0] == "user":
        print "found user"
    elif searchList[0] == "service":
        print "found device service"
    '''

    if searchList[0] == "userSummary":
        for (index, column) in enumerate(denaliVariables["columnData"]):
            if column[2] == "Device Service":
                denaliVariables["columnData"] = [denaliVariables["columnData"][index]]
                break

    # This is very much a brute force method of searching through the data and
    # pulling out only what is needed.  I'm sure there's a more elegant way to
    # make this happen; I just haven't thought about it hard enough.
    for row in printData:
        foundMatch = False
        for column in row:
            for item in searchList:
                if column.find(item) != -1:
                    foundMatch = True
                    break

            if foundMatch == True:
                break

        if foundMatch == True:
            if searchList[0] == "userSummary":
                printDataNew.append([row[index]])
            else:
                printDataNew.append(row)

    (printData, overflowData) = denali_search.wrapColumnData(denaliVariables, printDataNew)
    denali_search.prettyPrintData(printData, overflowData, {}, denaliVariables)



##############################################################################
#
# collectRowData(rowData, column)
#

def collectRowData(rowData, column):

    rowDict = {}

    for row in rowData:
        rowDict.update({row[0].strip():row[column].strip()})

    return rowDict



##############################################################################
#
# collectColumnData(ownerDict, column)
#
#   This function is given the ownerDictionary and a column (owner group) inside
#   of it.  It returns a keyed list of data from that specific owner group.
#          { "dev-service" : "owner1, owner2, owner3, ..." }
#

def collectColumnData(ownerDict, column):

    columnData = {}

    for devService in ownerDict:
        if column in ownerDict[devService]:
            # prettyprint will remove the comma and put a ',' in place
            # if a CSV output is selected, so there's no need to adjust
            # it here.
            data = ','.join(ownerDict[devService][column])
            columnData.update({devService:data})
        else:
            columnData.update({devService:''})

    return columnData



##############################################################################
#
# collectDevServiceOwners(group, printData, masterDict, hostNameColumn,deviceServiceColumn)
#
#   For the (owner) group passed in, go through the printData and look up
#   every device service.  Check that device service against the master
#   dictionary and see if the group is assigned.  If it is, add the owners
#   to the list.  There is a new entry per row in the printData object.
#   Multiple device services can exist for one entry, so loop through each
#   of those as well.
#

def collectDevServiceOwners(group, printData, masterDict, hostNameColumn, deviceServiceColumn):

    ownerColumnData = {}

    for row in printData:
        ownerList = ''
        devServices = row[deviceServiceColumn].strip().split(',')

        # if there are multiple devices services for a host, send the list off
        # to a function that determines which one (or ones) are required to be
        # in this list
        #if len(devServices) > 0:
        #    devServices = deviceServiceWhiteList(devServices)

        for dService in devServices:
            if dService in masterDict:
                if group in masterDict[dService]:
                    if len(ownerList) == 0:
                        ownerList = ','.join(masterDict[dService][group])
                    else:
                        ownerList += " // " + ','.join(masterDict[dService][group])

        ownerColumnData.update({row[hostNameColumn].strip():ownerList})
        ownerList = ''

    return ownerColumnData



##############################################################################
#
# collectSummaryData(ownerDict)
#

def collectSummaryData(ownerDict):

    summaryData = {}
    devServices = ownerDict.keys()

    for service in devServices:
        groups = ownerDict[service].keys()
        if len(groups) > 0:
            for ownerGroup in groups:
                if ownerGroup == '':
                    ownerGroup = "Empty"
                if ownerGroup not in summaryData:
                    summaryData.update({ownerGroup:[1, service]})
                else:
                    summaryData[ownerGroup][0] += 1
                    summaryData[ownerGroup].append(service)
        else:
            if "Empty" not in summaryData:
                summaryData.update({"Empty":[1, service]})
            else:
                summaryData["Empty"][0] += 1
                summaryData["Empty"].append(service)

    return summaryData



##############################################################################
#
# printSummaryData(summaryData, parameters)
#

def printSummaryData(summaryData, parameters):

    print "Device Service Summary Data"
    ownerGroups = summaryData.keys()

    for group in ownerGroups:
        print " %-27s : %d" % (group, summaryData[group][0])

    if len(parameters) == 0:
        # no parameters given, so return without printing
        # device services for owners
        return True

    for owner in parameters:
        if owner in summaryData:
            devServiceList = summaryData[owner]
            devServiceList.pop(0)
            devServiceList.sort()

            print "\nList of Device Services with \"%s\" as an owner:" % owner
            for devService in devServiceList:
                print " %s" % devService

        else:
            print "The owner \"%s\" was not found in the summary data" % owner

    return True



##############################################################################
#
# popoulateGroupsIntoOwnerDict(ownerDictionaryMaster, device_service)
#
#   Dictionary:
#       { device_service : [ group1:[owners], group2:[owners], ...], ... }
#

def populateGroupsIntoOwnerDict(ownerDictionaryMaster, device_service):

    user_sort_list = []
    team_sort_list = []

    ownerGroups    = device_service[1].strip().split(',')
    ownerTypes     = device_service[2].strip().split(',')
    ownerUsers     = device_service[3].strip().split(',')
    ownerTeams     = device_service[4].strip().split(',')
    sort_order     = device_service[5].strip().split(',')
    devService     = device_service[0].strip()

    # each device service gets its own key in the dictionary
    ownerDictionaryMaster.update({devService:{}})

    # user and team sort List creation
    #
    # These numbers will now preface the owners (user and team) for each
    # group; i.e., 2:Analytics DPO.  With a List of these, then they can
    # easily be sorted.  At that point, just rip off the number/colon, and
    # reassign ... done.
    for (index, owType) in enumerate(ownerTypes):
        if owType == '1':
            user_sort_list.append(sort_order[index])
        elif owType == '2':
            team_sort_list.append(sort_order[index])

    teamIndex = 0
    for (index, group) in enumerate(ownerGroups):
        userIndex = index - teamIndex
        if group not in ownerDictionaryMaster[devService]:
            ownerDictionaryMaster[devService].update({group:[]})

        # add the user owners
        if ownerTypes[index] == '1':
            user = user_sort_list[userIndex] + ':' + ownerUsers[userIndex]
            ownerDictionaryMaster[devService][group].append(user)
        else:
            teamIndex += 1

    # add any teams for this service at the end of the user/owner list
    teamIndex = 0
    for (index, oType) in enumerate(ownerTypes):
        if oType == '2':
            group = ownerGroups[index]
            team  = team_sort_list[teamIndex] + ':' + ownerTeams[teamIndex]
            ownerDictionaryMaster[devService][group].append(team)
            teamIndex += 1

    for group in ownerDictionaryMaster[devService]:
        # sort the owner list
        ownerDictionaryMaster[devService][group].sort()

        # rip off the sort indicator
        for (oIndex, owner) in enumerate(ownerDictionaryMaster[devService][group]):
            ownerDictionaryMaster[devService][group][oIndex] = owner[(owner.find(':')+1):]

    return ownerDictionaryMaster