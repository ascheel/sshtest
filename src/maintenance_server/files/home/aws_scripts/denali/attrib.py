
import denali_arguments
import denali_search
import denali_utility
import copy

#
#   Custom module to allow advanced attribute searching for hosts
#


MATCH_ALL     = 0
MATCH_PARTIAL = 0
MATCH_REMOVE  = 0
MATCH_NORMAL  = 0


##############################################################################
#
# main(denaliVariables, *parameters)
#

def main(denaliVariables, *parameters):

    # This "main" function is called by default if no specific function is identified
    # with the --ext switch.

    ccode = attributeMain(denaliVariables, *parameters)
    return ccode



##############################################################################
#
# attributeMain(denaliVariables, *parameters)
#

def attributeMain(denaliVariables, *parameters):

    debug = False

    denaliVariables['advAttribute'].update({'--attribute_name':[], '--attribute_value':[], 'error':False})

    for (index, item) in enumerate(denaliVariables['sqlParameters']):
        if item[0] == '--attribute_name' or item[0] == '--attribute_value':
            # found an attribute request -- analyze it
            if denaliVariables["attributes"] == False:
                # Likely the user did not use "-f/--fields" with at least the name and ATTRIBUTES field
                # idetifiers specified.  The ATTRIBUTES field is key to making this work, so add it in
                # and process this rest of this as if it were given originally.
                ccode = denali_arguments.getAttributeFields('name,ATTRIBUTES', denaliVariables)
                denaliVariables["attributes"] = True
                denaliVariables["fields"] = denali_arguments.fieldSubstitutionCheck(denaliVariables, 'name,ATTRIBUTES')

            # adjust sqlParameters as needed for this query
            adjustAttributeSQLParameters(denaliVariables, index, item)

    # see if any sql parameters need to be removed (for NOT: queries)
    removeAttributeSQLParameters(denaliVariables)

    # query for the data and then output it
    (sqlQuery, itemCount) = retrieveSearchList(denaliVariables)

    # show the sql query if requested
    if denaliVariables['showsql'] == True and len(sqlQuery):
        print
        print "SQL Query submitted (prior to searching algorithm application):\n%s" % sqlQuery

    # show the summary if requested
    if denaliVariables['summary'] == True:
        count = denaliVariables['attribute_count']
        denali_utility.printSummaryInformation(denaliVariables, itemCount, False, count)

    #
    # Return code from the attrib.py module
    #
    # If itemCount is False, it means the query came up empty (no matching devices found)
    # Should this return False?
    # If False is returned, the Denali exit code will be '1'; otherwise '0' with True returned
    #

    if denaliVariables['advAttribute']['error'] == True:
        if debug == True:
            print "returning False"
        return False

    if debug == True:
        print "returning True"

    return True



##############################################################################
#
# adjustAttributeSQLParameters(denaliVariables, index, item)
#

def adjustAttributeSQLParameters(denaliVariables, index, item):

    global MATCH_ALL
    global MATCH_PARTIAL
    global MATCH_NORMAL

    # determine the type of query
    AND_count = denaliVariables['sqlParameters'][index][1].count(' AND ')
    OR_count  = denaliVariables['sqlParameters'][index][1].count(' OR ')

    if AND_count > 0 and OR_count == 0:
        # all 'AND' is a match everything query
        MATCH_ALL += 1

    if AND_count > 0 and OR_count > 0:
        # mixed search with AND's and OR's
        MATCH_PARTIAL += 1

    if OR_count > 0 and AND_count == 0:
        # normal attribute search put in the advanced module
        MATCH_NORMAL += 1

    #
    # Check (1):  Replace all " AND " statements with " OR " to allow successful searching in CMDB.
    #
    if AND_count > 0:
        new_sql_value = denaliVariables['sqlParameters'][index][1].replace(' AND ', ' OR ')
        denaliVariables['sqlParameters'][index][1] = new_sql_value

    attribute_category = denaliVariables['sqlParameters'][index][0]
    attribute_values   = denaliVariables['sqlParameters'][index][1]

    if attribute_values.startswith("NOT:") == False:
        if attribute_category not in denaliVariables['advAttribute']:
            denaliVariables['advAttribute'][attribute_category] = attribute_values.split(' OR ')
        else:
            if len(denaliVariables['advAttribute'][attribute_category]) > 0:
                denaliVariables['advAttribute'][attribute_category].extend(attribute_values.split(' OR '))
            else:
                denaliVariables['advAttribute'][attribute_category] = attribute_values.split(' OR ')

    return


##############################################################################
#
# removeAttributeSQLParameters(denaliVarliabes)
#

def removeAttributeSQLParameters(denaliVariables):

    global MATCH_REMOVE

    debug = False

    sql_parameters_copy = []

    #
    # Check (2):  Remove all "NOT:" name/value pairs from denaliVariables['sqlParameters']
    #             Save in denaliVariables['advAttribute']['sql_remove'] for future use
    #
    for (index, item) in enumerate(denaliVariables['sqlParameters']):
        if item[1].startswith('NOT:'):
            # put the data in advAttribute
            if 'sql_remove' not in denaliVariables['advAttribute']:
                denaliVariables['advAttribute'].update({'sql_remove':[item]})
            else:
                denaliVariables['advAttribute']['sql_remove'].append(item)

            # Include the same data for attribute_name in the sql parameters
            # data object.  This tells Denali to show the specific attribute name
            # columns associated with the search.  If there is already a specified
            # attribute_name (without a NOT:) in the sql parameters, then don't do
            # anything; let the user's choice override this decision.
            #
            # Do nothing with the attribute value data -- it could be associated
            # with any attribute name.  The user will have to pick what they want
            # to see, or every attribute will be displayed by default.
            if item[0] == "--attribute_name":
                for sqlParm in denaliVariables['sqlParmsOriginal']:
                    if sqlParm[0] == "--attribute_name":
                        if sqlParm[1].find('NOT:') == -1:
                            break
                        else:
                            if debug == True:
                                print "it is a NOT"
                                print "  sqlParm = %s" % sqlParm

                            attribute_value = item[1].split(':', 1)[1]
                            sql_parameters_copy.append(['--attribute_name', attribute_value])

                else:
                    attribute_value = item[1].split(':', 1)[1]
                    sql_parameters_copy.append(['--attribute_name', attribute_value])
        else:
            # add this non-"NOT:" entry to the sql_parameters_copy List
            sql_parameters_copy.append(item)

    sql_parameters_copy = combineAttributeValues(denaliVariables, sql_parameters_copy)

    if debug == True:
        print "sql_copy = %s" % sql_parameters_copy

    #denaliVariables['sqlParameters'] = sql_parameters_copy
    denaliVariables["sqlParmsOriginal"] = list(sql_parameters_copy)
    #denaliVariables['sqlParmsOriginal'] = [['--device_service', 'Analytics - DB - Mongo NLS'], ['--location', 'lon5 or lon7'], ['--attribute_name', 'CLUSTER_NAME OR REPLICA_SET']]

    if debug == True:
        print "dvsql  = %s" % denaliVariables['sqlParameters']
        print "dvsqlo = %s" % denaliVariables['sqlParmsOriginal']

    if 'sql_remove' in denaliVariables['advAttribute']:
        if debug == True:
            print "sqlr   = %s" % denaliVariables['advAttribute']

        NOT_count = len(denaliVariables['advAttribute']['sql_remove'])
        if NOT_count > 0:
            # make sure and remove some items
            MATCH_REMOVE += 1

    return



##############################################################################
#
# combineAttributeValues(denaliVariables, list_data)
#

def combineAttributeValues(denaliVariables, list_data):

    debug         = False
    combine_data  = []
    new_list_data = []

    for item in list_data:
        if item[0] == '--attribute_name':
            combine_data.append(item[1])
        else:
            new_list_data.append(item)

    new_list_data.append(['--attribute_name', ' OR '.join(combine_data)])

    if debug == True:
        print "combine_data = %s" % combine_data
        print "new_list_data = %s" % new_list_data

    return new_list_data



##############################################################################
#
# retrieveSearchList(denaliVariables)
#

def retrieveSearchList(denaliVariables):

    if denaliVariables['api'] is None:
        denali_utility.retrieveAPIAccess(denaliVariables)

    if len(denaliVariables["sqlParameters"]) > 0:
        denaliVariables["sqlParameters"] = denali_utility.validateSQL(denaliVariables)
    else:
        # what's the point of being here without a qualifying search?
        denaliVariables["sqlParameters"] = ''

    (sqlQuery, wildcard) = denali_search.buildHostQuery(denaliVariables)
    (subData, itemCount) = executeAttributeSQLQuery(denaliVariables, sqlQuery, 0, 1)

    if subData == False and itemCount == False:
        # oops, problem -- no data returned
        print "Denali Response     : No data returned for attribute query"
        return (sqlQuery, False)

    return (sqlQuery, itemCount)



##############################################################################
#
# executeAttributeSQLQuery(denaliVariables, sqlQuery, index, numOfQueries)
#
#   This is a lift/copy of the executeSQLQuery function from denali_search
#   purpose-built to work with the advanced attribute query code in this external
#   module.  There are, of course, _some_ changes to the function, but for the
#   most part it is the same function with the same logic flow.  This function
#   was used specifically because it allows >5000 hosts, and has logic built-in
#   to work with the command functionality of Denali.  If either of those were
#   left out, this new feature would be less than complete or ideal (read: it
#   wouldn't be used or useful for most search applications).
#
#   The reason this is used here is so the core path of the search functionality
#   is not altered for this query-type that will be, essentially, a very low
#   proportionality of overall queries done in Denali.  The changes needed for
#   that would confuse that path and logic.  So, the code is done here with the
#   same logic and those purpose-built changes here (so it is readily apparent
#   what their purpose is and if there are bugs, they only affect this code path).
#

def executeAttributeSQLQuery(denaliVariables, sqlQuery, index, numOfQueries):

    if denaliVariables["debug"] == True:
        print "\n++Entered executeAttributeSQLQuery\n"

    subData     = ''
    next_page   = True
    page_number = 0
    commandSent = False

    for arg_parameter in denaliVariables["cliParameters"]:
        if arg_parameter[0] == "-c" or arg_parameter[0] == "--command":
            commandSent = True

    while next_page == True:
        page_number += 1

        # Set the file append mode for output files based on the page_number.
        # page_numbers >= 2 will set append mode to True.
        for item in denaliVariables['outputTarget']:
            item.append = page_number > 1

        responseDictionary = denali_search.executeWebAPIQuery(denaliVariables, sqlQuery)

        #print "rd = %s" % responseDictionary
        if denaliVariables["debug"] == True:
            print "\nresponseDictionary = %s" % responseDictionary

        if responseDictionary == False:
            return (False, False)

        # number of hosts found in responseDictionary
        #host_number = len(responseDictionary['data']['results'])
        #if host_number == 0:
        #    print "No devices found for the attribute query submitted (1)"

        # Find the requested matches between attribute names/values across multiple hosts and page responses
        responseDictionary = hostAttributeMatching(denaliVariables, responseDictionary)
        if responseDictionary == False:
            # error condition -- need to stop here
            return (False, False)
        if len(responseDictionary['data']['results']) == 0:
            # _This_ CMDB page response may have no matching hosts, but the next page could.
            # increment the page counter and resubmit for the next page query.
            (pageInfo, item_count) = denali_search.checkItemCount(denaliVariables, responseDictionary)
            if pageInfo != False:   # new pages to query fo
                continue
            else:                   # no new pages ... exit out
                return (False, False)

        if responseDictionary != False:
            # check the item count -- need another page?
            method = denaliVariables["method"]
            (pageInfo, item_count) = denali_search.checkItemCount(denaliVariables, responseDictionary)

            if (index + 1) == numOfQueries:
                (printData, overflowData) = denali_search.generateOutputData(responseDictionary, denaliVariables)
                if printData == False:
                    # problem creating printData -- error message should already have been
                    # printed in context with the problem.  Just exit here.
                    return (False, False)

                # Be careful here -- this is the main printing routine being controlled by a "command" variable
                # setting.  If this is incorrectly done, nothing will print.
                #
                # If False, then output data normally (screen, file, etc.)
                # If True, then record the host list for use with the command interface.
                if commandSent == False:
                    # normal path for outputting data
                    if denaliVariables["monitoring"] == False:
                        denali_search.prettyPrintData(printData, overflowData, responseDictionary, denaliVariables)
                    else:
                        # pull out the host names and put them in denaliVariables["serverList"]
                        if denaliVariables["debug"] == True:
                            print "Monitoring debug:  repopulate serverList after search"
                        denali_utility.repopulateHostList(denaliVariables, printData, responseDictionary)
                else:
                    # command request submitted
                    denali_utility.repopulateHostList(denaliVariables, printData, responseDictionary)

            else:
                # sub-query data handling / don't print sub-query data / just gather the data for later use
                subData = denali_search.gatherSearchedData(responseDictionary, denaliVariables)

            # clean up the data --- remove 'nones' (return as a dictionary)
            responseDictionary = denali_search.clearUpNones(responseDictionary)

            if pageInfo != False:      # new pages to query for
                sqlQuery = denali_search.modifyQueryPageSetting(sqlQuery, pageInfo)

                # if json activated for output type -- otherwise, don't store the data
                for target in denaliVariables["outputTarget"]:
                    if target.type.startswith("json"):
                        if not denaliVariables["jsonResponseDict"]:
                            denaliVariables["jsonResponseDict"]["results"] = responseDictionary["data"]["results"]
                        else:
                            denaliVariables["jsonResponseDict"]["results"].append(responseDictionary["data"]["results"])
                        break
            else:
                next_page = False

                # output the information
                for target in denaliVariables["outputTarget"]:
                    if target.type.startswith("json"):
                        # Retrieve and output the last page of json data if it exists from the "last" query
                        if not denaliVariables["jsonResponseDict"]:
                            responseDictionary = responseDictionary["data"]
                        else:
                            denaliVariables["jsonResponseDict"]["results"].append(responseDictionary["data"]["results"])
                            responseDictionary = denaliVariables["jsonResponseDict"]
                        denaliVariables["jsonPageOutput"] = True

                        (printData, overflowData) = denali_search.generateOutputData(responseDictionary, denaliVariables)
                        if printData == False:
                            # problem creating printData -- error message should already have been
                            # printed in context with the problem.  Just exit here.
                            return (False, False)
                        denali_search.prettyPrintData(printData, overflowData, responseDictionary, denaliVariables)
                        break
        else:
            next_page = False
            return False, False

    return (subData, item_count)



##############################################################################
#
# hostAttributeMatching(denaliVariables, responseDictionary)
#
#   This function is designed to handle any number of attributes name/value matches
#   and should be good with 5 or 10 or whatever.  The likely use would be 2 or perhaps
#   3 attributes (with name/value matches).
#
#   This is a filtering function.  One search result feeds the next, and so on.
#   After the first search is done (e.g., name search), those results are passed
#
#   Still to do:
#   (1) Allow multiple potential values for an attribute value (the value could be a or b or c, etc).
#   (3) Match correctly an empty string for the attribute value
#

def hostAttributeMatching(denaliVariables, responseDictionary):

    debug = False

    if MATCH_NORMAL > 0 and MATCH_ALL == 0 and MATCH_REMOVE == 0 and MATCH_PARTIAL == 0:
        # Default (not advanced) attribute query, just return the responseDictionary because
        # no advanced adding/subtracting is needed here.
        return responseDictionary

    # new dictionary where a subset of the query return is stored
    adjustedResponseDictionary = {}

    # The responseDictionary is > 99% data from the query.  So, rather than doing a deepcopy of
    # it (where the code then deletes that 99% anyway), this code just recreates an empty version
    # of the dictionary (saves memory and improves performance) where qualifying hosts can be
    # added

    # just in case anything funny is going on with the responseDictionary, do a 'get' on each
    # of the elements.  No need to crash here ... so the code is careful.
    ard_status         = responseDictionary.get('status', None)
    ard_messages       = responseDictionary.get('messages', [])
    ard_error_type     = responseDictionary.get('error_type', '')
    ard_last_page      = responseDictionary['data']['paging_info'].get('last_page', None)
    ard_items_per_page = responseDictionary['data']['paging_info'].get('items_per_page', None)
    ard_item_count     = responseDictionary['data']['paging_info'].get('item_count', None)
    ard_current_page   = responseDictionary['data']['paging_info'].get('current_page', None)

    adjustedResponseDictionary.update(
        {
            'status'     : ard_status,
            'messages'   : ard_messages,
            'error_type' : ard_error_type,
            'data'       : {
                            'paging_info': {
                                            'last_page'      : ard_last_page,
                                            'items_per_page' : ard_items_per_page,
                                            'item_count'     : ard_item_count,
                                            'current_page'   : ard_current_page
                                           },
                            'results' : []
                           }
        }
    )

    # make a copy of this "empty" dictionary (to avoid data crossover problems)
    empty_dictionary1 = copy.deepcopy(adjustedResponseDictionary)
    empty_dictionary2 = copy.deepcopy(adjustedResponseDictionary)
    empty_dictionary3 = copy.deepcopy(adjustedResponseDictionary)

    if MATCH_ALL > 0:
        if debug == True:
            print "MATCH_ALL"
        #
        # All names and values have to match (positive match)
        #
        # If the len of (currently added) hosts in the adjustedDictionary is non-zero, then the
        # responseDictionary is actually the adjustedDictionary.
        if len(adjustedResponseDictionary['data']['results']) > 0:
            adjustedResponseDictionary = attributeALLName_ValueIntersection(denaliVariables, adjustedResponseDictionary, empty_dictionary1)
        else:
            adjustedResponseDictionary = attributeALLName_ValueIntersection(denaliVariables, responseDictionary, empty_dictionary1)

        if adjustedResponseDictionary == False:
            return False

    if MATCH_REMOVE > 0:
        if debug == True:
            print "MATCH_REMOVE"
        #
        # One or more names and values cannot be included (negative match)
        #
        # If the len of (currently added) hosts in the adjustedDictionary is non-zero, then the
        # responseDictionary is actually the adjustedDictionary.
        if len(adjustedResponseDictionary['data']['results']) > 0:
            adjustedResponseDictionary = attributeNOTName_ValueIntersection(denaliVariables, adjustedResponseDictionary, empty_dictionary2)
        else:
            adjustedResponseDictionary = attributeNOTName_ValueIntersection(denaliVariables, responseDictionary, empty_dictionary2)

        if adjustedResponseDictionary == False:
            return False

    if MATCH_PARTIAL > 0:
        if debug == True:
            print "MATCH_PARTIAL"
        #
        # Some names and values have to match
        #
        # If the len of (currently added) hosts in the adjustedDictionary is non-zero, then the
        # responseDictionary is actually the adjustedDictionary.
        if len(adjustedResponseDictionary['data']['results']) > 0:
            adjustedResponseDictionary = attributePARTIALName_ValueIntersection(denaliVariables, adjustedResponseDictionary, empty_dictionary3)
        else:
            adjustedResponseDictionary = attributePARTIALName_ValueIntersection(denaliVariables, responseDictionary, empty_dictionary3)

        if adjustedResponseDictionary == False:
            return False

    return adjustedResponseDictionary



##############################################################################
#
# attributePartialName_ValueIntersection(denaliVariables, responseDictionary, adjustedDictionary)
#

def attributePartialName_ValueIntersection(denaliVariables, responseDictionary, adjustedDictionary):

    return responseDictionary



##############################################################################
#
# attributeNOTName_ValueIntersection(denaliVariables, responseDictionary, adjustedDictionary)
#
#   Spin through the denaliVariables['advAttribute']['sql_remove'] List
#   3 possibilities:
#       (1) Only attribute_name                                             [ TYPE I   ]
#           Find and remove hosts with a matching attribute name
#       (2) Only attribute_value                                            [ TYPE II  ]
#           Find and remove hosts with any attribute value that matches
#       (3) Both attribute_name and attribute_value                         [ TYPE III ]
#           Find and remove an attribute name and value pair that match
#

def attributeNOTName_ValueIntersection(denaliVariables, responseDictionary, adjustedDictionary):

    debug = False

    name  = 0
    value = 0
    count = 0

    #if debug == True:
    #    print "dvaa = %s" % denaliVariables['advAttribute']

    attributeName_List  = []
    attributeValue_List = []

    for item in denaliVariables['advAttribute']['sql_remove']:
        # Attribute Name
        if item[0] == "--attribute_name":
            attr_names = item[1].split(':')[1].strip()
            if attr_names.find(" OR "):
                attr_names = attr_names.split(' OR ')
                attributeName_List.extend(attr_names)
            else:
                attributeName_List.append(attr_names)

        # Attribute Value
        elif item[0] == "--attribute_value":
            attr_values = item[1].split(':')[1].strip()
            if attr_values.find(" OR "):
                attr_values = attr_values.split(' OR ')
                attributeValue_List.extend(attr_values)
            else:
                attributeValue_List.append(attr_values)

    attributeName_Set  = set(attributeName_List)
    attributeValue_Set = set(attributeValue_List)

    if debug == True:
        print "attr name  (l) = %s" % attributeName_List
        print "attr name  (s) = %s" % attributeName_Set
        print "attr value (l) = %s" % attributeValue_List
        print "attr value (s) = %s" % attributeValue_Set

    # classify the type of removal
    name  = len(attributeName_List)
    value = len(attributeValue_List)

    if name > 0 and value == 0:
        # TYPE I:  Only attribute names to check against
        adjustedDictionary = nameIntersectionCheck(denaliVariables, responseDictionary, adjustedDictionary, attributeName_Set, False)
        if adjustedDictionary == False:
            return False
    elif name == 0 and value > 0:
        # TYPE II:  Only attribute values to check against
        adjustedDictionary = valueIntersectionCheck(denaliVariables, responseDictionary, adjustedDictionary, attributeValue_Set, False)
        if adjustedDictionary == False:
            return False
    elif name > 0 and value > 0:
        # TYPE III:  Attribute names and values to check against
        if debug == True:
            print "  TYPE III Removal: Match by attribute name and value"

        if name != value:
            if name > value:
                # This code allows more attribute names to be submitted and then the output columns
                # will contain the data from these names (it's a wildcard search -- show what it has)
                # chop off the end of the name list to match the count from value
                attributeName_List = attributeName_List[:value]
                attributeName_Set  = set(attributeName_List)

            else:
                # value count is greater -- print an error to let the user know.
                # Mismatched set ... must match # of name removes and # of value removes (for now)
                # perhaps later the code will match up what it can, and then put the remaining requests
                # in one of the above two categories.
                print "Denali Syntax Error : --attribute_name=NOT:<values> and --attribute_value=NOT:<values> must come in equal pairs for a name/value search."
                print "                    : Attribute Names submitted: %i   Attribute Values submitted: %i" % (name, value)
                print "Submitted request   : %s" % denaliVariables['advAttribute']['sql_remove']
                denaliVariables['advAttribute']['error'] = True
                return adjustedDictionary

        for (index, host) in enumerate(responseDictionary['data']['results']):
            # counter for determining whether all attributes match
            attribute_match = 0

            if attributeName_Set.issubset(set(responseDictionary['data']['results'][index]['attribute_data.attribute.name'])) == True:
                # found a match on this host for attribute names
                #if debug == True:
                #    print "-" * 80
                #    print "attribute set   = %s :: %s" % (attributeName_Set, responseDictionary['data']['results'][index]['name'])
                for (a_index, attribute) in enumerate(attributeName_List):
                    list_index = responseDictionary['data']['results'][index]['attribute_data.attribute.name'].index(attribute)
                    attribute_value = responseDictionary['data']['results'][index]['attribute_data.value'][list_index]

                    # check and see if the attribute value, matches the requirement
                    # for this check, all attribute values have to be not equal, and
                    # then the host can be added
                    #if debug == True:
                    #    print "attribute value = %s" % attribute_value
                    #    print "attribute list  = %s" % attributeValue_List[a_index]
                    #    print "a list length   = %i" % len(attributeName_List)
                    if attribute_value == attributeValue_List[a_index]:
                    #    if debug == True:
                    #        print "attributes match"
                        attribute_match += 1
                    else:
                    #    if debug == True:
                    #        print "attributes don't match"
                        attribute_match -= 1
                    #if debug == True:
                    #    print
                #if debug == True:
                #    print "attribute_match = %s" % attribute_match
                if attribute_match != len(attributeName_List):
                    #if debug == True:
                    #    print "server kept"
                    adjustedDictionary['data']['results'].append(responseDictionary['data']['results'][index])
                    count += 1
                else:
                    pass
                    #if debug == True:
                    #    print "server removed"

            else:
                # attribute name/s does not exist -- add in the host
                # if all attributes (together) dont' exist, then this host will be added
                # if, for example, 1 of 5 is on the host but the other 4 are not, then this
                # code fork would not be taken.  This is a current limitation of the code;
                # it is all or nothing.
                adjustedDictionary['data']['results'].append(responseDictionary['data']['results'][index])
                count += 1

        if debug == True:
            print "    Matching hosts: %i\n" % count

        denaliVariables['attribute_count'] = count

    return adjustedDictionary



##############################################################################
#
# attributeAllName_ValueIntersection(denaliVariables, responseDictionary, adjustedDictionary)
#
#   All attribute names submitted must be present on the host.
#   All attribute values submitted must match on the host.
#

def attributeALLName_ValueIntersection(denaliVariables, responseDictionary, adjustedDictionary):

    debug = False

    if debug == True:
        print "dvaa = %s" % denaliVariables['advAttribute']

    name  = 0
    value = 0
    count = 0

    attributeName_List  = denaliVariables['advAttribute']['--attribute_name']
    attributeName_Set   = set(denaliVariables['advAttribute']['--attribute_name'])
    attributeValue_List = denaliVariables['advAttribute']['--attribute_value']
    attributeValue_Set  = set(denaliVariables['advAttribute']['--attribute_value'])

    if debug == True:
        print "attr names  (l) = %s" % attributeName_List
        print "attr names  (s) = %s" % attributeName_Set
        print "attr values (l) = %s" % attributeValue_List
        print "attr values (s) = %s" % attributeValue_Set

    # classify the type of "positive" attribute search
    name  = len(attributeName_List)
    value = len(attributeValue_List)

    if name > 0 and value == 0:
        # TYPE I: Only attribute names to check against
        adjustedDictionary = nameIntersectionCheck(denaliVariables, responseDictionary, adjustedDictionary, attributeName_Set, True)
        if adjustedDictionary == False:
            return False
    elif name == 0 and value > 0:
        # TYPE II: Only attribute values to check against
        adjustedDictionary = valueIntersectionCheck(denaliVariables, responseDictionary, adjustedDictionary, attributeValue_Set, True)
        if adjustedDictionary == False:
            return False
    elif name > 0 and value > 0:
        # TYPE III: Attribute names and values to check against
        if debug == True:
            print "  TYPE III: Match by attribute name and value"

        if name != value:
            if name > value:
                # This code allows more attribute names to be submitted and then the output columns
                # will contain the data from these names (it's a wildcard search -- show what it has)
                # Chop off the end of the name list to match the count from value
                attributeName_List = attributeName_List[:value]
                attributeName_Set  = set(attributeName_List)

            else:
                # Mismatched set ... must match # of name searches and # of value searches (for now)
                # perhaps later the code will match up what it can, and then put the remaining requests
                # in one of the above two categories.
                print "Denali Syntax Error : --attribute_name=<values> and --attribute_value==<values> must come in equal pairs for a name/value search."
                print "                    : Attribute Names submitted: %i   Attribute Values submitted: %i" % (name, value)
                print "Submitted request   : %s" % denaliVariables['advAttribute']
                denaliVariables['advAttribute']['error'] = True
                return adjustedDictionary

        # find the intersection ... of all names and all values
        # loop through all hosts matching attribute names, and then values
        for (index, host) in enumerate(responseDictionary['data']['results']):
            if attributeName_Set.issubset(set(responseDictionary['data']['results'][index]['attribute_data.attribute.name'])) == True:
                # found a match on this host for attribute names
                for (a_index, attribute) in enumerate(attributeName_List):
                    list_index = responseDictionary['data']['results'][index]['attribute_data.attribute.name'].index(attribute)
                    attribute_value = responseDictionary['data']['results'][index]['attribute_data.value'][list_index]

                    # If the attribute is an asterisk -- it means any kind of
                    # match, just move on to the next attribute for checking
                    if attributeValue_List[a_index] == '*':
                        continue

                    # check and see if the attribute value, matches the requirement
                    if attribute_value != attributeValue_List[a_index]:
                        break
                else:
                    # This host has matched for both attribute_names and values
                    # Add the host to the adjustedResponseDictionary for output/command operations
                    adjustedDictionary['data']['results'].append(responseDictionary['data']['results'][index])
                    count += 1

        if debug == True:
            print "    Matching hosts: %i\n" % count

        denaliVariables['attribute_count'] = count

    return adjustedDictionary



##############################################################################
#
# nameIntersectionCheck(denaliVariables, responseDictionary, adjustedDictionary, attributeNames, add_remove=True)
#

def nameIntersectionCheck(denaliVariables, responseDictionary, adjustedDictionary, attributeNames, add_remove=True):

    debug     = False
    count     = 0
    non_count = 0

    # TYPE I: Only attribute names to check against
    if debug == True:
        print "  TYPE I: Match by attribute name"
    for (index, host) in enumerate(responseDictionary['data']['results']):
        #if attributeNames.issubset(set(responseDictionary['data']['results'][index]['attribute_data.attribute.name'])) == add_remove:
        name_list = responseDictionary['data']['results'][index]['attribute_data.attribute.name']
        (ccode, retValue) = attributeSubsetCheck(denaliVariables, attributeNames, name_list, add_remove)
        if retValue == 'Error':
            return False
        elif ccode == add_remove and retValue == 'Success':
            # add host to adjusted dictionary
            adjustedDictionary['data']['results'].append(responseDictionary['data']['results'][index])
            count += 1
        else:
            # do not add host
            non_count += 1

    if debug == True:
        print "    Matching hosts     : %i" % count
        print "    Non-Matching hosts : %i\n" % non_count

    denaliVariables['attribute_count'] = count

    return adjustedDictionary



##############################################################################
#
# valueIntersectionCheck(denaliVariables, responseDictionary, adjustedDictionary, attributeValues, add_remove=True)
#

def valueIntersectionCheck(denaliVariables, responseDictionary, adjustedDictionary, attributeValues, add_remove=True):

    debug      = False
    count      = 0
    non_count  = 0

    # TYPE II: Only attribute values to check against
    if debug == True:
        print "  TYPE II: Match by attribute value"
    for (index, host) in enumerate(responseDictionary['data']['results']):
        #if attributeValues.issubset(set(responseDictionary['data']['results'][index]['attribute_data.value'])) == add_remove:
        value_list = responseDictionary['data']['results'][index]['attribute_data.value']
        name_list  = responseDictionary['data']['results'][index]['attribute_data.attribute.name']
        (ccode, retValue) = attributeSubsetCheck(denaliVariables, attributeValues, value_list, add_remove)
        if retValue == 'Error':
            return False
        elif ccode == add_remove and retValue == 'Success':
            # add host to adjusted dictionary
            adjustedDictionary['data']['results'].append(responseDictionary['data']['results'][index])
            count += 1

            # find the attribute names that correspond with the values found (if any)
            for item in attributeValues:
                #print "item = %s" % item
                indices = [i for (i, x) in enumerate(value_list) if x == item]
                #print "indices = %s" % indices
                for name_index in indices:
                    #print "  index = %s" % name_index
                    if 'notAttrNames' in denaliVariables['advAttribute']:
                        denaliVariables['advAttribute']['notAttrNames'].append(name_list[name_index])
                    else:
                        denaliVariables['advAttribute'].update({'notAttrNames': [name_list[name_index]]})
        else:
            # do not add host
            non_count += 1

    # if advAttribute/attribute_name is empty, and this is a REMOVE ONLY search, then add the name in
    # so the output will be nice.

    if debug == True:
        print "    Matching hosts     : %i" % count
        print "    Non-Matching hosts : %i" % non_count
        print "    Attribute Names    : %s\n" % denaliVariables['advAttribute']['notAttrNames']

    denaliVariables['attribute_count'] = count

    return adjustedDictionary



##############################################################################
#
# attributeSubsetCheck(denaliVariables, attribute_Set, data_list, add_remove=True)
#
#   TODO:
#   (1) Account for a single asterisk, or a line of asterisks only (2 or more).
#       In these cases, all names or values are included in the new_data_list.
#

def attributeSubsetCheck(denaliVariables, attribute_Set, data_list, add_remove=True):

    wildcard      = False
    new_data_list = []

    # check for and handle wildcard characters
    for item in attribute_Set:
        if '*' in item:
            wildcard = True
            if item[0] == '*':
                item = item[1:]
            if item[-1] == '*':
                item = item[:-2]
            if item.find('*') != -1:
                # found another one (or more) ... error out
                print "Denali Syntax Error : Up to 2 asterisks are allowed; one at the beginning and one at the end of an attribute name/value."
                print "Submitted request   : %s" % denaliVariables['advAttribute']
                denaliVariables['advAttribute']['error'] = True
                return (False, 'Error')

            for attribute in data_list:
                if attribute.find(item) != -1:
                    new_data_list.append(attribute)

    #print "new_data_list = %s" % new_data_list

    if wildcard == True:
        if len(new_data_list):
            return(add_remove, 'Success')
        else:
            return(add_remove, 'Failure')

    # default (non-wildcard) check
    if attribute_Set.issubset(set(data_list)) == add_remove:
        return (add_remove, 'Success')

    return (False, 'Failure')
