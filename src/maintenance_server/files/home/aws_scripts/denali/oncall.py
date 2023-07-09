
import denali_search
import denali_utility

from datetime import datetime

#
# Custom query -- collect on call information
#
#   There are a few use cases so far for this:
#   (1) Run this query and show every list/queue
#   (2) Run this query for a specific queue, and show the
#       individual(s) on call -- and their data.
#   (3) Run this query and show EVERYONE that is on call.
#


##############################################################################
#
# main(denaliVariables, *parameters)
#

def main(denaliVariables, *parameters):

    # This "main" function is called by default if no specific function is identified
    # with the --ext switch.  Pass everything through here for the default run type.

    ccode = onCallInfo(denaliVariables, parameters)
    return ccode



##############################################################################
#
# listQueues(denaliVariables, queueDictionary)
#

def listQueues(denaliVariables, queueDictionary):

    print "| Queue ID | Queue Name                         | Queue Description                                                     |"
    print "|==========|====================================|=======================================================================|"

    keys = queueDictionary.keys()
    keys.sort()

    for queue in keys:
        if len(queueDictionary[queue]) != 0:
            queueID          = queueDictionary[queue][0].strip()
            queueDescription = queueDictionary[queue][1].strip()
        else:
            queueID = queueDescription = ''
        queueName  = queue.strip()

        queueName = queueName.encode('ascii', 'ignore')
        queueDescription = queueDescription.encode('ascii', 'ignore')
        print "  %-4s       %-35s  %s" % (queueID, queueName, queueDescription)

    return True



##############################################################################
#
# collectQueueIDs(denaliVariables)
#

def collectQueueIDs(denaliVariables):

    #--dao=OnCallQueueDao --fields=name,queue_id,alt_user_id,enable_rotation,queue_type --full_name="SC*"

    callQueues      = []
    queueNameDict   = {}
    queueIDDict     = {}
    #full_name       = ''

    # Query #1: collect a list of all queue names
    denaliVariables["searchCategory"] = "OnCallQueueDao"
    denaliVariables["method"]         = "getCurrentOnCallInfo"
    respDictionary = denali_search.executeWebAPIQuery(denaliVariables, callQueues)

    if respDictionary == False:
        print "There was a problem with the query -- no results were returned."
        if denaliVariables["debug"] == True:
            api = denaliVariables["api"]
            print "\nERROR:"
            print "   STATUS  : " + api.get_response_status()
            print "   TYPE    : " + str(api.get_error_type())
            print "   MESSAGE : " + api.get_error_message()
        denali_search.cleanUp(denaliVariables)
        exit(1)

    key = respDictionary.keys()

    for (count, queue) in enumerate(respDictionary[key[0]]):
        callQueues.append(queue["full_name"])

    # Query #2: using query #1 data, get the queue IDs for each queue
    denaliVariables["fields"]       = "name,queue_id,description"
    denaliVariables["method"]       = "search"
    denaliVariables["serverList"]   = callQueues
    denaliVariables["textTruncate"] = False
    denaliVariables["textWrap"]     = False

    (sqlQuery, wildcard) = denali_search.buildGenericQuery(denaliVariables)
    sqlQuery = denaliVariables["searchCategory"] + ':' + sqlQuery
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

    for row in printData:       # key = name : [queue_id, description]
        # check for duplicates -- add an '*' at the end of the second one
        # so it can be added to the dictionary without replacing the original
        # entry
        if row[0].strip() in queueNameDict:
            row[0] = str(row[0].strip()) + '*'
        queueNameDict.update({row[0].strip():[row[1].strip(),row[2].strip()]})
    for row in printData:       # key = ID   : [queue_name, description]
        # check for duplicates --
        if row[1].strip() in queueIDDict:
            row[1] = str(row[1].strip()) + '*'
        queueIDDict.update({row[1].strip():[row[0].strip(),row[2].strip()]})

    return (queueNameDict, queueIDDict)



##############################################################################
#
# onCallInfo(denaliVariables, *parameters)
#

#
# Useful queries for this function (which Denali can currently answer successfully):
#   (1)
#   denali --dao=OnCallDao --fields=on_call_queue_id,queue_name,user_id --on_call_queue_id="63 OR 29"
#
#   This query requires the queue id number (63 or 29 in this case), and returns with the queue name,
#   and the user ID of the individual that is currently on call.
#
#   (2)
#   --dao=OnCallQueueDao --fields=name,queue_id,alt_user_id,enable_rotation,queue_type --full_name="SC*"
#
#   This query shows information about all on call queues that start with "SC".  Name, queue id, etc.
#   It also has an alternate user id (backup for on call?)
#   Using "--full_name="*" shows a list of all on call queues.
#
#   (3)
#   --dao=UserDao --fields=full_name,user_id,email,desk,phone,phone_ext,alternate_phone,alternate_phone_2,mobile --user_id="163 OR 671"
#
#   This query returns information about individual users (phone numbers are the important data items here).
#
#   (4)
#   --dao=OnCallQueueToUserDao --fields=user_id,on_call_queue_id,user.full_name --on_call_queue_id="79"
#
#   This query returns every user associated with a specific queue.
#

def onCallInfo(denaliVariables, parameters):

    listView    = True
    callQueues  = []

    # Check and see if the forwarding check is true
    # If so, it means that the user would like to use the submitted
    # queue to determine who is going to be on call given a specific
    # date.
    if denaliVariables['checkForwardingOnCall'] == True:
        date = parameters[1] if 2 <= len(parameters) else datetime.now().strftime("%Y-%m-%d")
        forwardOnCall = forwardScheduleOnCall(denaliVariables, parameters[0], date)
        curOnCall = currentOnCall(denaliVariables, parameters[0])
        if forwardOnCall != curOnCall:
            print "Needs to be on-call: %s" % forwardOnCall
        else:
            print "Is already on-call: %s" % curOnCall

        # exit out with a '0' (success)
        exit(0)

    (queueNameDict, queueIDDict) = collectQueueIDs(denaliVariables)
    # queueNameDict = { queueName : [queue_id, description] }
    # queueIDDict   = { queueID   : [queue_name, description] }

    if len(parameters) > 0:
        for parm in parameters:
            if (parm.lower()).startswith("list") == True:
                ccode = listQueues(denaliVariables, queueNameDict)
                return ccode
            elif (parm.lower()).startswith("table") == True:
                listView = False
            else:
                if parm.isdigit():
                    # if the input parameter is a number, assume it is the "queue id"
                    # translate it from ID to Queue name
                    if parm in queueIDDict:
                        callQueues.append(queueIDDict[parm][0])
                    else:
                        print "Denali - invalid Queue ID specified:"
                        print "  The specified queue ID (%s) wasn't found." % parm
                        denali_search.cleanUp(denaliVariables)
                        exit(1)
                elif '*' in parm:
                    parm = parm.replace('*', '')
                    for queue in queueNameDict:
                        if parm in queue.strip():
                            callQueues.append(queue)

                    if len(callQueues) == 0:
                        print "No OnCall Queues match the specified search criteria."
                        return False
                else:
                    for queueName in queueNameDict:
                        queueName = queueName.lower()
                        parm_lower = parm.lower()
                        if parm_lower == queueName:
                            callQueues.append(parm)
                            break
                    else:
                        print "Denali - invalid Queue Name specified:"
                        print "  The specified queue name (%s) wasn't found." % parm
                        denali_search.cleanUp(denaliVariables)
                        exit(1)

    # define the variables for the initial query of the blade chassis
    denaliVariables["searchCategory"] = "OnCallQueueDao"
    denaliVariables["method"]         = "getCurrentOnCallInfo"

    # this call short-circuits much of what Denali was built to do
    # however, with this method it will all be customized anyway, so ...
    respDictionary = denali_search.executeWebAPIQuery(denaliVariables, callQueues)

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

    if listView == True:
        key = respDictionary.keys()

        for (count, queue) in enumerate(respDictionary[key[0]]):
            try:
                queue_id = queueNameDict[queue["full_name"].strip()][0]
            except KeyError:
                queue_id = queue["on_call_queue_id"].strip()
            queue_name_data = queue["full_name"].strip().encode('ascii', 'ignore')
            print "\n(%3s) Queue Name: %s  (%s)" % (queue_id, queue_name_data, queue["description"].strip())
            if "on_call_user_info" in queue:
                print "  On Call Engineer         : %s" % queue["on_call_user_info"]["full_name"].strip()
                print "  Email                    : %s" % queue["on_call_user_info"]["email"].strip()

                countOfPhones = len(queue["on_call_user_info"]["phone_array"])
                phoneArray    = queue["on_call_user_info"]["phone_array"]

                for phone in range(countOfPhones):
                    phoneType   = phoneArray[phone]["phone_type"].strip()
                    phoneNumber = phoneArray[phone]["phone_number"].strip()
                    print "  %-23s  : %s" % (phoneType, phoneNumber)
    else:
        # create a dictionary to reference and build the table from
        # onCallDict = { queue_name: [queue_id, on_call_engineer_name] }
        onCallDict = {}
        userList   = []
        key = respDictionary.keys()

        # Check to see if specific on call queues were requested.
        # If this is empty, it means _all_ of them were requested.
        if len(callQueues) == 0:
            for queue in respDictionary[key[0]]:
                callQueues.append(queue["full_name"].strip())

        for queue in callQueues:
            for (count, queue) in enumerate(respDictionary[key[0]]):
                if "on_call_user_info" in queue:
                    queueName        = queue["full_name"].strip()
                    try:
                        queueID      = queueNameDict[queueName][0].strip()
                    except KeyError:
                        queueID      = queue["on_call_queue_id"].strip()
                    userName         = queue["on_call_user_info"]["full_name"].strip()
                    queueDescription = queue["description"].strip()
                    onCallDict.update({queueName:[queueID, userName, queueDescription]})
                else:
                    queueName = queue["full_name"].strip()
                    queueID   = queueNameDict[queueName][0].strip()
                    queueDescription = queue["description"].strip()
                    onCallDict.update({queueName:[queueID, '', queueDescription]})

        # add the not on-call users to the queue list
        # --dao=OnCallQueueToUserDao --fields=user_id,on_call_queue_id,user.full_name --on_call_queue_id="79"
        onCallQueues = onCallDict.keys()
        for (counter, queue) in enumerate(onCallQueues):
            userOnCall = onCallDict[queue][1]

            denaliVariables["fields"]         = "user_id,on_call_queue_id,user.full_name,user_type"
            denaliVariables["searchCategory"] = "OnCallQueueToUserDao"
            denaliVariables["method"]         = "search"
            denaliVariables["serverList"]     = [onCallDict[queue][0]]
            #denaliVariables["sqlParameters"]  = " AND user_type = '1'"      # managers not included 1=engineer, 2=owner
            denaliVariables["sqlParameters"]  = ''
            denaliVariables["textTruncate"]   = False
            denaliVariables["textWrap"]       = False

            (sqlQuery, wildcard) = denali_search.buildGenericQuery(denaliVariables, whereQuery="on_call_queue_id")
            sqlQuery = denaliVariables["searchCategory"] + ':' + sqlQuery
            # remove the "PAGE" directive at the end of the query -- allow it to gather as many names as possible.
            sqlQuery = sqlQuery[:(sqlQuery.find("PAGE"))]
            respDictionary = denali_search.constructSQLQuery(denaliVariables, sqlQuery, False)

            if respDictionary == False:
                print "1"
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
            (managers, printData) = getManagers(printData)

            if denaliVariables["showHeaders"] == True:
                if onCallDict[queue][0] not in queueIDDict:
                    continue

                print
                print "On Call Queue :  %s" % queueIDDict[onCallDict[queue][0]][0]
                print "Description   :  %s" % onCallDict[queue][2]
                print "Manager(s)    : ",
                for (index, manager) in enumerate(managers):
                    if index > 0:
                        print "/ %s" % manager,
                    else:
                        print "%s" % manager,
                print
                print "CMDB URL      :  https://skms.adobe.com/tools.oct.on_call_queue/view/?on_call_queue_id=%s" % onCallDict[queue][0]
                print

            # create a list of users, ordered according to the on call queues requested
            userList = []
            for row in printData:
                userList.append(row[2])

            if len(userList) == 0:
                # there are no users assigned to this?
                print "No users were found assigned to this On-Call Queue"
                continue

            denaliVariables["fields"]         = "full_name,email,mobile,phone,phone_ext,alternate_phone,alternate_phone_2,desk"
            denaliVariables["searchCategory"] = "UserDao"
            denaliVariables["method"]         = "search"
            denaliVariables["serverList"]     = userList
            denaliVariables["sqlParameters"]  = " AND active = '1'"     # only pull "active" users or "active" user IDs
            denaliVariables["textTruncate"]   = False
            denaliVariables["textWrap"]       = False

            (sqlQuery, wildcard) = denali_search.buildGenericQuery(denaliVariables, whereQuery="full_name")
            sqlQuery = denaliVariables["searchCategory"] + ':' + sqlQuery
            respDictionary = denali_search.constructSQLQuery(denaliVariables, sqlQuery, False)

            if respDictionary == False:
                print "There was a problem with the Queue query -- no results were returned."

                # display return error message from web api
                if denaliVariables["debug"] == True:
                    api = denaliVariables["api"]
                    print "\nERROR:"
                    print "   STATUS  : " + api.get_response_status()
                    print "   TYPE    : " + str(api.get_error_type())
                    print "   MESSAGE : " + api.get_error_message()

                #denali_search.cleanUp(denaliVariables)
                #exit(1)
            else:
                (printData, overflowData) = denali_search.generateOutputData(respDictionary, denaliVariables)

                denaliVariables["addColumnData"] = {userOnCall:"YES"}
                insertColumnNumber = 1
                newColumnData = ["on_call", "on_call", "On-Call", 9]
                printData = denali_utility.keyColumnInsert(printData, denaliVariables, insertColumnNumber, newColumnData, cKey="default")
                if len(printData) < 50:
                    denali_search.prettyPrintData(printData, overflowData, respDictionary, denaliVariables)
                else:
                    print "There's a problem with the data in queue %s (%s)" % (queueIDDict[onCallDict[queue][0]][0], onCallDict[queue][0])
                    print "Tabular data not printed."

    return True



##############################################################################
#
# getManagers(printData)
#

def getManagers(printData):

    managers = []

    for (index, row) in enumerate(printData):
        if row[3].strip() == "2":
            managers.append(row[2].strip())
            printData.pop(index)

    return (managers, printData)


##############################################################################
#
# Get current on-call
# currentOnCall(denaliVariables, queue_name)
#

def currentOnCall(denaliVariables, queue_name):
    denaliVariables["fields"]         = "start_datetime,end_datetime,user.adobe_username"
    denaliVariables["searchCategory"] = "OnCallDao"
    denaliVariables["method"]         = "search"
    denaliVariables["sqlParameters"]  = " AND end_datetime = '%s'" % "0000-00-00 00:00:00"
    denaliVariables["textTruncate"]   = False
    denaliVariables["textWrap"]       = False
    denaliVariables["serverList"]     = ["%s*" % queue_name]

    (sqlQuery, wildcard) = denali_search.buildGenericQuery(denaliVariables, whereQuery="on_call_queue.name")
    sqlQuery = denaliVariables["searchCategory"] + ':' + sqlQuery
    # remove the "PAGE" directive at the end of the query -- allow it to gather as many names as possible.
    # sqlQuery = sqlQuery[:(sqlQuery.find("PAGE"))]

    respDictionary = denali_search.constructSQLQuery(denaliVariables, sqlQuery, False)
    results = respDictionary["data"]["results"]
    if len(results) != 1:
        return None
    else:
        return results[0]["user.adobe_username"]

##############################################################################
#
# Get on-call for a given date, according to the forward schedule
# forwardScheduleOnCall(denaliVariables, queue_name, date)
#

def forwardScheduleOnCall(denaliVariables, queue_name, date):
    parsedDate = datetime.strptime(date, '%Y-%m-%d')
    denaliVariables["fields"]         = "on_call_queue_schedule.start_date,on_call_queue_schedule.end_date,on_call_queue_schedule.user.adobe_username"
    denaliVariables["searchCategory"] = "OnCallQueueDao"
    denaliVariables["method"]         = "search"
    # denaliVariables["sqlParameters"]  = " AND full_name LIKE '%s'" % queue_name
    denaliVariables["textTruncate"]   = False
    denaliVariables["textWrap"]       = False
    denaliVariables["serverList"]     = ["%s*" % queue_name]

    (sqlQuery, wildcard) = denali_search.buildGenericQuery(denaliVariables, whereQuery="full_name")
    sqlQuery = denaliVariables["searchCategory"] + ':' + sqlQuery
    # remove the "PAGE" directive at the end of the query -- allow it to gather as many names as possible.
    # sqlQuery = sqlQuery[:(sqlQuery.find("PAGE"))]

    respDictionary = denali_search.constructSQLQuery(denaliVariables, sqlQuery, False)

    schedule = respDictionary["data"]["results"][0]["on_call_queue_schedule"]

    sorted_schedule = sorted(schedule, key=lambda k: k['start_date']) 

    username = None
    # check date is equal to start date or is in between start and end dates
    for s in sorted_schedule:
        startDate = datetime.strptime(s["start_date"], '%Y-%m-%d')
        endDate = datetime.strptime(s["end_date"], '%Y-%m-%d')
        if parsedDate == startDate or (parsedDate > startDate and parsedDate < endDate):
            username = s["user"]["adobe_username"]
            break;

    # if we still don't have a user check end date
    if username == None:
        for s in sorted_schedule:
            endDate = datetime.strptime(s["end_date"], '%Y-%m-%d')
            if parsedDate == endDate:
                username = s["user"]["adobe_username"]
                break;

    return username





