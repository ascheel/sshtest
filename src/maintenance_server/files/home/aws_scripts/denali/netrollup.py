

import denali
import denali_search
import denali_utility

'''
This file is an example of the use of the available denali modular interface.

The idea here is that any python code can be dropped into the denali library directory, and then
  denali can make use of that code immediately.  This means that upgrades to the full set of
  libraries is unnecessary, as specific teams can code up their own module, drop it in and begin
  using the added functionality.

Normal or typical usage will be having denali pass in the list of hosts (devices) and the fields
  requested to be output (columns).  The custom module can then either accept the host/fields
  variables as constituted, or it can manipulate them.

The variables can then be passed to denali for search execution and results or an intermediate
  set of results (which can be manipulated and then output).



The command line use from denali is similar to this:

  denali.py <user> <hosts> <fields> --explain <module>.<function>:<parameters>

  Example:

  denali.py --user=demouser --hosts=db2255.oak1..db2280.oak1 --fields=name,device_state,device_service \
            --explain netrollup.find:parm1,parm2,parm3

In this instance the "netrollup" module will be dynamically loaded and the "find" function within that
  module will be executed passing in three parameters (parm1,parm2,parm3).  The use of parameters and a
  specific function name ("find" above) is optional.

A typical function definition in the module is as follows:
  def find(denaliVariables, *parameters):

By default, denali will pass the "denaliVariables" variable into every function it calls.  This variable
  contains program specific information (passed in command line attributes/values) that will be needed
  by add-on modules.  Because of this, all point of entry functions for an add-on module must at a
  minimum accept denaliVariables as the first parameter in the list.

Additional parameters are passed in via the "*parameters" value.  This is in tuple format giving each
  specific parameter a string value.
  Example:  ('1','2','True','/file.txt')

  The module will have to take the string assignment into account when using any passed in parameters.

The function parameters are separated from the function by use of the colon character (':') as shown
  in the first example above.  Each parameter is separated by a comma (',').  If the space character
  is required, enclose the entire set of parameters in double quotes.
  Exmpale:  netrollup.find:"1,2,3,find this"

If a function name for the new module is not specified, denali will assume "main" is the name of
  the function and will proceed with that in mind.
  Example:  denali.py ... --explain netrollup:parm1

  Denali will call netrollup.main(denaliVariables,parm1)


denaliVariables -- definition of what each value represents:

    "addColumn"         : boolean:       special case -- for the --power/powerid switch
    "addColumnData"     : dictionary:    column data to add
    "aliasLocation"     : string:        aliases file location
    "api"               : webapi object: SKMS web api return value (internal variable)
    "cliParameters"     : list:          cli switches entered
    "columnData"        : list:          column data (name, width, cmdb name, etc.)
    "debug"             : boolean:       status of the debugging flag
    "defaults"          : boolean:       status of the default setting (decommissioned, etc.)
    "denaliLocation"    : string:        location of the denali script
    "domainsToStrip"    : list:          domain names to strip from a submitted host list
    "explain"           : boolean:       custom module to run?
    "fields"            : string:        columns to display
    "method"            : string:        typically 'search' (CMDB method to use)
    "outputTarget"      : list:          where the output will be put (screen,file, etc.)
    "searchCategory"    : string:        the dao to query (default is 'DeviceDao')
    "searchCriteria"    : string:        for filtering the searches (unused)
    "serverList"        : list:          the list of servers/hosts to search for
    "sessionPath"       : string:        path for SKMS session file
    "showHeaders"       : boolean:       if the headers (column titles) should be shown
    "showsql"           : boolean:       status of the showsql option (show sql search string generated)
    "simpleSearch"      : boolean:       is this a simple search, or complex sql query? (internal variable)
    "sortColumnsFirst"  : boolean:       for special queries; i.e., --switch/--switchid
    "sqlParameters"     : list:          sql cli parameters entered -- for more complex queries
    "sqlSort"           : string:        sort information on retrieved data combined in sql query ("ORDER BY")
    "summary"           : boolean:       summary status information of the DB query/results (counts)
    "textTruncate"      : boolean:       for txt_screen output, truncate row at the column boundary if true
    "textWrap"          : boolean:       if true, wrap row column data in the txt display output
    "userAliases"       : dictionary:    user aliases found in .denali/aliases file
    "userName"          : string:        usename to authenticate against SKMS with

Those of use would likely be cliParameters, columnData, fields, outputTarget, serverList, showHeaders, showsql,
                             sqlParameters, and summary


At the end of execution, return "True" or "False" back to the calling function in denali.
True is the execution succeeded.
False means the execution failed.

If error messages are wanted, they can be printed in the function calls here.


'''



##############################################################################
#
# listing(denaliVariables, *parameters)
#

def listing(denaliVariables, *parameters):

    # This function takes a list of servers, and one by one queries CMDB for data pertaining
    # to them.  It then prints this data in a "list" with appropriate labels.

    deviceList = denaliVariables["serverList"]
    fields = denaliVariables["fields"]

    devicesNotFound = []

    '''
    # print the --fields output
    print
    print "fields to print = %s" % fields
    print

    # print a list of every device/host in the deviceList
    for (count, device) in enumerate(deviceList):
        print "count: #%02d  device: %s" % ((count + 1), device)
    '''

    # To have denali output the data (when it is correct), call "constructSimpleQuery"
    # This will do everything needed to print the data to the screen and/or file(s)
    # requested.
    #if denali_search.constructSimpleQuery(denaliVariables) == False:
    #    return False

    #
    # If the data is fine, but before being printed it needs to be massaged, or added
    # to, or in whatever other way manipulated, do the following.
    #
    # 1.  Can denali (as if from an outside script)
    #       See denali_utility.getDenaliResponse() for more information on the function
    # 2.  Using the returned data massage it (insert rows/columns, change cell data, etc.)
    # 3.  Submit the manipulated data back to denali for printing/output.
    #       Example:  Add a "ping response time" data point for each device
    #           See denali_utility.genericColumnInsert() for more information on the function
    #       OR
    # 4.  Print the data in the format/output wanted inside the custom module using
    #     the originally collected data as the base-point for generating the rest of
    #     the needed information.
    #


    #
    # For this specific example (netrollup), I want to take the list of host names (devices)
    # and determine what a device's network connectivity is (switch -> parent switch -> etc.).
    #

    for device in deviceList:

        select = "name,connected_to_device_interface.device.name,enclosure_device.name,enclosure_device_id,enclosure_slot,model"
        where = "name"

        # Return a dictionary with a key for each initial object (name, in this case) which
        # represent a row in the table.
        #
        #   e.g.,  { 'db2255.oak1': ['column1-data', 'column2-data', ...] }
        #
        # For the query submitted, each device will have 3 columns of data:
        #   [0] = switch
        #   [1] = enclosure_device.name : device name of the chassis (if populated)
        #   [2] = enclosure_device_id : device_id of the chassis
        #   [3] = enclosure_slot : if this is a blade, this is the slot in the chassis
        #   [4] = host/device model
        #
        # The code can then operate on the column data in whatever manner it chooses.
        #
        # All switches below for "getDenaliResponse()" are required.

        hostDict = denali_utility.getDenaliResponse(denaliVariables,     # internal variable data
                                                    select,              # equivalent to an SQL SELECT statement value(s)
                                                    where,               # equivalent to an SQL WHERE statement value(s)
                                                    device,              # the device requested to search on
                                                    True                 # True = generic response / False = used for "--power"
                                                                         # and "--powerid" switches
                                                   )

        if hostDict:
            print "\nHost Name: %s" % device

            # process the switch information
            if device in hostDict:
                if hostDict[device][0].count(',') > 0:
                    print "  Host Switches:  %s" % hostDict[device][0]
                else:
                    if hostDict[device][0] == '':
                        print "  Host Switch  :  Not populated in CMDB"
                    else:
                        print "  Host Switch  :  %s" % hostDict[device][0]
            else:
                print "  Host Switch  :  No Data Found"

            # process model information
            if hostDict[device][4] != '':
                print "  Host model   :  %s" % hostDict[device][4]

            # process the blade/chassis information
            if hostDict[device][1]:
                print
                print "  This host is a blade"
                print "    Blade Chassis   :  %s" % hostDict[device][1]
                print "    Blade Slot      :  %s" % hostDict[device][3]

                select = "name,connected_to_device_interface.device.name,model"
                where  = "name"

                # ok, so we found a blade that has a chassis -- let's get the chassis switch information
                chassDict = denali_utility.getDenaliResponse(denaliVariables, select, where, hostDict[device][1], True)

                if chassDict:
                    if hostDict[device][1] in chassDict:
                        if chassDict[hostDict[device][1]][0].count(',') > 0:
                            print "    Chassis Switches:  %s" % chassDict[hostDict[device][1]][0]
                        else:
                            print "    Chassis Switch  :  %s" % chassDict[hostDict[device][1]][0]
                    else:
                        print "  Chassis Switch  :  No Data Found"

        else:
            devicesNotFound.append(device)

    print
    print
    print "Requested Devices not found in CMDB:"
    for device in devicesNotFound:
        print " %s" % device



    return True



##############################################################################
#
# table(denaliVariables, *parameters)
#

def table(denaliVariables, *parameters):
    # This function repeats the operation from the "listing" function, but uses less
    # queries on the database.  The resulting data is displayed in a table.

    # To do in this function:
    #   1.  Investigate each device.  physical, virtual, blade, chassis?
    #       1a.  Display the machine type in a new column
    #   2.  If the machine is a blade, display it's chassis
    #       2a.  Display the chassis name, model and switch

    deviceList = denaliVariables["serverList"]
    fields = denaliVariables["fields"]

    denaliVariables["fields"] = fields = "name,connected_to_device_interface.device.name,enclosure_device.name,enclosure_slot,model"

    # Starting table
    # [0]        [1]          [2]                       [3]                     [4]
    # host name, host switch, (if blade) chassis name, (if blade) chassis slot, host model

    # Ending table
    # [0]        [1]          [2]-inserted  [2 -> 3]                 [3 -> 4]                 [5]-inserted    [4 -> 6]
    # host name, host switch, machine type, (if blade) chassis name, (if blade) chassis slot, chassis switch, host model

    # build the sql query with the given hosts
    (sqlQuery, wildcard) = denali_search.buildHostQuery(denaliVariables)

    # add the appropriate dao to the query (at the front)
    sqlQuery = "DeviceDao:" + sqlQuery

    # With this query built, the code can now call denali to ask it to execute it.
    # The "False" parameter means to return the data in dictionary format from the query.
    respDictionary = denali_search.constructSQLQuery(denaliVariables, sqlQuery, False)

    if respDictionary == False:
        print "something went wrong."
        denali_search.cleanUp(denaliVariables)
        exit(1)

    #print
    #print ":: Response Dictionary ::"
    #print
    #print respDictionary

    #
    # Put the dictionary-ized data into a row/column data format (in "printData")
    # "overflowData" is when a column string is longer than the column size (in print).
    #
    # Typically, the overflowdata can be ignore _unless_ a new column or row is added;
    # in that case because the overflow data is keyed by row number and column number, it
    # will have to be potentially re-keyed (re-numbered, if a row is added) and potentially
    # re-columned (if column(s) are added) to keep the data consistent with the proper and
    # column.
    #
    # printData is a python List of python Lists.
    #   [ [row1 data], [row2 data], [row3 data], ... ]
    # Each row is separated into columns by a comma (outside of quotes)
    #
    #   [   ['host name','model','device service','device state'],
    #       ['host name','model', ...]
    #       ...
    #   ]
    #
    #   printData[0] is the first row of data
    #   printData[0][0] is the first column item in the first row of data
    #   etc.
    #
    #   All of the data here is properly formated for the table (column width has been
    #   added).  If any modification is done, be sure and keep the columnWidth properly
    #   formated if the output is to go to the screen it table format.
    #
    #   All column formatting options are stored and used by denali here:
    #       denaliVariables["columnData"]
    #   The format is a list of lists (just as with the print data); one list for each column.
    #       ['alias column name', 'cmdb column name', 'printed column name', column width]
    #
    (printData, overflowData) = denali_search.generateOutputData(respDictionary, denaliVariables)

    #print
    #print ":: printData variable ::"
    #print
    #print printData

    #
    # At this point, any customization to the data can happen ...
    #   Add rows
    #   Add columns
    #   Change cell contents
    #   etc.
    #
    # Then put the data back together inside "printData" and send it off to be
    # pushed out to the screen or file if wanted, or create a new output/print routine
    # to display the data as desired.
    #

    # Change #1: (Add a column)
    # ===============================
    # For this module, detect the machine type first.  I just want this function to return a
    # list of data (one item representing each host).  Have it stored in the denaliVariable
    # of addColumnData.
    denaliVariables["addColumnData"] = detectMachineType(printData)

    # machineType is now a new column of data to insert
    # insertColumnNumber == what column should this new data be?  For this, '2' is the number.
    insertColumnNumber = 2

    # newColumnData == column header data for printing ... the most important are the last
    # two in the list -- that's the column heading and column width; the first two can be
    # anything for this application of it.  This makes the output look much cleaner and nice.
    newColumnData = ["machine_type", "machine_type", "Machine Type", 15]
    printData = denali_utility.genericColumnInsert(printData, denaliVariables, insertColumnNumber, newColumnData)


    # Change #2: (Add a column)
    # ===============================
    # For each chassis found, get the switch it is connected to and put it in the second to last column;
    # i.e., create a new column
    denaliVariables["addColumnData"] = getChassisSwitch(printData, denaliVariables)
    insertColumnNumber = 5
    newColumnData = ["chassis_switch", "chassis_switch", "Chassis Switch", 20]
    printData = denali_utility.genericColumnInsert(printData, denaliVariables, insertColumnNumber, newColumnData)


    # Change #3: (Change a column)
    # ===============================
    # For each server that is not a blade, make sure the blade slot number doesn't remain zero (0).
    # Instead, change it to "N/A".  This is changing the contents of a column (cell) in-place.
    # When the cell is changed, the cell padding (spaces) needs to be reset (columnWidth).
    # Also, be aware that the cell contents will be pre-padded with spaces -- strip the cell before
    # any comparisons.
    columnWidth = 14
    for (index, row) in enumerate(printData):
        if row[4].strip() == '0':
            printData[index][4] = "N/A".ljust(columnWidth)


    # The additions are done -- print the data
    denali_search.prettyPrintData(printData, overflowData, respDictionary, denaliVariables)

    # return True so denali knows whether this succeeded or failed.
    return True


##############################################################################
#
# getChassisSwitch(printData)
#

def getChassisSwitch(printData, denaliVariables):

    chassisSwitch = []

    for row in printData:
        if row[2].strip() == "Blade":

            # get the switch for this chassis
            select = "name,connected_to_device_interface.device.name"
            where  = "name"

            # ok, so we found a blade that has a chassis -- let's get the chassis switch information
            chassDict = denali_utility.getDenaliResponse(denaliVariables, select, where, row[3].strip(), True)
            if row[3].strip() in chassDict:
                chassisSwitch.extend(chassDict[row[3].strip()])
            else:
                chassisSwitch.append('')
        else:
            chassisSwitch.append('')

    return chassisSwitch



##############################################################################
#
# detectMachineType(printData)
#

def detectMachineType(printData):

    machineType = []

    for row in printData:
        if row[2].strip() != '':
            machineType.append("Blade")
        elif row[4].startswith("BladeSystem"):
            machineType.append("Blade Chassis")
        else:
            machineType.append("Physical")

    return machineType



##############################################################################
#
# main(denaliVariables, *parameters)
#

def main(denaliVariables, *parameters):
    # This is the default function executed if one isn't specifically identified
    print "main function"