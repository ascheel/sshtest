
import denali_search
import denali_utility

#
# Custom report adding the SisGroups column to the end of a table
#
#



##############################################################################
#
# getSisGroups(denaliVariables, *parameters)
#

def getSisGroups(denaliVariables, *parameters):

    #ccode = denali_utility.validateDeviceList(denaliVariables)
    ccode = denali_utility.createServerListFromArbitraryQuery(denaliVariables)

    # False is returned only if _ALL_ of the submitted hosts don't exist.
    if ccode == False:
        print "All submitted hosts do not exist in CMDB.  Query not executed."
        return False

    hostList = denaliVariables["serverList"]

    # retrieve the SIS Groups for each device submitted
    savedTruncate = denaliVariables["textTruncate"]
    savedWrap     = denaliVariables["textWrap"]

    denaliVariables["searchCategory"] = "DeviceDao"
    denaliVariables["method"]         = "getSisGroups"
    denaliVariables["textTruncate"]   = False
    denaliVariables["textWrap"]       = False

    # sql parameters are used in the validateDeviceList function -- not needed here.
    denaliVariables["sqlParameters"]  = []

    respDictionary = denali_utility.multiQueryMethodResponse(denaliVariables, hostList)

    # get the data to insert into the table
    denaliVariables["addColumnData"] = collectSisGroupInfo(respDictionary)

    # do the original data query, and then add the SIS Group data to it.
    dao = denaliVariables["searchCategory"]
    denaliVariables["method"] = "search"

    # build the sql query with the given hosts
    (sqlQuery, wildcard) = denali_search.buildHostQuery(denaliVariables)

    # Save the column data -- it is correct at this point but gets modified after
    # the construct sql query function.  This allows "url" column data to be successfully
    # displayed during a sis groups data query (it's actually only the "alias name" in
    # the column data that is changed here).
    savedCData = denaliVariables["columnData"]

    sqlQuery = dao + ':' + sqlQuery
    respDictionary = denali_search.constructSQLQuery(denaliVariables, sqlQuery, False)

    if respDictionary == False:
        print "There was a problem with the query -- no results were returned."

        # display return error message from web api
        if denaliVariables["debug"] == True:
            api = denaliVariables["api"]
            print "\nERROR:"
            print "   STATUS: " + api.get_response_status()
            print "   TYPE: " + str(api.get_error_type())
            print "   MESSAGE: " + api.get_error_message()
        denali_search.cleanUp(denaliVariables)
        exit(1)

    # remove "Closed" JIRA tickets (MRASEREQ-40937)
    if denaliVariables["fields"].find("jira_issue") != -1 and denaliVariables["jira_closed"] == False:
        respDictionary = denali_utility.removeClosedJIRA(denaliVariables, respDictionary)

    # restore the column data
    denaliVariables["columnData"] = savedCData
    (printData, overflowData) = denali_search.generateOutputData(respDictionary, denaliVariables)

    # add the new column data in the output
    insertColumnNumber = 1
    newColumnData = ["", "", "Host SIS Group(s)", 40]
    printData = denali_utility.keyColumnInsert(printData, denaliVariables, insertColumnNumber, newColumnData, cKey="default")

    # new data is probably larger than the columns -- wrap it and then print it (unless nowrap was specified)
    denaliVariables["textTruncate"] = savedTruncate
    denaliVariables["textWrap"]     = savedWrap

    (printData, overflowData) = denali_search.wrapColumnData(denaliVariables, printData)
    itemCount = len(printData)
    denali_search.prettyPrintData(printData, overflowData, respDictionary, denaliVariables)

    if denaliVariables["summary"] == True:
        denali_utility.printSummaryInformation(denaliVariables, itemCount, False)

    #if itemCount == 5000:
    #    print "This module only displays up to 5000 hosts and their associated SIS Groups."

    return True



##############################################################################
#
# collectSisGroupInfo(sisDictionary)
#

def collectSisGroupInfo(sisDictionary):

    sisColumn = {}
    keys      = sisDictionary.keys()

    for device in keys:
        sisGroups = ''
        for group in sisDictionary[device]["sis_groups"]:
            if sisGroups == '':
                sisGroups += group
            else:
                sisGroups += ',' + group
        sisColumn.update({device:sisGroups})

    return sisColumn



##############################################################################
#
# main(denaliVariables, *parameters)
#

def main(denaliVariables, *parameters):

    # This "main" function is called by default if no specific function is identified
    # with the --ext switch.  Pass everything through here for the default run type.

    ccode = getSisGroups(denaliVariables, parameters)
    return ccode