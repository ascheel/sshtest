
import denali_search
import denali_utility
import denali_arguments

#
#   Custom report module to print information about software versions
#
#   Given a list of hosts, this module will collect the software
#   installed on the server (as shown by CMDB), and then devide it
#   into columns for a quick look-up.  Each column will have a header
#   of the software (MySQL, PHP, etc.), and each item in the column
#   will have the version number of the software installed.
#


softwareVersions = {}


##############################################################################
#
# main(denaliVariables, *parameters)
#

def main(denaliVariables, *parameters):

    # This "main" function is called by default if no specific function is identified
    # with the --ext switch.  So, if the user forgets to put "software.data", denali
    # will call main, and the code will execute correctly anyway.

    ccode = data(denaliVariables, *parameters)
    return ccode



##############################################################################
#
# shrinkVersion(title)
#

def shrinkVersion(title):

    global softwareVersions

    if title in softwareVersions:
        title = softwareVersions[title]
    else:
        for (index, char) in enumerate(title):
            if char.isdigit():
                location = title.rfind('.')
                if title[(location + 1)].isdigit():
                    newTitle = title[index:]
                else:
                    newTitle = title[index:location]
                softwareVersions.update({title:newTitle})
                title = newTitle
                break
        else:
            softwareVersions.update({title:title})

    return title



##############################################################################
#
# getColumnHeaders(printData, softwareColumn)
#

def getColumnHeaders(printData, softwareColumn):

    columnList = []

    for row in printData:
        columns = row[softwareColumn].strip().split(',')
        for item in columns:
            if item not in columnList:
                columnList.append(item)

    return columnList



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

    # Verify the necessary columns were added -- shouldn't be necessary if
    # the above code does its job correctly.
    if host_name_column == -1:
        print "Could not find host name in field list."
        denali_search.cleanUp(denaliVariables)
        exit(1)

    return host_name_column



##############################################################################
#
# getSoftwareColumnNumbers(denaliVariables["fields"])
#

def getSoftwareColumnNumbers(fields):

    columnFields = fields.split(',')

    for (index, field) in enumerate(columnFields):
        if field == "software_name" or field == "software_version.software.name":
            nameColumn = index
            break
    else:
        nameColumn = -1

    for (index, field) in enumerate(columnFields):
        if field == "software_version" or field == "software_version.version":
            versionColumn = index
            break
    else:
        versionColumn = -1

    return (nameColumn, versionColumn)



##############################################################################
#
# data(denaliVariables, *parameters)
#

def data(denaliVariables, *parameters):

    # This variable controls whether the full text version is displayed or
    # just a shortened version.  [[ fullVersion ]]

    # check if there is a passed in parameter requesting a shorter version
    # description to be displayed
    if len(parameters) > 0:
        if parameters[0].lower() == "short":
            fullVersion = False
        else:
            fullVersion = True
    else:
        fullVersion = True

    # The host name field _MUST_ exist in the field list.  If it doesn't add it in.
    hostNameColumn = checkFieldList(denaliVariables)

    # define the variables for the initial query of the software versions
    dao = denaliVariables["searchCategory"]
    denaliVariables["textWrap"]     = False
    denaliVariables["textTruncate"] = False

    fields = denaliVariables["fields"].split(',')
    if "software_name" not in fields and "software_version.software.name" not in fields:
        denaliVariables["fields"] += ",software_name"

    if "software_version" not in fields and "software_version.version" not in fields:
        denaliVariables["fields"] += ",software_version"

    # get the software field column numbers
    (softwareNameColumn, softwareVersionColumn) = getSoftwareColumnNumbers(denaliVariables["fields"])

    # build the sql query with the given hosts
    denaliVariables["sqlParameters"] = denali_utility.processSQLParameters(denaliVariables)
    (sqlQuery, wildcard) = denali_search.buildHostQuery(denaliVariables)
    sqlQuery = dao + ':' + sqlQuery
    printData = denali_utility.sqlQueryConstructionResponse(denaliVariables, sqlQuery)

    if printData == False:
        print "There was a problem in the software query.  Halting execution."
        denali_search.cleanUp(denaliVariables)
        exit(1)

    itemCount = len(printData)

    # reset the output target variables -- so it can print everything in one go
    denali_utility.resetOutputTarget(denaliVariables)

    softwareHeaders = getColumnHeaders(printData, softwareNameColumn)

    # if the empty column (no software defined) is in the list, make sure it is the
    # last column printed (so, first in the list to add)
    if len(softwareHeaders) > 0:
        for (index, column) in enumerate(softwareHeaders):
            if column == '':
                softwareHeaders.pop(index)
                softwareHeaders.insert(0, '')
                break

    for column in softwareHeaders:
        columnPrint = []

        if column != '':
            category = column + " Version"
        else:
            category = "No Software Defined"

        for row in printData:
            softwareCell = {}

            softwareTitle = row[softwareNameColumn].strip().split(',')
            versionNumber = row[softwareVersionColumn].strip().split(',')

            for (index, software) in enumerate(softwareTitle):
                softwareCell.update({software:versionNumber[index]})

            for swTitle in softwareCell:
                if column == swTitle:
                    if fullVersion == False:
                        if len(swTitle) != 0:
                            swTitle = shrinkVersion(softwareCell[swTitle])
                            columnPrint.append(swTitle)
                        else:
                            columnPrint.append("No Software Defined")
                    else:
                        if len(swTitle) != 0:
                            columnPrint.append(softwareCell[swTitle])
                        else:
                            columnPrint.append("No Software Defined")
                    break
            else:
                columnPrint.append('')

        denaliVariables["addColumnData"] = columnPrint
        insertColumnNumber = len(denaliVariables["fields"])

        # set the column width according to the version format displayed
        if fullVersion == False:
            columnWidth = 21
        else:
            columnWidth = 45

        newColumnData = ["", "", category, columnWidth]

        printData = denali_utility.genericColumnInsert(printData, denaliVariables, insertColumnNumber, newColumnData)

    # remove the initial columns added to get the software version data
    printData = denali_utility.removeColumn(denaliVariables, printData, softwareNameColumn)
    #(softwareNameColumn, softwareVersionColumn) = getSoftwareColumnNumbers(denaliVariables["fields"])
    printData = denali_utility.removeColumn(denaliVariables, printData, (softwareVersionColumn - 1))

    # new data may be larger than the columns -- wrap it and then print it.
    denaliVariables["textWrap"] = True
    (printData, overflowData) = denali_search.wrapColumnData(denaliVariables, printData)
    itemCount = len(printData)
    respDictionary = {}
    denali_search.prettyPrintData(printData, overflowData, respDictionary, denaliVariables)

    if denaliVariables["summary"] == True:
        print
        print " Total Items Displayed: %d" % itemCount

    if denaliVariables["showsql"] == True:
        denali_utility.showSQLQuery(sqlQuery, denaliVariables)

    return True