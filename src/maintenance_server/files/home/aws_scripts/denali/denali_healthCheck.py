

import denali_commands

from denali_tty import colors

healthCheck_to_deviceService = {

    'Analytics - Reporting - Admin App Service'         : '/usr/share/tomcat/bin/check_microservice_health.sh',
    'Analytics - Reporting - App Service'               : '/usr/share/tomcat/bin/check_microservice_health.sh',
    'Analytics - Reporting - App Service Permissions'   : '/usr/share/tomcat/bin/check_microservice_health.sh',
    'Analytics - Reporting - Platform Service'          : '/usr/share/tomcat/bin/check_microservice_health.sh',
    'Analytics - Reporting - Segment Service'           : '/usr/share/tomcat/bin/check_microservice_health.sh',

}


# type of message to be displayed (color-coded)
NORMAL  = 0     # green
WARNING = 1     # yellow
ERROR   = 2     # red

##############################################################################


##############################################################################
#
# displayOutputMarker(denaliVariables, string)
#

def displayOutputMarker(denaliVariables, string, type=NORMAL):

    string_normal_color  = colors.bold + colors.fg.lightgreen
    string_failure_color = colors.bold + colors.fg.lightred
    string_problem_color = colors.bold + colors.fg.yellow

    # If the string is led with an exclamation point, change the color being
    # displayed, and remove that character for printing
    if len(string) and type == ERROR:
        string_color = string_failure_color
    elif type == WARNING:
        string_color = string_problem_color
    else:
        string_color = string_normal_color

    if denaliVariables['nocolors'] == True:
        print " :: %s ::"% string
    else:
        print string_color + " :: " + string + " ::" + colors.reset



##############################################################################
#
# identifySingleHost(denaliVariables, serverList)
#

def identifySingleHost(denaliVariables, serverList):

    hosts_to_use      = []
    verify_host_count = int(denaliVariables['devServiceVerifyData']['verify_host_count'])

    if denaliVariables['pdshSeparate'] != False:
        # Spin through each segment and pull the first host off each
        # segment List.  So if there are 7 segments, there will be 7
        # hosts to run this health check against.

        segment_list = denaliVariables['pdshSeparateData'].keys()

        for segment in segment_list:
            if len(segment):
                if verify_host_count <= len(denaliVariables['pdshSeparateData'][segment]):
                    for host_index in range(verify_host_count):
                        hosts_to_use.append(denaliVariables['pdshSeparateData'][segment][host_index])
                else:
                    hosts_to_use.append(denaliVariables['pdshSeparateData'][segment][0])
    else:
        # default use-case (no separator code).  pull off the count number of hosts
        if verify_host_count <= len(serverList):
            for host_index in range(verify_host_count):
                hosts_to_use.append(serverList[host_index])
        else:
            hosts_to_use = serverList

    return hosts_to_use



##############################################################################
#
# removeDomainStrings(denaliVariables, hostname_list)
#

def removeDomainStrings(denaliVariables, hostname_list):

    hostname_revised_list = []

    # strings that could be in the key field that need to be removed to match
    # with the hostlist being worked with here (add more if needed)
    remove_strings = [
                        '.omniture.com',
                        #'.adobe.net'       # ut1 devices need this
                     ]

    for host in hostname_list:
        # Loop through remove_strings and remove them from the host name (key) if
        # needed this assumes only one from all of the list will be in the text.
        for string_data in remove_strings:
            if host.find(string_data) != -1:
                host = host[:-len(string_data)]
                break

        hostname_revised_list.append(host)

    return hostname_revised_list



##############################################################################
#
# retrieveDeviceService(denaliVariables, hostname_list)
#

def retrieveDeviceService(denaliVariables, hostname_list):

    verify_host_service = {}

    hostname_list = removeDomainStrings(denaliVariables, hostname_list)

    for host in hostname_list:
        verify_host_service.update({host:denaliVariables['devServiceVerifyData'][host]['service']})

    return verify_host_service



##############################################################################
#
# deviceServiceHealthCommand(denaliVariables, service_list)
#

def deviceServiceHealthCommand(denaliVariables, service_list):

    command_list = {'host_list':{},'command_list':{}}

    for host in service_list.keys():
        if service_list[host] in healthCheck_to_deviceService:
            # code loop for device services that are pre-defined
            if 'verify_command' in denaliVariables['devServiceVerifyData']:
                # if the user entered a command, use it
                healthCheck = denaliVariables['devServiceVerifyData']['verify_command']
            else:
                # if not command was entered, take the hard-coded command
                healthCheck = healthCheck_to_deviceService[service_list[host]]
        else:
            # code loop for device services not defined
            if 'verify_command' in denaliVariables['devServiceVerifyData']:
                # if the user entered a command, use it
                healthCheck = denaliVariables['devServiceVerifyData']['verify_command']
            else:
                healthCheck = ''

        if len(healthCheck):
            if healthCheck not in command_list['command_list']:
                command_list['command_list'].update({healthCheck:[host]})
            else:
                command_list['command_list'][healthCheck].append(host)

            command_list['host_list'].update({host:healthCheck})

    return command_list



##############################################################################
#
# executePDSHCommand(denaliVariables, hostname_list)
#

def executePDSHCommand(denaliVariables, hostname_list):

    pdshSeparate_tmpSave = False

    displayOutputMarker(denaliVariables, "Execute PDSH Command Against Test Host(s)")

    # set this to False now, so it doesn't loop on the health check code
    denaliVariables['devServiceVerify'] = False

    # set the autoconfirm to yes so it doesn't stop on confirmation for the health check
    denaliVariables["autoConfirm"] = True

    temp_hostlist = denaliVariables['serverList']
    denaliVariables['serverList'] = removeDomainStrings(denaliVariables, hostname_list)

    # reset the progress indicator to look correct with this limited run
    denali_commands.generateProgressNumbers(denaliVariables)

    # for the first run, disable pdsh separate ... it doesn't matter for this
    if denaliVariables['pdshSeparate'] != False:
        pdshSeparate_tmpSave = denaliVariables['pdshSeparate']
        denaliVariables['pdshSeparate'] = False

    # jump right into the code by calling launchMPQuery
    retDict = denali_commands.launchMPQuery(denaliVariables, "pdsh", [])

    # if this was disabled, turned it back on
    if pdshSeparate_tmpSave != False:
        denaliVariables['pdshSeparate'] = pdshSeparate_tmpSave

    return (retDict, temp_hostlist)



##############################################################################
#
# parseForFailures(denaliVariables, retDict)
#

def parseForFailures(denaliVariables, retDict):

    log_filename = retDict['pdsh_log_file']
    failure_list = []

    with open(log_filename, 'r') as log_file:
        data = log_file.readlines()

    for line in data:
        line        = line.strip()
        line_list   = line.split(':')
        category    = line_list[0].strip()
        device_name = line_list[1].strip()

        if category == '[FAILURE]':
            failure_list.append(device_name)

    return failure_list



##############################################################################
#
# executeHealthCheck(denaliVariables, command_list)
#

def executeHealthCheck(denaliVariables, command_list):

    final_failure_list   = []
    pdshSeparate_tmpSave = False

    print
    displayOutputMarker(denaliVariables, "Execute Health Check Against Test Host(s)")

    # reset the progress indicator to look correct with this limited run
    denali_commands.generateProgressNumbers(denaliVariables)

    # for the first run, disable pdsh separate ... it doesn't matter for this
    if denaliVariables['pdshSeparate'] != False:
        pdshSeparate_tmpSave = denaliVariables['pdshSeparate']
        denaliVariables['pdshSeparate'] = False

    # Currently the list is optimized only by the same command being run
    command_keys = command_list['command_list'].keys()
    for command in command_keys:
        host_list = command_list['command_list'][command]

        denaliVariables['serverList'] = host_list
        denaliVariables['pdshCommand'] = command

        # jump right into the code by calling launchMPQuery
        retDict = denali_commands.launchMPQuery(denaliVariables, "pdsh", [])

        failure_list = parseForFailures(denaliVariables, retDict)
        final_failure_list.extend(failure_list)

    # if this was disabled, turned it back on
    if pdshSeparate_tmpSave != False:
        denaliVariables['pdshSeparate'] = pdshSeparate_tmpSave

    if len(final_failure_list):
        return final_failure_list
    else:
        return True



##############################################################################
#
# prepareHealthCheck(denaliVariables, hostname_list, command_list)
#
#   command_list is a dictionary that contains the hostname and command to run
#   for each health check.
#

def prepareHealthCheck(denaliVariables, hostname_list, command_list):

    # prep the code for a host command run

    # save the original command
    denaliVariables.update({'pdsh_command_temp':str(denaliVariables['pdshCommand'])})

    return False



##############################################################################
#
# entryPoint(denaliVariables)
#
#   Any failure will result in the main PDSH loop not executing.  If that loop
#   needs to execute (independent of the verify switch), then do NOT use the
#   --verify switch.  Run it without, and it will work exactly as before.
#

def hc_entryPoint(denaliVariables, serverList):

    #print "original serverList = %s" % serverList

    # pick a single host from the list submitted
    hostname_list_single = identifySingleHost(denaliVariables, serverList)
    #print "+ identifySingleHost()         hostname list = %s" % hostname_list_single

    # check the hostname_list for problems
    if not len(hostname_list_single):
        # no hosts selected ... bail
        displayOutputMarker(denaliVariables, "Identified host for verification not found:  Verify Canceled", WARNING)
        return False, False

    # get the device service(s) for the host(s) identified
    service_list = retrieveDeviceService(denaliVariables, hostname_list_single)
    #print "+ retrieveDeviceService()      service_list  = %s" % service_list

    # check the server_list for problems
    key_list = service_list.keys()
    if not len(key_list):
        displayOutputMarker(denaliVariables, "Service List of hosts incorrect:  Verify Canceled", WARNING)
        return False, False

    for host in key_list:
        if not len(service_list[host]):
            displayOutputMarker(denaliVariables, "Service List of hosts incorrect:  Verify Canceled", WARNING)
            return False, False

    # retrieve command to run against the host
    command_list = deviceServiceHealthCommand(denaliVariables, service_list)
    #print "+ deviceServiceHealthCommand() command_list  = %s" % command_list

    # check the command_list for problems
    if not len(command_list['host_list']) and not len(command_list['command_list']):
        displayOutputMarker(denaliVariables, "Assigned Device Service Verify Check Not Found:  Verify Canceled", WARNING)
        return False, False

    # run the initial command against the hostname_list
    (returnDict, hostname_list) = executePDSHCommand(denaliVariables, hostname_list_single)

    # check the returnDict for problems

    # prep for the health check
    ccode = prepareHealthCheck(denaliVariables, hostname_list, command_list)

    # execute the health check
    ccode = executeHealthCheck(denaliVariables, command_list)
    if ccode != True:
        return False, False

    denaliVariables['pdshCommand']  = denaliVariables['pdsh_command_temp']

    # set the hostlist back to the original
    denaliVariables['serverList'] = serverList

    # reset the device service data
    denaliVariables['devServiceVerifyData'] = {}

    return (ccode, hostname_list_single)
