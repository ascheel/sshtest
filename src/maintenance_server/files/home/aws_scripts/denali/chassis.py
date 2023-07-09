
import denali_search
import denali_utility

#
#   Custom module to print information about a given Chassis
#
#   The blade chassis is given (e.g., bc28.or1), and then this
#   code will list all of the blades in that chassis and their
#   associated slot numbers.
#



##############################################################################
#
# main(denaliVariables, *parameters)
#

def main(denaliVariables, *parameters):

    # This "main" function is called by default if no specific function is identified
    # with the --ext switch.  So, if the user forgets to put "chassis.data", denali
    # will call main, and the code will execute correctly anyway.

    ccode = data(denaliVariables, *parameters)
    return ccode



##############################################################################
#
# data(denaliVariables, *parameters)
#

def data(denaliVariables, *parameters):

    # MRASEREQ-41432 (several changes in this function)
    # Save the submitted fields list for use in the blade query below
    #   Change it to a List
    #   See if the slot was called out as a field/column to print; if not,
    #     add it (sorry, the slot is required output for the chassis)
    #   Change it back to a string so the output functions can correctly
    #     utilize it
    submitted_fields = denaliVariables['fields'].split(',')
    if 'slot' not in submitted_fields and 'enclosure_slot' not in submitted_fields:
        if len(submitted_fields) == 1:
            submitted_fields.append('slot')
        else:
            submitted_fields.insert(1, 'slot')
    submitted_fields = ','.join(submitted_fields)

    # allow any sql query search criteria to pass through as well
    denaliVariables["sqlParameters"] = denali_utility.processSQLParameters(denaliVariables)

    # save off the sqlParameters variable so it doesn't influence the chassis search
    sql_parm_save = denaliVariables['sqlParameters']
    denaliVariables['sqlParameters'] = ''

    # define the variables for the initial query of the blade chassis
    denaliVariables["fields"] = "name,device_id,model,device_state,device_service,rack_name,rack_id,cage_name,enclosure_devices"
    dao = denaliVariables["searchCategory"]

    # build the sql query with the given hosts
    (sqlQuery, wildcard) = denali_search.buildHostQuery(denaliVariables)
    sqlQuery = dao + ':' + sqlQuery
    respDictionary = denali_search.constructSQLQuery(denaliVariables, sqlQuery, False)

    if respDictionary == False:
        print "There was a problem with the query -- no results were returned."

        # display return error message from web api
        if denaliVariables["debug"] == True:
            api = denaliVariables["api"]
            print "\nERROR:"
            print "   STATUS  : " + api.get_response_status()
            print "   TYPE    : " + str(api.get_error_type())
            print "   MESSAGE : " + api.get_error_message()
        denali_search.cleanUp(denaliVariables)
        exit(1)

    (printData, overflowData) = denali_search.generateOutputData(respDictionary, denaliVariables)
    itemCount = len(printData)

    # restore any parameter search criteria
    denaliVariables['sqlParameters'] = sql_parm_save

    # loop through the printData structure and pull out the chassis information and display it in a list,
    # and then pull out the devices in that chassis and display them in a table.

    for row in printData:
        if denaliVariables["showHeaders"] == True:
            print
            print "Chassis           : %s  (%s)" % (row[0].strip(), row[1].strip())
            print "Model             : %s" % row[2].strip()
            print "Device State      : %s" % row[3].strip()
            print "Device Service    : %s" % row[4].strip()
            URL = "https://skms.adobe.com/cmdb.rack/view/?rack_id=%s" % row[6].strip()
            print "Rack Name/Rack ID : %s / %s  (%s)" % (row[5].strip(), row[6].strip(), URL)
            #print "Enclosed Devices  : %s" % row[8].strip()
            print

        denaliVariables["serverList"] = row[8].strip().split(',')
        denaliVariables['fields']     = submitted_fields
        (sqlQuery, wildcard) = denali_search.buildHostQuery(denaliVariables)
        sqlQuery = dao + ':' + sqlQuery
        respDictionary = denali_search.constructSQLQuery(denaliVariables, sqlQuery, False)

        if respDictionary == False:
            print "There was a problem with the query -- no results were returned."

            # display return error message from web api
            if denaliVariables["debug"] == True:
                api = denaliVariables["api"]
                print "\nERROR:"
                print "   STATUS  : " + api.get_response_status()
                print "   TYPE    : " + str(api.get_error_type())
                print "   MESSAGE : " + api.get_error_message()
            denali_search.cleanUp(denaliVariables)
            exit(1)

        (printData, overflowData) = denali_search.generateOutputData(respDictionary, denaliVariables)
        denali_search.prettyPrintData(printData, overflowData, respDictionary, denaliVariables)

    return True
