#! /usr/bin/env python

import os
import sys
import time
import glob
import datetime
import getpass
import math
import socket
import subprocess
import denali_healthCheck
import denali_history
import denali_monitoring
import denali_search
import denali_types
import denali_utility

from multiprocessing import Process, Queue, Lock, Pipe, Value, Manager

# for handling different types of socket errors
import errno
from socket import error as socket_error

from denali_tty import colors

##############################################################################


# variable (for this module only) that controls the width between columns
columnSeparatorWidth    = 7

# variable (for this module only) that controls how wide (by default) each column is
defaultColumnWidth      = 20

# command service column widths
defaultPingWidth        = 21
defaultSpotsWidth       = 40
defaultNMAPWidth        = 56

# default spots separator width
spotsDefaultWidth       = 9
loadSeparatorWidth      = 9
memorySeparatorWidth    = 11
swapSeparatorWidth      = 9

# default socket timeout (in seconds)
SOCKET_TIMEOUT          = 2

# maximum host length
max_host_length         = 0

# print column headers
print_column_headers    = True

# process pool of threads for command execution
MAX_PROCESS_COUNT       = 150
MAX_PROCESS_COUNT_ORIG  = 150
MAX_SSH_PROCESS_COUNT   = 10

# screen directives
pdsh_screen             = "screen bash -c "
pdsh_screen_dm          = "screen -dm bash -c "

# pdsh directory for log file storage
pdsh_log_directory      = "/pdsh_logs"
ssh_log_directory       = "/ssh_logs"

# ssh time_string
ssh_time_string         = ''

# command debug
command_debug           = False

# argument flags
argument_flag_ilo       = False
argument_flag_port      = False

# Maximum PDSH argument length (in characters)
BATCH_SIZE              = 130000

# Natural Sort order
use_natural_sort        = False

# Maximum Host Count with pdsh to always show dshbak output.  If the number
# of devices is greater than this, then the below percentage is used.
DSHBAK_OUTPUT_COUNT     = 50

# Maximum DSHBAK entries (for aggregate host collection) to automatically show
# when dshbak output runs at the end of the pdsh command execution.
DSHBAK_OUTPUT_ENTRIES   = 5

# How many (percentage-wise) different results are allowed from pdsh output
# to automatically be shown with dshbak
RETURN_PERCENTAGE       = 80.0

# Default process timeout for pdsh (10 minutes); on a per connection basis
PDSH_PROCESS_TIMEOUT = 600
#PDSH_CONNECT_TIMEOUT = 30

# Progress indicator display options
PROGRESS_DEFAULT        = 0     # percentage indicator and devices remaining displayed
PROGRESS_ADVANCED       = 1     # percentage plus others stats at the far-left of the log line
PROGRESS_BAR            = 2     # progress bar only with percentage/percentage-plus stats
PROGRESS_TEST           = 3     # allow testing without messing up currently defined orders
PROGRESS_DISABLED       = 4     # no progress information shown

# Relative size of the progress _bars_ for SCP functions as compared to the
# size of the bar with PDSH functions
SCP_BAR_MULTIPLIER      = 0.5

# Percentage justifier and rounding value
PERCENT_ROUND_DECIMALS  = 1
PERCENT_JUSTIFICATION   = 5 + PERCENT_ROUND_DECIMALS

# SCP Push/Pull Identifier
SCP_DEVICE_ID_STRING    = "@"

# SSH Default Options
SSH_DEFAULT_OPTIONS     = [
                            '-o StrictHostKeyChecking=no',
                            #'-o PreferredAuthentications=publickey',
                            '-o ConnectTimeout=10',
                          ]

# Pause time between retry attempts (in seconds)
RETRY_PAUSE_TIME        = 10

# Whether or not to show the 'summary' page on retries
RETRY_SHOW_SUMMARY      = False

# SCP Multi-File options for pdsh execution
SCP_PDSH_COMMAND        = "ls -l"
SCP_PDSH_OPTIONS        = "-f 150 -u 60"

# PDSH Environment Variables
# potential help for error 255: -o UserKnownHostsFile=/dev/null
PDSH_ENVIRONMENT        = {
                            'PDSH_RCMD_TYPE'       : 'ssh',
                            'PDSH_SSH_ARGS_APPEND' : '-q -o StrictHostKeyChecking=no -o PreferredAuthentications=publickey'
                          }

# hosts that were automatically removed because of problematic names
removedHostList          = []


##############################################################################
#
# determineMaximumProcessesCount(denaliVariables)
#

def determineMaximumProcessesCount(denaliVariables):

    global MAX_PROCESS_COUNT

    # order of setting:
    # (1) nofork   -- set to 1 (serial execution)
    # (2) user set -- set to whatever requested
    # (3) default  -- set to maximum defined value

    if denaliVariables["nofork"] == True:
        MAX_PROCESS_COUNT     = 1
        MAX_SSH_PROCESS_COUNT = 1
    elif denaliVariables["num_procs"] != -1:
        MAX_PROCESS_COUNT     = denaliVariables["num_procs"]
        MAX_SSH_PROCESS_COUNT = denaliVariables["num_procs"]
    else:
        MAX_PROCESS_COUNT = denaliVariables["maxProcesses"]



##############################################################################
#
# determineMaximumPDSHSeparatorProcesses(denaliVariables, segmentQueue, responseDictionary)
#

def determineMaximumPDSHSeparatorProcesses(denaliVariables, segmentQueue, responseDictionary):

    global MAX_PROCESS_COUNT

    separated_devices = denali_utility.separateDevicesByType(denaliVariables, denaliVariables['serverList'], responseDictionary)
    if separated_devices == False:
        return False
    #print "separated_devices = %s" % separated_devices

    # store the separated device list in denaliVariables
    denaliVariables['pdshSeparateData'] = separated_devices

    # Calculate the hosts/segments, etc. -- allows for the correct
    # MAX_PROCESS_COUNT to be implemented
    (pdsh_hosts, segmentQueue, separated_devices) = countSeparatorSegments(denaliVariables, segmentQueue, separated_devices)

    #print "MAX_PROCESS_COUNT (current)  = %s" % MAX_PROCESS_COUNT
    #if denaliVariables['hostCommands']['active'] == False:
    #    print "MAX_PROCESS_COUNT (proposed) = %s %s" % (len(separated_devices), separated_devices)
    #else:
    #    print "MAX_PROCESS_COUNT (proposed) = %s" % len(separated_devices)

    # Don't let this get out of hand -- only allow up to the ?maximum? in
    # concurrent version of pdsh running
    #
    # Is 150 instances of pdsh running in parallel ok?  I guess it would be as each will
    # only be allowed a single process (-f 1) to operate at a time.
    if len(separated_devices) > MAX_PROCESS_COUNT_ORIG:
        MAX_PROCESS_COUNT = MAX_PROCESS_COUNT_ORIG
    else:
        MAX_PROCESS_COUNT = len(separated_devices)

    # Calculate maximum processes per pdsh segment:
    #
    # This is to try and help the user from overwhelming the pdsh origin host
    # with a gargantuan number of processes it cannot handle (and cause it to
    # go _really_ slow while processing work and probably affect other work as
    # well).  If a host can handle it, then the user should manually set
    # "-f <number_desired>"; this setting will override this default here.
    #
    #   --pdsh_options="-f <num>"
    #   --po="-f <num>"
    #   --num_procs=<num>
    #
    # Any of the above three will work (they all do essentially the same thing)
    if denaliVariables['hostCommands']['active'] == True:
        # For this type of PDSH execution, no setting should be used as only
        # one host per PDSH process will be running.
        denaliVariables['pdshSeparate']['maximum_processes_per_segment'] = -1
    elif (len(separated_devices) * 32) > MAX_PROCESS_COUNT_ORIG:
        if len(separated_devices) > MAX_PROCESS_COUNT_ORIG:
            denaliVariables['pdshSeparate']['maximum_processes_per_segment'] = 1
        else:
            denaliVariables['pdshSeparate']['maximum_processes_per_segment'] = MAX_PROCESS_COUNT_ORIG / len(separated_devices)
    else:
        # -1 means no setting was used here
        denaliVariables['pdshSeparate']['maximum_processes_per_segment'] = -1



##############################################################################
#
# handleLimitSubmission(denaliVariables, responseDictionary)
#

def handleLimitSubmission(denaliVariables, responseDictionary):

    # see if a limit was given on the hosts

    # turn off all wrapping (overflow data is useless here)
    saveTrunc   = denaliVariables["textTruncate"]
    saveWrap    = denaliVariables["textWrap"]

    denaliVariables["textWrap"]     = False
    denaliVariables["textTruncate"] = False

    # massage the data so the limit segregator function can limit it
    (printData, overflowData) = denali_search.generateOutputData(responseDictionary, denaliVariables)
    (printData, overflowData) = denali_search.limitSegregation(denaliVariables, printData, overflowData)

    # restore the text wrapping state
    denaliVariables["textWrap"]     = saveWrap
    denaliVariables["textTruncate"] = saveTrunc

    # put the new list of devices in the serverList data variable
    ccode = denali_utility.pullOutHostsFromPrintData(denaliVariables, printData)
    if ccode == False:
        return False

    # create a new responseDictionary (printData -> responseDictionary conversion)
    ccode = denali_utility.covertPrintDataToResponseDictionary(denaliVariables, printData)
    if ccode == False:
        return False

    # ccode contains the response dictionary -- return it
    return ccode



##############################################################################
#
# expandCIDRAddressSubmission(denaliVariables)
#
#   This function takes the existing (submitted) server list, and checks it to
#   determine if there are any ip addresses in it that have a CIDR notation.
#   If that is found, that CIDR address is expanded to it's full set of addresses
#   and used as the submissions.
#
#   Example:
#       denali -h 10.0.0.0/28 -c ping
#
#   This will instruct denali to expand that address to 10.0.0.0 - 10.0.0.15, and
#   use all of those with the ping command.
#

def expandCIDRAddressSubmission(denaliVariables):

    ipHostList    = []
    modServerList = []

    for host in denaliVariables['serverList']:
        if host.count('.') == 3:
            host   = host.split('.')
            value1 = host[0]
            value2 = host[1]
            value3 = host[2]
            value4 = host[3]
            # see if this is a CIDR address
            if value4.find('/') != -1 and value4.split('/')[1].isdigit() == True:
                # cidr address found ... expand it
                cidr_data = denali_utility.cidrAddressData(denaliVariables, '.'.join(host))
                if cidr_data == "False":
                    # error condition triggered -- ignore the error, and print what can
                    # be successfully processed
                    pass
                else:
                    ipHostList.extend(cidr_data['address_list'])
            elif value1.isdigit() and value2.isdigit() and value3.isdigit():
                ipHostList.append('.'.join(host))
            else:
                # has 3 periods, but not an ip address host
                modServerList.append('.'.join(host))
        else:
            # host is not an ip address host
            modServerList.append(host)

    if denaliVariables["nofork"] != True or denaliVariables["num_procs"] != 1:
        modServerList = list(set(modServerList))

    # combine modServerList and ipHostList to make a full serverList
    denaliVariables['serverList'] = modServerList + ipHostList



##############################################################################
#
# pruneHostList(denaliVariables)
#
#   Hosts with a colon (:) in their name are not in service yet ... most likely
#   their state is racked.  When a host with a colon is included in a command
#   list, all hosts error out and cannot connect (whether they have a colon
#   in their name or not).  To prevent this, all hosts with a colon in the name
#   are automatically removed.
#
#   Two lists provided here:
#   (1) prunedHostList  :   list of hosts that will be processed
#   (2) removedHostList :   list of hosts that will not be processed
#

def pruneHostList(denaliVariables):

    global removedHostList
    prunedHostList = []

    for host in denaliVariables['serverList']:
        if host.find(':') == -1:
            prunedHostList.append(host)
        else:
            removedHostList.append(host)

    return prunedHostList



##############################################################################
#
# processArguments(denaliVariables, argument, responseDictionary)
#

def processArguments(denaliVariables, argument, responseDictionary):

    # The default method is to call the commandFunction with denaliVariables
    # as a single passed in argument.
    #
    # If more logic is wanted on this, identify the argument, and then call
    # the dispatcher with the required argument list.  Of course, the function
    # will have to be written to accept and process any/all arguments passed
    # in to it.
    #

    global max_host_length
    global MAX_PROCESS_COUNT
    global use_natural_sort

    oStream = denaliVariables['stream']['output']

    #print "         1         2         3         4         5         6         7         8         9         10        11        12        13        14"
    #print "123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901"
    #print "\nresponseDictionary = %s\n" % responseDictionary

    # Make sure there is a serverList here, or there's no reason to continue
    if len(denaliVariables['serverList']) == 0:
        print "Denali Error:  Empty server list, cannot continue."
        return False

    # The device list will come in with "denali_host_list" on the end
    # check for and remove this entry if it exists
    if denaliVariables['serverList'][-1] == "denali_host_list":
        denaliVariables['serverList'].remove('denali_host_list')

    # If any cidr addresses were submitted, find and expand them
    # This allows cidr addressing to be used to do a vlan ping or
    # a command check of a vlan, etc.
    expandCIDRAddressSubmission(denaliVariables)

    # Ensure that the hostlist submitted is comprised on unique devices
    if denaliVariables["nofork"] != True or denaliVariables["num_procs"] != 1:
        denaliVariables['serverList'] = list(set(denaliVariables['serverList']))
        denaliVariables['serverList'].sort()

    # if the user requested a limit (segmented) response (e.g., 5 from each device service)
    if 'definition' in denaliVariables["limitData"]:
        responseDictionary = handleLimitSubmission(denaliVariables, responseDictionary)
        if responseDictionary == False:
            return False

    # get the maximum host length
    max_host_length = getLongestHostname(denaliVariables["serverList"])

    # remove any host/device name with a colon in it
    denaliVariables['serverList'] = pruneHostList(denaliVariables)

    # determine the maximum processes to use
    #determineMaximumProcessesCount(denaliVariables)

    # for pdsh separator work-flows -- to get the segment count correct
    segmentQueue = Queue()

    # take care of some house-keeping: delete old log files
    ccode = deleteOldLogFiles(denaliVariables)

    # Loop for the number of commands entered -- comma separated behind '-c'
    # Commands are executed in the order they are entered:
    #   Example:
    #       -c ping,spots:memory,scp,pdsh
    #   For this example, ping comes first, followed by spots (showing only memory data),
    #   then scp, and finally pdsh.
    argument_list = argument.split(',')

    ccode = checkForDuplicates(argument_list)
    if ccode == True:
        oStream.write("\nDuplicate function names submitted -- only one allowed of each type.\n")
        oStream.write("Function list: %s\n" % argument_list)
        oStream.write("Execution of Denali will stop.\n\n")
        oStream.flush()
        return False

    argument_list = pdsh_ssh_optionAdd(denaliVariables, argument_list)

    # set any applicable argument flags to handle command variations
    #   example: ping ilo addresses  -c ping ilo
    argument_list = setArgumentFlags(denaliVariables, argument_list)

    if ('sort' in argument_list or 'sortd' in argument_list) and len(argument_list) > 1:
        use_natural_sort = True

    # generate the progress numbers for pdsh to use when it shows output
    generateProgressNumbers(denaliVariables)

    # scp-pull multi-file helper
    if 'scp-pull' in argument_list:
        argument_list = reviseArgumentList(denaliVariables, argument_list)

    for argument in argument_list:
        argument = argument.split(':')
        function = argument[0].strip()

        if denaliVariables["debug"] == True:
            print "Command argument to process : %s" % argument

        if len(argument) > 1:
            argument.pop(0)
            parameters = argument
        else:
            parameters = []

        # check and see if the submitted command (key) exists in the commandDictionary
        if function in commandFunctionCollect:
            denaliVariables['commandFunction'] = function
            ccode = preProcessHandling(denaliVariables, function, len(argument_list))
            if ccode == "slack":
                # denali command processing called incorrectly (via slack)
                print
                print "The command entered (\"%s\") is not supported when called via Slack." % argument
                print "Execution of Denali will stop."
                print
                return False
            elif ccode == False:
                # preProcessing failed (message handled in local function)
                return False

            # Retry functionality for specific command function types
            # Currently this does an immediate retry of failed devices
            # from the previous run.
            if function not in denaliVariables['retryFunctions']:
                retry_count = 0
            else:
                retry_count = denaliVariables['commandRetry']

            for retry in range(0, retry_count + 1):
                # save the current number of the retry loop
                denaliVariables['commandRetryCount'] = retry

                # This allows a delta time calculation across retry loops for pdsh
                if denaliVariables['retryStartTime']['start_time'] == 0:
                    denaliVariables['retryStartTime']['start_time'] = time.time()

                if retry > 0:
                    (failure_devices, success_devices, normal_devices, dual_devices) = readStateLogFile(denaliVariables, denaliVariables['serverList'], retry)
                    if len(failure_devices) == 0:
                        break

                    # rename the current state log files (file+retry_count_number)
                    ccode = renameExistingStateLogFile(denaliVariables, retry)

                    # assign the failed list of devices back to denaliVariables for reprocessing
                    denaliVariables['serverList'] = failure_devices

                    # (re)generate the progress numbers for pdsh to use when it shows output
                    generateProgressNumbers(denaliVariables)

                    # pause for the configured timeout before proceeding again
                    retryTimeoutPause(denaliVariables, retry)

                if function == "pdsh":
                    # pdsh is a special case -- it is already parallelized, so do not allow the launchMPQuery
                    # function to spin up multiple threads.  All it needs is a single one and from there it
                    # will take care of the rest creating processes on its own.
                    MAX_PROCESS_COUNT = 1
                    denaliVariables['pdshExecuting'] = True

                    if denaliVariables['pdshSeparate'] != False:
                        ccode = determineMaximumPDSHSeparatorProcesses(denaliVariables, segmentQueue, responseDictionary)
                        if ccode == False:
                            return "Failed"

                        # for log output, disable the progress code (for now)
                        denaliVariables['commandProgress']    = False
                        denaliVariables['commandProgressBar'] = 4

                    if denaliVariables['devServiceVerify'] == True:
                        for verify_host in responseDictionary['data']['results']:
                            v_hostname = verify_host['name']
                            v_service  = verify_host.get('device_service.full_name', '')
                            v_state    = verify_host.get('device_state.full_name', '')
                            v_env      = verify_host.get('environment.full_name', '')
                            denaliVariables['devServiceVerifyData'].update({v_hostname:{'state'  :v_state,
                                                                                        'service':v_service,
                                                                                        'env'    :v_env}})
                elif function == "info":
                    # info was not designed to be parallelized, only run in serial
                    MAX_PROCESS_COUNT = 1
                else:
                    denaliVariables['pdshExecuting'] = False
                    determineMaximumProcessesCount(denaliVariables)

                if function == "sort" or function == "sortd":
                    # this is a quasi-command -- no parallelization necessary
                    retDict = performSortOperation(denaliVariables, function)
                else:
                    #
                    # launch the MP query portion of code
                    #
                    retDict = launchMPQuery(denaliVariables, function, parameters)

                if function == "pdsh":
                    # restore the environment (if it was changed) to what it was prior to the run
                    restorePDSHEnvironment(denaliVariables)

                    # make sure the return dictionary has data -- if not, bail out.
                    if len(retDict) == 0:
                        return "Failed"

                    if denaliVariables['pdshSeparate'] != False:
                        # clear it out -- about to shove multiple log locations in it
                        denaliVariables['pdsh_log_file'] = []
                        for (index, group_set) in enumerate(retDict):
                            if 'pdsh_log_file' in group_set[1]:
                                denaliVariables['pdsh_log_file'].append(group_set[1]['pdsh_log_file'])

                    else:
                        denaliVariables['pdsh_log_file'] = retDict.pop('pdsh_log_file', None)

                elif function.startswith('scp') or function == 'ssh':
                    if retDict == "Failed":
                        return "Failed"
        else:
            print
            if len(argument) > 0 and argument[0] == 'Waiting':
                oStream.write("Denali Syntax Error:  The '-c' command does not have a proper command directive.\n")
            else:
                oStream.write("The command entered (\"%s\") is not in the command database.\n" % argument)
            oStream.write("Execution of Denali will stop.\n\n")
            return "Failed"

        if denaliVariables['scpMultiFile'] != True:
            if isinstance(retDict, dict) == True:
                start_time = retDict.get('start_time', None)
                displayCurrentTime(denaliVariables, "[ End Time  :", " ]", start_time)
            elif denaliVariables['commandFunction'] != 'info':
                start_time_list = []
                for (dIndex, dict_segment) in enumerate(retDict):
                    start_time = retDict[dIndex][1].get('start_time', None)
                    if start_time is not None:
                        start_time_list.append(start_time)
                start_time = min(start_time_list)
                displayCurrentTime(denaliVariables, "[ End Time  :", " ]", start_time)

        # remove the start_time key here, or every summary would need to do it
        if isinstance(retDict, dict) and 'start_time' in retDict:
            retDict.pop('start_time', None)
        elif isinstance(retDict, list) == True:
            for (dIndex, dict_segment) in enumerate(retDict):
                retDict[dIndex][1].pop('start_time', None)

        # Summary function serves two purposes:
        # (1) summary information for the command just run (if requested)
        # (2) individual integration items are prepared (column names, widths, etc.)
        redDict = commandFunctionSummary[function](denaliVariables, retDict)

        if denaliVariables['pdshCanceled'] == True:
            return "Failed"

        # flag to let the main code know a command was executed
        denaliVariables["commOptions"] = "completed"

        if denaliVariables["combine"] == True and len(argument_list) == 1:
            # Integrate the command data returned in the existing response dictionary
            responseDictionary = integrateCommandData(denaliVariables, retDict, responseDictionary)
            # format and output the data here
            # too many problems passing it back to the main function work with
            (printData, overflowPrintData) = denali_search.generateOutputData(responseDictionary, denaliVariables)
            denali_search.prettyPrintData(printData, overflowPrintData, responseDictionary, denaliVariables)
            return True

        elif function == 'pdsh' and len(argument_list) == 1:
            return redDict
        elif function == 'host':
            return retDict
        else:
            if len(argument_list) == 1:
                if redDict == True:
                    return True
                elif redDict == False:
                    return False
                elif redDict is not None and "error_return" in redDict:
                    if int(redDict["error_return"]) != 0:
                        return False
                    else:
                        return True
                else:
                    return True



##############################################################################
#
# setArgumentFlags(denaliVariables, argument_list)
#
#   This function goes through the list of arguments and sets command specific
#   flags to handle variations of commands requested.
#

def setArgumentFlags(denaliVariables, argument_list):

    global argument_flag_ilo
    global argument_flag_port
    modified_argument_list   = []

    for argument in argument_list:
        if argument == 'ilo':
            argument_flag_ilo = True
            continue
        elif argument.startswith('p:') or argument.startswith('port:'):
            argument_flag_port = True
            continue
        modified_argument_list.append(argument)

    # Modify serverList as needed by the argument flag
    # For now, just the ilo flag is set, so a single for loop will take care of
    # this.  If/when more flags are needed, the code will set a variable indicating
    # that one (or more) flags were altered, and if true, then a loop will ensure
    # modifying what the flags have requested.
    if argument_flag_ilo == True:
        for (index, server) in enumerate(denaliVariables['serverList']):
            site_location = server.find('.')
            server = server[:site_location] + '.ilo' + server[site_location:]
            denaliVariables['serverList'][index] = server

    if argument_flag_port == True:
        port_list = argument_list[1:]
        port_list = ','.join(port_list)
        port_list = port_list.replace(' ',',')
        denaliVariables['nmapOptions'] = port_list.split(':')[1]
        modified_argument_list = ['ping']

    return modified_argument_list



##############################################################################
#
# pdsh_ssh_optionAdd(denaliVariables, argument_list)
#
#   This function checks to see if pdsh was specified with a non-interactive
#   flag.  If so, see if SSH was also specified.  If it was not, activate
#   the fall-through code.
#

def pdsh_ssh_optionAdd(denaliVariables, argument_list):

    if denaliVariables["non_interact"] == True:
        if 'ssh' in argument_list:
            return argument_list
        elif 'pdsh' in argument_list:
            # pdsh fall-through configuration
            pdsh_index = argument_list.index('pdsh')
            argument_list.insert((pdsh_index+1), 'ssh')

            # set the ssh command to equal the pdsh command
            denaliVariables['sshCommand']     = denaliVariables['pdshCommand']
            denaliVariables['sshFallThrough'] = True

    return argument_list



##############################################################################
#
# reviseArgumentList(denaliVariables, argument_list)
#
#   If scp-pull is in the argument list, and if there is a wildcard search
#   on the remote host (either an asterisk '*' or question-mark '?' in the remote
#   filename), then add in a pdsh function before the scp-pull to get a list of
#   the files that will be retrieved.  I haven't found a way to parallelize the
#   scp-pull function with a potential multiple files on the source host with
#   each having a separate number.  So -- get the list first.
#
#   The best way to avoid this (wildcard pull/search on the remote host) is to
#   send a command to the remote hosts that puts all of the files into a single
#   file to download -- like a tarball.  If named the same then scp-pull will
#   retrieve that one file, and will work as normal.  Single file pull downloads
#   work as expected.
#

def reviseArgumentList(denaliVariables, argument_list):

    for (index, argument) in enumerate(argument_list):
        if argument == 'scp-pull' and ('*' in denaliVariables['scpSource'] or '?' in denaliVariables['scpSource']):
            # insert 'pdsh' into argument list before the scp-pull function
            argument_list.insert(index, 'pdsh')

            # now fill in the pdsh requirements
            denaliVariables['pdshCommand'] = SCP_PDSH_COMMAND + ' %s' % denaliVariables['scpSource']
            denaliVariables['pdshOptions'] = SCP_PDSH_OPTIONS

            # flag to alert the rest of the code that multi-file scp pull is happening
            denaliVariables['scpMultiFile'] = True

            break

    return argument_list



##############################################################################
#
# checkForDuplicates(argument_list)
#

def checkForDuplicates(argument_list):

    for arg_base in argument_list:
        counter = 0
        for argument in argument_list:
            if argument == arg_base:
                counter += 1
                if counter > 1:
                    return True

    return False



##############################################################################
#
# retrieveAuthenticationData(denaliVariables, function)
#

def retrieveAuthenticationData(denaliVariables, function):

    oStream = denaliVariables['stream']['output']
    iStream = denaliVariables['stream']['input']

    # backup the stdin pointer -- whatever it is at this point.
    stdin_backup=sys.stdin

    if len(denaliVariables["userName"]) == 0:
        detected_user = getpass.getuser()
    else:
        detected_user = denaliVariables["userName"]

    # set a pointer to /dev/tty -- to allow user input
    sys.stdin = open("/dev/tty")

    if function == 'pdsh':
        display_function = "pdsh -> ssh"
    else:
        display_function = function

    oStream.write("\nEnter Authentication Credentials for [%s]\n" % display_function)
    oStream.flush()
    if denaliVariables["userNameSupplied"] == False:
        username = getpass._raw_input("  Username [detected user: %s]: " % detected_user, oStream, iStream)
    else:
        username = getpass._raw_input("  Username [supplied user: %s]: " % detected_user, oStream, iStream)

    if username == '':
        # Empty username, use the username detected
        username = detected_user

    password_text = "  Password : "
    password      = getpass.getpass(password_text)

    # now restore the stdin pointer to whatever it was before.  This should allow
    # the processing to continue as expected
    sys.stdin=stdin_backup

    denaliVariables["non_interact_data"]["username"] = username
    denaliVariables["non_interact_data"]["password"] = password

    return True



##############################################################################
#
# verifySSHRequirements(denaliVariables)
#

def verifySSHRequirements(denaliVariables):

    # verify that the sshpass binary is available
    if os.path.isfile('/usr/bin/sshpass') == True:
        return True
    elif os.path.isfile('/usr/local/bin/sshpass') == True:
        return True
    else:
        return False



##############################################################################
#
# verifyPDSHEnvironment(denaliVariables)
#
#   This function ensures that the correct environment is configured to use
#   PDSH on a machine.
#
#   If there is an existing configuration, back it up and restore it after
#   using the tool.
#

def verifyPDSHEnvironment(denaliVariables):

    pdsh_rcmd = os.getenv('PDSH_RCMD_TYPE', False)
    if pdsh_rcmd != False:
        denaliVariables["pdshEnvironment"].update({'PDSH_RCMD_TYPE':pdsh_rcmd})
    os.environ['PDSH_RCMD_TYPE'] = PDSH_ENVIRONMENT['PDSH_RCMD_TYPE']

    pdsh_ssh  = os.getenv('PDSH_SSH_ARGS_APPEND', False)
    if pdsh_ssh != False:
        denaliVariables['pdshEnvironment'].update({'PDSH_SSH_ARGS_APPEND':pdsh_ssh})
    os.environ['PDSH_SSH_ARGS_APPEND'] = PDSH_ENVIRONMENT['PDSH_SSH_ARGS_APPEND']

    ccode = createLogDirectories(denaliVariables)
    if ccode == False:
        return False



##############################################################################
#
# restorePDSHEnvironment(denaliVariables)
#

def restorePDSHEnvironment(denaliVariables):

    if 'PDSH_RCMD_TYPE' in denaliVariables['pdshEnvironment']:
        os.environ['PDSH_RCMD_TYPE'] = denaliVariables['pdshEnvironment']['PDSH_RCMD_TYPE']

    if 'PDSH_SSH_ARGS_APPEND' in denaliVariables['pdshEnvironment']:
        os.environ['PDSH_SSH_ARGS_APPEND'] = denaliVariables['pdshEnvironment']['PDSH_SSH_ARGS_APPEND']



##############################################################################
#
# verifyPDSHRequirements(denaliVariables)
#

def verifyPDSHRequirements(denaliVariables):
    pdsh    = False
    dshbak  = False

    # verify pdsh is available
    if os.path.isfile('/usr/bin/pdsh') == True:
        pdsh = True
    elif os.path.isfile('/usr/local/bin/pdsh') == True:
        pdsh = True

    # verify dshbak is available
    if os.path.isfile('/usr/bin/dshbak') == True:
        dshbak = True
    elif os.path.isfile('/usr/local/bin/dshbak') == True:
        dshbak = True

    return (pdsh, dshbak)



##############################################################################
#
# retryTimeoutPause(denaliVariables, retry_counter)
#

def retryTimeoutPause(denaliVariables, retry_counter):

    global RETRY_PAUSE_TIME

    if RETRY_PAUSE_TIME > 0:
        RETRY_PAUSE_TIME = int(RETRY_PAUSE_TIME)
        print
        if denaliVariables['nocolors'] == True:
            print "[Retry # %i]: Pausing for %i seconds before retrying failed devices" % (retry_counter, RETRY_PAUSE_TIME)
        else:
            sys.stdout.write(colors.fg.white + '[' + colors.fg.red + 'Retry #' + str(retry_counter) + colors.fg.white + ']' + colors.reset)
            print ": Pausing for %i seconds before retrying failed devices." % RETRY_PAUSE_TIME

        # loop to count off the seconds until the code retries the request(s) again
        for counter in range(0, RETRY_PAUSE_TIME):
            time.sleep(1)
            sys.stdout.write('.')
            sys.stdout.flush()

        print "\n\n"

    return



##############################################################################
#
# preProcessHandling(denaliVariables, funciton, nr_arguments)
#

def preProcessHandling(denaliVariables, function, nr_arguments):

    global ssh_time_string

    oStream = denaliVariables['stream']['output']

    # If the command processing was called via slack and either "scp" or "pdsh"
    # were requested -- deny the request.  There is _no_way_ that denali should
    # copy files or execute commands to potentially thousands of servers via
    # slack.  That is way too dangerous to allow.
    if denaliVariables["slack"] == True:
        if function == "scp" or function == "pdsh":
            return "slack"

    # Turn off the combine switch if any of the following functions are requested
    # or if there is more than one command being submitted -- can't combine all of
    # the data into a single output -- so just disable it.
    if function == "spots" or function == "scp" or function == "pdsh" or nr_arguments > 1:
        denaliVariables["combine"] = False

    # if scp was chosen, and non-interactive mode, get the authentication data
    if function.startswith("scp"):
        if denaliVariables["non_interact"] == True:
            ccode = verifySSHRequirements(denaliVariables)
            if ccode == False:
                oStream.write("\nDenali: SSHPASS utility is not installed and is required for the non-interactive (--ni) switch to function.\n")
                oStream.write("        Re-run without the non-interactive switch.  Exiting.\n\n")
                oStream.flush()
                denaliVariables["non_interact"] = False
                return False
            else:
                ccode = retrieveAuthenticationData(denaliVariables, function)

        # make sure destination renames are off for push operations
        if function == "scp-push" or function == "scp":
            denaliVariables["scpRenameDestFile"] = False

        denaliVariables["scpStartTime"] = time.time()

    # if pdsh was chosen, verify that the binary is available
    if function == "pdsh":
        (pdsh, dshbak) = verifyPDSHRequirements(denaliVariables)
        if pdsh == False:
            oStream.write("\nPDSH utility not found (/usr/bin/pdsh) -- execution will stop.\n\n")
            oStream.flush()
            denaliVariables["pdsh_dshbak"][0] = False
            return False
        if dshbak == False:
            oStream.write("\nDSHBAK utility not found (/usr/bin/dshbak) -- pdsh log summary utility will not be used.\n\n")
            oStream.flush()
            denaliVariables["pdsh_dshbak"][1] = False

        ccode = verifyPDSHEnvironment(denaliVariables)
        if ccode == False:
            return False

        # PDSH does not support directly passing a password/passphrase to the session
        # it can pass a username, but that's only half of what I need
        if denaliVariables["non_interact"] == True:
            ccode = retrieveAuthenticationData(denaliVariables, function)

    # if ssh was chosen
    if function == "ssh":
        ccode = createLogDirectories(denaliVariables)
        if ccode == False:
            return False

        # Only ask for the username/password if --ni is used _AND_ the pdsh fall through to ssh
        # isn't active.  If it is active, it means that the command has been transferred over
        # already and the credentials have already been gathered
        if denaliVariables["non_interact"] == True:
            ccode = verifySSHRequirements(denaliVariables)
            if ccode == False:
                oStream.write("\nSSHPASS utility not found (/usr/bin/sshpass) -- non-interactive mode disabled.\n\n")
                oStream.flush()
                denaliVariables["non_interact"] = False
            else:
                if denaliVariables['sshFallThrough'] == False:
                    ccode = retrieveAuthenticationData(denaliVariables, function)

        ssh_time_string = datetime.datetime.now().strftime("%m%d_%H%M%S")

    # if ping with ports (nmap functionality) was requested
    if function == "ping":
        if argument_flag_port == True and os.path.isfile('/usr/bin/nmap') == False:
            print "Error:  NMAP utility not found at /usr/bin/nmap.  Port ping functionality is unavailable."
            return False

    return True



##############################################################################
#
# integrateCommandData(denaliVariables, commandDictionary, responseDictionary)
#
#   This function takes a dictionary (keyed by hostname) and inserts it into
#   the existing responseDictionary from SKMS.
#

def integrateCommandData(denaliVariables, commandDictionary, responseDictionary):

    # create the column header information (if it exists)
    if "new_column_data" in commandDictionary:
        newColumnData = commandDictionary["new_column_data"]
        for column_data in newColumnData:
            insertColumnNumber = column_data[0]
            column_data.pop(0)
            column_name = column_data[0]
            denaliVariables["columnData"].insert(insertColumnNumber, column_data)

            # integrate the data in the existing responseDictionary
            for (index, hostname) in enumerate(responseDictionary["data"]["results"]):
                if argument_flag_ilo == True:
                    # add in ".ilo" to allow the hostnames to match
                    ilo_hostname = hostname['name']
                    location     = ilo_hostname.find('.')
                    ilo_hostname = ilo_hostname[:location] + '.ilo' + ilo_hostname[location:]
                    hostname['name'] = ilo_hostname
                command_data = commandDictionary[hostname["name"]]
                hostname.update({column_name:command_data})
                responseDictionary["data"]["results"][index] = hostname
    else:
        pass

    if denaliVariables["debug"] == True:
        print "dvcd = %s" % denaliVariables["columnData"]
        print "rd   = %s" % responseDictionary

    return responseDictionary



##############################################################################
#
# getLongestHostname(serverList)
#
#   This function is called automatically when the command code is run.  All that
#   is needed is for functions below to use "max_host_length" (a global variable)
#   if the maximum host length in characters is required.
#

def getLongestHostname(serverList):

    hostLength = 0
    add_length = 13     # 13 characters for ".omniture.com"
    max_host   = ''

    # determine the character count of the longest hostname
    for (index, hostname) in enumerate(serverList):
        length = len(hostname)
        if hostname.find(".adobe.net") == -1 and hostname.find(".omniture.com") == -1 and hostname.find(".offermatica.com") == -1:
            length += add_length
        if length > hostLength:
            hostLength = length
            max_host   = hostname

    #print "max_host = %s" % max_host

    return hostLength



##############################################################################
#
# deleteOldLogFiles(denaliVariables)
#
#   This function will delete any 'old' log files for pdsh or ssh command
#   sessions.  It is called at the beginning of the routine to launch a new
#   command.
#

def deleteOldLogFiles(denaliVariables):

    pid = os.fork()
    if pid == 0:
        # child fork -- store analytics data in a database
        if denaliVariables["debug"] == True:
            print "Denali [Command] child process: %s" % os.getpid()

        ccode = discoverLogFiles(denaliVariables)

        # exit the forked process successfully (0) or with an error condition (1)
        if ccode == 0:
            os._exit(0)
        else:
            os._exit(1)
    else:
        # parent fork -- continue and present requested data to the user
        if denaliVariables["debug"] == True:
            print "Denali [Query] parent process: %s" % os.getpid()

        return True



##############################################################################
#
# discoverLogFiles(denaliVariables)
#
#   The pdsh_log_directory and ssh_log_directory variables are defined at
#   the top of the file.
#

def discoverLogFiles(denaliVariables):

    pdsh_log = denaliVariables['pdsh_log_file']
    ssh_log  = denaliVariables['ssh_log_file']

    # if the username isn't specified, get it from the environment or have the
    # user type it in
    if len(denaliVariables["userName"]) == 0:
        if len(os.environ['USER']) > 0:
            denaliVariables["userName"] = os.environ['USER']
        elif len(os.environ['USERNAME']) > 0:
            denaliVariables["userName"] = os.environ['USERNAME']

    # if the user didn't define a log path, go with the default
    if len(denaliVariables['logPath']) == 0:
        pdsh_file_path = "/home/" + denaliVariables["userName"] + "/.denali" + pdsh_log_directory
        ssh_file_path  = "/home/" + denaliVariables["userName"] + "/.denali" + ssh_log_directory
    else:
        pdsh_file_path = denaliVariables['logPath'] + pdsh_log_directory
        ssh_file_path  = denaliVariables['logPath'] + ssh_log_directory

    # pdsh logs
    if os.path.exists(pdsh_file_path):
        os.chdir(pdsh_file_path)
        pdsh_log_files = glob.glob(pdsh_log + '*.*')
        if len(pdsh_log_files) > 0:
            pdsh_log_files.sort()
            ccode = deleteLogFiles(denaliVariables, pdsh_file_path, pdsh_log_files)

    # ssh logs
    if os.path.exists(ssh_file_path):
        os.chdir(ssh_file_path)
        ssh_log_files = glob.glob(ssh_log + '*.*')
        if len(ssh_log_files) > 0:
            ssh_log_files.sort()
            ccode = deleteLogFiles(denaliVariables, ssh_file_path, ssh_log_files)

    return True



##############################################################################
#
# deleteLogFiles(denaliVariables, file_path, log_file_list)
#

def deleteLogFiles(denaliVariables, file_path, log_file_list):

    files_deleted_count = 0

    # Number of days to keep logs (default: 30 days from now)
    TIME_DELTA = denaliVariables['rbDaysToKeep'] * 24 * 60 * 60

    current_time = time.time()

    for log_file in log_file_list:
        log_file = file_path + '/' + log_file

        # get the modification timestamp
        mod_timestamp = os.path.getmtime(log_file)

        if (current_time - TIME_DELTA) > mod_timestamp:
            try:
                os.remove(log_file)
            except error as e:
                pass
            else:
                files_deleted_count += 1

    return files_deleted_count



##############################################################################
#
# gatherProcess(denaliVariables, function, hostQueue, q, lock, printLock, mCommandDict, mCommandList)
#
#   This function gathers data according to the function passed in as a parameter.
#   It first pulls a hostname off an MP-safe queue (hostQueue), and then calls the
#   passed in parameter's collection function against that host.
#
#   The host data retrieved from the function is then placed on an MP-safe queue (q)
#   for the listener process to pick up.  After the placement is complete, this
#   process looks at the hostQueue again to see if more hosts remain.  If so, the
#   next one is pulled off the queue and the cycle of data retrieval begins again.
#   If no hosts remain, an error will be asserted during the queue retrieval process,
#   indicating the queue is empty.  At that point, this process quits.
#
#   By looping after finishing with one piece of data, it allows the same process to
#   work on a new host without the need to tear down an existing process and create
#   a new one.  This gives the list of hosts a "pool" of worker processes.
#
#   PDSH uses this function a little differently.  Instead of looping through one
#   host at a time, all devices are sent to PDSH to process, and the parallelization
#   is left completely with PDSH.
#
#   MRASETEAM-41340: MP timing issue exposed:  hostQueue isn't populated yet and there
#                    were random pdsh command runs where a python stack was shown.
#                    Retry logic has been added to address this case.
#

def gatherProcess(denaliVariables, function, hostQueue, q, lock, printLock, mCommandDict, mCommandList):

    host_count  = 0
    retry_count = 0
    MAX_RETRIES = 5
    GET_DELAY   = 2     # in seconds

    # set the exception flag
    exception = False

    while True:

        # acquire the lock
        lock.acquire()

        try:
            if exception == True:
                # exception method -- wait for an item, and then throw an exception
                # if one does not appear
                if denaliVariables['debug'] == True:
                    print "hostQueue retry logic engaged (retry #%d)" % retry_count
                hostname = hostQueue.get(True, GET_DELAY)
            else:
                # default method -- no waiting, see if there is an item
                hostname = hostQueue.get(False)

            # increment the host counter
            host_count += 1
        except:
            # release the lock
            lock.release()

            # There are times when the hostQueue isn't populated yet, and the code
            # needs to wait.  This only happens when zero hosts have been processed
            # and the queue says it is empty.  This code checks for that condition
            # and implements some retry logic to ensure that enough time is given
            # for it to populate.
            #
            # If there is an exception and the host_count is greater than zero, it
            # means that the queue is empty and the retry logic is unnecessary.
            if host_count == 0 and denaliVariables['pdshExecuting'] == True:
                exception = True
                retry_count += 1
                if retry_count > 0 and retry_count < MAX_RETRIES:
                    continue
            break

        # release the lock
        lock.release()

        # (re)set the exception flag
        exception = False

        #  make a generic call here to collect the data
        retValue = commandFunctionCollect[function](denaliVariables, hostname, printLock, mCommandDict, mCommandList)

        # put the received data on the queue for the listenerProcess
        q.put([hostname, retValue])

    return



##############################################################################
#
# listenerProcess(denaliVariables, function, rcvData, lock, printLock, pipe, mCommandDict, mCommandList, printParameters=[])
#
#   This function's duty is to listen for data being sent to the rcvData queue.
#   Data is placed there by the gatherProcess function(s).  Once the data is
#   realized, it is first checked to see if it equals "FINISHED".  This is a key
#   to the code to know that the master process is requesting this process to exit
#   no matter the status of anything else.  Typically this is only seen when the
#   queue data is exhausted and processes need to be cleaned up.
#
#   Upon receipt of a non-FINISHED item of data is retrieved from the queue, a call
#   is made to the passed in parameter's specific recording function, and then to
#   the print function, typically.
#
#   Notes:
#   1.  There is only one listener process spawned -- it handles all data reception.
#
#   2.  The listener code will loop forever until told to stop by the launchMPQuery
#       process with a "FINISHED" signal.
#

def listenerProcess(denaliVariables, function, rcvData, lock, printLock, pipe, mCommandDict, mCommandList, printParameters=[]):

    retDictionary = {}
    pdshData      = []
    oStream       = denaliVariables['stream']['output']

    while True:
        # this call will block until data arrives
        processData = rcvData.get()

        # if the main process (launchMPQuery) signals that all watchers have
        # completed, then break out of the while loop here
        if processData == "FINISHED":
            break

        # special data handling for PDSH work-flows
        if denaliVariables['pdshExecuting'] == True:
            if denaliVariables['pdshSeparate'] != False:
                # With 'separate' PDSH operations, append each one to the end of
                # the existing data.  This allows an iterative operation to go
                # through each data response one-by-one.
                pdshData.append(processData[:])
            else:
                # With non-separate PDSH operations (a single operation), just
                # extend the existing data.
                pdshData.extend(processData[:])
            continue

        if function != 'ssh':
            # ssh data recording takes place in the function "executeSSH", not here
            retDictionary = commandFunctionRecordData[function](denaliVariables, retDictionary, processData)
        else:
            retDictionary = commandFunctionRecordData[function](denaliVariables, retDictionary, processData, processData[0])

        #print the collected data
        if denaliVariables["combine"] == False and function != 'ssh':
            commandFunctionPrint[function](denaliVariables, processData, printLock, mCommandDict, mCommandList, printParameters)

    if denaliVariables['pdshExecuting'] == True:
        if denaliVariables['pdshSeparate'] != False:
            pipe.send(pdshData)
            pipe.close()
        else:
            # remove the list of hosts (item[0])
            if len(pdshData):
                pdshData = pdshData[1]
            else:
                # problem detected -- print out a contextual error
                oStream.write("Denali execution error: hostQueue empty, no data returned.\n\n")
            pipe.send(pdshData)
            pipe.close()
    else:
        # send the completed dictionary to the main process
        pipe.send(retDictionary)
        pipe.close()

    return



##############################################################################
#
# countSeparatorSegments(denaliVariables, hostQueue, serverList)
#

def countSeparatorSegments(denaliVariables, hostQueue, serverList):

    pdsh_hosts = []

    # get the count
    separator_count = denaliVariables['pdshSeparate']['separator_count']

    if separator_count == 1:
        # working with a separation request/submission here
        serverList = denaliVariables['pdshSeparateData'].keys()
        # This loads the separation keys into the hostQueue.
        # performPDSHoperation() will use the key to get the correct host
        # list to work with.
        for separator in serverList:
            hostQueue.put(separator)
            pdsh_hosts.extend(denaliVariables['pdshSeparateData'][separator])

    elif separator_count == 2:
        serverList = []
        top_level_keys = denaliVariables['pdshSeparateData'].keys()
        for key in top_level_keys:
            lower_level_keys = denaliVariables['pdshSeparateData'][key].keys()
            for final_key in lower_level_keys:
                key_to_add = "%s:%s" % (key, final_key)
                serverList.append(key_to_add)
                hostQueue.put(key_to_add)
                pdsh_hosts.extend(denaliVariables['pdshSeparateData'][key][final_key])

    else:
        # fail!
        return (False, False, False)

    # Fixed in Python3 -- delay to allow the queue to finish populating
    #
    # This fixes (works around via a delay):
    #   IOError: [Errno 32] Broken pipe in multiprocessing/queues.py
    #
    # When a process first puts an item on the queue, a feeder thread is automatically
    # started which transfers objects from a buffer into the pipe (queue).  If the main
    # function ends before the feeder thread completes, the above error is observed.
    time.sleep(0.1)

    return (pdsh_hosts, hostQueue, serverList)



##############################################################################
#
# pdshMPHandling(denaliVariables, hostQueue, serverList)
#

def pdshMPHandling(denaliVariables, hostQueue, serverList):

    pdsh_hosts = []
    global MAX_PROCESS_COUNT

    if denaliVariables['pdshSeparate'] != False:
        # this code path handles --pdsh_separate work-flows
        (pdsh_hosts, hostQueue, serverList) = countSeparatorSegments(denaliVariables, hostQueue, serverList)
        if pdsh_hosts == False:
            return "Failed"

        (pdsh_hosts, data_center) = returnPDSHHostList(denaliVariables, pdsh_hosts)
        (pdsh_parms, pdshOptions, retry_command) = returnPDSHCommandString(denaliVariables, pdsh_hosts)
        if pdsh_parms == False:
            return "Failed"

        ccode = finalFunctionPromptCheck(denaliVariables, retry_command, pdsh_parms, pdshOptions, serverList, pdsh_hosts)
        if ccode == False:
            # clean up and exit out.
            return "Failed"

        # code to be run if the --verify switch is used WITH the --ps (--pdsh_separate) switch
        if denaliVariables['devServiceVerify'] == True:
            # Set the maximum # of processes to 1 (saving the existing value).
            # The reason for this is to allow the set of hosts to all run at the
            # same time under one PDSH execution umbrella (this setting also
            # includes the health check PDSH execution).
            MAX_PROCESS_COUNT_save = MAX_PROCESS_COUNT
            MAX_PROCESS_COUNT = 1

            (ccode, hostname_list) = denali_healthCheck.hc_entryPoint(denaliVariables, serverList)
            if ccode == False:
                print
                denali_healthCheck.displayOutputMarker(denaliVariables, "Health Check FAILURE - PDSH Execution Halted", 2)
                displayCurrentTime(denaliVariables, "[ End Time  :", " ]", time.time())
                return {}

            # reset variable to previous value to ensure pdsh efficiency in the "normal" run
            MAX_PROCESS_COUNT = MAX_PROCESS_COUNT_save

            # remove hosts that were checked (no need to "double-dip" here)
            removePDSHHosts(denaliVariables, hostname_list, pdsh_hosts, pdsh_parms)

            print
            denali_healthCheck.displayOutputMarker(denaliVariables, "Allow Complete PDSH Execution")

    else:
        hostQueue.put(serverList)
        time.sleep(0.1)

    return hostQueue



##############################################################################
#
# createSharedManagerObjects(manager, function)
#

def createSharedManagerObjects(manager, function):

    # Instantiate a shared manager dictionary object
    # Used for progress indicators w/ PDSH and SCP functions
    mCommandDict = manager.dict()
    mCommandList = manager.list()

    if function.startswith('scp'):
        mCommandDict.update({'scp_start_count'    : 0})
        mCommandDict.update({'scp_complete_count' : 0})
        mCommandDict.update({'scp_in_flight'      : 0})
        mCommandDict.update({'scp_success'        : 0})
        mCommandDict.update({'scp_failure'        : 0})

    if function == 'pdsh':
        mCommandDict.update({'pdsh_start_count'   : 0})
        mCommandDict.update({'pdsh_success_count' : 0})
        mCommandDict.update({'pdsh_failure_count' : 0})
        mCommandDict.update({'pdsh_normal_count'  : 0})

    if function == 'ssh':
        mCommandDict.update({'ssh_start_count'    : 0})
        mCommandDict.update({'ssh_complete_count' : 0})
        mCommandDict.update({'ssh_in_flight'      : 0})
        mCommandDict.update({'ssh_success'        : 0})
        mCommandDict.update({'ssh_failure'        : 0})
        mCommandDict.update({'ssh_normal'         : 0})
        mCommandDict.update({'ssh_hostkey'        : 0})
        mCommandDict.update({'ssh_keypass'        : 0})

    # https://bugs.python.org/issue6766
    # Python bug:  Cannot modify dictionaries, lists or sets inside of a
    #              managed dictionary (like above).  Because of this, there
    #              is mCommandDict (with counters to be updated) and
    #              mCommandList (for a list to be updated outside of the
    #              managed dictionary).
    mCommandList = []

    return mCommandDict, mCommandList



##############################################################################
#
# populatehostQueueData(denaliVariables, hostQueue, serverList)
#

def populatehostQueueData(denaliVariables, hostQueue, serverList):

    oStream    = denaliVariables['stream']['output']
    parameters = ''

    # Every other command function, except pdsh, will use a list of hosts given
    # to it and then one by one cycle through them (while creating processes to
    # gather the data, etc.).  With PDSH, the entire list needs to be given to
    # a single process and then PDSH will thread them out by itself.
    if denaliVariables['pdshExecuting'] == True:
        hostQueue = pdshMPHandling(denaliVariables, hostQueue, serverList)
        if hostQueue == "Failed":
            return {}
    else:
        if denaliVariables['devServiceVerify'] == True:
            print "Denali Execution Stopped: --verify only enabled for -c pdsh work-flows."
            return "Failed"

        for server in serverList:
            hostQueue.put(server)

        # time to allow queue to finish populating
        time.sleep(0.1)

        if denaliVariables['commandFunction'] == 'ssh':
            if len(denaliVariables['sshCommand']) == 0:
                oStream.write("\nSSH command to execute is empty -- execution will stop.\n")
                oStream.write("Use '--ssh_command=<command(s)_to_run>'.\n\n")
                return "Failed"
            parameters = denaliVariables['sshCommand']

        ccode = finalFunctionPromptCheck(denaliVariables, denaliVariables['retryCommand'], parameters)
        if ccode == False:
            # clean up and exit out.
            return "Failed"

        # code to be run if the --verify switch is used with -c ssh
        if denaliVariables['devServiceVerify'] == True:
            (ccode, hostname_list) = denali_healthCheck.hc_entryPoint(denaliVariables, serverList)
            if ccode == False:
                print
                denali_healthCheck.displayOutputMarker(denaliVariables, "Health Check FAILURE - PDSH Execution Halted", 2)
                displayCurrentTime(denaliVariables, "[ End Time  :", " ]", time.time())
                return {}

            return "Failed"

    return hostQueue



##############################################################################
#
# extractServerList(denaliVariables, function)
#

def extractServerList(denaliVariables, function):

    # extract the server list and fill the hostQueue
    # see if this is a pdsh/ssh fall through with failed hosts
    if denaliVariables['sshFallThrough'] == True and function == 'ssh':
        if len(denaliVariables['pdshFailedHosts']) > 0:
            # both conditions are true -- process the failed hostnames
            serverList = denaliVariables['pdshFailedHosts']
            print
            print "SSH command execution automatically engaged for pdsh failed hosts (PDSH Fall-through to SSH):"
            print
        else:
            # this is a 'fall-through' pass, but there are no failed hosts
            # -- just exit with an empty dictionary
            return {}
    else:
        serverList = denaliVariables['serverList']

    return serverList



##############################################################################
#
# launchMPQuery(denaliVariables, function, parameters)
#
#   This process is the start of creating an MP-enabled data gathering or querying
#   piece of code.  MP-safe queues, pipes and locks are used.
#
#   This function starts a single listener process and then loops through the host
#   list creating gather-er processes until either the maximum defined value is
#   reached (MAX_PROCESS_COUNT), or the number of processes created is equal to
#   the number of hosts in the list.  This gather process creation is the pool of
#   processes needed to gather the data in an MP fashion.
#
#   After the maximum number of processes have been spun up, the code waits for them
#   to exit (this happens when the host queue is empty).  Upon determining this, a
#   signal is sent to the listener ("FINISHED") that it is time to stop and submit any
#   remaining data.  After FINISHED is sent, all pipes, queues, and locks are closed
#   and released.
#

def launchMPQuery(denaliVariables, function, parameters):

    global MAX_PROCESS_COUNT
    procList                = []
    hostQueue               = Queue()
    rcvData                 = Queue()
    lock                    = Lock()
    printLock               = Lock()
    retDictionary           = {}
    manager                 = Manager()     # for shared process dictionary/list
    total_processes_created = 0

    if denaliVariables["debug"] == True:
        startingTime = time.time()

    # extract the serverList
    serverList = extractServerList(denaliVariables, function)
    if serverList == {}:
        return {}

    # populate the hostqueue data structure
    hostQueue = populatehostQueueData(denaliVariables, hostQueue, serverList)
    if hostQueue == {}:
        return {}
    if hostQueue == "Failed":
        return "Failed"

    # If --verify and --ps are used, recalculate the host list to be used.
    # devServiceVerifyData is set to {} after running, normally it is False
    if len(denaliVariables['devServiceVerifyData']) == 0 and denaliVariables['pdshSeparate'] != False:
        if len(denaliVariables['pdshSeparateData'].keys()) != MAX_PROCESS_COUNT:
            MAX_PROCESS_COUNT = len(denaliVariables['pdshSeparateData'].keys())

        # adjust the serverList to be equal to the remaining separator hosts
        modified_host_list = []
        for key_separator in denaliVariables['pdshSeparateData'].keys():
            modified_host_list.extend(denaliVariables['pdshSeparateData'][key_separator])
        serverList = modified_host_list

        # Put this modified list of hosts back in serverList so comparison and numbers
        # will be correct for logs and output.  The potential downside of this is that
        # now the original list is gone (poof) ... overwritten by this updated list of
        # hostnames.  If the original list is needed, for whatever reason ... ???
        denaliVariables['serverList'] = serverList

        # Clear out the existing queue ... repopulate with new data because the size
        # and element number/s _may_ have changed (due to segments only having one host
        # and that host being checked already); otherwise, without doing this and when
        # the function below is executed, it will add redundant elements (again) to the
        # queue, causing confusion in the output.

        # close out the existing queue
        hostQueue.close()
        # create a new queue (same new)
        hostQueue = Queue()
        # populate the new queue with the adjusted list
        hostQueue = populatehostQueueData(denaliVariables, hostQueue, serverList)
        if hostQueue == {}:
            return {}
        if hostQueue == "Failed":
            return "Failed"

    # get the serverList length
    serverListLength = len(serverList)

    # get the pipe configured correctly
    (parentPipe, listenerPipe) = Pipe()

    # create the shared dictionary
    (mCommandDict, mCommandList) = createSharedManagerObjects(manager, function)

    # start up the listener process -- get it ready for when the data comes
    listener = Process(target=listenerProcess, args=(denaliVariables, function, rcvData, lock, printLock, listenerPipe, mCommandDict, mCommandList, parameters))
    listener.start()

    # spin up a pool of processes to work the request -- each pulling from the hostQueue
    while True:
        if total_processes_created < MAX_PROCESS_COUNT:
            producer = Process(target=gatherProcess, args=(denaliVariables, function, hostQueue, rcvData, lock, printLock, mCommandDict, mCommandList))
            producer.start()
            procList.append(producer)
            total_processes_created += 1

            # don't create processes beyond the number of hosts in the list
            if total_processes_created >= serverListLength:
                break
        else:
            break

    # wait until all of the gather processes have finished executing
    for producer in procList:
        producer.join()

    # signal the listenerProcess to stop and collect the completed dictionary
    rcvData.put("FINISHED")
    retDictionary = parentPipe.recv()

    # close out the listenerProcess / close out the parentPipe
    listener.join()
    parentPipe.close()

    if denaliVariables["debug"] == True:
        print
        print "Total processes created : %s" % total_processes_created
        print "Elapsed mp-[%s] time   : %ss" % (function, str(time.time() - startingTime))

    return retDictionary



##############################################################################
#
# printCommandHeader(serverList, columnNames)
#
#   This function prints the header information for commands sent in.
#   columnName comes in as an array of arrays.  The array inside is a string
#   combined with a number ['Ping Data', 20].  This represents the column
#   header and total width of the column to print.
#

def printCommandHeader(serverList, columnNames):

    hostLength            = max_host_length
    lineLength            = 0
    columnTotalLength     = 0
    command_column_names  = ''

    for name in columnNames:
        columnTotalLength    += len(name[0])
        command_column_names += name[0].ljust(name[1])
        lineLength           += name[1]

    lineLength = hostLength + columnSeparatorWidth + lineLength

    # print column headers for ping
    print " Hostname".ljust(max_host_length + 1) + (" " * columnSeparatorWidth) + command_column_names
    print "=" * (lineLength + 1)

    return hostLength



##############################################################################
#
# serverPing(denaliVariables, hostname, printLock, mCommandDict, mCommandList)
#

def serverPing(denaliVariables, hostname, printLock, mCommandDict, mCommandList):

    with open(os.devnull, "wb") as limbo:
        if hostname.find("adobe") == -1 and hostname.find("omniture") == -1:
            # allow a list of ip addresses (not DNS names) to be submitted
            # This test checks the first character; if it is a digit, then this
            # is likely an ip address; assume it is so and continue.
            if hostname[0].isdigit() == True:
                pass
            else:
                hostname += ".omniture.com"

        if argument_flag_port == False:
            #
            # ping definition
            #   -c = 1  :: number/count of echo requests to send
            #   -n      :: numeric output only
            #   -W = 2  :: wait timeout value (in seconds)
            startTime = time.time()
            result    = subprocess.Popen(["ping", "-c", "1", "-n", "-W", "1", hostname], stdout=limbo, stderr=limbo).wait()
            timeDiff  = str(time.time() - startTime)[:6]
        else:
            #
            # nmap definition
            #   -p = submitted port(s)
            port_list   = str(denaliVariables['nmapOptions'])

            if port_list.find(',') == -1:
                command = "nmap -p%s --reason %s 2>/dev/null" % (port_list, hostname)
            else:
                command = "nmap -p%s %s 2>/dev/null" % (port_list, hostname)
            nmap_output = os.popen(command)
            (timeDiff, port_state, result) = parseNMAPResult(nmap_output)

        if hostname.find(".omniture.com") != -1:
            location = hostname.find(".omniture.com")
            hostname = hostname[:location]

        if result == 0:
            result = "Active"
            if argument_flag_port == False:
                result += " (%ss)" % timeDiff
            else:
                result += " (%ss | %s)" % (timeDiff, port_state)
        elif result == 2:
            if argument_flag_port == False:
                result = "Inactive"
            else:
                result = "Closed"
                result += " (%ss | %s)" % (timeDiff, port_state)
        elif result == 3:
            # only used with nmap port scan
            result = "Mixed"
            result += " (%ss | %s)" % (timeDiff, port_state)
        else:
            if argument_flag_port == False:
                result = "Failed"
            else:
                result = "Failed (%ss | No Host Response)" % timeDiff

        #if denaliVariables["debug"] == True and result.startwith("Active") == False:
        #    result += " (%ss)" % timeDiff

    return result



##############################################################################
#
# parseNMAPResult(nmap_output)
#

def parseNMAPResult(nmap_output):

    timeDiff    = ''
    port_state  = ''
    result      = 1
    nmap_output = nmap_output.read().splitlines()

    for line in nmap_output:
        if len(line) == 0:
            continue

        # successfully contacted
        if line.find('1 host up') != -1:
            timeDiff = line.split()[-2]

        # failed to contact
        elif line.find('0 hosts up') != -1:
            result = 1
            timeDiff = line.split()[-2]

        if line[0].isdigit() == True:
            # entire line for the port data response
            if len(port_state):
                port_state += ', ' + line
            else:
                port_state = line

    # remove double (or more) space characters
    count = 0
    while port_state.find('  ') != -1:
        port_state = port_state.replace('  ', ' ')
        count += 1
        # just in case
        if count > 5: break

    if port_state.count('open') > 0 and port_state.count('closed') > 0:
        result = 3  # mixed: some ports open, some ports closed
    elif port_state.count('open') > 0:
        result = 0
    elif port_state.count('closed') > 0:
        result = 2

    return timeDiff,port_state,result



##############################################################################
#
# serverPingPrint(denaliVariables, data, printLock, mCommandDict, mCommandList, printParameters=[])
#

def serverPingPrint(denaliVariables, data, printLock, mCommandDict, mCommandList, printParameters=[]):

    global print_column_headers

    ping_success  = colors.fg.lightgreen
    ping_inactive = colors.fg.lightred
    ping_failure  = colors.fg.lightred
    port_mixed    = colors.fg.yellow

    if print_column_headers == True:
        if argument_flag_port == False:
            columnNames = [['Ping Data', defaultPingWidth]]
        else:
            columnNames = [['Ping/NMAP Data', defaultPingWidth]]
        hostLength  = printCommandHeader(denaliVariables["serverList"], columnNames)
        print_column_headers = False

    result = data[1].split()[0]

    if result == "Active":
        ping_color = ping_success
    elif result == "Inactive":
        ping_color = ping_inactive
    elif result == "Closed":
        ping_color = ping_inactive
    elif result == "Mixed":             # mixed nmap port responses: some open, some closed
        result = "Mixed "
        ping_color = port_mixed
    elif result == "Failed":
        ping_color = ping_failure
    else:
        ping_color = ping_inactive

    if denaliVariables['nocolors'] == False:
        result = colors.bold + ping_color + result + colors.reset
    result += " " + ' '.join(data[1].split()[1:])   # time difference
    if denaliVariables["combine"] == False:
        print " " + data[0].ljust(max_host_length) + (" " * columnSeparatorWidth) + result

    return



##############################################################################
#
# serverPingRecordData(denaliVariables, pingDictionary, pingData)
#

def serverPingRecordData(denaliVariables, pingDictionary, pingData):

    key   = pingData[0]
    value = pingData[1]
    pingDictionary.update({key:value})

    return pingDictionary



##############################################################################
#
# serverPingSummary(denaliVariables, pingDictionary)
#

def serverPingSummary(denaliVariables, pingDictionary):

    pingOK             = 0
    pingOK_hosts       = ''
    pingOK_hosts_ilo   = ''
    pingNR             = 0
    pingNR_hosts       = ''
    pingNR_hosts_ilo   = ''
    pingFail           = 0
    pingFail_hosts     = ''
    pingFail_hosts_ilo = ''

    ilo_host_request   = False

    if denaliVariables["combine"] == True or denaliVariables['noSummary'] == True:
        # update the pingDictionary with the column information (for possible display/output)
        if argument_flag_port == False:
            columnWidth = defaultPingWidth
        else:
            columnWidth = defaultNMAPWidth
        newColumnData = [[ 1, 'Ping Data', 'Ping Data', 'Ping Data', columnWidth]]
        pingDictionary.update({"new_column_data":newColumnData})
        return pingDictionary

    hostnames = pingDictionary.keys()

    for host in hostnames:
        if host.find('.ilo.') != -1:
            ilo_host_request = True
            host_ilo  = host[:]
            host_orig = host.replace('.ilo.', '.', 1)
        else:
            host_orig = host[:]
            site_location = host.find('.')
            host_ilo = host[:site_location] + '.ilo' + host[site_location:]

        if pingDictionary[host].startswith("Active"):
            pingOK += 1
            if pingOK_hosts:
                pingOK_hosts       += ',' + host_orig
                pingOK_hosts_ilo   += ',' + host_ilo
            else:
                pingOK_hosts       += host_orig
                pingOK_hosts_ilo   += host_ilo
            continue
        elif pingDictionary[host].startswith("Inactive"):
            pingNR += 1
            pingDictionary.update({"error_return":1})
            if pingNR_hosts:
                pingNR_hosts       += ',' + host_orig
                pingNR_hosts_ilo   += ',' + host_ilo
            else:
                pingNR_hosts       += host_orig
                pingNR_hosts_ilo   += host_ilo
            continue
        else:
            pingFail += 1
            pingDictionary.update({"error_return":1})
            if pingFail_hosts:
                pingFail_hosts     += ',' + host_orig
                pingFail_hosts_ilo += ',' + host_ilo
            else:
                pingFail_hosts     += host_orig
                pingFail_hosts_ilo += host_ilo
            continue

    # set the return value according to whether any failed
    if pingFail > 0 or pingNR > 0:
        pingDictionary.update({"error_return":1})
    else:
        pingDictionary.update({"error_return":0})

    if argument_flag_port == False:
        command = "Ping"
    else:
        command = "Ping/NMAP"

    sys.stdout.write("\n %s Summary [ %d " % (command, len(hostnames)))
    if len(hostnames) > 1:
        print "hosts queried ]"
    else:
        print "host queried ]"

    print "   Success    : %d" % pingOK
    print "   Failure    : %d" % pingFail
    print "   No Response: %d" % pingNR
    print

    if denaliVariables["summary"] == True:
        # print a list of hosts in each category found
        if pingOK > 0:
            if denaliVariables['nocolors'] == True:
                print "Successful %s Response [%d]:" % (command, pingOK)
            else:
                print colors.bold + colors.fg.lightgreen + "Successful %s Response [%d]:" % (command, pingOK) + colors.reset
            printPingHostData(denaliVariables, pingOK_hosts, pingOK_hosts_ilo, ilo_host_request)

        if pingFail > 0:
            if denaliVariables['nocolors'] == True:
                print "Failure %s Response [%d]:" % (command, pingFail)
            else:
                print colors.bold + colors.fg.lightred + "Failure %s Response [%d]:" % (command, pingFail) + colors.reset
            printPingHostData(denaliVariables, pingFail_hosts, pingFail_hosts_ilo, ilo_host_request)

        if pingNR > 0:
            if denaliVariables['nocolors'] == True:
                print "No %s Response (unknown host) [%d]:" % (command, pingNR)
            else:
                print colors.bold + colors.fg.lightred + "No %s Response (unknown host) [%d]:" % (command, pingNR) + colors.reset
            printPingHostData(denaliVariables, pingNR_hosts, pingNR_hosts_ilo, ilo_host_request)

    return pingDictionary



##############################################################################
#
# printPingHostData(denaliVariables, host_list, ilo_host_list, ilo_flag)
#

def printPingHostData(denaliVariables, host_list, ilo_host_list, ilo_flag):
    host_list = host_list.split(',')
    host_list.sort()
    ilo_host_list = ilo_host_list.split(',')
    ilo_host_list.sort()

    host_cat_color = colors.fg.cyan

    # only print the '[Hostname]' text if "ping ilo" was requested
    if ilo_flag == True:
        if denaliVariables['nocolors'] == True:
            print "[Hostname]"
        else:
            print host_cat_color + "[Hostname]" + colors.reset

    print "%s" % ','.join(host_list)
    print

    # only print the ilo "hostnames" if "ping ilo" was requested
    if ilo_flag == False:
        return

    if denaliVariables['nocolors'] == True:
        print "[ILO Name]"
    else:
        print host_cat_color + "[ILO Name]" + colors.reset
    print "%s" % ','.join(ilo_host_list)
    print



##############################################################################
#
# listServers(denaliVariables, hostname, printLock, mCommandDict, mCommandList)
#

def listServers(denaliVariables, hostname, printLock, mCommandDict, mCommandList):

    serverList = denaliVariables["serverList"]

    for server in serverList:
        print "Server hostname: %s" % server

    return



##############################################################################
#
# retrieveSocketData(denaliVariables, host, port, content='')
#

def retrieveSocketData(denaliVariables, host, port, content=''):

    nc_data = ''

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        s.settimeout(SOCKET_TIMEOUT)
        s.connect((host, int(port)))
    except socket.gaierror:
        return "connect error"
    except socket.timeout:
        return "socket timeout"
    except socket_error as serr:
        if serr.errno == 111:
            return "connection refused"
        else:
            print "Socket Connect Error = %s" % serr.errno
            return "unclassified error"

    s.settimeout(None)
    s.sendall(content.encode())
    s.shutdown(socket.SHUT_WR)

    while True:
        try:
            data = s.recv(1024)
        except socket_error as serr:
            if serr.errno == 104:
                return "connection reset"
            else:
                print "Socket Receive Error = %s" % serr.errno
                return "unclassified error"
        if not data:
            if nc_data == '':
                nc_data = False
            break

        nc_data += data

        # safeguard just in case something goes crazy
        if len(nc_data) > 2048:
            s.close()
            print "oops: length of data = %s" % len(nc_data)
            return nc_data

    s.close()

    return nc_data



##############################################################################
#
# organizeSpotsData(denaliVariables, spotsData)
#

def organizeSpotsData(denaliVariables, spotsData):

    spotsDictionary = {}

    if spotsData == "socket timeout":
        spotsDictionary.update({"error":"socket timeout"})
        return spotsDictionary
    elif spotsData == "connect error":
        spotsDictionary.update({"error":"connect error"})
        return spotsDictionary
    elif spotsData == "connection reset":
        spotsDictionary.update({"error":"connection reset by peer (errno = 104)"})
        return spotsDictionary
    elif spotsData == "connection refused":
        spotsDictionary.update({"error":"connection refused (errno = 111)"})
        return spotsDictionary
    elif spotsData == "unclassified error":
        spotsDictionary.update({"error":"unclassified"})
        return spotsDictionary
    elif spotsData == False:
        spotsDictionary.update({"error":"no data returned"})
        return spotsDictionary

    # organize the data
    spotsData = spotsData.split('\n')

    for data in spotsData:
        origData = data
        data = data.split(':',1)     # split on colon

        if len(data) > 1:
            tagID   = data[0].lower().strip()
            tagData = data[1].strip()

            if tagID == "host":
                tagData = denali_utility.stripServerName([tagData], denaliVariables)
                spotsDictionary.update({"hostname":tagData[0]})
            elif tagID == "isilon version":
                # Fill in everything that Isilon doesn't provide
                # Without this section, if an Isilon host is found (on purpose or on accident), a
                # python stack will be observed -- which isn't wanted.
                # The Isilon hosts are found because they are "SiteCatalyst - DataWarehouse - Storage"
                # boxes.  The different hosts found for each is because each Isilon host responds to
                # a set of different IP addresses.
                spotsDictionary.update({"os_version"      :tagData + " (Isilon Version)"})
                spotsDictionary.update({"kernel"          :tagData + " (Isilon Version)"})
                spotsDictionary.update({"uptime"          :"N/A"})
                spotsDictionary.update({"free_memory"     :"N/A"})
                spotsDictionary.update({"used_memory"     :"N/A"})
                spotsDictionary.update({"available_memory":"N/A"})
                spotsDictionary.update({"free_swap"       :"N/A"})
                spotsDictionary.update({"used_swap"       :"N/A"})
                spotsDictionary.update({"www_count"       :"N/A"})
            elif tagID == "release":
                spotsDictionary.update({"os_version":tagData})
            elif tagID == "kernel":
                spotsDictionary.update({"kernel":tagData})
            elif tagID == "uptime":
                spotsDictionary.update({"uptime":tagData})
            elif tagID == "date in seconds":
                spotsDictionary.update({"date_in_seconds":tagData})
            elif tagID == "date":
                spotsDictionary.update({"date":tagData})
            elif tagID == "1 minute load avg":
                spotsDictionary.update({"1_minute":tagData})
            elif tagID == "5 minute load avg":
                spotsDictionary.update({"5_minute":tagData})
            elif tagID == "15 minute load avg":
                spotsDictionary.update({"15_minute":tagData})
            elif tagID == "free memory":
                spotsDictionary.update({"free_memory":tagData})
            elif tagID == "used memory":
                space = tagData[:-2] + " MB"
                spotsDictionary.update({"used_memory":space})
            elif tagID == "available memory":
                space = tagData[:-2] + " MB"
                spotsDictionary.update({"available_memory":space})
            elif tagID == "free swap":
                spotsDictionary.update({"free_swap":tagData})
            elif tagID == "used swap":
                space = tagData[:-2] + " MB"
                spotsDictionary.update({"used_swap":space})
            elif tagID == "www count":
                spotsDictionary.update({"www_count":tagData})
            elif tagID == "free disk space":
                spotsDictionary.update({"free_disk_space":tagData})
            elif tagID.startswith('/'):
                if data[0].startswith('/bin/df'):
                    continue

                if "disk_space" not in spotsDictionary:
                    partition_name  = data[0].split()[0]
                    partition_space = data[1].strip()
                    data = [partition_name, partition_space]
                    spotsDictionary.update({"disk_space":[data]})
                else:
                    # current data
                    dSpace = spotsDictionary["disk_space"]

                    # adjust incoming if needed
                    # get last item in the list
                    dSpaceLast = dSpace[-1]
                    if len(dSpaceLast) < 4:
                        space = data[1].strip()[:-2] + " MB"
                        dSpaceLast.append(space)
                        dSpace[-1] = dSpaceLast
                    else:
                        partition_name = data[0].split()[0]
                        partition_space = data[1].strip()
                        data = [partition_name, partition_space]
                        dSpace.append(data)

                    spotsDictionary.update({"disk_space":dSpace})


    return spotsDictionary



##############################################################################
#
# printIndividualStatistic(denaliVariables, arguments, print_hostname, hostname, data)
#

def printIndividualStatistic(denaliVariables, arguments, print_hostname, hostname, data):

    # add .omniture.com host_length adjustment for UT1 hosts
    if hostname.find("omniture") != -1 and len(hostname) > max_host_length:
        host_length = max_host_length + 13
    else:
        host_length = max_host_length

    if len(arguments):
        if print_hostname:
            if denaliVariables['spotsGrep'] == False:
                print_hostname = False
            print hostname.ljust(host_length),
        else:
            print ' '.ljust(host_length),

    # MRASEREQ-41091
    if len(arguments) > 1:
        print data
    else:
        print ' ' + data

    return print_hostname



##############################################################################
#
# printSpotsHost(denaliVariables, column_data, print_hostname, host_buffer, arguments, hostname)
#

def printSpotsHost(denaliVariables, column_data, print_hostname, host_buffer, arguments, hostname):

    title_line   = column_data['title']
    title_length = len(title_line)

    #
    # MRASEREQ-41427
    # colors for disk space usage thresholds:
    less_than_10  = colors.bold + colors.fg.lightred
    less_than_20  = colors.bold + colors.fg.yellow
    less_than_50  =               colors.fg.blue
    less_than_100 = colors.fg.default


    # add .omniture.com host_length adjustment for UT1 hosts
    if hostname.find("omniture") != -1 and len(hostname) > max_host_length:
        host_length = max_host_length + 13
    else:
        host_length = max_host_length

    # internal function for displaying the hostname
    def displayHostname(print_hostname, hostname):

        if len(arguments):
            if print_hostname:
                if denaliVariables['spotsGrep'] == False:
                    print_hostname = False
                sys.stdout.write(hostname.ljust(host_length))
            else:
                sys.stdout.write(' '.ljust(host_length))
            return print_hostname

    # MRASEREQ-41427
    # internal function for determining the line color to print
    def determineLineColor(free_space):
        free_space = free_space.strip()
        free_space = int(free_space[:-1])

        if free_space <= 10:
            return less_than_10
        elif free_space <= 20:
            return less_than_20
        elif free_space <= 50:
            return less_than_50
        else:
            return less_than_100

    # print the title -- if requested
    if len(arguments) == 1:
        if denaliVariables['spotsTitle'] == False:
            denaliVariables['spotsTitle'] = True
            buffer = host_length * ' '
            sys.stdout.write(buffer + title_line)
            output_line = ''
            for data_element in column_data['order']:
                output_line += data_element.ljust(column_data[data_element]['column_width'])
            if denaliVariables['nocolors'] == True:
                print output_line
            else:
                print colors.bold + column_data['color'] + output_line + colors.reset
        output_line = title_length * ' '

        # for single argument queries -- hostname prints _after_ the title
        print_hostname = displayHostname(print_hostname, hostname)

    else:
        # for no args or args>1 -- hostname prints _before_ the title (they go together)
        print_hostname = displayHostname(print_hostname, hostname)
        sys.stdout.write(title_line)
        output_line = ''
        for data_element in column_data['order']:
            output_line += data_element.ljust(column_data[data_element]['column_width'])
        if denaliVariables['nocolors'] == True:
            print output_line
        else:
            print colors.bold + column_data['color'] + output_line + colors.reset
        output_line = host_buffer

    # print the data elements
    if column_data['title'].find('Disk') == -1:
        for data_element in column_data['order']:
            output_line += column_data[data_element]['data'].ljust(column_data[data_element]['column_width'])
        print output_line
    else:
        number_partitions = len(column_data['Partition']['data'])

        for disk in range(number_partitions):
            part  = (column_data['Partition']['data'][disk]).ljust(column_data['Partition']['column_width'])    # partition name
            free  = (column_data['Free']['data'][disk]).ljust(column_data['Free']['column_width'])              # free space remaining (percentage)
            used  = (column_data['Used']['data'][disk]).ljust(column_data['Used']['column_width'])              # used space (MB)
            avail = (column_data['Available']['data'][disk]).ljust(column_data['Available']['column_width'])    # available space (MB)

            # MRASEREQ-41427
            # retrieve the line color
            line_color = determineLineColor(free)

            # root (/) disk -- handle specifically
            if disk == 0:
                output_line = host_buffer
                # MRASEREQ-41091
                if len(arguments) > 1:
                    output_line += ' ' * max_host_length
            else:
                if denaliVariables['spotsGrep'] == True:
                    print_hostname = displayHostname(True, hostname)
                    output_line    = host_buffer
                else:
                    # MRASEREQ-41091
                    if len(arguments) == 0:
                        output_line = host_buffer
                    else:
                        output_line = host_length * ' ' + title_length * ' '

            output_line += "%s%s%s%s" % (part, free, used, avail)

            # MRASEREQ-41427
            if denaliVariables['nocolors'] == True:
                print output_line
            else:
                print line_color + output_line + colors.reset

    # provide a space between each element -- cleaner look
    if len(arguments) == 0:
        print

    return print_hostname



##############################################################################
#
# printSpotsData(denaliVariables, server, spotsData, arguments)
#

def printSpotsData(denaliVariables, server, spotsData, arguments):

    load_average_color  = colors.fg.lightcyan
    memory_color        = colors.fg.yellow
    swap_memory_color   = colors.fg.lightred
    disk_space_color    = colors.fg.lightgreen

    print_hostname      = True

    # disk display widths
    partition_width     = 28
    free_width          = 9
    used_width          = 14
    available_width     = 14

    valid_arguments = [
                        'os' , 'os_version', 'kernel', 'uptime'     , 'time', 'date'   ,
                        'www', 'www_count' , 'load'  , 'loadavg'    , 'free_disk_space',
                        'mem', 'memory'    , 'swap'  , 'swap_memory', 'disk', 'disk_space'
                      ]

    # check for errors
    if "error" in spotsData:
        return False

    if len(arguments):
        arguments = arguments[0].split(' ')
        for (index, arg) in enumerate(arguments):
            arg = arg.strip()
            arguments[index] = arg
            if arg in valid_arguments:
                break
        else:
            # no valid arguments - clear out the list so data is displayed
            arguments = []

    # display/print the data
    hostname = spotsData["hostname"]
    if len(arguments) == 0:
        print hostname
        host_buffer = (' ' * 24)
    else:
        if denaliVariables["spotsGrep"] == True:
            host_buffer = hostname.ljust(max_host_length) + (' ' * 25)
        else:
            if len(arguments) > 1:
                host_buffer = (' ' * max_host_length) + (' ' * 24)
            else:
                host_buffer = (' ' * max_host_length) + (' ' * 25)

    if len(arguments) == 0 or (len(arguments) and ("os" in arguments or "os_version" in arguments)):
        output_line = "   OS Version      :   %s" % spotsData["os_version"]
        print_hostname = printIndividualStatistic(denaliVariables, arguments, print_hostname, hostname, output_line)
    if len(arguments) == 0 or (len(arguments) and ("kernel" in arguments)):
        output_line = "   Kernel          :   %s" % spotsData["kernel"]
        print_hostname = printIndividualStatistic(denaliVariables, arguments, print_hostname, hostname, output_line)
    if len(arguments) == 0 or (len(arguments) and ("uptime" in arguments)):
        output_line = "   UpTime          :   %s" % spotsData["uptime"]
        print_hostname = printIndividualStatistic(denaliVariables, arguments, print_hostname, hostname, output_line)
    if len(arguments) == 0 or (len(arguments) and ("date" in arguments or "time" in arguments)):
        output_line = "   Current Time    :   %s" % spotsData["date"]
        print_hostname = printIndividualStatistic(denaliVariables, arguments, print_hostname, hostname, output_line)
    if len(arguments) == 0 or (len(arguments) and ("www" in arguments or "www_count" in arguments)):
        output_line = "   WWW Count       :   %s" % spotsData["www_count"]
        print_hostname = printIndividualStatistic(denaliVariables, arguments, print_hostname, hostname, output_line)
    if len(arguments) == 0 or (len(arguments) and ("free_disk_space" in arguments)):
        output_line = "   Free Disk Space :   %s" % spotsData["free_disk_space"]
        print_hostname = printIndividualStatistic(denaliVariables, arguments, print_hostname, hostname, output_line)

    if len(arguments) == 0 or (len(arguments) and ("load" in arguments or "loadavg" in arguments)):
        # server's load average (`cat /proc/loadavg`)
        if denaliVariables["spotsGrep"] == True:
            print_hostname = True

        column_data = {
                        '1m'    : {'column_width':loadSeparatorWidth, 'data':spotsData['1_minute']},
                        '5m'    : {'column_width':loadSeparatorWidth, 'data':spotsData['5_minute']},
                        '15m'   : {'column_width':loadSeparatorWidth, 'data':spotsData['15_minute']},
                        'color' : load_average_color,
                        'title' : "    Load Average    :   ",
                        'order' : ['1m', '5m', '15m'],
                      }

        print_hostname = printSpotsHost(denaliVariables, column_data, print_hostname, host_buffer, arguments, hostname)

    if len(arguments) == 0 or (len(arguments) and ("mem" in arguments or "memory" in arguments)):
        # server's memory usage (`free`)
        if denaliVariables["spotsGrep"] == True:
            print_hostname = True

        column_data = {
                        'Free'      : {'column_width':spotsDefaultWidth,    'data':spotsData['free_memory']},
                        'Used'      : {'column_width':memorySeparatorWidth, 'data':spotsData['used_memory']},
                        'Available' : {'column_width':memorySeparatorWidth, 'data':spotsData['available_memory']},
                        'color'     : memory_color,
                        'title'     : "    Memory          :   ",
                        'order'     : ['Free', 'Used', 'Available'],
                      }

        print_hostname = printSpotsHost(denaliVariables, column_data, print_hostname, host_buffer, arguments, hostname)

    if len(arguments) == 0 or (len(arguments) and ("swap" in arguments or "swap_memory" in arguments)):
        # server's swap usage (`free`)
        if denaliVariables["spotsGrep"] == True:
            print_hostname = True

        column_data = {
                        'Free'  : {'column_width':swapSeparatorWidth, 'data':spotsData['free_swap']},
                        'Used'  : {'column_width':swapSeparatorWidth, 'data':spotsData['used_swap']},
                        'color' : swap_memory_color,
                        'title' : "    Swap Memory     :   ",
                        'order' : ['Free', 'Used'],
                      }

        print_hostname = printSpotsHost(denaliVariables, column_data, print_hostname, host_buffer, arguments, hostname)


    if len(arguments) == 0 or (len(arguments) and ("disk" in arguments or "disk_space" in arguments)):
        # server's disk usages (all partitions: `df -h`)
        if denaliVariables["spotsGrep"] == True:
            print_hostname = True

        host_buffer    = (' ' * 24)
        output_line    = "    Disk Space      :   "

        column_data = {
                        'Partition' : {'column_width':partition_width, 'data':[]},
                        'Free'      : {'column_width':free_width,      'data':[]},
                        'Used'      : {'column_width':used_width,      'data':[]},
                        'Available' : {'column_width':available_width, 'data':[]},
                        'color'     : disk_space_color,
                        'title'     : "    Disk Space      :   ",
                        'order'     : ['Partition', 'Free', 'Used', 'Available'],
                      }

        for disk in spotsData['disk_space']:
            column_data['Partition']['data'].append(disk[0])
            column_data['Free']['data'].append(disk[1])
            column_data['Used']['data'].append(disk[2])
            column_data['Available']['data'].append(disk[3])

        print_hostname = printSpotsHost(denaliVariables, column_data, print_hostname, host_buffer, arguments, hostname)

    return True



##############################################################################
#
# retrieveSpotsInfo(denaliVariables, hostname, printLock, mCommandDict, mCommandList)
#

def retrieveSpotsInfo(denaliVariables, hostname, printLock, mCommandDict, mCommandList):

    error_data = []

    # add .omniture.com for UT1 hosts
    if hostname.find("adobe") == -1 and hostname.find("omniture") == -1:
        hostname += ".omniture.com"

    spotsData = retrieveSocketData(denaliVariables, hostname, 24210)

    # Make sure the first line is legitimate (data) or it's an error with no data
    # that follows.  If it's an error with data after, remove the line(s) and allow
    # processing as normal.
    #
    # Example error with data:
    #   open /var/log/newrelic/newrelic-daemon.log: permission denied
    #
    # OR
    #
    #   /bin/df: '/var/lib/docker/devicemapper': Permission denied
    #   ERROR: '/bin/df -lm' exited abnormally.
    #
    # If the lines returned are > 1, it means is _SHOULD_ have a 'Host'
    # designator that starts the first line.  The code also saves off the
    # error data ... maybe it will be used later by adjusting the spots
    # data sent back from here.

    if type(spotsData) is not bool:
        sd = spotsData.split('\n')
        if len(sd) > 1 and sd[0].split(':')[0] != "Host":
            for (index, line) in enumerate(sd):
                if line.split(':')[0] == "Host":
                    return '\n'.join(sd[index:])
                else:
                    error_data.append(line)
    return spotsData



##############################################################################
#
# spotsInfoRecordData(denaliVariables, spotsDictionary, spotsData)
#

def spotsInfoRecordData(denaliVariables, spotsDictionary, spotsData):

    key   = spotsData[0]
    value = spotsData[1]

    if value == False:
        # connected successfully, but no data was returned
        spotsDictionary.update({key:"no data returned"})
        sys.stdout.write("%s     " % key.ljust(max_host_length))
        return spotsDictionary

    spotsDictionary.update({key:value})

    if value.startswith("Host") == False:
        sys.stdout.write("%s     " % key.ljust(max_host_length))

    return spotsDictionary



##############################################################################
#
# spotsInfoPrint(denaliVariables, spotsData, printLock, mCommandDict, mCommandList, printParameters=[]):
#

def spotsInfoPrint(denaliVariables, spotsData, printLock, mCommandDict, mCommandList, printParameters=[]):

    spotsDictionary = {}
    spotsDictionary = organizeSpotsData(denaliVariables, spotsData[1])

    ccode = printSpotsData(denaliVariables, spotsData[0], spotsDictionary, printParameters)
    if ccode == False:
        # error handling
        print "%s" % spotsDictionary["error"]

    return



##############################################################################
#
# spotsInfoSummary(denaliVariables, spotsDictionary):
#

def spotsInfoSummary(denaliVariables, spotsDictionary):

    spotsConnect      = 0
    spotsConnectHosts = ''
    spotsReset        = 0
    spotsResetHosts   = ''
    spotsTimeout      = 0
    spotsTimeoutHosts = ''
    spotsConRef       = 0
    spotsConRefHosts  = ''
    spotsNoData       = 0
    spotsNoDataHosts  = ''
    spotsUnclass      = 0
    spotsUnclassHosts = ''
    spotsOK           = 0
    spotsOKHosts      = ''

    if denaliVariables["combine"] == True or denaliVariables['noSummary'] == True:
        # update the pingDictionary with the column information (for possible display/output)
        #newColumnData = [[ 1, 'Spots Data', 'Spots Data', 'Spots Data', defaultSpotsWidth]]
        #spotsDictionary.update({"new_column_data":newColumnData})
        return spotsDictionary

    for server in spotsDictionary.keys():
        if spotsDictionary[server].startswith("connection reset"):
            spotsReset += 1
            if spotsResetHosts:
                spotsResetHosts += ',' + server
            else:
                spotsResetHosts += server
            continue
        elif spotsDictionary[server].startswith("connection refused"):
            spotsConRef += 1
            if spotsConRefHosts:
                spotsConRefHosts += ',' + server
            else:
                spotsConRefHosts += server
            continue
        elif spotsDictionary[server] == "connect error":
            spotsConnect += 1
            if spotsConnectHosts:
                spotsConnectHosts += ',' + server
            else:
                spotsConnectHosts += server
            continue
        elif spotsDictionary[server] == "socket timeout":
            spotsTimeout += 1
            if spotsTimeoutHosts:
                spotsTimeoutHosts += ',' + server
            else:
                spotsTimeoutHosts += server
            continue
        elif spotsDictionary[server] == "no data returned":
            spotsNoData += 1
            if spotsNoDataHosts:
                spotsNoDataHosts += ',' + server
            else:
                spotsNoDataHosts += server
            continue
        elif spotsDictionary[server] == "unclassified error":
            spotsUnclass += 1
            if spotsUnclassHosts:
                spotsUnclassHosts += ',' + server
            else:
                spotsUnclassHosts += server
            continue
        else:
            spotsOK += 1
            if spotsOKHosts:
                spotsOKHosts += ',' + server
            else:
                spotsOKHosts += server
            continue

    print
    if len(spotsDictionary.keys()) > 1:
        print " Spots Summary [%d hosts queried]" % len(spotsDictionary.keys())
    else:
        print " Spots Summary [1 host queried]"

    print "   Success             : %d" % spotsOK
    print "   Connection Failure  : %d" % spotsConnect
    print "   Connection Reset    : %d" % spotsReset
    print "   Connection Refused  : %d" % spotsConRef
    print "   Socket Timeout      : %d" % spotsTimeout
    print "   No Data Returned    : %d" % spotsNoData
    print "   Unclassified Errors : %d" % spotsUnclass
    print

    if denaliVariables["summary"] == True:
        # print a list of hosts in each category found
        if spotsOK > 0:
            spotsOKHosts = spotsOKHosts.split(',')
            spotsOKHosts.sort()
            spotsOKHosts = ', '.join(spotsOKHosts)
            print "SPOTS Successful Return [%d]:" % spotsOK
            print "%s" % spotsOKHosts
            print
        if spotsConnect > 0:
            spotsConnectHosts = spotsConnectHosts.split(',')
            spotsConnectHosts.sort()
            spotsConnectHosts = ', '.join(spotsConnectHosts)
            print "SPOTS Connection Error [%d]:" % spotsConnect
            print "%s" % spotsConnectHosts
            print
        if spotsReset > 0:
            spotsResetHosts = spotsResetHosts.split(',')
            spotsResetHosts.sort()
            spotsResetHosts = ', '.join(spotsResetHosts)
            print "SPOTS Connection Reset Error [%d]:" % spotsReset
            print "%s" % spotsResetHosts
            print
        if spotsConRef > 0:
            spotsConRefHosts = spotsConRefHosts.split(',')
            spotsConRefHosts.sort()
            spotsConRefHosts = ', '.join(spotsConRefHosts)
            print "SPOTS Connection Refused Error [%d]:" % spotsConRef
            print "%s" % spotsConRefHosts
            print
        if spotsTimeout > 0:
            spotsTimeoutHosts = spotsTimeoutHosts.split(',')
            spotsTimeoutHosts.sort()
            spotsTimeoutHosts = ', '.join(spotsTimeoutHosts)
            print "SPOTS Socket Timeout Error [%d]:" % spotsTimeout
            print "%s" % spotsTimeoutHosts
            print
        if spotsNoData > 0:
            spotsNoDataHosts = spotsNoDataHosts(',')
            spotsNoDataHosts.sort()
            spotsNoDataHosts = ', '.join(spotsNoDataHosts)
            print "SPOTS No Data Returned [%d]:" % spotsNoData
            print "%s" % spotsNoDataHosts
            print
        if spotsUnclass > 0:
            spotsUnclassHosts = spotsUnclassHosts.split(',')
            spotsUnclassHosts.sort()
            spotsUnclassHosts = ', '.join(spotsUnclassHosts)
            print "SPOTS Unclassified Errors [%d]:" % spotsUnclass
            print "%s" % spotsUnclassHosts
            print

    return



##############################################################################
#
# retrieveSpotsInfo_y(denaliVariables, arguments=[])
#
'''
def retrieveSpotsInfo_y(denaliVariables, arguments=[]):

    spotsDictionary = {}
    serverList      = denaliVariables["serverList"]
    spotsOK         = 0
    spotsConnect    = 0
    spotsTimeout    = 0

    # disable combine until it is fixed for spots
    denaliVariables["combine"] = False

    for server in serverList:
        data = retrieveSocketData(denaliVariables, server, 24210)

        if data == "connect error":
            spotsConnect += 1
        elif data == "socket timeout":
            spotsTimeout += 1
        else:
            spotsOK      += 1

        if denaliVariables["combine"] == False:
            # call the spots print function
            printSpotsData(server.ljust(max_host_length), data, arguments)

        # store the information in a temporary dictionary to
        # pass back and integrate if requested with the main
        # SKMS/CMDB response json
        spotsDictionary.update({server:data})

    if denaliVariables["combine"] == False:
        print
        if len(serverList) > 1:
            print " Spots Summary [%d hosts queried]" % len(serverList)
        else:
            print " Spots Summary [1 host queried]"

        print "   Success            : %d" % spotsOK
        print "   Connection Failure : %d" % spotsConnect
        print "   Socket Timeout     : %d" % spotsTimeout
        print

    return spotsDictionary
'''


##############################################################################
#
# networkInfo(denaliVariables, hostname, printLock, mCommandDict, mCommandList)
#

def networkInfo(denaliVariables, hostname, printLock, mCommandDict, mCommandList):

    # name,model.name,connected_to_device_interface.name,connected_to_device_interface.device.name
    # ./denali.py --hosts=bc* --fields=name,model,switch_port_name,switch_port_device --sort=name

    deviceList = denaliVariables["serverList"]
    scriptLoc  = denaliVariables["denaliLocation"]

    '''
    PID = os.getpid()
    time = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
    fileName  = '/tmp/denali-tmp-%s-%s.newline' % (PID, time)

    authenticationParm = denali_arguments.returnLoginCLIParameter(denaliVariables)

    if authenticationParm == False:
        # punt?  How did we get this far then?  Manual authentication?
        return False
    else:
        try:
            os.remove(fileName)
        except:
            pass

        authenticationParm = authenticationParm[0] + '=' + authenticationParm[1]

        if deviceType == False:     # device name submitted
            denali_call="%s %s --sql=\"DeviceDao:SELECT model,device_id,cage_location,rack_name WHERE name = '%s'\" -o %s --noheaders" % (scriptLoc, authenticationParm, device, fileName)
        else:                       # device_id submitted
            denali_call="%s %s --sql=\"DeviceDao:SELECT model,name,cage_location,rack_name WHERE device_id = '%s'\" -o %s --noheaders" % (scriptLoc, authenticationParm, device, fileName)

        os.system(denali_call)

        try:
            data = open(fileName, 'r')
        except:
            return

    # build server IN / LIKE list.
    denaliVariables["fields"] = "name,model,switch_port_name,switch_port_device"
    (sqlQuery, wildcard) = denali_search.buildHostQuery(denaliVariables)

    print "sqlQuery = %s" % sqlQuery

    sqlQuery = "DeviceDao:SELECT name,model,switch_port_name,switch_port_device WHERE name IN ('%s') ORDER BY name" % (RACK_FIELDS, rackID)

    if constructSQLQuery(denaliVariables, sqlQuery, True) == False:
        pass
    '''



##############################################################################
#
# executeSCP(denaliVariables, hostname, printLock, scpOptions, scpSource, scpDestination, mCommandDict, mCommandList)
#

def executeSCP(denaliVariables, hostname, printLock, scpOptions, scpSource, scpDestination, mCommandDict, mCommandList):

    hostname_color = colors.fg.darkgrey

    #
    # build the parameter list to send
    #

    # first, the command itself -- "scp"
    # use "/usr/bin/scp"?

    if denaliVariables["non_interact"] == False:
        scp_parms = ['/usr/bin/scp']
    else:
        scp_password = '%s' % denaliVariables["non_interact_data"]["password"]
        scp_parms = ['/usr/bin/sshpass', '-p', scp_password, '/usr/bin/scp']

    # if scp options were specified, append them on here (index position 1)
    if scpOptions:
        scp_parms.extend(scpOptions)

    # append the list of files to be copied into a single source parameter
    for parm in scpSource:
        scp_parms.append(parm)

    # append the destination to the parameters
    scp_parms.append(scpDestination)

    if denaliVariables["debug"] == True or command_debug == True:
        print "scp_parms = %s" % scp_parms

    # why python cannot see the progress meter/bar for scp/sftp:
    # http://axb.no/2012/09/07/realtime-scp-output-with-ruby/
    #
    # After some time with mr google, I managed to track down the issue with scp itself.
    # It runs the isatty() function to check and see if the command is being run in a
    # shell. If it is not, then all is quiet! This means ruby, python et al do not get
    # scp output.
    #
    # The solution was to send output to a shell! e.g. ...
    #
    #   scp -r "remote_server:/directory/test_copy" ~/test_files/ > /dev/tty
    #

    # print the hostname and number of files to copy -- to show a notion of progress
    # I haven't found a way to determine the actual progress of a file or files.  It
    # ends when it ends ...
    hostname_buffered = hostname.ljust(max_host_length)
    printLock.acquire()

    # record that a device scp session has begun
    mCommandDict['scp_start_count'] += 1
    mCommandDict['scp_in_flight']   += 1
    progress_string = createProgressIndicator(denaliVariables, hostname, mCommandDict, mCommandList, 'scp_start')

    if denaliVariables['commandProgressBar'] != PROGRESS_BAR:
        # any valid data for '--logoutput' switch, disables scp send display data
        if len(denaliVariables['commandOutput']) != 0:
            print_data = False
        else:
            print_data = True

        if denaliVariables['commandFunction'] == 'scp-pull' or len(scpSource) == 1:
            if scpSource[0].find(':') != -1:
                objectName = scpSource[0].split(':',1)[1]
            else:
                objectName = scpSource[0]
        else:
            objectName = "%i objects" % len(scpSource)

        if print_data == True:
            if denaliVariables["nocolors"] == False:
                print progress_string + hostname_color + "%s" % hostname_buffered + colors.reset + " :  Starting SCP File Copy (%s)" % objectName
            else:
                print progress_string + "%s" % hostname_buffered + " :  Starting SCP File Copy (%s)" % objectName
        else:
            # normally only print data that is requested; however, show when the
            # remaining device count is zero (as a marker)
            if mCommandDict['scp_start_count'] == denaliVariables['commandProgressID']['maxCount']:
                print progress_string
            else:
                sys.stdout.write(progress_string + '\r')
                sys.stdout.flush()

    printLock.release()

    # execute the scp process
    startTime = time.time()
    proc = subprocess.Popen(scp_parms, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.wait()

    return (proc, startTime)



##############################################################################
#
# retrieveFileList(denaliVariables, hostname)
#

def retrieveSCPSourceFileList(denaliVariables, hostname):

    source_files = []
    scpSource    = denaliVariables["scpSource"].strip()
    if denaliVariables["debug"] == True:
        print "scpSource (in)  = %s" % scpSource

    if denaliVariables['commandFunction'] == 'scp-pull' or scpSource[0] == SCP_DEVICE_ID_STRING:
        denaliVariables['scpPullOperation'] = True

        # remove the SCP ID string if included
        if scpSource[0] == SCP_DEVICE_ID_STRING:
            scpSource = scpSource[1:]

        # If the hostname is in the remote file, this code searches for it
        # and replaces it with the hosthame.
        if scpSource.find("%S") != -1:
            # make sure the hostname is the 'short' version, not the long
            if hostname.find('.omniture.com') != -1:
                host_name = hostname.replace('.omniture.com', '')
            elif hostname.find('.adobe.net') != -1:
                host_name = hostname.replace('.adobe.net', '')
            else:
                host_name = hostname

            scpSource = scpSource.replace("%S", host_name)

        if denaliVariables["non_interact"] == False:
            # use the default user that ran this denali session
            source_files = [denaliVariables["userName"] + '@' + hostname + ':' + scpSource]
        else:
            # use a supplied user
            source_files = [denaliVariables["non_interact_data"]["username"] + '@' + hostname + ':' + scpSource]
    else:
        scpSource = denaliVariables["scpSource"].strip().split(',')
        for source_entry in scpSource:
            if len(source_files) == 0:
                source_files = glob.glob(source_entry)
            else:
                files = glob.glob(source_entry)
                source_files.extend(files)

    if denaliVariables["debug"] == True:
        print "scpSource (out) = %s" % source_files

    return source_files



##############################################################################
#
# createSCPDestinationString(denaliVariables, hostname, scpSource)
#

def createSCPDestinationString(denaliVariables, hostname, scpSource):

    scpDestination = denaliVariables["scpDestination"].strip()

    if denaliVariables['commandFunction'] == 'scp-push' or denaliVariables['scpPullOperation'] == False:
        if denaliVariables["non_interact"] == False:
            # use the default user that ran this denali session
            scpDestination = denaliVariables["userName"] + '@' + hostname + ':' + scpDestination
        else:
            # use a supplied user
            scpDestination = denaliVariables["non_interact_data"]["username"] + '@' + hostname + ':' + scpDestination

    if denaliVariables['scpRenameDestFile'] == True:
        # shorten the hostname (remove .omniture.com / .adobe.net)
        if hostname.find('.omniture.com') != -1:
            hostname = hostname.replace('.omniture.com', '')
        elif hostname.find('.adobe.net') != -1:
            hostname = hostname.replace('.adobe.net', '')

        # Rename the remote file so when it lands there aren't conflicts with multiple
        # files of the same name from different devices all overwriting each other.
        if scpDestination == '.':
            scpDestination = ''
        elif scpDestination[-1] == '.':
            scpDestination = scpDestination[:-1]

        # take the last item as the source file (user@device:/source_path/source_file)
        scpSourcePath = scpSource[0].split(':')[-1]

        # break out the path to get the last item
        # the source must have at least one slash '/' character and that
        # character cannot be the last one in the string.  If it's last,
        # then don't split and operate with it.
        if scpSourcePath.find('/') != -1 and scpSourcePath[-1] != '/':
            scpSourceFile = scpSourcePath.split('/')[-1]
            scpSourcePath = scpSourcePath.replace(scpSourceFile, '')
        else:
            scpSourceFile = scpSourcePath
            scpSourcePath = ''

        if scpDestination[-1] != '/':
            scpDestination += '/'

        # append the hostname on the front of the source path and file for the destination
        if denaliVariables['commandFunction'] == 'scp-pull':
            scpSourcePath = ''

        scpDestination = scpDestination + hostname + '-' + scpSourcePath + scpSourceFile

    return scpDestination



##############################################################################
#
# createSCPOptionsString(denaliVariables)
#

def createSCPOptionsString(denaliVariables):

    scpOptions = denaliVariables["scpOptions"].split('-')

    # fix-up the scp options list:
    #  (1) add a dash to each (was removed during the split operation above)
    #  (2) delete the initial entry in the list if it is empty
    if len(scpOptions[0]) == 0:
        scpOptions.pop(0)

    for (index, option) in enumerate(scpOptions):
        scpOptions[index] = '-' + option.strip()

    # MRASEREQ-42098: Add in StrictHostKeyChecking=no
    # This is now a default option requested by development
    scpOptions.append("-o StrictHostKeyChecking=no")

    # put scp in batch mode (disable authentications by default)
    if denaliVariables["non_interact"] == False:
        scpOptions.append("-o BatchMode=yes")

    # if a connect timeout value was specified, include it in the options
    if denaliVariables["connectTimeout"] != -1:
        connect_timeout = "-o ConnectTimeout=%i" % int(denaliVariables["connectTimeout"])
        scpOptions.append(connect_timeout)

        # Note:
        # This setting only applies to hosts that can be resolved that will not allow
        # a connection.
        #
        # This setting does not appear to interfere with or override the base host's
        # resolution timeout.  So, if a host (or hosts) is presented to scp that cannot be
        # resolved, that timeout (at least on my machine) is 15 seconds.  In other words,
        # if 4 hosts are submitted that cannot be resolved, then this process may take at
        # least 60s (4 * 15s) if the app is set to a single process.
        #
        # See "man 5 resolv.conf" for more information

    return scpOptions



##############################################################################
#
# performSCPOperation(denaliVariables, hostname, printLock, mCommandDict, mCommandList)
#

def performSCPOperation(denaliVariables, hostname, printLock, mCommandDict, mCommandList):

    timeDiff = 0

    # If the host doesn't have either 'adobe' or 'omniture' in it, there is
    # a likelihood of the SCP operation failing _IF_ this is a dev/qe host.
    # Add it in.
    if hostname.find("adobe") == -1 and hostname.find("omniture") == -1:
        hostname_orig  = hostname[:]
        hostname      += ".omniture.com"
    else:
        hostname_orig  = hostname[:]

    if len(denaliVariables['scpMultiFileList']) > 0:
        if list(denaliVariables['scpMultiFileList'])[0] == "no files found":
            error_message = "No remote files with name specified [%s] found" % denaliVariables['scpSource']
            return {1:error_message}

        old_scp_source = denaliVariables['scpSource']

        # retrieve a list of all files specified
        scpSource = retrieveSCPSourceFileList(denaliVariables, hostname)
        # make sure there are files to copy -- if not, immediately error out
        if len(scpSource) == 0 and denaliVariables['commandFunction'] != 'scp-pull':
            error_message = "File count: %i  Invalid source file(s) specified" % len(scpSource)
            return {1:error_message}

        # retrieve the scp destination string
        scpDestination = createSCPDestinationString(denaliVariables, hostname, scpSource)

        # retrieve the scp options string
        scpOptions = createSCPOptionsString(denaliVariables)

        if hostname_orig not in denaliVariables['scpMultiFileList']:
            return{1:"File(s) not found"}
        else:
            # [1:] because host meta-data is at position [0] of the list, stored
            # in a list with the count at 0, and size total at 1 (in bytes)
            # {hostname: [[count, size], file1, file2, ...]}
            for filename in denaliVariables['scpMultiFileList'][hostname_orig][1:]:
                if filename.find('/') != -1:
                    filename = filename.split('/')[-1]
                if old_scp_source.find('/') != -1 and old_scp_source[-1] != '/':
                    old_scp_source = old_scp_source.split('/')[-1]

                scpSource[0]   = scpSource[0].replace(old_scp_source, filename)
                scpDestination = scpDestination.replace(old_scp_source, filename)

                if denaliVariables["debug"] == True:
                    print "scp options [%02i]: %s" % (len(scpOptions), scpOptions)
                    print "scp source      : %s" % scpSource
                    print "scp destination : %s" % scpDestination
                    print

                #
                (proc, startTime) = executeSCP(denaliVariables, hostname, printLock, scpOptions, scpSource, scpDestination, mCommandDict, mCommandList)
                #

                timeDifference = time.time() - startTime
                scpReturnCode  = proc.returncode
                if scpReturnCode:
                    printLock.acquire()
                    if denaliVariables['nocolors'] == True:
                        print "SCP ERROR: Host: %s, returned SCP error  %i for file copy of %s" % (hostname, scpReturnCode, filename)
                    else:
                        sys.stdout.write(colors.fg.red + "SCP ERROR:" + colors.reset + " Host: " + colors.fg.yellow + hostname + colors.reset)
                        sys.stdout.write(", returned SCP error [" + colors.fg.lightcyan + str(scpReturnCode) + colors.reset)
                        sys.stdout.write("] for remote file copy of: " + colors.fg.purple + filename + colors.reset + "\n")
                        sys.stdout.flush()
                    printLock.release()

                if denaliVariables["debug"] == True:
                    print "return code     = %s" % proc.returncode
                    print "result (stdout) = %s" % eval(repr(proc.stdout.read()))
                    print "result (stderr) = %s" % eval(repr(proc.stderr.read()))

                # change the filename to be replaced for the next loop
                old_scp_source = filename

                # add up each file copy time for this host
                timeDiff += timeDifference

            # turn the time value into a string
            timeDiff = str(timeDiff)[:6]

    else:

        # retrieve a list of all files specified
        scpSource = retrieveSCPSourceFileList(denaliVariables, hostname)

        # make sure there are files to copy -- if not, immediately error out
        if len(scpSource) == 0 and denaliVariables['commandFunction'] != 'scp-pull':
            error_message = "File count: %i  Invalid source file(s) specified" % len(scpSource)
            return {1:error_message}

        # retrieve the scp destination string
        scpDestination = createSCPDestinationString(denaliVariables, hostname, scpSource)

        # retrieve the scp options string
        scpOptions = createSCPOptionsString(denaliVariables)

        if denaliVariables["debug"] == True:
            print "scp options [%02i]: %s" % (len(scpOptions), scpOptions)
            print "scp source      : %s" % scpSource
            print "scp destination : %s" % scpDestination

        #
        (proc, startTime) = executeSCP(denaliVariables, hostname, printLock, scpOptions, scpSource, scpDestination, mCommandDict, mCommandList)
        #

        timeDiff  = str(time.time() - startTime)[:6]
        scpReturnCode = proc.returncode

        if denaliVariables["debug"] == True:
            print "return code     = %s" % proc.returncode
            print "result (stdout) = %s" % eval(repr(proc.stdout.read()))
            print "result (stderr) = %s" % eval(repr(proc.stderr.read()))

    if scpReturnCode == 0:
        # Successful scp file copy
        return {0:timeDiff}
    else:
        # Error / Failure scp file copy
        return {1:eval(repr(proc.stderr.read()))}



##############################################################################
#
# scpInfoRecordData(denaliVariables, scpDictionary, scpData)
#

def scpInfoRecordData(denaliVariables, scpDictionary, scpData):

    hostname = scpData[0]
    retValue = scpData[1]
    scpDictionary.update({hostname:retValue})

    return scpDictionary



##############################################################################
#
# scpInfoPrint(denaliVariables, scpData, printLock, mCommandDict, mCommandList, printParameters=[])
#

def scpInfoPrint(denaliVariables, scpData, printLock, mCommandDict, mCommandList, printParameters=[]):

    hostname_color    = colors.fg.lightcyan
    success_color     = colors.fg.lightgreen
    failure_color     = colors.fg.lightred
    hostname          = scpData[0]
    result            = scpData[1].keys()[0]
    result_data       = scpData[1][result]
    hostname_buffered = hostname.ljust(max_host_length)

    # the scp command function is unique in that it prints during gathering and after
    # because of this, the printLock must be acquired to ensure the screen doesn't
    # look like garbage with intermingled data printed.
    printLock.acquire()

    mCommandDict['scp_complete_count'] += 1     # increment the completed counter
    mCommandDict['scp_in_flight']      -= 1     # decrement the in-flight count

    if result == 0:
        mCommandDict['scp_success'] += 1
    else:
        mCommandDict['scp_failure'] += 1

    progress_string = createProgressIndicator(denaliVariables, hostname, mCommandDict, mCommandList, 'scp_end')

    if denaliVariables['commandProgressBar'] != PROGRESS_BAR:
        # See if output has been limited to specific types
        if len(denaliVariables['commandOutput']) != 0:
            print_data = False
            if ('failure' in denaliVariables['commandOutput'] and result == 1 or
                'success' in denaliVariables['commandOutput'] and result == 0):
                print_data = True
        else:
            print_data = True

        # Output result from scp copy process
        if print_data == True:
            if denaliVariables["nocolors"] == False:
                sys.stdout.write(progress_string + colors.bold + hostname_color + "%s" % hostname_buffered + colors.reset + " :  Complete SCP File Copy [")
            else:
                sys.stdout.write(progress_string + "%s" % hostname_buffered + " :  Complete SCP File Copy [")
            sys.stdout.flush()

            if result == 0:
                if denaliVariables["nocolors"] == False:
                    print colors.bold + success_color + "SUCCESSFUL" + colors.reset + "] - " + result_data + "s"
                else:
                    print "SUCCESSFUL] - " + result_data + "s"
            else:
                if denaliVariables["nocolors"] == False:
                    print colors.bold + failure_color + "FAILURE" + colors.reset + "]    - " + repr(result_data)
                else:
                    print "FAILURE]    - " + repr(result_data)
        else:
            # normally only print data that is requested; however, show when the
            # remaining device count is zero (as a marker)
            if mCommandDict['scp_complete_count'] == denaliVariables['commandProgressID']['maxCount']:
                print progress_string
            else:
                sys.stdout.write(progress_string + '\r')
                sys.stdout.flush()

    # release the console printing lock
    printLock.release()

    return True



##############################################################################
#
# scpInfoSummary(denaliVariables, scpDictionary)
#

def scpInfoSummary(denaliVariables, scpDictionary):

    scp_success       = 0
    scp_success_hosts = ''
    scp_failure       = 0
    scp_failure_hosts = ''
    time_minimum      = 9999
    time_maximum      = 0
    time_average      = 0
    time_total        = 0

    time_elapsed = time.time() - denaliVariables["scpStartTime"]

    hostnames = scpDictionary.keys()
    hostnames.sort()

    for host in hostnames:
        result = scpDictionary[host].keys()[0]
        if result == 0:
            scp_success += 1
            time_to_complete = float(scpDictionary[host][result])

            # scp average time
            time_average += time_to_complete

            # scp total time -- running total
            time_total += time_to_complete

            # scp minimum time
            if time_to_complete < time_minimum:
                time_minimum = time_to_complete

            # scp maximum time
            if time_to_complete > time_maximum:
                time_maximum = time_to_complete

            # append successful host name to string list
            if scp_success_hosts:
                scp_success_hosts += ',' + host
            else:
                scp_success_hosts += host

        else:
            scp_failure += 1

            # append failure host name to string list
            if scp_failure_hosts:
                scp_failure_hosts += ',' + host
            else:
                scp_failure_hosts += host

    # calculate the average time spent doing the scp options
    # on a per host basis (for successful copies only)
    if scp_success > 0:
        time_average = time_average / scp_success
    else:
        time_average = 0

    if denaliVariables['noSummary'] == False:
        print
        if len(hostnames) > 1:
            print " SCP Summary  [ %d hosts accessed ]" % len(hostnames)
        else:
            print " SCP Summary  [ 1 host queried ]"

        print "   Success        : %d"  % scp_success
        print "   Failure        : %d"  % scp_failure
        print "   Time (min)     : %ss" % time_minimum
        print "   Time (max)     : %ss" % time_maximum
        print "   Time (avg)     : %ss" % time_average
        print "   Time (total)   : %ss" % time_total
        print "   Time (elapsed) : %ss" % time_elapsed
        print

    if denaliVariables["summary"] == True:
        print
        # print a list of hosts in each category found
        if len(scp_success_hosts) > 0:
            # the 'split' is used because the host list is a comma separated
            # string
            if denaliVariables['nocolors'] == True:
                print "Successful SCP [%d]:" % len(scp_success_hosts.split(','))
            else:
                print colors.bold + colors.fg.lightgreen + "Successful SCP [%d]:" % len(scp_success_hosts.split(',')) + colors.reset
            print "%s" % scp_success_hosts
            print
        if len(scp_failure_hosts) > 0:
            if denaliVariables['nocolors'] == True:
                print "Failure SCP [%d]:" % len(scp_failure_hosts.split(','))
            else:
                print colors.bold + colors.fg.lightred + "Failure SCP [%d]:" % len(scp_failure_hosts.split(',')) + colors.reset
            print "%s" % scp_failure_hosts
            print

    if scp_failure_hosts > 0:
        return False
    else:
        return True



##############################################################################
#
# createLogDirectories(denaliVariables)
#
#   This function determines if the "pdsh_log" or "ssh_log" directories are
#   present in the current user's ~/.denali directory.  If one or both are not,
#   create them.
#

def createLogDirectories(denaliVariables):

    oStream = denaliVariables['stream']['output']
    iStream = denaliVariables['stream']['input']

    home_directory = denali_utility.returnHomeDirectory(denaliVariables)

    # if the username isn't specified, get it from the environment or have the
    # user type it in
    if len(denaliVariables["userName"]) == 0:
        if len(os.environ['USER']) > 0:
            denaliVariables["userName"] = os.environ['USER']
        elif len(os.environ['USERNAME']) > 0:
            denaliVariables["userName"] = os.environ['USERNAME']
        else:
            oStream.write("\nSKMS Username required\n")
            oStream.flush()
            denaliVariables["userName"] = getpass._raw_input("  Username : ", oStream, iStream)

    # if the user didn't define a log path, go with the default settings
    if len(denaliVariables['logPath']) == 0:
        pdsh_file_path = home_directory + "/.denali" + pdsh_log_directory
        ssh_file_path  = home_directory + "/.denali" + ssh_log_directory
    else:
        pdsh_file_path = denaliVariables['logPath'] + pdsh_log_directory
        ssh_file_path  = denaliVariables['logPath'] + ssh_log_directory

    if os.path.isdir(home_directory) == False:
        oStream.write("Denali Error:  Directory " + home_directory + " doesn't exist.\n")
        return False

    # ensure the /home/user/.denali directory exists -- if not, create it
    denali_directory = home_directory + "/.denali"
    try:
        if os.path.isdir(denali_directory) == False:
            os.makedirs(denali_directory)

        # make the pdsh_log directory now if it doesn't exist
        if os.path.isdir(pdsh_file_path) == False:
            os.makedirs(pdsh_file_path)

        # make the ssh_log directory now if it doesn't exist
        if os.path.isdir(ssh_file_path) == False:
            os.makedirs(ssh_file_path)
    except OSError as e:
        oStream.write("Denali Error:  Directory creation failed.  %s\n" % str(e))
        if len(denaliVariables['logPath']):
            fileName = "%s/.denali/config" % home_directory
            oStream.write("            :  The config file \"log_path\" setting may be incorrect (typically %s).\n" % fileName)
        return False

    # include the log file path in denaliVariables with existing data
    if denaliVariables['pdsh_log_file'] == 'denali-pdsh_log':
        denaliVariables["pdsh_log_file"] = pdsh_file_path + '/' + denaliVariables["pdsh_log_file"]
    if denaliVariables['ssh_log_file'] == 'denali-ssh_log':
        denaliVariables["ssh_log_file"]  = ssh_file_path  + '/' + denaliVariables["ssh_log_file"]

    if denaliVariables["debug"] == True:
        oStream.write("PDSH log_file_path = %s\n" % pdsh_file_path)
        oStream.write("SSH log file path  = %s\n" % ssh_file_path)

    return True



##############################################################################
#
# retrieveInteractivePDSHCommand(denaliVariables)
#
#   User applied the "--pci" switch to Denali which requests an interactive
#   session where the PDSH command to be executed is entered manually.
#

def retrieveInteractivePDSHCommand(denaliVariables):

    oStream = denaliVariables['stream']['output']
    iStream = denaliVariables['stream']['input']

    response = getpass._raw_input("Enter PDSH Command: ", oStream, iStream)

    if len(response) > 1:
        denaliVariables["pdshCommand"] = response
        return True
    else:
        oStream.write("Denali Error:  Invalid PDSH command string entered, exiting program.")
        return False



##############################################################################
#
# determinePDSHFanoutValue(denaliVariables, pdsh_hosts, fanoutValue)
#

def determinePDSHFanoutValue(denaliVariables, pdsh_hosts, fanoutValue):

    # remove the percentage sign(s)
    fanout_value = fanoutValue.replace('%', '')
    if fanout_value.isdigit() == False:
        # incorrectly formatted fanout value -- do not continue
        print colors.reset + "\nDenali Syntax Error:  The PDSH variable fanout value [-f %s] is incorrectly formatted.  Use -f <#>%%." % fanoutValue
        denali_search.cleanUp(denaliVariables)
        exit(1)

    multiplier       = float(fanout_value) / 100
    device_count     = len(pdsh_hosts)
    new_fanout_value = multiplier * device_count

    if int(new_fanout_value) == 0:
        new_fanout_value = 1

    if denaliVariables['debug'] == True:
        print "Current fanoutValue   = %s" % fanout_value
        print "Total number of hosts = %s" % device_count
        print "Calculated multiplier = %s" % multiplier
        print "New fanout value      = %d" % new_fanout_value

    return new_fanout_value



##############################################################################
#
# createPDSHOptionsString(denaliVariables, pdsh_hosts)
#

def createPDSHOptionsString(denaliVariables, pdsh_hosts):

    pdshOptions = denaliVariables["pdshOptions"].split('-')

    # fix-up the pdsh options list:
    #  (1) add a dash to each (was removed during the split operation above)
    #  (2) delete the initial entry in the list if it is empty
    if len(pdshOptions[0]) == 0:
        pdshOptions.pop(0)

    for (index, option) in enumerate(pdshOptions):
        pdshOptions[index] = '-' + option.strip()

        # Check for a variable fanout value
        if option.startswith('f ') and option.find('%') != -1:
            denaliVariables['pdshVariableFanout'] = True
            fanoutValue = option[2:]
            calculatedFanoutValue = determinePDSHFanoutValue(denaliVariables, pdsh_hosts, fanoutValue)
            if not len(denaliVariables['devServiceVerifyData']) > 1:
                pdshOptions[index] = "-f %i" % calculatedFanoutValue
            else:
                pdshOptions.remove("-" + option)

    # Check and see if a default process setting (used with pdsh separator code)
    # was configured automatically.  If so, set it unless the user declared a
    # specific "-f <num>"
    if denaliVariables['pdshSeparate'] != False:
        if denaliVariables['pdshVariableFanout'] == True:
            denaliVariables['pdshSeparate']['maximum_processes_per_segment'] = -1

        else:
            max_proc_per_segment = denaliVariables['pdshSeparate'].get('maximum_processes_per_segment', None)
            if max_proc_per_segment != -1 and max_proc_per_segment is not None:
                if type(max_proc_per_segment) == str:
                    # this could be a string "Suggested maximum fanout" -- handle this case
                    max_proc_per_segment = max_proc_per_segment.split()[-1].strip()
                # only used if user didn't give a fanout value
                num_procs = "-f %i" % int(max_proc_per_segment)
                for option in pdshOptions:
                    if option.split()[0] == '-f':
                        currentFanout = option.split()[1]
                        if int(currentFanout) > int(max_proc_per_segment):
                            # -f option exists -- (re)set max_processes_per_segment to identify difference
                            denaliVariables['pdshSeparate']['maximum_processes_per_segment'] = "Suggested maximum fanout: -f %s" % max_proc_per_segment
                        else:
                            denaliVariables['pdshSeparate']['maximum_processes_per_segment'] = -1
                        break
                    elif option.startswith('-f'):
                        # potentially an incorrectly typed -f parameter -- fix it
                        currentFanout = option[2:]
                        # remove the current one, and (re)add the correct syntax
                        pdshOptions.remove(option)
                        pdshOptions.append("-f %s" % currentFanout)
                        if int(currentFanout) > int(max_proc_per_segment):
                            # -f option exists -- (re)set max_processes_per_segment to identify difference
                            denaliVariables['pdshSeparate']['maximum_processes_per_segment'] = "Suggested maximum fanout: -f %s" % max_proc_per_segment
                        else:
                            denaliVariables['pdshSeparate']['maximum_processes_per_segment'] = -1
                        break
                else:
                    # Before automatically adding the programmtically determined fanout value,
                    # check and see if the user specified a num_procs value, if so that should
                    # be used instead.
                    if denaliVariables["num_procs"] != -1:
                        num_procs = "-f %i" % int(denaliVariables["num_procs"])
                        for option in pdshOptions:
                            if option.split()[0] == '-f':
                                break
                        else:
                            pdshOptions.append(num_procs)
                            if int(denaliVariables["num_procs"]) > int(max_proc_per_segment):
                                # -f option exists -- (re)set max_processes_per_segment to identify difference
                                denaliVariables['pdshSeparate']['maximum_processes_per_segment'] = "Suggested maximum fanout: -f %s" % max_proc_per_segment
                            else:
                                denaliVariables['pdshSeparate']['maximum_processes_per_segment'] = -1
                    else:
                        pdshOptions.append(num_procs)

    #
    # Number of processes (default fanout is 32 processes if not specified)
    #
    # if a number for processes was specified, include it in the options
    if denaliVariables["num_procs"] != -1:
        num_procs = "-f %i" % int(denaliVariables["num_procs"])
        for option in pdshOptions:
            if option.split()[0] == '-f':
                break
        else:
            pdshOptions.append(num_procs)

    #
    # Process timeout (default value used if not specified)
    #
    # if a remote process timeout value was specified, include it in the options
    if denaliVariables["processTimeout"] != -1:
        process_timeout = "-u %i" % int(denaliVariables["processTimeout"])
    else:
        # no timeout specified, use the default setting
        process_timeout = "-u %i" % PDSH_PROCESS_TIMEOUT

    # make sure an existing connection timeout value wasn't already specified
    for option in pdshOptions:
        if option.split()[0] == '-u':
            break
    else:
        pdshOptions.append(process_timeout)

    #
    # Connect timeout
    #
    # if a connect timeout value was specified, include it in the options
    if denaliVariables['connectTimeout'] != -1:
        connect_timeout = "-t %i" % int(denaliVariables['connectTimeout'])

        for option in pdshOptions:
            if option.split()[0] == "-t":
                break
        else:
            pdshOptions.append(connect_timeout)

    return pdshOptions



##############################################################################
#
# determineDataCenter(device_list)
#

def determineDataCenter(device_list):

    saved_data_center = ''

    for host in device_list:
        data_center = host.split('.')[-1]
        if data_center == "net" or data_center == "com":
            # the '.' is added here because of mirror1.or1 causing confusion
            location = host.find('.' + host.split('.')[1]) + 1
            if location != -1:
                data_center = host[location:]
            else:
                if data_center == "net":
                    data_center = host.split('.', 1)[1]
                else:
                    data_center = "omniture.com"

        if len(saved_data_center) == 0:
            saved_data_center = data_center
        else:
            if data_center != saved_data_center:
                return None

    return '.' +  saved_data_center



##############################################################################
#
# separateHostnameAndData(denaliVariables, output_line, data_center)
#
#   This function looks at all return data and attempts to determine if the
#   data represents an error/failure (rcode = 1) or a successful response
#   (rcode = 0).  rcode=2 means a normal return line of just data.
#
#   After this is done, the hostname is appended with the data center name
#   so as to make log searching easier.
#

def separateHostnameAndData(denaliVariables, output_line, data_center, stdout=True):

    # determine if this line is an error or not, and pull
    # out the hostname in the process

    # list of ssh error to ignore from stderr
    ssh_stderr_errors = [
                            '@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@',
                            'NOTICE TO USERS',
                            'This system is the property of Adobe',
                            'All Data is to be treated as Confidential',
                            'be disclosed in accordance with Adobe policies',
                            'this system and access to this system',
                            'policies and may be intercepted, monitored',
                            'Unauthorized or improper use of this system may result in',
                            'administrative disciplinary action and civil',
                            'By continuing to use this system you indicate',
                            'consent to these terms and conditions of use',
                            'LOG OFF IMMEDIATELY if you do not agree to the conditions',
                            'stated in this warning',

                            'IT IS POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!',
                            'Someone could be eavesdropping on you right now',
                            'It is also possible that a host key has just been changed',
                            'The fingerprint for the RSA key sent by the remote host is',
                            'The fingerprint for the ECDSA key sent',
                            'SHA256',
                            'Please contact your system administrator',
                            'Add correct host key in',
                            'Offending RSA key in',
                            'Offending ECDSA key in',
                            'Offending key for IP in',
                            'Matching host key in',
                            'You can use following command to remove the offending key',
                            'ssh-keygen -R',
                            'Password authentication is disabled to avoid',
                            'Keyboard-interactive authentication is disabled to avoid',

                            'WARNING: POSSIBLE DNS SPOOFING DETECTED!',
                            'The RSA host key for',
                            'and the key for the corresponding IP address',
                            'is unknown. This could either mean that',
                            'DNS SPOOFING is happening or the IP address for the host',
                            'and its host key have changed at the same time',

                            'Password change required but no TTY available',
                            'CentOS release',
                            'Kernel ',

                            'Warning: Permanently added', # <ip_address> (RSA) to the list of known hosts.

                            'sending SIGTERM to ssh',
                            'sending signal 15 to',
                        ]

    if output_line.startswith('pdsh@'):
        output          = output_line.split(':', 2)
        host            = output[1].strip()
        data_line       = output[2].rstrip()
        data_line_strip = output[2].strip()
    elif denaliVariables['commandFunction'] == 'ssh':
        data_line       = output_line.rstrip()
        data_line_strip = output_line.strip()
        host            = data_center                     # hostname passed through data_center with 'ssh'
        data_center     = determineDataCenter([host])
    else:
        try:
            output          = output_line.split(':', 1)
            host            = output[0].strip()
            data_line       = output[1].rstrip()
            data_line_strip = output[1].strip()
        except:
            if output_line.find('sending SIGTERM') != -1:
                data_line       = output_line.rstrip()
                data_line_strip = output_line.strip()
                host            = output_line.split()[-1]
            elif output_line.find('sending signal 15') != -1:
                data_line       = output_line.rstrip()
                data_line_strip = output_line.strip()
                host            = output_line.split()[4]
            else:
                if len(output_line) > 0:
                    # print this out for debugging purposes
                    print "Unclassified data line = %s" % output_line.strip()

                    # need to handle this problem here - or it will propagate
                    return (1, 'UNKNOWN', output_line.strip())
                else:
                    # empty line given by pdsh/ssh; no server name ... no nothing.
                    # at this point there is nothing in the line of text that can
                    # identify it to us ... suppress it for now.
                    return (1, 'MISSING_HOSTNAME', 'Empty string from host')

    # With the pdsh fall-through execution code-path, the hostname is prepended
    # with the username ... remove the "username@" characters.
    if host.find('@') != -1:
        if denaliVariables['non_interact'] == True and 'username' in denaliVariables['non_interact_data']:
            ni_username = denaliVariables['non_interact_data']['username'] + '@'
        else:
            # non-interactive code-path, and still an '@' in the hostname portion
            # try to determine the reason and remove it if possible
            ni_username = denaliVariables['userName'] + '@'

        # there is a case where the ni_username isn't found ... handle it.
        if host.find(ni_username) != -1:
            host = host.split(ni_username, 1)[1]
        elif len(host):
            # if the host has a length, then it is what it is
            pass
        else:
            # If neither of the above checks are true, then designate a hostname
            #
            # I thought about putting a counter on the name; however, this function
            # receives every line from every host ... so the counter would actually
            # just be a count of returned lines from hosts (without a hostname), not
            # a way to differentiate one host from another.  So, for now it will stay
            # as a generic empty hostname designator name until a better method is
            # needed.
            host = "<Empty Hostname>"

    if host.find('.omniture.com') != -1:
        loc_domain = host.rfind('.', 0, len(host) - 5)
        host       = host[0:loc_domain]
    elif host.find('.adobe.net') != -1:
        data_center = determineDataCenter([host])
        # .adobe.net hosts can have multiple periods:  vcd-10-90-206-95.lon5.cpt.adobe.net
        # Split on the first period, and take that as the hostname, with the rest being
        # the host's domain name already as the "data_center"
        host = host.split('.', 1)[0]

    if (data_line_strip.startswith('result = 1') or
        data_line_strip.startswith('return = 1') or
        data_line_strip.startswith('return 1') or
        data_line_strip.startswith('result 1')):
        # failure / error
        rcode = 1

    elif (data_line_strip.startswith('result = 0') or
        data_line_strip.startswith('return = 0') or
        data_line_strip.startswith('return 0') or
        data_line_strip.startswith('result 0')):
        # success
        rcode = 0

    elif data_line_strip.find('ssh exited with exit code') != -1:
        # ssh error exit code -- mark as a failure/error
        rcode = 255

    elif data_line_strip.find('banner exchange') != -1:
        # ssh time out during banner exchange
        rcode = 255
        data_line = "SSH Connection attempt timed out during banner exchange. Exit code 255"

    elif data_line_strip.lower().find('could not resolve hostname') != -1:
        # ssh resolve failed
        rcode = 255
        data_line = "SSH could not resolve hostname; name or service not known. Exit code 255"

    elif (data_line_strip.find('change your password') != -1 or data_line_strip.find('password has expired') != -1):
        # ssh permission denied (public key or password)
        rcode = 4
        data_line = "SSH connection refused, permission denied (public key / password). Exit code 255"

    elif data_line_strip.lower().find('closed by remote host') != -1:
        # connection closed by remote host
        rcode = 255
        data_line = "SSH connection closed by remote host. Exit code 255"

    elif data_line_strip.find(': Connection refused') != -1:
        rcode = 255
        loc_s = data_line_strip.rfind('port')
        loc_e = data_line_strip.rfind(':')
        port  = data_line_strip[loc_s:loc_e]
        data_line = "SSH Connection refused  (%s): Exit code 255" % port

    elif data_line_strip.find(': Connection reset by peer') != -1:
        rcode = 255
        data_line += ". Exit code 255"

    elif data_line_strip.find(': Connection timed out') != -1:
        # ssh timed out the connection -- mark as a failure
        rcode = 255
        loc_s = data_line_strip.rfind('port')
        loc_e = data_line_strip.rfind(':')
        port  = data_line_strip[loc_s:loc_e]
        data_line = "SSH Connection attempt timed out (%s): Exit code 255" % port

    else:
        if stdout == False:
            for error_string in ssh_stderr_errors:
                if output_line.find(error_string) != -1:
                    rcode = 1
                    data_line = ""
                    break

            # stderr code path -- only allow specific lines through
            if (output_line.find('REMOTE HOST IDENTIFICATION HAS CHANGED') != -1 or
                output_line.find('differs from the key for the IP address') != -1):
                data_line = "SSH host keys have changed."
                rcode = 3
            else:
                # Clear out the data_line so it won't be output
                # This only allows categorized errors to hit the screen
                # Comment the next line out to allow everything through,
                # classified as an error
                #data_line = ""
                rcode = 5
        else:
            # unknown -- mark as 'normal'
            rcode = 2

    # add in the data center if necessary
    if data_center is not None:
        add_omniture = False
        if data_center.endswith('.omniture.com'):
            data_center = data_center.replace('.omniture.com', '')
            add_omniture = True
        if host.endswith(data_center) == False:

            # check for pdsh debug lines -- don't add an extension
            # otherwise handle as normal
            if output_line.strip().startswith("Connect time:  Avg"):
                hostname = "Connect time"
            elif output_line.strip().startswith("Command time:  Avg"):
                hostname = "Command time"
            elif output_line.strip().startswith("Failures:  "):
                hostname = "Failures"
            else:
                hostname = host + data_center
                if add_omniture == True:
                    hostname += ".omniture.com"
        else:
            hostname = host
    else:
        hostname = host

    # make sure the hostname given here is unique, or it will
    # create recording (data) issues with multiple hosts and
    # the same data
    hostname = ensureUniqueHostname(denaliVariables, hostname)

    return (rcode, hostname, data_line)



##############################################################################
#
# ensureUniqueHostname(denaliVariables, hostname)
#
#   This function helps squash hostnames that are duplicated internally and
#   then presented externally as 2 (or more) devices.  This is really confusing
#   to the user.
#
#   Example:
#       denali -h db35.dev.ut1 db29.dev.ut1 -c pdsh --pc="uptime"
#
#   Before this code, the above would return the following:
#     db29.ut1:   08:31:35 up 142 days, 14:17,  0 users,  load average: 0.48, 0.38, 0.34
#     db35.ut1:   08:31:35 up 32 days, 21:20,  0 users,  load average: 0.01, 0.02, 0.05
#     db35.dev.ut1:  No data returned. Success assumed.
#     db29.dev.ut1:  No data returned. Success assumed.
#
#   The first two have the wrong name with the correct data.
#   The second two have the correct name with the wrong data.
#
#   This only happens if ALL submitted devices are from the exact same data center.
#   If one (ore more) devices is different, then the existing code works just fine.
#
#   After the hostname is returned, the code does a search for hidden devices, and
#   based on what was submitted initially, and what was output, it finds two more
#   devices that didn't report data, so it prints them out (which confuses everything)
#   believing they are hidden devices.  The hidden search code is doing its job correctly,
#   but unfortunately it is presenting confusing data.
#
#   This function will make sure the hostname is unique, so the "hidden" search code
#   doesn't believe it is hidden.
#

def ensureUniqueHostname(denaliVariables, hostname):

    # look and see if the hostname found is one that was given
    if hostname not in denaliVariables['serverList']:
        # See if the device name has "omniture.com/adobe.net", etc., at the end
        # If so, remove it.
        if hostname.endswith('.omniture.com') == True:
            hostname = hostname[:-13]
        elif hostname.endswith('.adobe.net') == True:
            hostname = hostname[:-10]

        # look at the characters before the first period and find a match
        # in the device list
        if len(denaliVariables['hostNameCheck']) == 0:
            for (index, device) in enumerate(denaliVariables['serverList']):
                if device.find('.') != -1:
                    device_name = device.split('.', 1)[0]
                else:
                    device_name = device
                denaliVariables['hostNameCheck'].update({device_name:device})

        if len(denaliVariables['hostNameCheck']):
            if hostname.find('.') != -1:
                device_hostname = hostname.split('.', 1)[0]
            else:
                device_hostname = hostname

            if device_hostname in denaliVariables['hostNameCheck'].keys():
                hostname = denaliVariables['hostNameCheck'][device_hostname]

    return hostname



##############################################################################
#
# determineNumberOfPDSHCommands(denaliVariables)
#

def determineNumberOfPDSHCommands(denaliVariables):

    commands = denaliVariables["pdshCommand"]
    app_count_singles  = commands.count(';')
    app_count_singles += 1
    app_count_ands     = commands.count('&&')
    app_count_ors      = commands.count('||')
    app_count_total    = app_count_singles + app_count_ands + app_count_ors

    # ls -l ; ls -l | wc -l ; ls /dev/usb/ && ls /dev/disk/by-id || ls /dev/disk/by-path
    # 5 commands --
    #   #1, #2, #3 should always execute --> these are "singles"   3
    #   #4 executes only if #3 succeeds  --> 4 is an "and"         1
    #   #5 executes only if #4 fails     --> 5 is an "or"          1   "sssao"
    #
    # ls -l && ls -l | wc -l && ls /dev/usb/ || ls /dev/disk/by-id/ || ls /dev/disk/by-path
    # saaoo -- [s]ingle / [a]nd / [a]nd/ [o]r / [o]r

    command_order = 's'

    for (index, char) in enumerate(commands):
        if char == ';':
            command_order += 's'
        elif char == '&':
            if commands[(index + 1)] == '&':
                command_order += 'a'
        elif char == '|':
            if commands[(index + 1)] == '|':
                command_order += 'o'

    if denaliVariables["debug"] == True:
        print "command_order = %s" % command_order

    if app_count_total == 0:
        return { "singles": 1,
                 "ands"   : 0,
                 "ors"    : 0,
                 "order"  :'s',
                 "total"  : app_count_total     }
    else:
        return { "singles": app_count_singles,
                 "ands"   : app_count_ands,
                 "ors"    : app_count_ors,
                 "order"  : command_order,
                 "total"  : app_count_total     }



##############################################################################
#
# adjustHostnameForUse(denaliVariables, pdsh_hosts)
#
#   If the host doesn't have either 'adobe' or 'omniture' in it, there is
#   a likelihood of the SCP operation failing _IF_ this is a dev/qe host.
#   Add it in.
#

def adjustHostnameForUse(denaliVariables, pdsh_hosts):

    for (index, hostname) in enumerate(pdsh_hosts):
        if hostname.find("adobe") == -1 and hostname.find("omniture") == -1:
            pdsh_hosts[index] += ".omniture.com"

    return pdsh_hosts



##############################################################################
#
# printHostsAndCommands(denaliVariables, pdsh_command)
#

def printHostsAndCommands(denaliVariables, pdsh_command):

    maxHostWidth = 0
    oStream      = denaliVariables['stream']['output']
    host_list    = denaliVariables['hostCommands'].keys()
    host_list.sort()

    # grab the number of expected commands
    commands_expected = denaliVariables['pdshCommand'].count('%s')

    # get the maximum host width
    for host in host_list:
        hostWidth = len(host)
        if hostWidth > maxHostWidth:
            maxHostWidth = hostWidth

    maxHostWidth += 3

    # loop through each host and substitute the command/s in the proper place for display
    for host in host_list:
        if host == "active":
            continue

        # copy the pdsh command for substitution
        pdsh_command_copy = pdsh_command[:]

        # loop through each host command and replace where the %s is found
        for command in denaliVariables['hostCommands'][host]:
            pdsh_command_copy = pdsh_command_copy.replace('%s', command, 1)
        oStream.write("  %s : %s\n" % (host.ljust(maxHostWidth), pdsh_command_copy))
    oStream.flush()

    return True



##############################################################################
#
# printGroupedHostnamesInColumns(denaliVariables, hostnames)
#
#   This function prints out a group of hostnames in columns (the number of
#   which is determined during execution).
#
#   hostnames is a 'List' of server/device names.
#

def printGroupedHostnamesInColumns(denaliVariables, hostnames):

    oStream = denaliVariables['stream']['output']

    if hostnames > 0:
        hostCount        = 0
        maxHostWidth     = 0
        printingMaxWidth = 80

        # determine the maximum width (num of characters) for the
        # largest host name; adjust the printing accordingly
        for host in hostnames:
            hostWidth = len(host)
            if hostWidth > maxHostWidth:
                maxHostWidth = hostWidth

        # spacing between printed devices
        maxHostWidth += 3

        # how many devices to print on each row (integer division)
        hostsToPrint  = printingMaxWidth / maxHostWidth

        for (index, host) in enumerate(hostnames):
            if hostCount == 0:
                # indentation at the beginning
                oStream.write("   ")
            oStream.write("%s" % host.ljust(maxHostWidth))
            hostCount += 1
            if hostCount > hostsToPrint and (len(hostnames) > (index+1)):
                hostCount = 0
                oStream.write('\n')

    oStream.write('\n')
    oStream.flush()

    return True



##############################################################################
#
# generateProgressNumbers(denaliVariables)
#

def generateProgressNumbers(denaliVariables):

    maxCount = len(denaliVariables['serverList'])
    maxChars = len(str(maxCount))
    maxCount = str(maxCount).rjust(maxChars)

    #if denaliVariables['pdshSeparate'] != False:
        # doing a separation pdsh run
    #    for device in denaliVariables['serverList']:
    #        pass
    #else:
    for (index, device) in enumerate(denaliVariables['serverList']):
        currentCount = str(index + 1).rjust(maxChars)
        progress_string = currentCount + '/' + maxCount
        denaliVariables['commandProgressID'].update({device:{'indexID'         : currentCount,
                                                             'progress_string' : progress_string}})

    denaliVariables['commandProgressID'].update({'maxCount':len(denaliVariables['serverList'])})

    error_string = ('?' * maxChars) + '/' + maxCount
    denaliVariables['commandProgressID'].update({'host_not_found': error_string})

    return True



##############################################################################
#
# printSSHOptions(denaliVariables, retry_command)
#

def printSSHOptions(denaliVariables, retry_command):

    oStream = denaliVariables['stream']['output']

    if denaliVariables["non_interact"] == False:
        # use the default user that ran this denali session
        username = denaliVariables["userName"]
    else:
        # use a supplied user
        username = denaliVariables["non_interact_data"]["username"]

    # gather SCP options to show
    options = createSSHOptionsString(denaliVariables)

    if denaliVariables['nocolors'] == True:
        ccode = printCommandOptions(denaliVariables, options)
        oStream.write("SSH User Account               : %s\n" % username)
        if denaliVariables['commandRetry'] > 0:
            oStream.write("Retry Failed Device(s)         : Enabled")
            if denaliVariables['commandRetry'] > 1:
                oStream.write("  (retry count: %s)\n" % denaliVariables['commandRetry'])
            else:
                oStream.write('\n')
            if len(retry_command) > 0:
                oStream.write("SSH Retry Command              : %s\n" % retry_command)
        oStream.write("Number of Targeted Devices     : %d\n\n" % len(denaliVariables['serverList']))
        oStream.write("Available options are:\n")
        oStream.write(" -> Accept command(s), execute SSH          (enter 'YES')\n")
        oStream.write(" -> Show [t]argeted device list             (enter  't' )\n")

    else:
        ccode = printCommandOptions(denaliVariables, options)
        oStream.write("SSH User Account               : %s" % colors.fg.yellow + username + colors.reset + '\n')
        if denaliVariables['commandRetry'] > 0:
            oStream.write("Retry Failed Device(s)         : %s" % colors.fg.white + "Enabled" + colors.reset)
            if denaliVariables['commandRetry'] > 1:
                oStream.write("  (retry count: " + colors.fg.red + str(denaliVariables['commandRetry']) + colors.reset + ")\n")
            else:
                oStream.write('\n')
            if len(retry_command) > 0:
                oStream.write("SSH Retry Command              : " + colors.fg.blue + retry_command + colors.reset + '\n')
        oStream.write("Number of Targeted Devices     : " + colors.fg.lightred + str(len(denaliVariables['serverList'])) + colors.reset + '\n\n')
        oStream.write("Available options are:\n")
        oStream.write(" -> Accept command(s), execute SSH          (enter '" + colors.fg.cyan + "YES" + colors.reset + "')\n")
        oStream.write(" -> Show [t]argeted device list             (enter  '" + colors.fg.cyan + "t"   + colors.reset + "' )\n")


    return



##############################################################################
#
# printPDSHOptions(denaliVariables, options, serverList)
#

def printPDSHOptions(denaliVariables, options, serverList):

    segmented_pdsh = False

    oStream = denaliVariables['stream']['output']

    if denaliVariables['pdshSeparate'] != False:
        targeted_devices = len(serverList)
        segmented_pdsh   = True
    else:
        targeted_devices = len(denaliVariables['serverList'])

    if denaliVariables['pdshVariableFanout'] == True:
        for (index, item) in enumerate(options):
            if item.startswith("-f "):
                options[index] = "-f <variable>"

    pdsh_options = ' '.join(options)

    if denaliVariables['nocolors'] == True:
        if segmented_pdsh == True:
            oStream.write("PDSH Command Option(s)/Segment : %s" % pdsh_options)
            if denaliVariables['pdshSeparate']['maximum_processes_per_segment'] != -1:
                if (type(denaliVariables['pdshSeparate']['maximum_processes_per_segment']) == str and
                    denaliVariables['pdshSeparate']['maximum_processes_per_segment'].startswith('Suggested')):
                    oStream.write("  [%s]" % denaliVariables['pdshSeparate']['maximum_processes_per_segment'])
                else:
                    oStream.write("  [-f fanout value programmatically determined]")
            oStream.write('\n')
        else:
            ccode = printCommandOptions(denaliVariables, options)
    else:
        if segmented_pdsh == True:
            oStream.write("PDSH Command Option(s)/Segment : %s" % colors.fg.lightcyan + pdsh_options + colors.reset)
            if denaliVariables['pdshSeparate']['maximum_processes_per_segment'] != -1:
                if (type(denaliVariables['pdshSeparate']['maximum_processes_per_segment']) == str and
                    denaliVariables['pdshSeparate']['maximum_processes_per_segment'].startswith('Suggested')):
                    oStream.write("  [%s]" % denaliVariables['pdshSeparate']['maximum_processes_per_segment'])
                else:
                    oStream.write("  [-f fanout value programmatically determined]")
            oStream.write('\n')
        else:
            ccode = printCommandOptions(denaliVariables, options)



##############################################################################
#
# printPDSHDeviceInformation(denaliVariables, segmentList, serverList, retry_command)
#

def printPDSHDeviceInformation(denaliVariables, segmentList, serverList, retry_command):

    segmented_pdsh = False

    oStream = denaliVariables['stream']['output']

    if denaliVariables['pdshSeparate'] != False:
        targeted_devices = len(serverList)
        segmented_pdsh   = True
    else:
        targeted_devices = len(denaliVariables['serverList'])

    if denaliVariables['nocolors'] == True:
        if denaliVariables['devServiceVerify'] == True:
            verification_host_count = int(denaliVariables['devServiceVerifyData']['verify_host_count'])
            verification_command    = denaliVariables['devServiceVerifyData'].get('verify_command', 'Default Health Check')
            oStream.write("Device Verification            : True\n")
            oStream.write("  Verification Health Command  : %s\n" % verification_command)
            if segmented_pdsh == True:
                string_data = ' (per segment)\n'
            else:
                string_data = '\n'
            oStream.write("  Verification Host Count      : %s" % verification_host_count + string_data)

        if denaliVariables['commandRetry'] > 0:
            oStream.write("Retry Failed Device(s)         : Enabled")
            if denaliVariables['commandRetry'] > 1:
                oStream.write("  (retry count: %s)\n" % denaliVariables['commandRetry'])
            else:
                oStream.write('\n')
            if len(denaliVariables['retryCommand']) > 0:
                oStream.write("Retry Command                  : %s\n" % retry_command)

        if segmented_pdsh == True:
            oStream.write("Number of Targeted Segments    : %s\n" % len(segmentList))
        oStream.write("Number of targeted devices     : %s\n\n" % len(denaliVariables['serverList']))
        oStream.write("Available options are:\n")
        oStream.write(" -> Accept command(s), execute PDSH         (enter 'YES')\n")
        if segmented_pdsh == True:
            oStream.write(" -> Show [s]egmented device list            (enter  's' )\n")
        oStream.write(" -> Show [t]argeted device list             (enter  't' )\n")
        if denaliVariables['hostCommands']['active'] == True:
            oStream.write(" -> Show [h]ost command(s)                  (enter  'h' )\n")
    else:
        if denaliVariables['devServiceVerify'] == True:
            verification_host_count = int(denaliVariables['devServiceVerifyData']['verify_host_count'])
            verification_command    = denaliVariables['devServiceVerifyData'].get('verify_command', 'Default Health Check')
            oStream.write("Device Verification            : True\n")
            oStream.write("  Verification Health Command  : %s" % colors.fg.green + verification_command + colors.reset + '\n')
            if segmented_pdsh == True:
                string_data = ' (per segment)\n'
            else:
                string_data = '\n'
            oStream.write("  Verification Host Count      : " + colors.fg.yellow + str(verification_host_count) + colors.reset + string_data)

        if denaliVariables['commandRetry'] > 0:
            oStream.write("Retry Failed Device(s)         : %s" % colors.fg.white + "Enabled" + colors.reset)
            if denaliVariables['commandRetry'] > 1:
                oStream.write("  (retry count: " + colors.fg.red + str(denaliVariables['commandRetry']) + colors.reset + ')\n')
            else:
                oStream.write('\n')
            if len(denaliVariables['retryCommand']) > 0:
                oStream.write("PDSH Retry Command             : %s" % colors.fg.blue + retry_command + colors.reset + '\n')
        if segmented_pdsh == True:
            oStream.write("Number of Targeted Segments    : %s" % colors.fg.red + str(len(segmentList)) + colors.reset + '\n')
        oStream.write("Number of Targeted Devices     : %s" % colors.fg.red + str(len(denaliVariables['serverList'])) + colors.reset + '\n\n')
        oStream.write("Available options are:\n")
        oStream.write(" -> Accept command(s), execute PDSH         (enter '" + colors.fg.cyan + "YES" + colors.reset + "')\n")
        if segmented_pdsh == True:
            oStream.write(" -> Show [s]egmented device list            (enter  '" + colors.fg.cyan + "s"   + colors.reset + "' )\n")
        oStream.write(" -> Show [t]argeted device list             (enter  '" + colors.fg.cyan + "t"   + colors.reset + "' )\n")
        if denaliVariables['hostCommands']['active'] == True:
            oStream.write(" -> Show [h]ost command(s)                  (enter  '" + colors.fg.cyan + "h" + colors.reset + "' )\n")

    return segmented_pdsh



##############################################################################
#
# printCheckTitle(denaliVariables, parameters='')
#

def printCheckTitle(denaliVariables, parameters=''):

    title_bar_color = colors.fg.lightcyan

    command_strings = {
                        'pdsh'     : 'PDSH Command to Execute',
                        'ssh'      : 'SSH Command to Execute',
                        'count'    : 32,
    }

    oStream  = denaliVariables['stream']['output']
    function = denaliVariables['commandFunction']

    oStream.write("\n%s Summary Information\n" % function.upper())

    if denaliVariables['commandFunction'] == 'ssh':
        parameters = [parameters]

    if denaliVariables["nocolors"] == True:
        oStream.write('=' * command_strings['count'] + '\n')
        if len(parameters):
            oStream.write(command_strings[function].ljust(command_strings['count']-1) + ': %s\n' % parameters[-1])
    else:
        oStream.write(title_bar_color + ("=" * command_strings['count']) + colors.reset + '\n')
        if len(parameters):
            oStream.write(command_strings[function].ljust(command_strings['count']-1) + ': %s' % colors.fg.lightgreen + parameters[-1] + colors.reset + '\n')



##############################################################################
#
# printCommandOptions(denaliVariables, option_list)
#

def printCommandOptions(denaliVariables, option_list):

    function = denaliVariables['commandFunction']
    oStream  = denaliVariables['stream']['output']

    function_string = { 'ssh'       : "SSH Command Options            : ",
                        'scp'       : "SCP Options                    : ",
                        'scp-pull'  : "SCP Options                    : ",
                        'scp-push'  : "SCP Options                    : ",
                        'pdsh'      : "PDSH Command Options           : " }

    if function in function_string:
        option_string = function_string[function]
    else:
        option_string = "!!@@!! : "

    if denaliVariables['nocolors'] == True:
        if len(option_list) > 1:
            oStream.write(option_string)
            for (index, option_item) in enumerate(option_list):
                if index == 0:
                    oStream.write(option_item + '\n')
                else:
                    oStream.write(' ' * 31 + ': ' + option_item + '\n')
        else:
            if len(option_list):
                if type(option_list) is str:
                    option_list = [option_list]
                oStream.write("%s%s\n" % (option_string, option_list[0]))
    else:
        if len(option_list) > 1:
            oStream.write(option_string)
            for (index, option_item) in enumerate(option_list):
                if index == 0:
                    oStream.write(colors.fg.lightcyan + option_item + colors.reset + '\n')
                else:
                    oStream.write(' ' * 31 + ': ' + colors.fg.lightcyan + option_item + colors.reset + '\n')
        else:
            if len(option_list):
                if type(option_list) is str:
                    option_list = [option_list]
                oStream.write(option_string + colors.fg.lightcyan + option_list[0] + colors.reset + '\n')
    return True



##############################################################################
#
# printSCPOptions(denaliVariables)
#

def printSCPOptions(denaliVariables):

    oStream = denaliVariables['stream']['output']

    LOCAL_COLOR  = colors.fg.yellow
    REMOTE_COLOR = colors.fg.blue
    GRAY         = colors.fg.darkgrey
    LTGRAY       = colors.fg.lightgrey

    if denaliVariables["non_interact"] == False:
        # use the default user that ran this denali session
        username = denaliVariables["userName"]
    else:
        # use a supplied user
        username = denaliVariables["non_interact_data"]["username"]


    if denaliVariables['commandFunction'] == 'scp-pull':
        SCP_TEXT    = "SCP file pull (remote -> local)"
        PULL_TEXT   = "REMOTE : [%s@server]:" % username
        PUSH_TEXT   = "LOCAL  : "
        PULL_TEXT_C = LOCAL_COLOR  + "REMOTE : " + GRAY + "[" + LTGRAY + username + "@server" + GRAY + ']:' + colors.reset
        PUSH_TEXT_C = REMOTE_COLOR + PUSH_TEXT + colors.reset

    else:
        # default 'push' operation
        SCP_TEXT    = "SCP file push (local -> remote)"
        PULL_TEXT   = "LOCAL  : "
        PUSH_TEXT   = "REMOTE : [%s@server]:" % username
        PULL_TEXT_C = LOCAL_COLOR  + PULL_TEXT + colors.reset
        PUSH_TEXT_C = REMOTE_COLOR + "REMOTE : " + GRAY + "[" + LTGRAY + colors.reset + username + "@server" + GRAY + ']:' + colors.reset


    # gather SCP options to show
    options = createSCPOptionsString(denaliVariables)

    if denaliVariables['scpDestination'] == '.':
        denaliVariables['scpDestination'] = os.getcwd() + '/'
    if denaliVariables['scpDestination'][-1] != '/' and denaliVariables['commandFunction'] == "scp-pull":
        # Only put a trailing slash on a pull operation as this could be a push
        # with a rename included.
        denaliVariables['scpDestination'] += '/'

    if denaliVariables['nocolors'] == True:
        oStream.write("SCP Command Type               : %s\n" % SCP_TEXT)
        ccode = printCommandOptions(denaliVariables, options)
        oStream.write("SCP Source Files(s)            : %s%s\n" % (PULL_TEXT, denaliVariables['scpSource']))
        oStream.write("SCP Destination Location       : %s%s\n" % (PUSH_TEXT, denaliVariables['scpDestination']))
        if len(denaliVariables['scpMultiFileList']) > 0:
            total_file_count, total_file_size = retrieveSCPFileMetadata(denaliVariables)
            oStream.write("SCP File Meta-data             : Count  : %i\n" % total_file_count)
            oStream.write("                                 Size   : %s\n" % total_file_size)

            if os.path.isdir(denaliVariables['scpDestination']) == True:
                part_stats = os.statvfs(denaliVariables['scpDestination'])
                free_space = part_stats.f_frsize * part_stats.f_bavail
                oStream.write("                               : Avail  : %s\n" % convert_size(free_space))
            else:
                oStream.write("                               : Avail  : !!Warning!! Submitted directory path not found [%s]\n" % denaliVariables['scpDestination'])
        oStream.write("Number of Targeted Devices     : %d\n\n" % len(denaliVariables['serverList']))

        oStream.write("Available options are:\n")
        oStream.write(" -> Accept command(s), execute SCP          (enter 'YES')\n")
        oStream.write(" -> Show [t]argeted device list             (enter  't' )\n")

    else:
        oStream.write("SCP Command Type               : " + colors.fg.lightgreen + SCP_TEXT + colors.reset + '\n')
        ccode = printCommandOptions(denaliVariables, options)
        oStream.write("SCP Source Files(s)            : " + PULL_TEXT_C + denaliVariables['scpSource'] + '\n')
        oStream.write("SCP Destination Location       : " + PUSH_TEXT_C + denaliVariables['scpDestination'] + '\n')
        if len(denaliVariables['scpMultiFileList']) > 0:
            total_file_count, total_file_size = retrieveSCPFileMetadata(denaliVariables)
            oStream.write("SCP File Meta-data             : " + colors.fg.lightgreen + "Count  : " + colors.reset + "%i\n" % total_file_count)
            oStream.write("                               : " + colors.fg.lightgreen + "Size   : " + colors.reset + "%s\n" % total_file_size)

            if os.path.isdir(denaliVariables['scpDestination']) == True:
                part_stats = os.statvfs(denaliVariables['scpDestination'])
                free_space = part_stats.f_frsize * part_stats.f_bavail
                oStream.write("                               : " + colors.fg.lightgreen + "Avail  : " + colors.reset + "%s\n" % convert_size(free_space))
            else:
                oStream.write("                               : " + colors.fg.lightgreen + "Avail  : " + colors.fg.red)
                oStream.write("!!Warning!! Submitted directory path not found" + colors.reset + " [%s]\n" % denaliVariables['scpDestination'])
        oStream.write("Number of Targeted Devices     : " + colors.fg.lightred + str(len(denaliVariables['serverList'])) + colors.reset + '\n\n')

        oStream.write("Available options are:\n")
        oStream.write(" -> Accept command(s), execute SCP          (enter '" + colors.fg.cyan + "YES" + colors.reset + "')\n")
        oStream.write(" -> Show [t]argeted device list             (enter  '" + colors.fg.cyan + "t"   + colors.reset + "' )\n")



##############################################################################
#
# retrieveSCPFileMetadata(denaliVariables)
#

def retrieveSCPFileMetadata(denaliVariables):

    file_count = 0
    file_size  = 0

    for hostname in denaliVariables['scpMultiFileList']:
        metadata    = denaliVariables['scpMultiFileList'][hostname][0]
        file_count += metadata[0]
        file_size  += metadata[1]

    return file_count, convert_size(file_size)



##############################################################################
#
# convert_size(size_bytes)
#

def convert_size(size_bytes):
    if size_bytes == 0:
        return "0 bytes"

    size_name = ("bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])



##############################################################################
#
# obtainResponse(denaliVariables, segmented_pdsh, parameters, segmentList)
#

def obtainResponse(denaliVariables, segmented_pdsh, parameters, segmentList):

    oStream = denaliVariables['stream']['output']
    iStream = denaliVariables['stream']['input']

    oStream.write(" -> Any other text entry will exit this command loop.\n\n")
    oStream.flush()
    response = getpass._raw_input("Enter choice: ", oStream, iStream)

    #print "         1         2         3         4         5         6         7         8         9         10        11        12        13        14"
    #print "123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901"

    available_commands = ['YES', 't', 'd']
    if segmented_pdsh == True:
        available_commands.append('s')
    if denaliVariables['hostCommands']['active'] == True:
        available_commands.append('h')

    if response not in available_commands:
        oStream.write("Undefined entry submitted. %s command execution canceled.\n" % denaliVariables['commandFunction'].upper())
        oStream.flush()
        denaliVariables['pdshCanceled'] = True
        return "False"

    if response == 'd' or response == 't':
        dev_print = "devices" if len(denaliVariables['serverList']) > 1 else "device"
        oStream.write("\nList of targeted %s [%s total]:\n" % (dev_print, len(denaliVariables['serverList'])))
        ccode = printGroupedHostnamesInColumns(denaliVariables, denaliVariables['serverList'])
        if len(removedHostList):
            oStream.write("\nList of pruned %s [%s total]:\n" % (dev_print, len(removedHostList)))
        ccode = printGroupedHostnamesInColumns(denaliVariables, removedHostList)
    elif response == 'h':
        oStream.write("\nList of hosts and associated commands to process:\n\n")
        ccode = printHostsAndCommands(denaliVariables, parameters[-1])
    elif response == 's':
        separator_count = denaliVariables['pdshSeparate']['separator_count']
        ccode = segmentedResponse(denaliVariables, segmentList, separator_count)
        if ccode == "False":
            return False

    return response



##############################################################################
#
# returnFanoutValue(denaliVariables)
#

def returnFanoutValue(denaliVariables):

    fanoutValue  = -1
    pdsh_options = denaliVariables['pdshOptions'].split('-')
    if pdsh_options[0] == '':
        pdsh_options.pop(0)

    for option in pdsh_options:
        if option.startswith('f '):
            fanoutValue = option[2:].split()[-1]
            fanoutValue = fanoutValue.replace('%', '')
            if fanoutValue.isdigit() == False:
                # incorrectly formatted fanout value -- do not continue
                print colors.reset + "\nDenali Syntax Error:  The PDSH variable fanout value [-%s] is incorrectly formatted.  Use -f <#>%%." % option
                denali_search.cleanUp(denaliVariables)
                exit(1)
            break

    return fanoutValue



##############################################################################
#
# segmentedResponse(denaliVariables, segmentList, separator_count)
#

def segmentedResponse(denaliVariables, segmentList, separator_count):

    oStream = denaliVariables['stream']['output']
    iStream = denaliVariables['stream']['input']

    segmentList.sort()
    oStream.write("\nList of segments and devices to process:\n\n")

    print "Separators declared: %s - [%s]\n" % (separator_count, denaliVariables['pdshSeparate']['separator'])

    if separator_count == 1:
        # show the segments with devices enumerated
        for (index, segment) in enumerate(segmentList):
            dev_print = "devices" if len(denaliVariables['pdshSeparateData'][segment]) > 1 else "device"
            if denaliVariables['nocolors'] == True:
                if denaliVariables['hostCommands']['active'] == False:
                    oStream.write("Segment #%i (%i %s): [%s]\n" % ((index+1), len(denaliVariables['pdshSeparateData'][segment]), dev_print, segment))
                else:
                    oStream.write("Segment #%i:\n" % (index+1))

                if denaliVariables['pdshVariableFanout'] == True:
                    fanoutValue = returnFanoutValue(denaliVariables)
                    fanout = determinePDSHFanoutValue(denaliVariables, denaliVariables['pdshSeparateData'][segment], fanoutValue)
                    oStream.write("Fanout Value: %i\n" % fanout)
            else:
                if denaliVariables['hostCommands']['active'] == False:
                    oStream.write(colors.fg.lightcyan + "Segment #%i (%i %s): [%s]\n" % ((index+1), len(denaliVariables['pdshSeparateData'][segment]), dev_print, segment) + colors.reset)
                else:
                    oStream.write(colors.fg.lightcyan + "Segment #%i:\n" % (index+1) + colors.reset)

                if denaliVariables['pdshVariableFanout'] == True:
                    fanoutValue = returnFanoutValue(denaliVariables)
                    fanout = determinePDSHFanoutValue(denaliVariables, denaliVariables['pdshSeparateData'][segment], fanoutValue)
                    oStream.write(colors.fg.lightcyan + "Fanout Value: %i\n" % fanout + colors.reset)

            ccode = printGroupedHostnamesInColumns(denaliVariables, denaliVariables['pdshSeparateData'][segment])
            oStream.write(colors.reset + '\n')
            oStream.flush()
        if denaliVariables['hostCommands']['active'] == False:
            if denaliVariables['nocolors'] == True:
                oStream.write("\nList of segments/counts to process:\n")
            else:
                oStream.write(colors.fg.lightgreen + "\nList of segments/counts to process:\n" + colors.reset)

            # show a total list of counts per segment
            segment_size = 0
            for segment in segmentList:
                if len(segment) >  segment_size:
                    segment_size = len(segment)
            for (index, segment) in enumerate(segmentList):
                oStream.write("  %s   [%s]\n" % (segment.ljust(segment_size), str(len(denaliVariables['pdshSeparateData'][segment])).rjust(5)))
            oStream.write("\n")

    elif separator_count == 2:
        # show the segments with devices enumerated
        for (index, segment) in enumerate(segmentList):
            seg_split = segment.split(':')
            segment   = segment.replace(':', '] [')
            dev_print = "devices" if len(denaliVariables['pdshSeparateData'][seg_split[0]][seg_split[1]]) > 1 else "device"
            oStream.write("Segment #%i (%i %s): [%s]\n" % ((index+1), len(denaliVariables['pdshSeparateData'][seg_split[0]][seg_split[1]]), dev_print, segment))
            ccode = printGroupedHostnamesInColumns(denaliVariables, denaliVariables['pdshSeparateData'][seg_split[0]][seg_split[1]])
            oStream.write('\n')
            oStream.flush()
        if denaliVariables['nocolors'] == True:
            oStream.write("\nList of segments/counts to process:\n")
        else:
            oStream.write(colors.fg.lightgreen + "\nList of segments/counts to process:\n" + colors.reset)

        # show a total list of counts per segment
        segment_size = 0
        for segment in segmentList:
            if len(segment) >  segment_size:
                segment_size = len(segment)
        for (index, segment) in enumerate(segmentList):
            seg_split = segment.split(':')
            segment = segment.replace(':', '  ||  ')
            oStream.write("  [%s]\t %s\n" % (str(len(denaliVariables['pdshSeparateData'][seg_split[0]][seg_split[1]])).rjust(4), segment.ljust(segment_size)))
        oStream.write("\n")

    else:
        oStream.write("Denali Error: Incorrect separator count found\n")
        oStream.write("       denaliVariables['pdshSeparate'] = %s\n" % denaliVariables['pdshSeparate'])
        oStream.write("                       separator_count = %s\n" % separator_count)
        oStream.write("                       segmentList     = %s\n" % segmentList)
        oStream.write("                       serverList      = %s\n" % serverList)
        oStream.flush()
        denaliVariables['pdshCanceled'] = True
        #sys.stdin=stdin_backup
        return "False"



##############################################################################
#
# finalFunctionPromptCheck(denaliVariables, retry_command, parameters='', options='', segmentList=[], serverList=[], warning='')
#
#   MRASETEAM-40846: This function does a final sanity check for the issued
#                    pdsh command.  The reason for this is that it is possible
#                    for a user to accidentally select devices to run this
#                    command against that they did not intend to.  This will
#                    give the user a chance to review and accept/reject the
#                    operation that is about the take place.
#
#   Return: False == don't do the operation
#           True  == proceed
#

def finalFunctionPromptCheck(denaliVariables, retry_command, parameters='', options='', segmentList=[], serverList=[], warning=''):

    loop     = True
    function = denaliVariables['commandFunction']
    oStream  = denaliVariables['stream']['output']
    iStream  = denaliVariables['stream']['input']

    # every function (except potentially PDSH) will have this as false
    segmented_pdsh = False

    # functions/features for which no pre-summary is given
    skip_functions = [
                        'info',
                        'ping',
                        'spots',
                    ]

    # If this switch is set, automatically run the command
    # Skip if scp multi-file because that runs pdsh/'ls' looking
    # for wildcard filenames for the scp-pull function
    if denaliVariables['autoConfirm'] == True or function in skip_functions or denaliVariables['scpMultiFile'] == True:
        if denaliVariables['autoConfirm'] == True and denaliVariables['scpMultiFile'] == False:
            # Don't display the time if --yes is used and scpMultiFile is enabled.  This means
            # to not show the time when "collection file data from [x] queried devices" is displayed.
            displayCurrentTime(denaliVariables, "[ Start Time:", " ]")
        return True

    # do not check on a pdsh->ssh fallthrough
    if denaliVariables['sshFallThrough'] == True and denaliVariables['commandFunction'] == 'ssh':
        return True

    # if this is a retry, make sure it should be shown
    if denaliVariables['commandRetryCount'] > 0 and RETRY_SHOW_SUMMARY == False:
        return True

    # backup the stdin pointer -- whatever it is at this point.
    stdin_backup=sys.stdin
    # set a pointer to /dev/tty -- to allow user input
    sys.stdin = open("/dev/tty")

    if len(warning) > 0:
        oStream.write(colors.fg.red + "!!WARNING!!" + colors.reset + "\n%s\n" % warning)

    # main loop to do before proceeding
    while (loop == True):

        printCheckTitle(denaliVariables, parameters)

        if function == 'pdsh':
            if len(options):
                printPDSHOptions(denaliVariables, options, serverList)
            segmented_pdsh = printPDSHDeviceInformation(denaliVariables, segmentList, serverList, retry_command)
        elif function.startswith('scp'):
            printSCPOptions(denaliVariables)
        elif function == 'ssh':
            printSSHOptions(denaliVariables, retry_command)

        response = obtainResponse(denaliVariables, segmented_pdsh, parameters, segmentList)
        if response == "False":
            sys.stdin=stdin_backup
            return False
        elif response == 'YES':
            sys.stdin=stdin_backup
            oStream.flush()
            displayCurrentTime(denaliVariables, "[ Start Time:", " ]")
            return True

    # now restore the stdin pointer to whatever it was before.  This should allow
    # the processing to continue as expected
    sys.stdin=stdin_backup

    return True



##############################################################################
#
# displayCurrentTime(beginningString="Current Time:", endingString="")
#
#   Print the current time (HH:MM:SS AM/PM TZ) on the screen
#

def displayCurrentTime(denaliVariables, beginningString="Current Time:", endingString="", startTime=""):

    # only print start/stop/duration for pdsh and ssh functions
    if denaliVariables['commandFunction'] not in denaliVariables['retryFunctions']:
        return

    DASH_LINE_LENGTH = len(beginningString) + len(endingString) + 16
    if DASH_LINE_LENGTH < 31:
        DASH_LINE_LENGTH = 31

    def printTimeString(beginningString, endingString):
        print "%s %s%s" % (beginningString, time.strftime("%I:%M:%S %p %Z"), endingString)

    # If the 'start_time' key is not present, and a 'startTime' was not given, it means that
    # this is the very first run ... so record the start time.
    if 'start_time' not in denaliVariables['commandTimeValues'] and startTime == "":
        denaliVariables['commandTimeValues'].update({'start_time': time.time()})
        print
        printTimeString(beginningString, endingString)
        print "-" * DASH_LINE_LENGTH
        print
        return

    if startTime != "":
        print
        print "-" * DASH_LINE_LENGTH
        printTimeString(beginningString, endingString)
        # determine time difference/delta
        if startTime is not None:
            difference = str(datetime.timedelta(seconds=(time.time() - startTime)))
            print "[ Duration  : %ss ]" % difference
        print

    return



##############################################################################
#
# quoteShellArg(argument_string)
#
#   Quote an argument suitable for passing to a bourne shell.
#

def quoteShellArg(argument_string):
    return "'" + argument_string.replace( "'", r"'\''" ) + "'"



##############################################################################
#
# validatePDSHHostCommands(denaliVariables)
#
#   This function enforces what the user has submitted.  If the user requests
#   that PDSH run 3 commands, then the individual hosts need to have 3 commands
#   assigned to them.  If there are more or less than this number, the code
#   will detect this and print a syntax error message stating the problem.
#

def validatePDSHHostCommands(denaliVariables):

    debug          = False
    syntax_error   = False
    header_printed = False
    command        = "command"
    word           = "was"
    oStream        = denaliVariables['stream']['output']

    # This switch means that multiple command submissions are combined into a
    # single substitution.  In other words, the commands would be something like
    # this:
    #         'uptime;date;ls -l /home/'
    # All of those are capable of a single substitution
    #
    # TO DO:
    # Allow combinations of commands to be compressed down.
    # For example:  Allow 3 commands to be compressed into 2, with the last 2
    # combining into a single one or perhaps the first two ... etc.
    allow_combined_singles = denaliVariables['pdshCombinedCmds']

    commands_expected = denaliVariables['pdshCommand'].count('%s')

    if debug == True:
        print "PDSH commands expected  = %s" % commands_expected

    host_list = denaliVariables['hostCommands'].keys()
    host_list.sort()

    for host in host_list:
        if host == "active":
            continue

        commands_submitted = len(denaliVariables['hostCommands'][host])

        if allow_combined_singles == True and commands_submitted > 1 and commands_expected == 1:
            denaliVariables['hostCommands'][host] = [';'.join(denaliVariables['hostCommands'][host])]
            commands_submitted = 1

        if debug == True:
            print "PDSH commands submitted = %s" % commands_submitted
            print "  host = %s : %s" % (host, denaliVariables['hostCommands'][host])

        if commands_submitted != commands_expected:

            syntax_error = True

            # Make the english grammar correct for singular or plural
            if commands_submitted > 1:
                command = "commands"
            if commands_expected > 1:
                word    = "were"
            if header_printed == False:
                header_printed = True
                oStream.write("Denali Syntax Error(s):  Submitted host list has a command mismatch.\n")

            oStream.write("   Found host [%s] with [%d] %s, when [%d] %s expected\n" % (host, commands_submitted, command, commands_expected, word))

    if syntax_error == True:
        oStream.flush()
        return False

    return True



##############################################################################
#
# augmentPDSHCommandString(denaliVariables, pdsh_parms, pdsh_command, command_user_string)
#

def augmentPDSHCommandString(denaliVariables, pdsh_parms, pdsh_command, command_user_string):

    oStream = denaliVariables['stream']['output']

    if pdsh_command:
        # MRASEREQ-41775
        if command_user_string:
            # Verify the user did not put 'sudo' on the front of the command
            # while at the same time requesting a sudo user.  Without this check
            # that would create an ugly mess of text to be executed, potentially
            # doing something unexpected.
            # If they did, do not add the command string.  Let the command run
            # as presently constituted
            #
            # 8/13/2019: Revert this change
            #
            # Engineering needs this functionality.  They go in as a different user,
            # like 'httpd', and then from that user's access, they need to sudo to
            # run a command to do different things (start/stop services, etc.).
            #
            # This allows: --pc="sudo service httpd restart" --sudo=httpd
            #
            # The check now only looks for 'bash -c' before making a decision.
            location_bash = pdsh_command.find('bash -c')
            if location_bash != -1 and location_bash < 3:
                # Do not use the 'command_user_string' in prefacing the submitted
                # command(s) to be executed.
                pdsh_parms.append(pdsh_command)
            else:
                # Always use single quotes since they quote dollar signs, backticks etc.
                # It can get messy, but is more reliable than trying to escape everything
                pdsh_parms.append(command_user_string+" "+quoteShellArg(pdsh_command))
        else:
            pdsh_parms.append(pdsh_command)

        # save the altered command line string
        #denaliVariables['pdshCommand'] = pdsh_parms[-1]
    else:
        oStream.write("\nPDSH command to execute is empty -- execution will stop.\n")
        oStream.write("Use '--pdsh_command=<command(s)_to_run>'.\n\n")
        return False

    return pdsh_parms



##############################################################################
#
# returnPDSHCommandString(denaliVariables, pdsh_hosts)
#

def returnPDSHCommandString(denaliVariables, pdsh_hosts):

    pdshData       = ''
    pdshDictionary = {}
    pdsh_command   = denaliVariables["pdshCommand"]
    retry_command  = 'Not Submitted'
    time_string    = datetime.datetime.now().strftime("%m%d_%H%M%S")
    oStream        = denaliVariables['stream']['output']

    # if this is a retry loop, and the retry command is populated, use it
    if denaliVariables['commandRetryCount'] > 0 and len(denaliVariables['retryCommand']) > 0:
        pdsh_command = denaliVariables['retryCommand']

    # PDSH sudo command user string
    # MRASEREQ-41775
    if denaliVariables['sudoUser']:
        command_user_string = "sudo -H -u %s -i bash -c" % denaliVariables['sudoUser']
    else:
        command_user_string = ''

    # Verify that the number of commands requested is matched with the commands
    # supplied in the host list
    if denaliVariables['hostCommands']['active'] == True:
        ccode = validatePDSHHostCommands(denaliVariables)
        if ccode == False:
            # Bail out with a contextual error message
            return False, False, False

    # retrieve the pdsh options string
    pdshOptions = createPDSHOptionsString(denaliVariables, pdsh_hosts)

    #
    # build the parameter list to send to pdsh
    #
    pdsh_parms = ['pdsh']

    if pdshOptions:
        pdsh_parms.extend(pdshOptions)

    if pdsh_hosts:
        pdsh_parms.append('-w')
        pdsh_parms.append(','.join(pdsh_hosts))

        if denaliVariables['debug'] == True:
            print "  pdsh_command = %s" % pdsh_command
            print "  pdshOptions  = %s" % pdshOptions
            print "  pdsh_parms   = %s" % pdsh_parms
    else:
        # if there are no hosts -- do not run pdsh
        print "Denali Error: No hosts were found, pdsh execution halted."
        print "  pdsh_hosts   = %s" % pdsh_hosts
        print "  pdsh_command = %s" % pdsh_command
        print "  pdshOptions  = %s" % pdshOptions
        print "  pdsh_parms   = %s" % pdsh_parms
        return False, False, False

    # Create the retry command string -- even though this isn't used, it is for
    # display purposes ... to make sure the user knows what will happen with this.
    if len(denaliVariables['retryCommand']) > 0:
        retry_command = augmentPDSHCommandString(denaliVariables, pdsh_parms, denaliVariables['retryCommand'], command_user_string)[-1]
        if retry_command == False:
            return False, False, False

        # Drop the last item on pdsh_parms (retry command) -- otherwise, after the next function call,
        # both the original command and the retry command will occupy the last two indexes in the pdsh_parms
        # List -- and the command for PDSH will fail.
        #    pdsh_parms = [... "retry_pdsh_command", "original_pdsh_command"]
        del pdsh_parms[-1]

    pdsh_parms = augmentPDSHCommandString(denaliVariables, pdsh_parms, pdsh_command, command_user_string)
    if pdsh_parms == False:
        return False, False, False
    denaliVariables['pdsh_command'] = pdsh_parms[-1]

    # Add the detached screen directive to the pdsh command string
    # The location of the screen command is purposely placed at the beginning of the
    # command line so as to assign the screen ownership to the user requesting the
    # command to be run.
    if denaliVariables["pdshScreenDM"] == True or denaliVariables["pdshScreen"] == True:
        pdsh_parms[-1] = pdsh_screen_dm + quoteShellArg(pdsh_parms[-1])
        denaliVariables['pdshCommand'] = pdsh_parms[-1]

        if retry_command != 'Not Submitted':
            retry_command = pdsh_screen_dm + quoteShellArg(retry_command)

    if denaliVariables["debug"] == True or command_debug == True:
        print "pdsh_parms             = %s" % pdsh_parms
        print "PDSH command submitted = %s" % denaliVariables["pdshCommand"]
        print "Parameter app count    = %s" % denaliVariables["pdshAppCount"]
        print "PDSH retry command     = %s" % retry_command

        if denaliVariables["pdshAppCount"] != -1:
            print "Parsed app count       = %s" % denaliVariables['pdshAppCount']

    return (pdsh_parms, pdshOptions, retry_command)



##############################################################################
#
# returnPDSHHostList(denaliVariables, pdsh_hosts)
#

def returnPDSHHostList(denaliVariables, pdsh_hosts):

    # determine the data center for submitted hosts
    data_center = determineDataCenter(pdsh_hosts)
    pdsh_hosts  = adjustHostnameForUse(denaliVariables, pdsh_hosts)

    if denaliVariables["debug"] == True:
        print "Data Center = %s" % data_center

    if denaliVariables["pdshAppCount"] != -1:
        # determine the number of commands run -- pdsh_app_count
        app_count = determineNumberOfPDSHCommands(denaliVariables)
        denaliVariables["pdshAppCount"] = app_count

    return (pdsh_hosts, data_center)



##############################################################################
#
# removePDSHHosts(denaliVariables, hostname_list, pdsh_hosts, pdsh_parms)
#
#   This function will remove hosts from the pdsh list of hosts to process.
#   It loops through the list of hosts supplied (hostname_list), and removes
#   the hosts from the pdsh_hosts List (simple pdsh_hosts.remove() action),
#   and then from pdsh_parms (which is a comma separated list as the 2nd from
#   the last element in that variable -- so there are a few hoops to jump
#   through to get that working).
#

def removePDSHHosts(denaliVariables, hostname_list, pdsh_hosts, pdsh_parms):

    # location index in the pdsh_parm LIST for the hosts (2nd from the rear)
    host_index = -2

    if denaliVariables['pdshSeparate'] != False:
        # removing hosts when --ps is used is different than normal
        separator_list = denaliVariables['pdshSeparateData'].keys()

        for separator in separator_list:
            for hostname in hostname_list:
                if hostname in denaliVariables['pdshSeparateData'][separator]:
                    denaliVariables['pdshSeparateData'][separator].remove(hostname)

        # check for empty keys and remove them
        new_dict = {}
        for separator in separator_list:
            if len(denaliVariables['pdshSeparateData'][separator]):
                new_dict.update({separator:denaliVariables['pdshSeparateData'][separator]})

        denaliVariables['pdshSeparateData'] = new_dict

    else:
        # remove all checked hosts from the list
        parm_host_list = pdsh_parms[host_index].split(',')
        for hostname_ls in hostname_list:
            try:
                if hostname_ls in pdsh_hosts:
                    pdsh_hosts.remove(hostname_ls)
                else:
                    pdsh_hosts.remove(hostname_ls + '.omniture.com')
                if hostname_ls in parm_host_list:
                    parm_host_list.remove(hostname_ls)
                else:
                    parm_host_list.remove(hostname_ls + '.omniture.com')
            except ValueError:
                # this means the host given wasn't in the list, ignore and continue
                pass

        # join the shortened parm list together and put it back
        pdsh_parms[host_index] = ','.join(parm_host_list)

        # reset the progress indicator to look correct when PDSH executes
        generateProgressNumbers(denaliVariables)

    return



##############################################################################
#
# performPDSHOperation(denaliVariables, pdsh_hosts, printLock, mCommandDict, mCommandList)
#
#   Because the pdsh command is already parallelized, the printLock lock is
#   not passed in.  Also, there is not a group of threads that collect the
#   data as with the other commands run through the command code.  The pdsh
#   command operates semi-independently of the main mp engine functions above.
#
#   pdsh_hosts is sent in as a List of hosts ['host1', 'host2', etc.]
#

def performPDSHOperation(denaliVariables, pdsh_hosts, printLock, mCommandDict, mCommandList):

    #denaliVariables["debug"] = False

    pdshData        = ''
    pdshDictionary  = {}
    separator_id    = 'blank'
    time_string     = datetime.datetime.now().strftime("%m%d_%H%M%S")
    pdsh_batch_mode = False
    oStream         = denaliVariables['stream']['output']

    if denaliVariables['debug'] == True:
        print "pdsh_hosts               = %s" % pdsh_hosts
        print "variable length of hosts = %s" % len(''.join(pdsh_hosts))

    if denaliVariables['pdshSeparate'] != False:
        # Run the separator path.  The ID is the pdsh_hosts, which in the case of the DPC
        # separator, is a data center (e.g., da2).
        separator_id    = pdsh_hosts
        separator_count = denaliVariables['pdshSeparate']['separator_count']
        if separator_count == 1:
            try:
                pdsh_hosts = denaliVariables['pdshSeparateData'][pdsh_hosts]
            except KeyError:
                # If a category/separator has been completedly removed, and the code has
                # not removed it (for whatever reason) make sure that this doesn't stop
                # the execution from finishing ... ignore the error and continue.
                print "Denali Error:  PDSH Separator KeyError: %s" % pdsh_hosts
                return {}
        elif separator_count == 2:
            segment_split = pdsh_hosts.split(':')
            pdsh_hosts = denaliVariables['pdshSeparateData'][segment_split[0]][segment_split[1]]
        (pdsh_hosts, data_center) = returnPDSHHostList(denaliVariables, pdsh_hosts)
        (pdsh_parms, pdshOptions, retry_command) = returnPDSHCommandString(denaliVariables, pdsh_hosts)
        if pdsh_parms == False:
            # clean up and exit out
            return {}

        if denaliVariables['hostCommands']['active'] == True:
            pdsh_command = pdsh_parms[-1]
            command_list = denaliVariables['hostCommands'][pdsh_hosts[0]]
            for command in command_list:
                pdsh_command = pdsh_command.replace('%s', command, 1)
            pdsh_parms[-1] = pdsh_command

        if denaliVariables['debug'] == True:
            print "  (a) pdshOptions  = %s" % pdshOptions
            print "  (a) pdsh_parms   = %s" % pdsh_parms

    else:
        (pdsh_hosts, data_center) = returnPDSHHostList(denaliVariables, pdsh_hosts)
        (pdsh_parms, pdshOptions, retry_command) = returnPDSHCommandString(denaliVariables, pdsh_hosts)
        if pdsh_parms == False:
            # clean up and exit out
            return {}

        # MRASETEAM-40846: Before executing the command, make sure that what the user
        #                  requested, is what they actually want.  There is a possibility
        #                  that a lot of damage could be done here accidentally.
        ccode = finalFunctionPromptCheck(denaliVariables, retry_command, pdsh_parms, pdshOptions)
        if ccode == False:
            # clean up and exit out
            return {}

        # code to be run if the --verify switch is used (no --ps switch ... single pdsh execution run)
        if denaliVariables['devServiceVerify'] == True:
            (ccode, hostname_list_single) = denali_healthCheck.hc_entryPoint(denaliVariables, pdsh_hosts)
            if ccode == False:
                print
                denali_healthCheck.displayOutputMarker(denaliVariables, "Health Check FAILURE - PDSH Execution Halted", 2)
                displayCurrentTime(denaliVariables, "[ End Time  :", " ]", time.time())
                return {}
            print

            # remove hosts that were checked (no need to "double-dip" here)
            removePDSHHosts(denaliVariables, hostname_list_single, pdsh_hosts, pdsh_parms)
            # The list may have domains that need to be stripped (otherwise the output host will have the
            # FQDN name, which is different than the healh check just run - which looks wrong)
            denaliVariables['serverList'] = denali_utility.stripServerName(denaliVariables['serverList'], denaliVariables)
            if not len(denaliVariables['serverList']):
                denali_healthCheck.displayOutputMarker(denaliVariables, "No Devices Remain.  PDSH Execution canceled")
                return {}
            denali_healthCheck.displayOutputMarker(denaliVariables, "Allow Complete PDSH Execution")

    # notify the user that data collection is happening
    if denaliVariables['scpMultiFile'] == True:
        print "Collecting file data from %i queried devices (please stand-by): " % len(pdsh_hosts),

    if denaliVariables['pdshOffset'] != -1:
        # requested pdsh batch mode run-through
        pdsh_batch_data = separatePDSHHostsForBatches(denaliVariables, pdsh_parms)
        if pdsh_batch_data == "Failed":
            return {}
    else:
        pdsh_batch_data = [pdsh_parms]

    # Store the log file name for later
    # The separator_id is used if this is a pdshSeparate operation; it means that each separate
    # instance of pdsh that runs will create a separate log for its specific data.  If there are
    # 5 runs, then there are 5 log files.
    if denaliVariables['pdshSeparate'] != False:
        # Careful, if separated data is run in a no-fork mode, this log file data location will
        # be the same between runs (and it will confuse you when debugging) because it is the
        # same process space (same denaliVariables, etc.).  That is why this is assigned directly
        # with the required name (not a += addition as with a single-run PDSH operation).
        if denaliVariables['pdsh_log_file'].endswith('.txt'):
            # existing file -- truncate it for a new one
            denaliVariables['pdsh_log_file'] = denaliVariables['pdsh_log_file'].rsplit('-',2)[0]

        denaliVariables["pdsh_log_file"] += '-' + time_string  + '-' + separator_id + ".txt"
    else:
        # Log appending across retry loops:
        # This check allows the retry logic to append to an existing pdsh log file, instead of
        # creating a new one for each retry loop.
        if denaliVariables['pdsh_log_file'].endswith('.txt') == False:
            denaliVariables["pdsh_log_file"] += '-' + time_string + ".txt"

            # If the user requested a symlink to the log file ... do it here
            if len(denaliVariables['commandOutputSymlink']):
                try:
                    os.symlink(denaliVariables['pdsh_log_file'], denaliVariables['commandOutputSymlink'])
                except OSError as e:
                    # Symlink creation failed.  Do not stop, continue without it.
                    print "Denali Error: Symlink creation [%s] failed: %s\n" % (denaliVariables['commandOutputSymlink'], str(e))
                    if denaliVariables['debug'] == True:
                        print "PDSH symlink to the log file failed to successfully create."
                        print "  Symlink source      = %s" % denaliVariables['pdsh_log_file']
                        print "  Symlink destination = %s" % denaliVariables['commandOutputSymlink']

    # Iterate through PDSH commands to execute (if necessary)
    #
    # The log file is already/automatically appended to, so breaking up a single PDSH request
    # into multiple batches will automatically combine the data across batch runs without any
    # other work.
    for (index, pdsh_parms) in enumerate(pdsh_batch_data):

        if denaliVariables['debug'] == True:
            print "PDSH batch #%d" % (index + 1)

        try:
            # If subprocess' stdout uses a block buffering instead of a line buffering in
            # non-interactive mode (that leads to a delay in the output until the child's
            # buffer is full or flushed explicitly by the child) then you could try to
            # force an unbuffered output using pexpect, pty modules or unbuffer, stdbuf,
            # script utilities, see Q: Why not just use a pipe (popen())?

            # bufsize, if given, has the same meaning as the corresponding argument to the
            # built-in open() function:
            #
            #   0 means unbuffered
            #   1 means line buffered
            #
            # Any other positive value means use a buffer of (approximately) that size. A
            # negative bufsize means to use the system default, which usually means fully
            # buffered.  The default value for bufsize is 0 (unbuffered).

            # With the method below, both stdout and stderr are output.

            proc = subprocess.Popen(pdsh_parms, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, shell=False)

        except Exception as e:
            if str(e) == "[Errno 7] Argument list too long":
                pdsh_batch_mode = True
                if denaliVariables['debug'] == True:
                    oStream.write("Argument list too long; PDSH batch mode automatically engaged.\n")
            else:
                oStream.write("Denali: Error caught during PDSH operation: %s" % e)
                oStream.write("Execution halted.")
                return {}

        if pdsh_batch_mode == False:
            #
            # Default run-through, typically <5000 hosts to process, so a single batch
            # will work just fine.
            #

            ##
            ## This method for showing the results of PDSH works well -- it prints the data
            ## as it's received rather than waiting until the processes (all of them) finish
            ## completely to dump their buffers -- which is a bit of a pain, especially if
            ## there is a large number of hosts to churn through - the wait would be interminable.
            ##

            for output_line in iter(proc.stdout.readline, ""):
                # separate data in the returned log line from pdsh
                (result, hostname, data_line) = separateHostnameAndData(denaliVariables, output_line, data_center)

                # record the data received -- based upon the result
                pdshDictionary = pdshInfoRecordData(denaliVariables, pdshDictionary, result, hostname)

                # print the received data ... so far
                #
                # For non-app counted runs, this means a doubling of the output; however, it
                # is better to show output (for the sake of "user entertaininment" -- let them
                # know it is working) rather than waiting until the end and dumping everything
                # to the screen at once.
                pdshInfoPrint(denaliVariables, result, hostname, data_line, time_string, mCommandDict, mCommandList, printLock)

        else:
            #
            # PDSH batch mode run-through, typically >5000 hosts to process, so it needs to
            # be batched up in groupings of <5000/batch each.
            #

            pdsh_batch_data = separatePDSHHostsForBatches(denaliVariables, pdsh_parms)
            if pdsh_batch_data == "Failed":
                return {}

            for pdsh_parms in pdsh_batch_data:
                proc = subprocess.Popen(pdsh_parms, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, shell=False)
                for output_line in iter(proc.stdout.readline, ""):
                    (result, hostname, data_line) = separateHostnameAndData(denaliVariables, output_line, data_center)
                    pdshDictionary = pdshInfoRecordData(denaliVariables, pdshDictionary, result, hostname)
                    pdshInfoPrint(denaliVariables, result, hostname, data_line, time_string, mCommandDict, mCommandList, printLock)

        # handle devices that were successful, but did not return any data
        ccode = handleSilentSuccessDevices(denaliVariables, pdshDictionary, pdsh_hosts, data_center, time_string, mCommandDict, mCommandList, printLock)

    # Because PDSH runs in a separate process, adjusting denaliVariables here will not
    # be remembered in the main process.  To counter this, pass back the log file name
    # in the pdshDictionary
    pdshDictionary.update({'pdsh_log_file':denaliVariables['pdsh_log_file']})

    proc.stdout.close()
    return_code = proc.wait()

    ## saving code -- for now -- in case I need to revisit this
    ##
    ## this method prints data as it's given -- which is nice
    ##
    #while True:
    #    nextline = proc.stdout.readline()
    #    if nextline == '' and proc.poll() is not None:
    #        break
    #    sys.stdout.write(nextline)
    #    sys.stdout.flush()
    #output = proc.communicate()

    ##
    ## this method waits for the whole thing to finish
    ## before printing any output/error data
    ##
    #(stdout, stderr) = proc.communicate()
    #print "stdout = %s" % stdout
    #print "stderr = %s" % stderr

    return pdshDictionary



##############################################################################
#
# handleSilentSuccessDevices(denaliVariables, pdshDictionary, pdsh_hosts,
#                            data_center, time_string, mCommandDict, mCommandList,
#                            printLock)
#
#   With PDSH it isn't possible to know which host/s are being operated on,
#   and which are still waiting for assignment in the parallel distribution.
#   Because of this, it isn't possible to know if a host has finished (completely)
#   or it is still waiting for information from the operating system.  This means
#   if a host finishes silently (think "touch file"), then there is no return code
#   indicating either success or failure.  This function will assume that all
#   devices that do not return any data/message indicate a successful run of the
#   command/s requested of it.
#
#   Because of the caveat of not knowing what host is being operated on by PDSH,
#   this function can only run once PDSH completes its work of contacting and
#   receiving data from all submitted hosts.  It has to know the full list of
#   reported hosts to get the opposite list of non-reporting hosts.
#
#   The method of calculating these silently succeeding hosts to to take the enitre
#   list of hosts given to PDSH and then cross-reference that with all of the hosts
#   that are recorded with any kind of success or failure.  Removing those hosts
#   (ones that have responded) from the full submitted list, leaves a list of
#   silently succeeding hosts.
#
#   This code finds the silently succeeding hosts, adds them to the pdshDictionary
#   as if they responded, and then prints out a standard piece of text indicating
#   that the host did not reply.
#

def handleSilentSuccessDevices(denaliVariables, pdshDictionary, pdsh_hosts, data_center, time_string, mCommandDict, mCommandList, printLock):

    submitted_device_list = denaliVariables['serverList']
    original_device_list  = pdsh_hosts
    returned_device_list  = set(pdshDictionary.keys())
    unknown_device_list   = []

    for (index, device) in enumerate(original_device_list):
        if device not in submitted_device_list:
            # See if the device name has "omniture.com/adobe.net", etc., at the end
            # If so, remove it.
            if device.endswith('.omniture.com') == True:
                device = device[:-13]
            elif device.endswith('.adobe.net') == True:
                device = device[:-10]

            # have a modified device name now, check and see if this is a valid
            # device: submitted
            if device not in submitted_device_list:
                unknown_device_list.append(device)
            else:
                original_device_list[index] = device

    original_device_list = set(original_device_list)
    unknown_device_list  = set(unknown_device_list)

    # remove all "UNKNOWN" devices
    original_device_list = original_device_list - unknown_device_list

    if len(returned_device_list) == 0:
        silent_devices = original_device_list
    else:
        # 'set' arithmatic -- find the difference from the original to the returned
        silent_devices = (original_device_list - returned_device_list)

    for device in silent_devices:
        output_line = "%s: No data returned. Success assumed." % device
        (result, hostname, data_line) = separateHostnameAndData(denaliVariables, output_line, data_center)
        pdshDictionary = pdshInfoRecordData(denaliVariables, pdshDictionary, result, hostname)
        pdshInfoPrint(denaliVariables, result, hostname, data_line, time_string, mCommandDict, mCommandList, printLock)

    for device in unknown_device_list:
        output_line = "%s: Unknown device in output list.  No data returned. Success assumed." % device
        (result, hostname, data_line) = separateHostnameAndData(denaliVariables, output_line, data_center)
        pdshDictionary = pdshInfoRecordData(denaliVariables, pdshDictionary, result, hostname)
        pdshInfoPrint(denaliVariables, result, hostname, data_line, time_string, mCommandDict, mCommandList, printLock)

    return True



##############################################################################
#
# separatePDSHHostsForBatches(denaliVariables, pdsh_parms)
#
#   This function is called from performPDSHOperation when a host list is
#   passed into PDSH and the OS returns an error saying the arguments passed
#   in are too large.
#
#   The purpose of this function is to "carve up" the hosts into smaller units
#   or batches so that the argument size is small enough to allow PDSH to use
#   and execute with it.
#
#   From some quick testing, the limit for hosts in somewhere around 5000;
#   however, it is completedly dependent upon the combined characters in the
#   string, so it could be more less -- aggregate of host names being considered
#   here.  My testing showed that 5447 hosts could be successfully passed in
#   and used; however, these names did not have ".omniture.com" on the end
#   and were relatively short (i.e., db455.or1, etc.).  Because of that a
#   conservative BATCH_SIZE of 130,000 characters was chosen to be the delimiter
#   for host batches (hopefully it works correctly all of the time).
#

def separatePDSHHostsForBatches(denaliVariables, pdsh_parms):

    batch_counter  = 0
    host_index     = -1
    host_data      = ''
    host_list      = []
    pdsh_parm_data = []
    host_data_list = []
    new_pdsh_parms = []
    offset         = denaliVariables['pdshOffset']
    oStream        = denaliVariables['stream']['output']

    #denaliVariables['debug'] = True

    if offset == -1:
        BATCH_LIMIT = 20    # Limit on the number of times the code
                            # will loop/iterate to create batches
                            # for the hosts passed in.  Each batch
                            # will be ~5000, so 20*5000 = 100,000 hosts
    else:
        # have a much higher limit if a manual offset is supplied
        BATCH_LIMIT = 1000

    for (index, parm) in enumerate(pdsh_parms):
        if len(parm) < 1000:
            # Any PDSH parameter that is NOT the list of hosts; hopefully this
            # is all parameters < 1000 characters in length
            pdsh_parm_data.append(parm)
        else:
            # This is probably the host list and it's big.  Mark the index of
            # it's placement in the pdsh_parms List, remove all commas from the
            # list, and assign the result to "host_data".
            host_index = index
            host_data = parm.replace(',', ' ')
            host_list = host_data.split()

            if denaliVariables['debug'] == True:
                print "host_list length = %s" % len(host_list)
                print "offset           = %s" % offset

    if len(host_list) == 0:
        # probably a small subset of hosts requested
        # assume -2 is the host_list
        # remove hosts from the pdsh_parm_data list
        host_list = pdsh_parm_data.pop(-2)

    if host_index == -1:
        # Weird -- couldn't find one >= 1000 characters, yet we're in this
        # function; just return with pdsh_parms (List of a List)
        if denaliVariables['debug'] == True:
            oStream.write("separatePDSHParmsForBatches function failed")
        return [pdsh_parms]

    else:
        while True:
            # Don't let this while loop run wild -- put a limit on it
            batch_counter += 1
            if batch_counter > BATCH_LIMIT:
                oStream.write("Greater than %d batches have been created via the automated method; investigation suggested." % BATCH_LIMIT)
                return "Failed"

            if offset != -1:
                # Manual host offset requested (count by host, not by character)
                if len(host_list) > offset:
                    pdsh_batch = host_list[:offset]
                    host_data_list.append(','.join(pdsh_batch))
                    host_list  = host_list[offset:]

                    if denaliVariables['debug'] == True:
                        print "PDSH Offset #%d :: %d hosts" % (batch_counter, len(pdsh_batch))
                        print "  First host   :: %s" % pdsh_batch[0]
                        print "  Last host    :: %s" % pdsh_batch[-1]

                else:
                    pdsh_batch = host_list[:]
                    host_data_list.append(','.join(pdsh_batch))

                    if denaliVariables['debug'] == True:
                        print "PDSH Offset #%d :: %d hosts" % (batch_counter, len(pdsh_batch))
                        print "  First host   :: %s" % pdsh_batch[0]
                        print "  Last host    :: %s" % pdsh_batch[-1]
                    break

            else:
                # Automatic host batching - required with a try/exception PDSH exception
                # Count by character
                if len(host_data) > BATCH_SIZE:
                    # Find the nearest [[SPACE]] to the index of BATCH_SIZE in the string
                    location   = host_data.find(' ', BATCH_SIZE)                # find the nearest SPACE
                    pdsh_batch = (host_data[:location]).replace(' ', ',')       # cut the host list, put commas back
                    host_data_list.append(pdsh_batch.strip())                   # append the new batch to a List
                    host_data  = host_data[(location+1):]                       # reset host_data for the next run

                    if denaliVariables['debug'] == True:
                        print "PDSH Batch #%d :: %d hosts" % (batch_counter, len(pdsh_batch.split(',')))
                        print "  First host   :: %s" % pdsh_batch.split(',')[0]
                        print "  Last host    :: %s" % pdsh_batch.split(',')[-1]

                else:
                    # Last iteration of the loop, replace the commas and append the batch to the List
                    pdsh_batch = host_data.strip().replace(' ', ',')
                    host_data_list.append(pdsh_batch)

                    if denaliVariables['debug'] == True:
                        print "PDSH Batch #%d :: %d hosts" % (batch_counter, len(pdsh_batch.split(',')))
                        print "  First host   :: %s" % pdsh_batch.split(',')[0]
                        print "  Last host    :: %s" % pdsh_batch.split(',')[-1]
                    break

    # The host list is batched up for PDSH.  Now integrate it with the existing PDSH
    # commands and options passed in.  This is essentially making multiple commands
    # of the same type, with a different list of hosts for each one based on the
    # separated host list(s) generated just above.
    for hosts in host_data_list:
        npp = list(pdsh_parm_data)
        npp.insert(host_index, hosts)
        new_pdsh_parms.append(npp)

    # Set the offset back to -1.  This prevents problems if one or more of the requested
    # batches have an argument list that is too long.  If that is the case, then the code
    # will do the character separation to resolve the problem instead of repeating a host
    # separation that will surely fail.
    denaliVariables['pdshOffset'] = -1

    if denaliVariables['debug'] == True:
        print "new_pdsh_parms = %s" % new_pdsh_parms

    #denaliVariables['debug'] = False

    return new_pdsh_parms



##############################################################################
#
# pdshInfoRecordData(denaliVariables, pdshDictionary, result, hostname)
#

def pdshInfoRecordData(denaliVariables, pdshDictionary, result, hostname):

    #print "pd = %s" % pdshDictionary

    # add the start time to the dictionary for future use
    if 'start_time' not in pdshDictionary:
        if 'start_time' not in denaliVariables['commandTimeValues']:
            denaliVariables['commandTimeValues'].update({'start_time' : denaliVariables['retryStartTime']['start_time']})
        pdshDictionary.update({'start_time' : denaliVariables['commandTimeValues']['start_time']})

    # PDSH burped (no data returned).  Don't record this as it will cause unneeded
    # concern over a non-issue.  Just return the dictionary with the current data
    if hostname == "MISSING_HOSTNAME":
        return pdshDictionary

    if hostname in pdshDictionary:
        success_count = pdshDictionary[hostname]["success_count"]
        failure_count = pdshDictionary[hostname]["failure_count"]
        normal_count  = pdshDictionary[hostname]["normal_count"]
    else:
        # avoid recording debug pdsh "hostnames"
        if hostname.strip() == "Connect time" or hostname.strip() == "Command time" or hostname.strip() == "Failures":
            return pdshDictionary

        pdshDictionary.update({hostname:{}})
        pdshDictionary[hostname]["success_count"] = 0
        pdshDictionary[hostname]["failure_count"] = 0
        pdshDictionary[hostname]["normal_count"]  = 0
        success_count = 0
        failure_count = 0
        normal_count  = 0

    if result == 0:
        success_count += 1
        pdshDictionary[hostname]["success_count"] = success_count
    elif result == 1:
        failure_count += 1
        pdshDictionary[hostname]["failure_count"] = failure_count
    else:
        normal_count += 1
        pdshDictionary[hostname]["normal_count"]  = normal_count

    return pdshDictionary



##############################################################################
#
# createProgressIndicator(denaliVariables, hostname, mCommandDict, mCommandList, function='pdsh')
#

def createProgressIndicator(denaliVariables, hostname, mCommandDict, mCommandList, function='pdsh'):

    # Which of the below 5 to show for a progress indicator
    PROGRESS_INDICATOR = denaliVariables['commandProgressBar']

    # if the progress indicator is disabled, return an empty string (display nothing)
    if denaliVariables['commandProgress'] == False or PROGRESS_INDICATOR == PROGRESS_DISABLED:
        return ''

    # definitions for progress bar building blocks
    PROGRESS_PERCENTAGE         = 1
    PROGRESS_REMAINING          = 2
    PROGRESS_ACTIVE_DEVICE      = 3
    PROGRESS_BAR_BLOCK          = 4
    PROGRESS_SUCCESS            = 5
    PROGRESS_FAILURE            = 6
    PROGRESS_LOGDATA            = 7
    PROGRESS_HOSTKEY            = 8
    PROGRESS_SPINNER            = 9
    PROGRESS_START_STRING       = 10
    PROGRESS_MIDDLE_STRING      = 11
    PROGRESS_END_STRING         = 12
    PROGRESS_SPACE_STRING       = 13
    PROGRESS_COMBINED           = 14
    PROGRESS_COMBINED_REMAINING = 15

    function_progress_indicators = {
        'pdsh': {
                    PROGRESS_DEFAULT  : [
                                            PROGRESS_START_STRING,
                                            PROGRESS_PERCENTAGE,
                                            PROGRESS_MIDDLE_STRING,
                                            PROGRESS_REMAINING,
                                            PROGRESS_END_STRING,
                                        ],
                    PROGRESS_ADVANCED : [
                                            PROGRESS_START_STRING,
                                            PROGRESS_PERCENTAGE,
                                            PROGRESS_MIDDLE_STRING,
                                            PROGRESS_ACTIVE_DEVICE,
                                            PROGRESS_MIDDLE_STRING,
                                            PROGRESS_REMAINING,
                                            PROGRESS_END_STRING,
                                        ],
                    PROGRESS_BAR      : [
                                            PROGRESS_START_STRING,
                                            PROGRESS_SPINNER,
                                            PROGRESS_END_STRING,
                                            PROGRESS_START_STRING,
                                            PROGRESS_ACTIVE_DEVICE,
                                            PROGRESS_MIDDLE_STRING,
                                            PROGRESS_REMAINING,
                                            PROGRESS_END_STRING,
                                            PROGRESS_BAR_BLOCK,
                                            PROGRESS_START_STRING,
                                            PROGRESS_LOGDATA,
                                            PROGRESS_FAILURE,
                                            PROGRESS_SUCCESS,
                                            PROGRESS_END_STRING,
                                        ],
                    PROGRESS_TEST     : [],
                },

        'scp':  {
                    PROGRESS_DEFAULT  : [
                                            PROGRESS_START_STRING,
                                            PROGRESS_COMBINED_REMAINING,
                                            PROGRESS_END_STRING,
                                            PROGRESS_SPACE_STRING,
                                        ],
                    PROGRESS_ADVANCED : [
                                            PROGRESS_START_STRING,
                                            PROGRESS_COMBINED,
                                            PROGRESS_END_STRING,
                                            PROGRESS_SPACE_STRING,
                                        ],
                    PROGRESS_BAR      : [
                                            PROGRESS_START_STRING,
                                            PROGRESS_SPINNER,
                                            PROGRESS_END_STRING,
                                            PROGRESS_BAR_BLOCK,
                                            PROGRESS_SUCCESS,
                                            PROGRESS_FAILURE,
                                        ],
                    PROGRESS_TEST     : [],
                },

        'ssh':  {
                    PROGRESS_DEFAULT  : [
                                            PROGRESS_START_STRING,
                                            PROGRESS_PERCENTAGE,
                                            PROGRESS_MIDDLE_STRING,
                                            PROGRESS_REMAINING,
                                            PROGRESS_END_STRING,
                                        ],
                    PROGRESS_ADVANCED : [
                                            PROGRESS_START_STRING,
                                            PROGRESS_COMBINED,
                                            PROGRESS_END_STRING,
                                            PROGRESS_SPACE_STRING,
                                        ],
                    PROGRESS_BAR      : [
                                            PROGRESS_START_STRING,
                                            PROGRESS_SPINNER,
                                            PROGRESS_END_STRING,
                                            PROGRESS_START_STRING,
                                            PROGRESS_ACTIVE_DEVICE,
                                            PROGRESS_MIDDLE_STRING,
                                            PROGRESS_REMAINING,
                                            PROGRESS_END_STRING,
                                            PROGRESS_BAR_BLOCK,
                                            PROGRESS_START_STRING,
                                            PROGRESS_FAILURE,
                                            PROGRESS_LOGDATA,
                                            PROGRESS_HOSTKEY,
                                            PROGRESS_SUCCESS,
                                            PROGRESS_END_STRING,
                                        ],
                    PROGRESS_TEST     : [],
                },
    }

    if hostname.find('.omniture.com') != -1:
        host_name = hostname[:hostname.find('.omniture.com')]
    else:
        host_name = hostname

    if 'devices_processed' not in denaliVariables['commandProgressID']:
        denaliVariables['commandProgressID'].update({'devices_processed':set()})
    denaliVariables['commandProgressID']['devices_processed'].update([host_name])

    # collect generic statistics used by each type of progress indicator
    if denaliVariables['pdshSeparate'] != False:
        curCount = len(mCommandList)
    else:
        curCount = len(denaliVariables['commandProgressID']['devices_processed'])

    totCount   = denaliVariables['commandProgressID']['maxCount']
    totChCount = len(str(totCount))

    # Special case:  scp has a start and end function ('scp_start'/'scp_end')
    # If this is an scp function, it is accessed as 'scp' solely.
    if function.startswith('scp'):
        use_function = 'scp'
    elif function.startswith('ssh'):
        use_function = 'ssh'
    else:
        use_function = function

    # Pull out the order in which to create the progress indicator for this
    # specific function (pdsh, scp, etc.)
    progressBlocks = function_progress_indicators[use_function][PROGRESS_INDICATOR]

    progress_indicator_string = ''

    for (index, block) in enumerate(progressBlocks):
        if block == PROGRESS_PERCENTAGE:
            block_string = buildPercentageBlock(denaliVariables, function, mCommandDict, mCommandList, curCount, totCount)
        elif block == PROGRESS_REMAINING:
            block_string = buildRemainingBlock(denaliVariables, function, mCommandDict, mCommandList, curCount, totCount, totChCount, 'r:')
        elif block == PROGRESS_ACTIVE_DEVICE:
            block_string = buildActiveDeviceBlock(denaliVariables, function, host_name, totCount, totChCount, mCommandDict, mCommandList)
        elif block == PROGRESS_BAR_BLOCK:
            block_string = buildPercentageBlock(denaliVariables, function, mCommandDict, mCommandList, curCount, totCount)
            block_string = buildProgressBarBlock(denaliVariables, function, mCommandDict, mCommandList, totCount, totChCount, block_string, '', '')
        elif block == PROGRESS_SUCCESS:
            block_string = buildSuccessBlock(denaliVariables, function, mCommandDict, mCommandList, totChCount, ' S', ' ')
        elif block == PROGRESS_FAILURE:
            block_string = buildFailureBlock(denaliVariables, function, mCommandDict, mCommandList, totChCount, ' Fail', ' ')
        elif block == PROGRESS_LOGDATA:
            block_string = buildLogDataBlock(denaliVariables, function, mCommandDict, mCommandList, totChCount, ' Norm', ' ')
        elif block == PROGRESS_HOSTKEY:
            block_string = buildHostKeyBlock(denaliVariables, function, mCommandDict, mCommandList, totChCount, ' Key', ' ')
        elif block == PROGRESS_SPINNER:
            block_string = buildSpinnerBlock(denaliVariables, function, mCommandDict, mCommandList)
        elif block == PROGRESS_START_STRING:
            block_string = '[ '
        elif block == PROGRESS_MIDDLE_STRING:
            block_string = ' | '
        elif block == PROGRESS_END_STRING:
            block_string = ' ]'
        elif block == PROGRESS_SPACE_STRING:
            block_string = ' '
        elif block == PROGRESS_COMBINED:
            block_string = buildCombinedBlock(denaliVariables, function, mCommandDict, mCommandList, curCount, totCount, totChCount)
        elif block == PROGRESS_COMBINED_REMAINING:
            block_string = buildCombinedRemainingBlock(denaliVariables, function, mCommandDict, mCommandList, curCount, totCount, totChCount)
        else:
            block_string = ''

        progress_indicator_string += block_string

    # The progress bar block string needs to be printed here because all output
    # is supressed in the direct print/output for each function.
    if PROGRESS_INDICATOR == PROGRESS_BAR:
        sys.stdout.write(progress_indicator_string + '\r')
        sys.stdout.flush()

    return progress_indicator_string



##############################################################################
#
# buildPercentageBlock(denaliVariables, function, mCommandDict, mCommandList, current_count, total_count, startString='', endString='')
#

def buildPercentageBlock(denaliVariables, function, mCommandDict, mCommandList, current_count, total_count, startString='', endString=''):

    if function == 'scp_start':
        if startString is not None:
            startString = "S:"
        else:
            startString = ''
        current_count = mCommandDict['scp_start_count']
    elif function == 'scp_end':
        if startString is not None:
            startString = "C:"
        else:
            startString = ''
        current_count = mCommandDict['scp_complete_count']
    elif function == 'ssh_start':
        current_count = mCommandDict['ssh_start_count']
    elif function == 'ssh_end':
        current_count = mCommandDict['ssh_complete_count']

    # make sure the percentage never goes above 100
    device_percent = round(((float(current_count) / float(total_count)) * 100), PERCENT_ROUND_DECIMALS)
    if device_percent > 100:
        device_percent = 100.0

    return startString + (str(device_percent) + '%').rjust(PERCENT_JUSTIFICATION) + endString



##############################################################################
#
# buildRemainingBlock(denaliVariables, function, mCommandDict, mCommandList)
#

def buildRemainingBlock(denaliVariables, function, mCommandDict, mCommandList, current_count, total_count, total_c_chars, startString='', endString=''):

    if function   == 'scp_start':
        current_count = mCommandDict['scp_start_count']
    elif function == 'scp_end':
        current_count = mCommandDict['scp_complete_count']
    elif function == 'ssh_start':
        current_count = mCommandDict['ssh_start_count']
    elif function == 'ssh_end':
        current_count = mCommandDict['ssh_complete_count']

    # make sure the count never goes negative
    devices_remaining = total_count - current_count
    if devices_remaining < 0:
        devices_remaining = 0

    return startString + str(devices_remaining).rjust(total_c_chars) + endString



##############################################################################
#
# buildCombinedBlock(denaliVariables, function, mCommandDict, mCommandList, current_count, total_count, total_c_chars)
#
#   This function is a combination one that puts together the starting and ending
#   percentages and remaining count.  This is useful for an operation that has a
#   beginning and an end where both need to be tracked.  It's a little different from
#   the other 'block' functions as it uses a dictionary with unique data to control
#   the different pieces needed.
#

def buildCombinedBlock(denaliVariables, function, mCommandDict, mCommandList, current_count, total_count, total_c_chars):

    if function.startswith('scp'):

        scp_adv_dict      =     {
                                    0: {'scp_string': "S:", 'scp_count' : mCommandDict['scp_start_count']},
                                    1: {'scp_string': "C:", 'scp_count' : mCommandDict['scp_complete_count']},
                                    2: {'scp_string': "O:", 'scp_count' : mCommandDict['scp_in_flight']}
                                }
        scp_remain_string = 'r:'
        progress_string   = ''
        last_dict_index   = len(scp_adv_dict) - 1

        for (index, scp_data) in enumerate(scp_adv_dict):
            scp_string = scp_adv_dict[scp_data]['scp_string']
            scp_count  = scp_adv_dict[scp_data]['scp_count']

            if index != last_dict_index:
                scp_remaining = str(total_count - scp_count).rjust(total_c_chars)
            else:
                scp_remaining = str(scp_count).rjust(3)

            scp_percent = (str(round(((float(scp_count) / float(total_count)) * 100), PERCENT_ROUND_DECIMALS)) + '%').rjust(PERCENT_JUSTIFICATION)
            progress_string += scp_string + scp_percent + ' ' + scp_remain_string + scp_remaining

            if index != last_dict_index:
                progress_string += ' | '

    elif function.startswith('ssh'):

        ssh_adv_dict      =     {
                                    0: {'ssh_string': "S:", 'ssh_count' : mCommandDict['ssh_start_count']},
                                    1: {'ssh_string': "C:", 'ssh_count' : mCommandDict['ssh_complete_count']},
                                    2: {'ssh_string': "O:", 'ssh_count' : mCommandDict['ssh_in_flight']}
                                }
        ssh_remain_string = 'r:'
        progress_string   = ''
        last_dict_index   = len(ssh_adv_dict) - 1

        for (index, ssh_data) in enumerate(ssh_adv_dict):
            ssh_string = ssh_adv_dict[ssh_data]['ssh_string']
            ssh_count  = ssh_adv_dict[ssh_data]['ssh_count']

            if index != last_dict_index:
                ssh_remaining = str(total_count - ssh_count).rjust(total_c_chars)
            else:
                ssh_remaining = str(ssh_count).rjust(3)

            ssh_percent = (str(round(((float(ssh_count) / float(total_count)) * 100), PERCENT_ROUND_DECIMALS)) + '%').rjust(PERCENT_JUSTIFICATION)
            progress_string += ssh_string + ssh_percent + ' ' + ssh_remain_string + ssh_remaining

            if index != last_dict_index:
                progress_string += ' | '

    else:
        return ''

    return progress_string



##############################################################################
#
# buildCombinedRemainingBlock(denaliVariables, function, mCommandDict, mCommandList, curCount, total_count, total_c_chars)
#

def buildCombinedRemainingBlock(denaliVariables, function, mCommandDict, mCommandList, curCount, total_count, total_c_chars):

    if function.startswith('scp'):

        scp_combined_remain_dict =  {
                                        0: {'scp_string': "Sr:", 'scp_count' : mCommandDict['scp_start_count']},
                                        1: {'scp_string': "Cr:", 'scp_count' : mCommandDict['scp_complete_count']},
                                    }

        progress_string = ''
        last_dict_index = len(scp_combined_remain_dict) - 1

        for (index, scp_data) in enumerate(scp_combined_remain_dict):
            scp_string       = scp_combined_remain_dict[scp_data]['scp_string']
            scp_count        = scp_combined_remain_dict[scp_data]['scp_count']
            scp_remaining    = total_count - scp_count
            if scp_remaining < 0:
                scp_remaining = 0
            scp_remaining    = str(scp_remaining).rjust(total_c_chars)
            progress_string += scp_string + scp_remaining

            if index != last_dict_index:
                progress_string += ' | '

    elif function.startswith('ssh'):

        ssh_combined_remain_dict =  {
                                        0: {'ssh_string': "Sr:", 'ssh_count' : mCommandDict['ssh_start_count']},
                                        1: {'ssh_string': "Cr:", 'ssh_count' : mCommandDict['ssh_complete_count']},
                                    }

        progress_string = ''
        last_dict_index = len(ssh_combined_remain_dict) - 1

        for (index, ssh_data) in enumerate(ssh_combined_remain_dict):
            ssh_string       = ssh_combined_remain_dict[ssh_data]['ssh_string']
            ssh_count        = ssh_combined_remain_dict[ssh_data]['ssh_count']
            ssh_remaining    = total_count - ssh_count
            if ssh_remaining < 0:
                ssh_remaining = 0
            ssh_remaining    = str(ssh_remaining).rjust(total_c_chars)
            progress_string += ssh_string + ssh_remaining

            if index != last_dict_index:
                progress_string += ' | '

    else:
        return ''

    return progress_string



##############################################################################
#
# buildActiveDeviceBlock(denaliVariables, function, hostname, mCommandDict, mCommandList, startString='', endString='')
#

def buildActiveDeviceBlock(denaliVariables, function, hostname, total_count, total_c_chars, mCommandDict, mCommandList, startString='', endString=''):

    # Is there an entry for the host (this only matters for the 'ActiveDeviceBlock' function)
    if hostname not in denaliVariables['commandProgressID']:
        # Handle the error case where the hostname isn't found -- put question marks for the number
        # The value wanted is the 'number' of the device (in relation to the rest of the devices) and
        # the total number of devices.  This is the 'active device' number prepared here.
        avail_string = denaliVariables['commandProgressID']['host_not_found']
    else:
        # Use the already created string of the device (no prep necessary -- just pull it and use it).
        avail_string = denaliVariables['commandProgressID'][hostname]['progress_string']

    return startString + avail_string + endString



##############################################################################
#
# buildProgressBarBlock(denaliVariables, function, mCommandDict, mCommandList, total_count, total_c_chars, percent_done, startString='', endString='')
#

def buildProgressBarBlock(denaliVariables, function, mCommandDict, mCommandList, total_count, total_c_chars, percent_done, startString='', endString=''):

    PROGRESS_BAR_MULTIPLIER = 0.45
    PROGRESS_BAR_CHARACTER  = '-'
    PROGRESS_BAR_POINTER    = '>['
    scp_remain_string       = 'r:'

    if function == 'pdsh':
        percent_done_int    = int(percent_done[:percent_done.index('.')])
        progress_bar        = PROGRESS_BAR_CHARACTER * int(percent_done_int * PROGRESS_BAR_MULTIPLIER)
        progress_bar_total  = ' ' * (int(100.0 * PROGRESS_BAR_MULTIPLIER) - len(progress_bar))
        progress_string     = '|' + progress_bar + PROGRESS_BAR_POINTER + percent_done + ']' + progress_bar_total + '|'

    elif function.startswith('ssh'):
        percent_done_int    = int(percent_done[:percent_done.index('.')])
        progress_bar        = PROGRESS_BAR_CHARACTER * int(percent_done_int * PROGRESS_BAR_MULTIPLIER)
        progress_bar_total  = ' ' * (int(100.0 * PROGRESS_BAR_MULTIPLIER) - len(progress_bar))
        progress_string     = '|' + progress_bar + PROGRESS_BAR_POINTER + percent_done + ']' + progress_bar_total + '|'

    elif function.startswith('scp'):

        # Shrink the progress bar by 50% over the pdsh version (by default)
        # because there are two progress bars shown at the same time on screen
        PROGRESS_BAR_MULTIPLIER *= SCP_BAR_MULTIPLIER

        progress_string = ''
        scp_bar_dict    =   {
                                0: {'scp_string': " St:",  'scp_count' : mCommandDict['scp_start_count']},
                                1: {'scp_string': " Cmp:", 'scp_count' : mCommandDict['scp_complete_count']}
                            }

        for bar_data in scp_bar_dict:
            scp_string          = scp_bar_dict[bar_data]['scp_string']
            scp_count           = scp_bar_dict[bar_data]['scp_count']
            scp_percent         = (str(round(((float(scp_count) / float(total_count)) * 100), PERCENT_ROUND_DECIMALS)) + '%').rjust(PERCENT_JUSTIFICATION)
            scp_remaining       = str(total_count - scp_count).rjust(total_c_chars)
            scp_percent_int     = int(scp_percent[:scp_percent.index('.')])
            progress_bar_line   = PROGRESS_BAR_CHARACTER * int(scp_percent_int * PROGRESS_BAR_MULTIPLIER)
            progress_bar_space  = ' ' * (int(100.0 * PROGRESS_BAR_MULTIPLIER) - len(progress_bar_line))

            progress_string    += "%s[ %s%s ]" % (scp_string, scp_remain_string, scp_remaining)
            progress_string    += '|' + progress_bar_line + PROGRESS_BAR_POINTER + scp_percent + ']' + progress_bar_space + '| '

    else:
        return ''

    return progress_string



##############################################################################
#
# buildSuccessBlock(denaliVariables, function, mCommandDict, mCommandList, total_c_chars, startString='', endString='')
#

def buildSuccessBlock(denaliVariables, function, mCommandDict, mCommandList, total_c_chars, startString='', endString=''):

    if function == 'pdsh':
        success_count = str(denaliVariables['commandProgressID']['success']).rjust(total_c_chars)
    elif function.startswith('scp'):
        success_count = str(mCommandDict['scp_success']).rjust(total_c_chars)
    elif function.startswith('ssh'):
        success_count = str(mCommandDict['ssh_success']).rjust(total_c_chars)

    return startString + ':' + success_count + endString



##############################################################################
#
# buildFailureBlock(denaliVariables, function, mCommandDict, mCommandList, total_c_chars, startString='', endString='')
#

def buildFailureBlock(denaliVariables, function, mCommandDict, mCommandList, total_c_chars, startString='', endString=''):

    if function == 'pdsh':
        failure_count = str(denaliVariables['commandProgressID']['failure']).rjust(total_c_chars)
    elif function.startswith('scp'):
        failure_count = str(mCommandDict['scp_failure']).rjust(total_c_chars)
    elif function.startswith('ssh'):
        failure_count = str(mCommandDict['ssh_failure']).rjust(total_c_chars)

    return startString + ':' + failure_count + endString



##############################################################################
#
# buildLogDataBlock(denaliVariables, function, mCommandDict, mCommandList, total_c_chars, startString='', endString='')
#

def buildLogDataBlock(denaliVariables, function, mCommandDict, mCommandList, total_c_chars, startString='', endString=''):

    if function == 'pdsh' or function.startswith('ssh'):
        logdata_count = str(denaliVariables['commandProgressID']['logdata']).rjust(total_c_chars)

    return startString + ':' + logdata_count + endString



##############################################################################
#
# buildHostKeyBlock(denaliVariables, function, mCommandDict, mCommandList, total_c_chars, startString='', endString='')
#

def buildHostKeyBlock(denaliVariables, function, mCommandDict, mCommandList, total_c_chars, startString='', endString=''):

    if function.startswith('ssh'):
        hostkey_count = str(denaliVariables['commandProgressID']['hostkey']).rjust(total_c_chars)

    return startString + ':' + hostkey_count + endString



##############################################################################
#
# buildSpinnerBlock(denaliVariables, function, mCommandDict, mCommandList, startString='', endString='')
#

def buildSpinnerBlock(denaliVariables, function, mCommandDict, mCommandList, startString='', endString=''):

    COMMAND_SPINNER = [ '|', '/', '-', '\\' ]
    spinner_string  = COMMAND_SPINNER[denaliVariables['commandSpinner']]

    # update the spinner index
    denaliVariables['commandSpinner'] += 1
    if denaliVariables['commandSpinner'] >= 4:
        denaliVariables['commandSpinner'] = 0

    return spinner_string



##############################################################################
#
# commandCategorization(denaliVariables, hostname, mCommandDict, mCommandList, result)
#

def commandCategorization(denaliVariables, hostname, mCommandDict, mCommandList, result):

    SUCCESS = { 'message': 'SUCCESS', 'color': colors.fg.lightgreen }
    FAILURE = { 'message': 'FAILURE', 'color': colors.fg.lightred   }
    NORMAL  = { 'message': 'LOGDATA', 'color': colors.fg.darkgrey   }
    HOSTKEY = { 'message': 'HOSTKEY', 'color': colors.fg.yellow     }
    KEYPASS = { 'message': 'KEYPASS', 'color': colors.fg.blue       }
    UNKNOWN = { 'message': 'UNKNOWN', 'color': colors.fg.cyan       }

    if 'success' not in denaliVariables['commandProgressID']:
        denaliVariables['commandProgressID'].update({'success':0, 'success_devices': set()})
        denaliVariables['commandProgressID'].update({'failure':0, 'failure_devices': set()})
        denaliVariables['commandProgressID'].update({'logdata':0, 'normal_devices' : set()})
        denaliVariables['commandProgressID'].update({'hostkey':0, 'hostkey_devices': set()})
        denaliVariables['commandProgressID'].update({'keypass':0, 'keypass_devices': set()})

    # First: categorize the type of log line returned
    if denaliVariables['pdshSeparate'] != False:
        # With a segmented work-flow, there are multiple instances of centralized pdsh and
        # as such, a different method for tracking stats and process synchronization is required.
        if result == 0:
            # [S]uccess log line
            data_variable = SUCCESS
            if hostname not in mCommandList:
                mCommandDict['pdsh_success_count'] += 1
                mCommandList.append(hostname)
        elif result == 1:
            # [E]rror log line
            data_variable = FAILURE
            if hostname not in mCommandList:
                mCommandDict['pdsh_failure_count'] += 1
                mCommandList.append(hostname)
        else:
            # [N]ormal log line
            data_variable = NORMAL
            if hostname not in mCommandList:
                mCommandDict['pdsh_normal_count'] += 1
                mCommandList.append(hostname)

    else:
        # With a non-segemented pdsh work-flow, everything flows through a central location
        # and as such the variables do not need any special process synchronization outside
        # of the print lock (which this function operates under by default).
        if result == 0:
            # [S]uccess log line
            data_variable = SUCCESS
            if hostname not in denaliVariables['commandProgressID']['success_devices']:
                denaliVariables['commandProgressID']['success'] += 1
                denaliVariables['commandProgressID']['success_devices'].update([hostname])
        elif result == 1 or result == 255 or result == 5:
            # [E]rror log line
            data_variable = FAILURE
            if hostname not in denaliVariables['commandProgressID']['failure_devices']:
                denaliVariables['commandProgressID']['failure'] += 1
                denaliVariables['commandProgressID']['failure_devices'].update([hostname])
        elif result == 2:
            # [N]ormal log line
            data_variable = NORMAL
            if hostname not in denaliVariables['commandProgressID']['normal_devices']:
                denaliVariables['commandProgressID']['logdata'] += 1
                denaliVariables['commandProgressID']['normal_devices'].update([hostname])
        elif result == 3:
            # [K]ey failure log line
            data_variable = HOSTKEY
            if hostname not in denaliVariables['commandProgressID']['hostkey_devices']:
                denaliVariables['commandProgressID']['hostkey'] += 1
                denaliVariables['commandProgressID']['hostkey_devices'].update([hostname])
        elif result == 4:
            # [K]ey/password permission failure log line
            data_variable = KEYPASS
            if hostname not in denaliVariables['commandProgressID']['keypass_devices']:
                denaliVariables['commandProgressID']['keypass'] += 1
                denaliVariables['commandProgressID']['keypass_devices'].update([hostname])

    return data_variable



##############################################################################
#
# pdshInfoPrint(denaliVariables, result, hostname, data_line, time_string, mCommandDict, mCommandList, printLock)
#

def pdshInfoPrint(denaliVariables, result, hostname, data_line, time_string, mCommandDict, mCommandList, printLock):

    PROGRESS_INDICATOR      = denaliVariables['commandProgressBar']     # which of the below 3 to show for a progress indicator
    PERCENTAGE_REMAINING    = 0     # percentage indicator and devices remaining displayed
    PERCENTAGE_PLUS         = 1     # percentage plus others stats at the far-left of the log line
    PROGRESS_BAR            = 2     # progress bar only with percentage/percentage-plus stats

    COMMAND_SPINNER         = [ '|', '/', '-', '\\' ]

    SUCCESS = { 'message': 'SUCCESS', 'color': colors.fg.lightgreen }
    FAILURE = { 'message': 'FAILURE', 'color': colors.fg.lightred   }
    NORMAL  = { 'message': 'LOGDATA', 'color': colors.fg.darkgrey   }
    #NORMAL = { 'message': 'NORMAL ', 'color': colors.fg.darkgrey   }

    if denaliVariables['pdshSeparate'] != False:
        # Careful, if separated data is run in a no-fork mode, this log file data location will
        # be the same between runs (and it will confuse you when debugging) because it is the
        # same process space (same denaliVariables, etc.).  That is why this is assigned directly
        # with the required name (not a += addition as with a single-run PDSH operation).
        #log_filename = 'denali-pdsh_log-' + separator_id + '-' + time_string + ".txt"
        log_filename = denaliVariables['pdsh_log_file']
    else:
        log_filename = denaliVariables['pdsh_log_file']

    #data_line = data_line.decode('ascii', 'ignore')
    hostname = str(hostname)

    printLock.acquire()

    # categorize the return code
    data_variable = commandCategorization(denaliVariables, hostname, mCommandDict, mCommandList, result)

    # retrieve the progress string
    progress_indicator_string = createProgressIndicator(denaliVariables, hostname, mCommandDict, mCommandList)

    #
    # Output of the log data

    # See if output has been limited to specific types
    if len(denaliVariables['commandOutput']) != 0:
        print_data = False
        if ('failure' in denaliVariables['commandOutput'] and data_variable == FAILURE or
            'success' in denaliVariables['commandOutput'] and data_variable == SUCCESS or
            'normal'  in denaliVariables['commandOutput'] and data_variable == NORMAL):
            print_data = True
    else:
        print_data = True

    # do not print data for an empty line received from pdsh
    if hostname == "MISSING_HOSTNAME":
        print_data = False

    # don't print anything with scp-pull multi-file request
    if denaliVariables['scpMultiFile'] == True:
        ent_chars = [ '|', '/', '-', '\\' ]
        index     = denaliVariables['pdshEntertainment']
        sys.stdout.write(ent_chars[index] + '\b')
        print_data = False
        index    += 1
        if index > 3:
            denaliVariables['pdshEntertainment'] = 0
        else:
            denaliVariables['pdshEntertainment'] = index
        sys.stdout.flush()

    if print_data == False:
        pass
    else:
        if (print_data == True and (PROGRESS_INDICATOR == PERCENTAGE_REMAINING or
                                    PROGRESS_INDICATOR == PERCENTAGE_PLUS or
                                    PROGRESS_INDICATOR == PROGRESS_DISABLED)):
            if denaliVariables['nocolors'] == False:
                print "%s[" % progress_indicator_string + colors.bold + data_variable['color'] + data_variable['message'] + colors.reset + "]: %s: %s" % (hostname, data_line)
            else:
                print "%s[" % progress_indicator_string + data_variable['message'] + "]: %s: %s" % (hostname, data_line)
            sys.stdout.flush()
        else:
            # handle the case where the user requested only errors -- show updates anyway (without printing log lines)
            if PROGRESS_INDICATOR != PROGRESS_BAR:
                sys.stdout.write("%s\r" % progress_indicator_string)
                sys.stdout.flush()

    printLock.release()

    # debug pdsh code -- again.  Don't record it in the logs
    if hostname.strip() == "Connect time" or hostname.strip() == "Command time" or hostname.strip() == "Failures":
        return

    if denaliVariables['noLogging'] == False:
        # write the device:success/failure/normal:return code to a log file
        state_log_filename = log_filename + '.state'
        state_data_line = hostname + ':' + data_variable['message'] + ':' + getReturnCode(data_line) + '\n'
        with open(state_log_filename, 'a') as state_log_file:
            state_log_file.write(state_data_line)

        # write the data to a log file
        log_data_line = "[" + data_variable['message'] + "]: %s: %s\n" % (hostname, data_line)
        with open(log_filename, 'a') as log_file:
            log_file.write(log_data_line)

    return



##############################################################################
#
# getReturnCode(data_line)
#

def getReturnCode(data_line):

    if (data_line.startswith('result = 1') or
        # failure / error
        data_line.startswith('return = 1') or
        data_line.startswith('return 1') or
        data_line.startswith('result 1')):
        return '1'
    elif (data_line.startswith('result = 0') or
        # success
        data_line.startswith('return = 0') or
        data_line.startswith('return 0') or
        data_line.startswith('result 0')):
        return '0'
    elif data_line.find('ssh exited with exit code') != -1:
        # ssh error exit code -- mark as a failure/error
        return data_line
    else:
        # unknown -- mark as 'normal'
        return '0'



##############################################################################
#
# pdshAppCountSummary(denaliVariables, host_list, sent_pdshDictionary, log_filename_list)
#

def pdshAppCountSummary(denaliVariables, host_list, sent_pdshDictionary, log_filename_list):

    if denaliVariables["pdshAppCount"] != -1:
        # determine the number of commands run -- pdsh_app_count
        app_count = determineNumberOfPDSHCommands(denaliVariables)
        denaliVariables["pdshAppCount"] = app_count

    # Ensure the app_count is never zero (as this would give a divide by zero error)
    if "total" in denaliVariables["pdshAppCount"]:
        app_count = denaliVariables["pdshAppCount"]["total"]
        app_order = denaliVariables["pdshAppCount"]["order"]
    else:
        app_count = int(denaliVariables["pdshAppCount"])
        app_order = "Scripted"
    if app_count == 0:
        app_count = 1

    columnNames = [['Log Lines' , 11],
                   ['Success'   , 10],
                   ['Failure'   , 10],
                   ['% Complete [S%/F%]', 20]]

    for (index, log_filename) in enumerate(log_filename_list):
        if denaliVariables['pdshSeparate'] != False:
            pdshAppCountTitleOutput(denaliVariables, host_list[index], app_count, app_order)
            pdshDictionary = sent_pdshDictionary[index][1]
            pdshDictionary.pop('pdsh_log_file', None)
            hostname_list  = pdshDictionary.keys()
        else:
            pdshAppCountTitleOutput(denaliVariables, host_list, app_count, app_order)
            pdshDictionary = sent_pdshDictionary
            hostname_list  = host_list[:]

        printCommandHeader(host_list, columnNames)

        for hostname in hostname_list:
            success   = pdshDictionary[hostname]["success_count"]
            failure   = pdshDictionary[hostname]["failure_count"]
            log_lines = pdshDictionary[hostname]["normal_count"]

            print ' ' + hostname.ljust(max_host_length) + ' '*7,
            print str(log_lines).rjust(7),
            print str(success).rjust(8),
            print str(failure).rjust(9),

            complete_success = (float(success) / app_count) * 100
            complete_failure = (float(failure) / app_count) * 100

            if denaliVariables["nocolors"] == True:
                completion_percent = "%5.1f%% / %5.1f%%" % (complete_success, complete_failure)
                print completion_percent.rjust(20)
            else:
                # because of the colors added to the print statement, the code here does a
                # manual right-justify procedure.  [[ 100.0% / 0.0% ]]
                # This is 13 character in length (w/o color), and 41 in length (with).
                completion_percent  = "%5.1f%% / %5.1f%%" % (complete_success, complete_failure)
                length              = len(completion_percent)
                # column length of '% Complete [S%/F%]' from above is 20, so ...
                right_justify       = (20 - length)

                completion_percent  = colors.bold + colors.fg.lightgreen + ("%5.1f%%" % complete_success) + colors.reset + ' / '
                completion_percent += colors.bold + colors.fg.lightred   + ("%5.1f%%" % complete_failure) + colors.reset
                print completion_percent.rjust(48)

        print
        print " Note:"
        print "   Completion percentages only make sense if the commands issued each report back"
        print "   successful ('return = 0') or not ('return = 1').  If the success or failure isn't"
        print "   reported, then additional one-off commands are required to verify execution success"
        print "   or failure."
        print
        print " PDSH Log Filename: %s" % log_filename
        print

    return True



##############################################################################
#
# pdshAppCountTitleOutput(denaliVariables, host_list, app_count, app_order)
#

def pdshAppCountTitleOutput(denaliVariables, host_list, app_count, app_order):

    print
    print
    print "----------------------------------"
    print "| PDSH Command Execution Summary |"
    print "----------------------------------"
    print
    if denaliVariables['pdshSeparate'] != False:
        if denaliVariables['hostCommands']['active'] == True:
            print " Total number of hosts      : %i" % len(denaliVariables['serverList'])
        else:
            print " Segmented Group Name       : %s" % host_list[0]
            print " Total number of hosts      : %i" % host_list[1]
    else:
        print " Total number of hosts      : %i" % len(host_list)

    print " Commands executed per host : %i" % app_count
    print " Command execution order    : %s    [Key: s=single, a=and, o=or]" % app_order
    print

    return



##############################################################################
#
# pdshDshbakTitleOutput(denaliVariables, host_list)
#

def pdshDshbakTitleOutput(denaliVariables, host_list):

    if denaliVariables['pdshDshbakLog'] == True:
        print "----------------------------------------------"
        print "| PDSH Command Execution Log piped to dshbak |"
        print "----------------------------------------------"
    else:
        print "-----------------------------------------------"
        print "| PDSH Command [return codes] piped to dshbak |"
        print "-----------------------------------------------"
    print
    if denaliVariables['pdshSeparate'] != False:
        if denaliVariables['hostCommands']['active'] == True:
            print " Total number of hosts : %i" % len(denaliVariables['serverList'])
        else:
            print " Segmented Group Name  : %s" % host_list[0]
            print " Total number of hosts : %i" % host_list[1]
    else:
        summary_log_filename = denaliVariables['pdsh_log_file'] + '.summary'
        print " Total number of hosts : %i" % len(host_list)
    print

    # Read in the state log file and return host lists
    # The 'rcode' file is created in this function as well
    (failure_devices, success_devices, normal_devices, dual_devices) = readStateLogFile(denaliVariables, host_list)

    # do not print the device categorization summary unless '--summary' is requested
    if denaliVariables['summary'] == False:
        return

    if denaliVariables['pdshSeparate'] != False:
        pass
    else:
        if denaliVariables['noLogging'] == False:
            with open(summary_log_filename, 'a') as log_file:
                log_file.write("Denali Command Submitted:\n")
                log_file.write(denaliVariables['argumentList'] + '\n\n')

    normal_count = len(normal_devices)
    if normal_count > 0:
        if denaliVariables["nocolors"] == True:
            if denaliVariables['summary'] == True and denaliVariables["pdshDshbakLog"] == False:
                print "Devices that returned NORMAL log entries: %d" % normal_count
            else:
                print "Devices that returned NORMAL log entries [%d]:\n%s" % (normal_count, ','.join(normal_devices))
        else:
            if denaliVariables['summary'] == True and denaliVariables["pdshDshbakLog"] == False:
                message = "Devices that returned NORMAL log entries: %d" % normal_count
                print colors.bold + colors.fg.lightgreen + message + colors.reset
            else:
                message = "Devices that returned NORMAL log entries [%d]:" % normal_count
                print colors.bold + colors.fg.lightgreen + message + colors.reset
                print ','.join(normal_devices)
        print

        # write the summary data to the summary_log_file
        log_data_line = "Devices that returned NORMAL log entries [%d]:\n%s\n\n" % (normal_count, ','.join(normal_devices))
        if denaliVariables['pdshSeparate'] != False:
            pass
        else:
            if denaliVariables['noLogging'] == False:
                with open(summary_log_filename, 'a') as log_file:
                    log_file.write(log_data_line)
    else:
        if denaliVariables['nocolors'] == True:
            print "Devices that returned NORMAL log entries: 0\n"
        else:
            message = "Devices that returned NORMAL log entries: 0\n"
            print colors.bold + colors.fg.lightgreen + message + colors.reset


    success_count = len(success_devices)
    if success_count > 0:
        if denaliVariables["nocolors"] == True:
            if denaliVariables['summary'] == True and denaliVariables["pdshDshbakLog"] == False:
                print "Devices that returned a SUCCESS return code: %d" % success_count
            else:
                print "Devices that returned a SUCCESS return code [%d]:\n%s" % (success_count, ',',join(success_devices))
        else:
            if denaliVariables['summary'] == True and denaliVariables["pdshDshbakLog"] == False:
                message = "Devices that returned a SUCCESS return code: %d" % success_count
                print colors.bold + colors.fg.lightgreen + message + colors.reset
            else:
                message = "Devices that returned a SUCCESS return code [%d]:" % success_count
                print colors.bold + colors.fg.lightgreen + message + colors.reset
                print ','.join(success_devices)
        print

        if denaliVariables['noLogging'] == False:
            # write the summary data to the summary_log_file
            log_data_line = "Devices that returned a SUCCESS return code [%d]:\n%s\n\n" % (success, ','.join(success_devices))
            if denaliVariables['pdshSeparate'] != False:
                pass
            else:
                with open(summary_log_filename, 'a') as log_file:
                    log_file.write(log_data_line)

    failure_count = len(failure_devices)
    if failure_count > 0:
        if denaliVariables["nocolors"] == True:
            print "Devices that returned a FAILURE/ERROR return code [%d]:\n%s" % (failure_count, ','.join(failure_devices))
        else:
            message = "Devices that returned a FAILURE/ERROR return code [%d]:" % failure_count
            print colors.bold + colors.fg.lightred + message + colors.reset
            print ','.join(failure_devices)
        print

        if denaliVariables['noLogging'] == False:
            # write the summary data to the summary_log_file
            log_data_line = "Devices that returned a FAILURE/ERROR return code [%d]:\n%s\n\n" % (failure_count, ','.join(failure_devices))
            if denaliVariables['pdshSeparate'] != False:
                pass
            else:
                with open(summary_log_filename, 'a') as log_file:
                    log_file.write(log_data_line)

    dual_count = len(dual_devices)
    if dual_count > 0:
        if denaliVariables["nocolors"] == True:
            print "Devices that returned both SUCCESS and FAILURE return codes [%d]:\n%s" % (dual_count, ','.join(dual_devices))
        else:
            message = "Devices that returned both SUCCESS and FAILURE return codes [%d]:" % dual_count
            print colors.bold + colors.fg.lightcyan + message + colors.reset
            print ','.join(dual_devices)
        print

        if denaliVariables['noLogging'] == False:
            # write the summary data to the summary_log_file
            log_data_line = "Devices that returned both SUCCESS and FAILURE return codes [%d]:\n%s\n\n" % (dual_count, ','.join(dual_devices))
            if denaliVariables['pdshSeparate'] != False:
                pass
            else:
                with open(summary_log_filename, 'a') as log_file:
                    log_file.write(log_data_line)

    return



##############################################################################
#
# renameExistingStateLogFile(denaliVariables, retry_counter)
#
#   This function is only called during a retry loop from processArguments().
#
#   Rename the existing "state" log files for either PDSH or SSH work-flows.
#   What this does is essentially reset the "failed devices" state  so that
#   each retry can stand independent of the last.  The "state" file is the
#   source of the failed devices, so without this rename, it will always count
#   the devices as the same across retry loops because the first loop had the
#   original failed device list.  If there is even one failure, it is permanent
#   in the return from the readStateLogFile function unless the file is cleared
#   first.
#

def renameExistingStateLogFile(denaliVariables, retry_counter):

    if denaliVariables['commandFunction'] == 'pdsh':
        state_log_filename = denaliVariables['pdsh_log_file'] + '.state'
    elif denaliVariables['commandFunction'] == 'ssh':
        state_log_filename = denaliVariables['ssh_log_file'] + '-' + ssh_time_string + '.txt.state'

    addendum = "-retry_%i" % retry_counter

    try:
        os.rename(state_log_filename, state_log_filename + addendum)
    except:
        # do nothing here -- let it ride.
        pass

    return True



##############################################################################
#
# aggregateLogFiles(denaliVariables, log_filename)
#
#   This function is called to make sure there aren't any intermediate log files
#   that need to be integrated into the "final" log file to know of any/all
#   failed devices and/or successful devices.
#
#   The logic for this is to take the current log file as the base, and then in
#   reverse order (retry_3, then retry_2, then retry_1) go through the intermediate
#   log files adding in the hosts.  The reverse order is necessary because hosts
#   can and will drop off as the retry loops progress, so the final file has only
#   failed hosts, and the previous one may have some that succeeded, etc.  In this
#   way all of the failed hosts are preserved and the hosts that succeed are then
#   added back in for the final summary output.
#
#   No error handling is done here ... yet.  If an exception is found, the code
#   will need to be revisited to see what caused it.  Putting a try/except around
#   this whole thing is possible (preventing potential issues), but it would not
#   allow a complete summary.  Hopefully this doesn't come back to bite us.
#

def aggregateLogFiles(denaliVariables, log_filename):

    log_dictionary = {}

    file_list = glob.glob(log_filename + '-*')
    if len(file_list) == 0:
        return True

    file_list.sort(reverse=True)

    # read the log_filename contents and pull out the hostname
    with open(log_filename, 'r') as log_file:
        log_data = log_file.readlines()

    for line in log_data:
        line_new = line.split(':')
        log_dictionary.update({line_new[0].strip():line.strip()})

    # augment the retry logs into the dictionary
    for log in file_list:
        with open(log, 'r') as log_file:
            log_data = log_file.readlines()

        for line in log_data:
            line_new = line.split(':')
            host     = line_new[0].strip()

            if host not in log_dictionary:
                log_dictionary.update({host:line.strip()})

    if denaliVariables['noLogging'] == False:
        # write out the final aggregated log file
        with open(log_filename, 'w') as log_file:
            hostnames = log_dictionary.keys()
            hostnames.sort()
            for host in hostnames:
                log_file.write(log_dictionary[host] + '\n')

    return True



##############################################################################
#
# readStateLogFile(denaliVariables, host_list, retry_counter=0)
#

def readStateLogFile(denaliVariables, host_list, retry_counter=0):

    failure_devices     = set()
    success_devices     = set()
    normal_devices      = set()
    device_return_codes = {}

    if denaliVariables['pdshSeparate'] != False:
        for log_file in denaliVariables['pdsh_log_file']:
            if log_file.find(host_list[0]) != -1:
                state_log_filename = log_file + '.state'
                rcode_log_filename = log_file + '.rcode'
                break
        else:
            # no segment match found in log file list
            # print debugging information (and then crash below)
            print "host_list     = %s" % host_list
            print "pdsh_log_file = %s" % denaliVariables['pdsh_log_file']
    else:
        if denaliVariables['commandFunction'] == 'pdsh':
            state_log_filename = denaliVariables['pdsh_log_file'] + '.state'
            rcode_log_filename = denaliVariables['pdsh_log_file'] + '.rcode'
        elif denaliVariables['commandFunction'] == 'ssh':
            state_log_filename = denaliVariables['ssh_log_file'] + '-' + ssh_time_string + '.txt.state'
            rcode_log_filename = denaliVariables['ssh_log_file'] + '-' + ssh_time_string + '.txt.rcode'

    rcode_data = []

    # handle state log file aggregation
    if retry_counter == 0:
        ccode = aggregateLogFiles(denaliVariables, state_log_filename)

    with open(state_log_filename, 'r') as state_log_file:
        state_data = state_log_file.readlines()

    for line in state_data:
        line        = line.strip()
        line_list   = line.split(':')
        device_name = line_list[0]
        category    = line_list[1]
        return_code = line_list[2]

        if category == 'FAILURE':
            failure_devices.update([device_name])
        elif category == 'LOGDATA':
            normal_devices.update([device_name])
        elif category == 'SUCCESS':
            success_devices.update([device_name])

        if device_name not in device_return_codes:
            device_return_codes.update({device_name:"%s:%s" % (device_name, return_code)})
        else:
            device_return_codes[device_name] = "%s:%s" % (device_name, return_code)

    if denaliVariables['noLogging'] == False:
        # save the return code data
        with open(rcode_log_filename, 'w') as rcode_log_file:
            rcode_devices = device_return_codes.keys()
            rcode_devices.sort()
            for device in rcode_devices:
                rcode_log_file.write(device_return_codes[device] + '\n')

    # account for an existing rcode file on a retry loop -- rename it
    if retry_counter > 0:
        addendum = "-retry_%i" % retry_counter
        try:
            os.rename(rcode_log_filename, rcode_log_filename + addendum)
        except:
            pass

    # handle rcode log file aggregation
    if retry_counter == 0:
        ccode = aggregateLogFiles(denaliVariables, rcode_log_filename)

    # Find out if there are devices that reported both a success
    # and a failure
    success_failure = failure_devices.intersection(success_devices)
    normal_failure  = failure_devices.intersection(normal_devices)
    dual_devices    = success_failure.union(normal_failure)

    if denaliVariables['pdshFailSucceedHosts'] == False:
        # Remove all dual-listed devices from the success/normal status Lists.
        # Count these devices as a failure only.
        normal_devices  = normal_devices  - dual_devices
        success_devices = success_devices - dual_devices

        # clear out the dual_devices set
        dual_devices = set()

    # Turn the Sets into Lists and sort them
    failure_devices = list(failure_devices)
    failure_devices.sort()
    success_devices = list(success_devices)
    success_devices.sort()
    normal_devices  = list(normal_devices)
    normal_devices.sort()
    dual_devices    = list(dual_devices)
    dual_devices.sort()

    return (failure_devices, success_devices, normal_devices, dual_devices)



##############################################################################
#
# showDSHBAKOutput(denaliVariables, log_filename)
#
#   This function analyzes the dshbak output and determines if every successful
#   device response is different (>90%).  If it is, then then output from dshbak
#   is not shown on the screen; rather, a command to create that output will be
#   shown.
#

def showDSHBAKOutput(denaliVariables, log_filename):

    new_dshbak_output = ""
    error_count       = 0
    non_error_count   = 0
    total_count       = 0
    device_names      = False
    dashed_line       = 'none'
    device_name       = ""
    dshbak_entries    = 0

    # run dshbak against the log file
    # remove all successful return codes from the rcode dshbak output (grep -v ':0$')
    if denaliVariables['pdshDshbakLog'] == False:
        command = "cat \"%s\" | grep -v ':0$' | dshbak -c" % (log_filename + '.rcode')
    elif denaliVariables['pdshDshbakLog'] == True or denaliVariables['sshDshbakLog'] == True:
        command = "cat \"%s\" | cut -c 11- | dshbak -c" % log_filename
    else:
        command = "cat \"%s\" | egrep -v ':0$|ssh exited with exit code 0$' | dshbak -c" % (log_filename + '.rcode')

    dshbak_output = os.popen(command)

    for line in dshbak_output:
        line = line.rstrip()
        if line == "----------------":
            dshbak_entries += 1
            if dashed_line == 'two':
                dashed_line = 'one'
                line = '\n' + line
            elif dashed_line == 'one':
                dashed_line = 'two'
            else:
                dashed_line = 'one'

            new_dshbak_output += line + '\n'
            continue

        else:
            if dashed_line == 'one':
                # found the device name(s)
                device_name = line
                new_dshbak_output += line + '\n'
            elif dashed_line == 'two':
                # found the device result
                new_dshbak_output += line + '\n'

                count = len(device_name.split(','))
                total_count += count
                if line.startswith('ssh exited with exit code'):
                    error_count += count
                else:
                    non_error_count += 1

    # do some math
    hosts_wo_errors = float(total_count - error_count)
    if hosts_wo_errors > 0:
        percentage = round(((float(non_error_count) / hosts_wo_errors) * 100), 1)
    else:
        percentage = 0

    # two lines per host, divide by two to get the number output
    dshbak_entries /= 2

    # request for dshbak output to show all of the time (no matter the percentage)
    # this means if both --summary and --rcode are used, show the output
    if denaliVariables['summary'] == True and denaliVariables["pdshDshbakLog"] == False:
        show_dshbak_output = True
    elif dshbak_entries > DSHBAK_OUTPUT_ENTRIES:
        show_dshbak_output = False
    elif percentage < RETURN_PERCENTAGE:
        show_dshbak_output = True
    else:
        show_dshbak_output = False

    if show_dshbak_output == False:
        print ": DSHBAK output not shown       ; Output is %s%% unique for non-erroring devices." % percentage

    return (show_dshbak_output, new_dshbak_output)



##############################################################################
#
# gatherSCPMultiFileList(denaliVariables)
#
#   Analytics the PDSH log file and pull out the file names.  A dictionary is
#   created with one key per host, so each host an individual set of files
#   unique to it.
#

def gatherSCPMultiFileList(denaliVariables):

    file_count   = 0
    size_count   = 0
    pdsh_logfile = denaliVariables['pdsh_log_file']

    with open(pdsh_logfile, 'r') as pdsh_log:
        file_contents = pdsh_log.readlines()

    for line in file_contents:
        # don't do any analysis on failure lines -- just move to the next
        new_line = line.split(':')
        status   = new_line[0]
        message  = new_line[-1].strip()
        if (status == '[FAILURE]' or
            message.startswith('command timeout') or
            message.startswith('sending') or
            message.startswith('No such file or directory') or
            message.startswith('ssh exited') or
            message.startswith('SSH connection') or
            message.startswith('Password change')):
            continue

        hostname = new_line[1].strip()
        filedata = line.split(':', 2)[-1].strip()       # grab the file data details (permissions, etc.)
        filedata = filedata.split(None, 8)              # one or more space split, to get size and name
        filename = filedata[-1].strip()
        filesize = filedata[4].strip()

        if len(filename) == 0 or len(hostname) == 0:
            pass
        else:
            # global parameters
            file_count += 1
            try:
                size_count += int(filesize)
            except:
                # catch all - in case something was missed
                print "Denali Debug Error:  Problematic data line: %s" % line
                continue

            # store the filename in slots 1+
            # store the file meta-data (total count and total size per host) in slot 0 (in a List)
            if hostname not in denaliVariables['scpMultiFileList']:
                denaliVariables['scpMultiFileList'].update({hostname:[filename]})
                denaliVariables['scpMultiFileList'][hostname].insert(0, [1, int(filesize)])
            else:
                denaliVariables['scpMultiFileList'][hostname].append(filename)
                denaliVariables['scpMultiFileList'][hostname][0][0] += 1
                denaliVariables['scpMultiFileList'][hostname][0][1] += int(filesize)

    return True



##############################################################################
#
# pdshDshbakSummary(denaliVariables, host_list, log_filename_list)
#

def pdshDshbakSummary(denaliVariables, host_list, log_filename_list):

    if len(log_filename_list) == 0 or log_filename_list[0] is None:
        return False

    # don't output anything with the multi-file scp
    if denaliVariables['scpMultiFile'] == True:
        # print a line to create space from the user entertainment above
        print

        # set the flag to False so SCP can stop for the summary information display
        denaliVariables['scpMultiFile'] = False

        # gather the file information obtained for SCP
        ccode = gatherSCPMultiFileList(denaliVariables)
        return True

    for (index, log_filename) in enumerate(log_filename_list):
        # ensure the log_filename exists, and isn't zero byte
        if os.path.isfile(log_filename) == True and os.stat(log_filename).st_size > 0:
            print
            print
            if denaliVariables["pdshScreen"] == False and denaliVariables["pdshScreenDM"] == False:
                if denaliVariables["pdsh_dshbak"][1] == True:
                    if denaliVariables['pdshSeparate'] != False:
                        pdshDshbakTitleOutput(denaliVariables, host_list[index])
                    else:
                        pdshDshbakTitleOutput(denaliVariables, host_list)

                    # run dshbak against the log file
                    command       = "cat \"%s\" | cut -c 11- | dshbak -c" % log_filename
                    command_rcode = "cat \"%s\" | dshbak -c" % (log_filename + '.rcode')

                    # determine if every successful run is different; if so, give the command to
                    # see the dshbak output instead of throwing log lines at the screen unnecessarily
                    (show_dshbak, dshbak_output) = showDSHBAKOutput(denaliVariables, log_filename)

                    if show_dshbak == True:
                        print
                        print dshbak_output
                        print
                    print ": DSHBAK log output command     ; %s" % command
                    print ": DSHBAK return code command    ; %s" % command_rcode
                print ": PDSH Log Filename             ; %s" % log_filename
                print ": PDSH Return Code Log Filename ; %s" % (log_filename + '.rcode')
                if denaliVariables['summary'] == True:
                    print ": PDSH Summary Log Filename     ; %s" % (log_filename + '.summary')
                print
            else:
                print " PDSH does not log host information when the \'--screen\' switch is used."
                print " Manual checking of any target host(s) is required for command validation."
                print
        else:
            if denaliVariables['noLogging'] == True:
                pass
            elif denaliVariables['pdshCanceled'] == False:
                print
                print "Denali: PDSH did not return any information -- log file not created."
                print

    return True



##############################################################################
#
# combinePDSHLogs(denaliVariables, log_filename_list)
#

def combinePDSHLogs(denaliVariables, log_filename_list):

    debug                  = False
    delete_aggregated_logs = True

    # Take the first log off the list, and make the combined log filename a
    # variation of this log's name
    first_logfile    = log_filename_list[0]
    combined_logfile = first_logfile[:first_logfile.rfind('-')] + '-combined.txt'

    if debug == True:
        print "first_logfile    = %s" % first_logfile
        print "combined_logfile = %s" % combined_logfile

    # Loop through each file -- appending it's contents into the combined log
    with open(combined_logfile, 'w') as outfile:
        for logfile in log_filename_list:
            # get the segment name and original hostname from the pdshSeparateData location
            segment_name     = logfile[(logfile.rfind('-')+1):logfile.rfind('.txt')]
            segment_hostname = denaliVariables['pdshSeparateData'][segment_name][0]

            if debug == True:
                print "segment name     = %s" % segment_name
                print "segment hostname = %s" % segment_hostname
                print "logfile name     = %s" % logfile

            with open(logfile) as infile:
                for line in infile:
                    # Replace the host name in the log file with the host name from the
                    # pdshSeparateData location.  PDSH trims characters from the host name
                    # that it thinks are redundant -- which can confuse knowing which host
                    # is reporting which data.  This code puts that hostname back.  This
                    # is easy because the code is already looping through the logfiles; just
                    # piggy-back on this process, check each line, and replace the host.  Done.
                    if debug == True:
                        print "orig line = %s" % line

                    # This host name lives between the first and second colons in the line.
                    # Get the locations, and rewrite the line with the rest of the data in-tact.
                    start   = line.find(':')
                    end     = line.find(':', start + 1)
                    newline = line[:(start + 2)] + segment_hostname + line[end:]

                    if debug == True:
                        print "new line  = %s" % newline

                    if denaliVariables['noLogging'] == False:
                        # output the newline to the aggregated logfile
                        outfile.write(newline)

            # remove the separate log file (redundant)
            if delete_aggregated_logs == True:
                os.remove(logfile)

    return [combined_logfile]



##############################################################################
#
# pdshInfoSummary(denaliVariables, pdshDictionary)
#

def pdshInfoSummary(denaliVariables, pdshDictionary):

    host_list    = []
    log_filename = denaliVariables["pdsh_log_file"]

    # only proceed if the pdshDictionary has data
    if not pdshDictionary:
        return False

    # ensure the the log data is in List form (potential for > 1)
    if denaliVariables['pdshSeparate'] != False:
        pass
    else:
        log_filename = [log_filename]

    if denaliVariables['pdshSeparate'] != False:
        # pdsh 'separate' work-flow -- handle the dictionary a little differently
        for segment in pdshDictionary:
            # this is the segment/separate name, and then number of hosts in the
            # segment (minus one because the segment name is the first item)
            host_list.append([segment[0], (len(segment[1].keys()) - 1)])
    else:
        host_list = pdshDictionary.keys()
        host_list.sort()

    if denaliVariables['hostCommands']['active'] == True:
        # combine separate log files into one
        log_filename = combinePDSHLogs(denaliVariables, log_filename)

    if denaliVariables['pdshAppCount'] != -1:
        # print out the 'app count' summary information
        summary_ret = pdshAppCountSummary(denaliVariables, host_list, pdshDictionary, log_filename)
    else:
        # print out the 'dshbak' summary information
        summary_ret = pdshDshbakSummary(denaliVariables, host_list, log_filename)

    if summary_ret == True:
        for log in log_filename:
            if os.path.isfile(log) == True and os.stat(log).st_size > 0:
                # count the failed hosts (cannot pdsh in) from pdsh, returning false if they exist
                ccode = scanPDSHLogForFailedHosts(denaliVariables, log)
            else:
                # No log file exists, just return True.  This can happen depending upon the command
                # issued.
                ccode = True
    else:
        ccode = True

    return ccode



##############################################################################
#
# scanPDSHLogForFailedHosts(denaliVariables, pdsh_logfile)
#
#   This a pretty weak parser right now.  It has a single hard-coded error
#   condition that it looks for.  If that condition isn't found, the return
#   from pdsh is considered successful (no failure).
#
#   If a separated list comes through, all hosts from all segments are put
#   together into a single list.
#

def scanPDSHLogForFailedHosts(denaliVariables, pdsh_logfile):

    # 'ssh exited with exit code 1'     : Failure of the command to execute
    # 'ssh exited with exit code 255'   : Failure to authenticate to the host

    errors = ['ssh exited with exit code 255']

    pdshFailedHosts   = []
    pdshCanceledHosts = []

    with open(pdsh_logfile, 'r') as pdsh_file:
        for line in pdsh_file:
            if len(line) > 2:
                line = line.split(':')
                if len(line) > 1:
                    if line[2].find('sending SIGTERM') != -1:
                        line     = line[2].strip()
                        message  = line
                        hostname = line.split()[-1]
                        pdshCanceledHosts.append(hostname)

                    elif line[2].find('sending signal 15') != -1:
                        line     = line[2].strip()
                        message  = line
                        hostname = line.split()[4]
                        pdshCanceledHosts.append(hostname)

                    else:
                        hostname = line[1].strip()
                        message  = line[-1].strip()

                else:
                    hostname = "UNKNOWN"
                    message  = ':'.join(line)

            if message in errors:
                pdshFailedHosts.append(hostname)

    if len(denaliVariables['pdshFailedHosts']):
        denaliVariables['pdshFailedHosts'].extend(pdshFailedHosts)
    else:
        denaliVariables['pdshFailedHosts'] = pdshFailedHosts

    # store the canceled hosts, even though they currently are not output
    if len(denaliVariables['pdshCanceledHosts']):
        denaliVariables['pdshCanceledHosts'].extend(pdshCanceledHosts)
    else:
        denaliVariables['pdshCanceledHosts'] = pdshCanceledHosts

    if len(denaliVariables['pdshFailedHosts']) > 0 or len(denaliVariables['pdshCanceledHosts']) > 0:
        return False

    return True



##############################################################################
#
# createSSHOptionsString(denaliVariables)
#

def createSSHOptionsString(denaliVariables):

    sshOptions = denaliVariables["sshOptions"].split('-')

    # fix-up the scp options list:
    #  (1) add a dash to each (was removed during the split operation above)
    #  (2) delete the initial entry in the list if it is empty
    if len(sshOptions[0]) == 0:
        sshOptions.pop(0)

    for (index, option) in enumerate(sshOptions):
        sshOptions[index] = '-' + option.strip()

    # put ssh in batch mode (disable authentications by default)
    if denaliVariables["non_interact"] == False:
        sshOptions.append("-o BatchMode=yes")

    # if a connect timeout value was specified, include it in the options
    if denaliVariables["connectTimeout"] != -1:
        connect_timeout = "-o ConnectTimeout=%i" % int(denaliVariables["connectTimeout"])
        sshOptions.append(connect_timeout)

        # Note:
        # This setting only applies to hosts that can be resolved that will not allow
        # a connection.
        #
        # This setting does not appear to interfere with or override the base host's
        # resolution timeout.  So, if a host (or hosts) is presented to ssh that cannot be
        # resolved, that timeout (at least on my machine) is 15 seconds.  In other words,
        # if 4 hosts are submitted that cannot be resolved, then this process may take at
        # least 60s (4 * 15s) if the app is set to a single process.
        #
        # See "man 5 resolv.conf" for more information
    elif denaliVariables['sshFallThrough'] == True:
        # if no options were specified, set a timeout of 30s (instead of 120s)
        sshOptions.append("-o ConnectTimeout=30")

    # put the default options on
    options_to_add = []
    for default_option in SSH_DEFAULT_OPTIONS:
        default_opt = default_option.split('=')[0]
        default_opt = default_opt[3:].strip()

        # make sure the default option was specified by the user (no duplicates)
        for submitted_option in sshOptions:
            submitted_option = submitted_option.split('=')[0]
            submitted_option = submitted_option[3:]

            if submitted_option == default_opt:
                # found a duplicate
                break
        else:
            # add it in
            options_to_add.append(default_option)

    if len(options_to_add):
        sshOptions.extend(options_to_add)

    return sshOptions



##############################################################################
#
# executeSSH(denaliVariables, hostname, printLock, mCommandDict, mCommandList, sshCommand, sshOptions)
#

def executeSSH(denaliVariables, hostname, printLock, mCommandDict, mCommandList, sshCommand, sshOptions):

    hostname_color = colors.fg.darkgrey
    sshDictionary  = {}

    #
    # build the parameter list to send
    #

    # add .omniture.com for UT1 hosts
    if hostname.find("adobe") == -1 and hostname.find("omniture") == -1:
        hostname += ".omniture.com"

    #data_center = determineDataCenter(hostname)

    if denaliVariables["non_interact"] == False:
        ssh_parms = ['/usr/bin/ssh']
        ssh_parms.extend(sshOptions)
        ssh_parms.append(hostname)
        ssh_parms.append(sshCommand)
    else:
        ssh_password = '%s' % denaliVariables["non_interact_data"]["password"]
        ssh_parms    = ['/usr/bin/sshpass', '-p', ssh_password, '/usr/bin/ssh']
        ssh_username = '%s' % denaliVariables["non_interact_data"]["username"]
        hostname = ssh_username + '@' + hostname
        ssh_parms.extend(sshOptions)
        ssh_parms.append(hostname)
        ssh_parms.append(sshCommand)

    if denaliVariables["debug"] == True:
        print "ssh_parms = %s" % ssh_parms

    # print the hostname -- to show a notion of progress
    hostname_buffered = hostname.ljust(max_host_length)

    # record that a device ssh session has begun
    printLock.acquire()
    mCommandDict['ssh_start_count'] += 1
    mCommandDict['ssh_in_flight']   += 1
    printLock.release()

    # execute the scp process
    result = ''
    startTime = time.time()
    proc = subprocess.Popen(ssh_parms, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, shell=False)
    for output_line in iter(proc.stdout.readline, ""):
        (result, hostname, data_line) = separateHostnameAndData(denaliVariables, output_line, hostname)
        sshInfoPrint(denaliVariables, hostname, result, printLock, mCommandDict, mCommandList, data_line)

    for output_line in iter(proc.stderr.readline, ""):
        (result, hostname, data_line) = separateHostnameAndData(denaliVariables, output_line, hostname, stdout=False)
        # suppress all unclassified stderr
        if len(data_line):
            sshInfoPrint(denaliVariables, hostname, result, printLock, mCommandDict, mCommandList, data_line)

    if result == '':
        # no results/return text from the device
        result      = '0'
        output_line = '[EMPTY] - No Data Returned from Device.'
        (result, hostname, data_line) = separateHostnameAndData(denaliVariables, output_line, hostname)
        sshInfoPrint(denaliVariables, hostname, result, printLock, mCommandDict, mCommandList, data_line)

    return (proc, startTime, result)



##############################################################################
#
# performSSHOperation(denaliVariables, hostname, printLock, mCommandDict, mCommandList)
#
#   This function performs the SSH operation
#

def performSSHOperation(denaliVariables, hostname, printLock, mCommandDict, mCommandList):

    # reset the process count (default is 10 right now -- take it slow)
    global MAX_PROCESS_COUNT
    MAX_PROCESS_COUNT = MAX_SSH_PROCESS_COUNT

    #denaliVariables["debug"] = True

    # retrieve the scp options string
    sshOptions = createSSHOptionsString(denaliVariables)

    # retrieve the ssh command(s) to execute
    if denaliVariables['commandRetryCount'] > 0 and len(denaliVariables['retryCommand']) > 0:
        sshCommand = denaliVariables['retryCommand']
    else:
        sshCommand = denaliVariables["sshCommand"]

    if denaliVariables["debug"] == True:
        print "ssh options [%02i]: %s" % (len(sshOptions), sshOptions)
        print "ssh command     : %s" % sshCommand

    #
    (proc, startTime, sshReturnCode) = executeSSH(denaliVariables, hostname, printLock, mCommandDict, mCommandList, sshCommand, sshOptions)
    #

    timeDiff  = str(time.time() - startTime)[:6]

    return [sshReturnCode, timeDiff]



##############################################################################
#
# sshInfoRecordData(denaliVariables, sshDictionary, result, hostname)
#
#   This function records returning SSH data
#

def sshInfoRecordData(denaliVariables, sshDictionary, result, hostname):

    if 'start_time' not in sshDictionary:
        if denaliVariables['sshFallThrough'] == False:
            sshDictionary.update({'start_time' : denaliVariables['commandTimeValues']['start_time']})

    # if SSH returns nothing, don't record it (just like in the PDSH case)
    if hostname == "MISSING_HOSTNAME":
        return sshDictionary

    # The variable 'result' looks like this:  [<hostname>, [returncode, time-differential]]
    result = result[1][0]

    #print "result = %s" % result
    #print "sDict  = %s" % sshDictionary
    #print "host   = %s" % hostname

    if hostname in sshDictionary:
        success_count = sshDictionary[hostname]["success_count"]
        failure_count = sshDictionary[hostname]["failure_count"]
        normal_count  = sshDictionary[hostname]["normal_count"]
        hostkey_count = sshDictionary[hostname]["hostkey_count"]
        keypass_count = sshDictionary[hostname]["keypass_count"]
    else:
        sshDictionary.update({hostname:{}})
        sshDictionary[hostname]["success_count"] = 0
        sshDictionary[hostname]["failure_count"] = 0
        sshDictionary[hostname]["normal_count"]  = 0
        sshDictionary[hostname]["hostkey_count"] = 0
        sshDictionary[hostname]["keypass_count"] = 0
        success_count = 0
        failure_count = 0
        normal_count  = 0
        hostkey_count = 0
        keypass_count = 0

    if result == 0:
        success_count += 1
        sshDictionary[hostname]["success_count"] = success_count
    elif result == 1:
        failure_count += 1
        sshDictionary[hostname]["failure_count"] = failure_count
    elif result == 2:
        normal_count  += 1
        sshDictionary[hostname]["normal_count"]  = normal_count
    elif result == 3:
        hostkey_count += 1
        sshDictionary[hostname]["hostkey_count"] = hostkey_count
    else:
        keypass_count += 1
        sshDictionary[hostname]["keypass_count"] = keypass_count

    return sshDictionary



##############################################################################
#
# writeSSHDataToLog(denaliVariables, hostname, sshData)
#
#   This function takes the sshData and appends it to the end of the log
#   for this session
#

def writeSSHDataToLog(denaliVariables, hostname, sshData, success='normal'):

    # define the log file name -- appended with the date/time
    log_filename  = denaliVariables["ssh_log_file"] + '-' + ssh_time_string + ".txt"
    #log_data_line = sshData.decode('ascii', 'ignore')
    log_data_line = sshData

    # If the user requested a symlink to the log file ... do it here.
    # The logic here is different than the pdsh symlink code, because here the
    # filename is only created when entering this function due to the fact that
    # each ssh session is on its own process.  With pdsh, there is a command
    # process that then separates into threads.  Because of the difference between
    # the pdsh and ssh implementations, this code needs to test every time whether
    # a symlink exists or not and then create one if requested and needed.
    if len(denaliVariables['commandOutputSymlink']):
        try:
            ccode = os.path.islink(denaliVariables['commandOutputSymlink'])
            if ccode == False:
                os.symlink(log_filename, denaliVariables['commandOutputSymlink'])
        except OSError as e:
            # Symlink creation failed.  Do not stop, continue without it.
            print "Denali Warning:  Symlink creation [%s] failed:  %s\n" % (denaliVariables['commandOutputSymlink'], str(e))

            if denaliVariables['debug'] == True:
                print "SSH symlink to the log file failed to successfully create."
                print "  Symlink source      = %s" % log_filename
                print "  Symlink destination = %s" % denaliVariables['commandOutputSymlink']

    # Force the hostname to a string to prevent unicode issues in the
    # log_line statements below.
    hostname = str(hostname)

    if success == 'success':
        log_line = '[SUCCESS]: ' + hostname + ': ' + log_data_line + '\n'
    elif success == 'failure':
        log_line = '[FAILURE]: ' + hostname + ': ' + log_data_line + '\n'
    elif success == 'normal':
        log_line = '[LOGDATA]: ' + hostname + ': ' + log_data_line + '\n'
    elif success == 'hostkey':
        log_line = '[HOSTKEY]: ' + hostname + ': ' + log_data_line + '\n'
    elif success == 'keypass':
        log_line = '[KEYPASS]: ' + hostname + ': ' + log_data_line + '\n'
    else:
        log_line = '[UNKNOWN]: ' + hostname + ': ' + log_data_line + '\n'

    if denaliVariables['noLogging'] == False:
        # write the data to a log file
        try:
            with open(log_filename, 'a') as log_file:
                log_file.write(log_line)
        except:
            return False

        state_log_filename = denaliVariables["ssh_log_file"] + '-' + ssh_time_string + '.txt.state'
        data_state         = log_line.split(':')[0]

        # get the rcode data to write out
        if data_state == "[FAILURE]":
            rcode = '0'
        else:
            rcode = '1'

        state_data_line    = hostname + ':' + log_line.split(':')[0][1:-1] + ':' + rcode + '\n'
        try:
            with open(state_log_filename, 'a') as state_log_file:
                state_log_file.write(state_data_line)
        except:
            return False

    return True



##############################################################################
#
# sshInfoPrint(denaliVariables, scpData, result, printLock, mCommandDict, mCommandList, data_line, printParameters=[])
#
#   This function prints SSH output to the screen
#

def sshInfoPrint(denaliVariables, hostname, result, printLock, mCommandDict, mCommandList, data_line, printParameters=[]):

    PROGRESS_INDICATOR   = denaliVariables['commandProgressBar']     # which of the below 3 to show for a progress indicator
    PERCENTAGE_REMAINING = 0     # percentage indicator and devices remaining displayed
    PERCENTAGE_PLUS      = 1     # percentage plus others stats at the far-left of the log line
    PROGRESS_BAR         = 2     # progress bar only with percentage/percentage-plus stats

    SUCCESS = { 'message': 'SUCCESS', 'color': colors.bold + colors.fg.lightgreen }
    FAILURE = { 'message': 'FAILURE', 'color': colors.bold + colors.fg.lightred   }
    NORMAL  = { 'message': 'LOGDATA', 'color': colors.bold + colors.fg.darkgrey   }
    HOSTKEY = { 'message': 'HOSTKEY', 'color': colors.bold + colors.fg.yellow     }
    KEYPASS = { 'message': 'KEYPASS', 'color': colors.bold + colors.fg.blue       }
    UNKNOWN = { 'message': 'UNKNOWN', 'color': colors.bold + colors.fg.lightcyan  }

    # Force the hostname to a string to prevent unicode issues in the
    # print statements below.
    hostname = str(hostname)

    printLock.acquire()

    data_variable = commandCategorization(denaliVariables, hostname, mCommandDict, mCommandList, result)

    if hostname not in mCommandList:
        mCommandDict['ssh_complete_count'] += 1     # increment the completed counter
        mCommandDict['ssh_in_flight']      -= 1     # decrement the in-flight count
        mCommandList.append(hostname)

    if result == 0:
        mCommandDict['ssh_success'] += 1
        message = SUCCESS['message']
        color   = SUCCESS['color']
        success = 'success'
    elif result == 1 or result == 255:
        mCommandDict['ssh_failure'] += 1
        message = FAILURE['message']
        color   = FAILURE['color']
        success = 'failure'
    elif result == 2:
        mCommandDict['ssh_normal']  += 1
        message = NORMAL['message']
        color   = NORMAL['color']
        success = 'normal'
    elif result == 3:
        mCommandDict['ssh_hostkey']  += 1
        message = HOSTKEY['message']
        color   = HOSTKEY['color']
        success = 'hostkey'
    elif result == 4:
        mCommandDict['ssh_keypass']  += 1
        message = KEYPASS['message']
        color   = KEYPASS['color']
        success = 'keypass'
    elif result == 5:
        mCommandDict['ssh_failure']  += 1
        message = UNKNOWN['message']
        color   = UNKNOWN['color']
        success = 'failure'

    progress_string = createProgressIndicator(denaliVariables, hostname, mCommandDict, mCommandList, 'ssh_end')
    if hostname == "MISSING_HOSTNAME":
        print_data = False
    else:
        print_data = True

    if (print_data == True and (PROGRESS_INDICATOR == PERCENTAGE_REMAINING or
                                PROGRESS_INDICATOR == PERCENTAGE_PLUS or
                                PROGRESS_INDICATOR == PROGRESS_DISABLED)):

        if denaliVariables['nocolors'] == True:
            print progress_string + '[' + message + "]: %s " % hostname + ': ' + data_line
        else:
            print progress_string + '[' + color + message + colors.reset + "]: %s " % hostname + ': ' + data_line

    printLock.release()

    # store the data information in a log file
    ccode = writeSSHDataToLog(denaliVariables, hostname, data_line, success)
    if ccode == False:
        ssh_log_name = denaliVariables["ssh_log_file"] + '-' + ssh_time_string + ".txt"
        print "Failure to update ssh log: %s" % ssh_log_name

    return



##############################################################################
#
# sshInfoSummary(denaliVariables, sshDictionary)
#
#   This function summarizes the SSH execution run
#
def sshInfoSummary(denaliVariables, sshDictionary):

    if sshDictionary == "Failed":
        return False

    log_filename = denaliVariables["ssh_log_file"] + '-' + ssh_time_string + ".txt"

    if os.path.isfile(log_filename) == True and os.stat(log_filename).st_size > 0:
        print
        print
        print " SSH Log Filename: %s" % log_filename

    if not sshDictionary:
        return False

    device_names = sshDictionary.keys()
    device_names.sort()

    summary_ret = sshDshbakSummary(denaliVariables, device_names, log_filename)

    return True



##############################################################################
#
# sshDshbakSummary(denaliVariables, device_names, log_filename_list)
#

def sshDshbakSummary(denaliVariables, device_names, log_filename_list):

    if len(log_filename_list) == 0 or log_filename_list[0] is None:
        return False

    # In the future the log_filename_list may exist, until then this is a
    # single entry only.
    log_filename_list = [log_filename_list]

    for (index, log_filename) in enumerate(log_filename_list):
        # ensure the log_filename exists, and isn't zero byte
        if os.path.isfile(log_filename) == True and os.stat(log_filename).st_size > 0:
            print
            print
            sshDshbakTitleOutput(denaliVariables, device_names, log_filename)

            # run dshbak against the log file
            command       = "cat \"%s\" | cut -c 11- | dshbak -c" % log_filename
            command_rcode = "cat \"%s\" | dshbak -c" % (log_filename + '.rcode')

            # determine if every successful run is different; if so, give the command to
            # see the dshbak output instead of throwing log lines at the screen in what
            # would would appear to be an indiscriminate manner, and unnecessary.
            (show_dshbak, dshbak_output) = showDSHBAKOutput(denaliVariables, log_filename)

            if show_dshbak == True:
                print
                print dshbak_output
                print

            print ": DSHBAK log output command     ; %s" % command
            print ": DSHBAK return code command    ; %s" % command_rcode
            print ": SSH Log Filename              ; %s" % log_filename
            print ": SSH Return Code Log Filename  ; %s" % (log_filename + '.rcode')
            if denaliVariables['summary'] == True:
                print ": SSH Summary Log Filename      ; %s" % (log_filename + '.summary')
        else:
            if denaliVariables['noLogging'] == False:
                print
                print "Denali: SSH did not return any information -- log file not created."
                print

    return True



##############################################################################
#
# sshDshbakTitleOutput(denaliVariables, host_list, log_filename)
#

def sshDshbakTitleOutput(denaliVariables, host_list, log_filename):

    summary_log_filename = log_filename + '.summary'

    if denaliVariables['sshDshbakLog'] == True:
        print "---------------------------------------------"
        print "| SSH Command Execution Log piped to dshbak |"
        print "---------------------------------------------"
    else:
        print "----------------------------------------------"
        print "| SSH Command [return codes] piped to dshbak |"
        print "----------------------------------------------"
    print
    print " Total number of hosts : %i" % len(host_list)
    print

    # Read in the state log file and return host lists
    # The 'rcode' file is created in this function as well
    (failure_devices, success_devices, normal_devices, dual_devices) = readStateLogFile(denaliVariables, host_list)

    # do not print the device categorization summary unless '--summary' is requested
    if denaliVariables['summary'] == False:
        return

    if denaliVariables['noLogging'] == False:
        with open(summary_log_filename, 'a') as log_file:
            log_file.write("Denali Command Submitted:\n")
            log_file.write(denaliVariables['argumentList'] + '\n\n')

    normal_count = len(normal_devices)
    if normal_count > 0:
        if denaliVariables["nocolors"] == True:
            if denaliVariables['summary'] == True and denaliVariables["sshDshbakLog"] == False:
                print "Devices that returned NORMAL log entries: %d" % normal_count
            else:
                print "Devices that returned NORMAL log entries [%d]:\n%s" % (normal_count, ','.join(normal_devices))
        else:
            if denaliVariables['summary'] == True and denaliVariables["sshDshbakLog"] == False:
                message = "Devices that returned NORMAL log entries : %d" % normal_count
                print colors.bold + colors.fg.lightgreen + message + colors.reset
            else:
                message = "Devices that returned NORMAL log entries [%d]:" % normal_count
                print colors.bold + colors.fg.lightgreen + message + colors.reset
                print ','.join(normal_devices)
        print

        if denaliVariables['noLogging'] == False:
            # write the summary data to the summary_log_file
            log_data_line = "Devices that returned NORMAL log entries [%d]:\n%s\n\n" % (normal_count, ','.join(normal_devices))
            with open(summary_log_filename, 'a') as log_file:
                log_file.write(log_data_line)
    else:
        if denaliVariables['nocolors'] == True:
            print "Devices that returned NORMAL log entries: 0\n"
        else:
            message = "Devices that returned NORMAL log entries: 0\n"
            print colors.bold + colors.fg.lightgreen + message + colors.reset


    success_count = len(success_devices)
    if success_count > 0:
        if denaliVariables["nocolors"] == True:
            if denaliVariables['summary'] == True and denaliVariables["sshDshbakLog"] == False:
                print "Devices that returned a SUCCESS return code: %d" % success_count
            else:
                print "Devices that returned a SUCCESS return code [%d]:\n%s" % (success_count, ',',join(success_devices))
        else:
            if denaliVariables['summary'] == True and denaliVariables["sshDshbakLog"] == False:
                message = "Devices that returned a SUCCESS return code: %d" % success_count
                print colors.bold + colors.fg.lightgreen + message + colors.reset
            else:
                message = "Devices that returned a SUCCESS return code [%d]:" % success_count
                print colors.bold + colors.fg.lightgreen + message + colors.reset
                print ','.join(success_devices)
        print

        if denaliVariables['noLogging'] == False:
            # write the summary data to the summary_log_file
            log_data_line = "Devices that returned a SUCCESS return code [%d]:\n%s\n\n" % (success_count, ',',join(success_devices))
            with open(summary_log_filename, 'a') as log_file:
                log_file.write(log_data_line)

    failure_count = len(failure_devices)
    if failure_count > 0:
        if denaliVariables["nocolors"] == True:
            print "Devices that returned a FAILURE/ERROR return code [%d]:\n%s" % (failure_count, ','.join(failure_devices))
        else:
            message = "Devices that returned a FAILURE/ERROR return code [%d]:" % failure_count
            print colors.bold + colors.fg.lightred + message + colors.reset
            print ','.join(failure_devices)
        print

        if denaliVariables['noLogging'] == False:
            # write the summary data to the summary_log_file
            log_data_line = "Devices that returned a FAILURE/ERROR return code [%d]:\n%s\n\n" % (failure_count, ','.join(failure_devices))
            with open(summary_log_filename, 'a') as log_file:
                log_file.write(log_data_line)
    else:
        if denaliVariables['nocolors'] == True:
            print "Devices that returned a FAILURE/ERROR return code: 0\n"
        else:
            message = "Devices that returned a FAILURE/ERROR return code: 0\n"
            print colors.bold + colors.fg.lightred + message + colors.reset


    dual_count = len(dual_devices)
    if dual_count > 0:
        if denaliVariables["nocolors"] == True:
            print "Devices that returned both SUCCESS and FAILURE return codes [%d]:\n%s" % (dual_count, ','.join(dual_devices))
        else:
            message = "Devices that returned both SUCCESS and FAILURE return codes [%d]:" % dual_count
            print colors.bold + colors.fg.lightcyan + message + colors.reset
            print ','.join(dual_devices)
        print

        if denaliVariables['noLogging'] == False:
            # write the summary data to the summary_log_file
            log_data_line = "Devices that returned both SUCCESS and FAILURE return codes [%d]:\n%s\n\n" % (dual_count, ','.join(dual_devices))
            with open(summary_log_filename, 'a') as log_file:
                log_file.write(log_data_line)

    return



##############################################################################
#
# performHostOperation(denaliVariables, hostname, printLock, mCommandDict, mCommandList)
#

def performHostOperation(denaliVariables, hostname, printLock, mCommandDict, mCommandList):

    result = subprocess.Popen(["host", hostname], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, err = result.communicate()
    output = output.split('\n')

    for line in output:
        match_string = hostname + ' is an alias for'
        if line.find(match_string) != -1:
            alias = line.split(match_string)[1].strip()
            alias = alias[:-1]
            new_name = {hostname:alias}
            break
    else:
        new_name = {hostname:''}

    return new_name



##############################################################################
#
# hostRecordData(denaliVariables, hostDictionary, hostData)
#

def hostRecordData(denaliVariables, hostDictionary, hostData):
    hostData = hostData[1]
    hostDictionary.update(hostData)
    return hostDictionary

def hostInfoPrint(denaliVariables, data, printLock, mcDict, printParams=[]):   return True
def hostInfoSummary(denaliVariables, hostDictionary):                          return True



##############################################################################
#
# jiraTicketDataMassage(denaliVariables, jira_tickets, jira_status)
#

def jiraTicketDataMassage(denaliVariables, jira_tickets, jira_status):

    jira_data = []
    jira_url  = "https://jira.corp.adobe.com/browse/"

    include_closed_tickets = denaliVariables['jira_closed']
    jira_tickets = jira_tickets.split(',')
    jira_status  = jira_status.split(',')

    # sort the tickets -- some semblance of order
    jira_tickets.sort()

    for (index, status) in enumerate(jira_status):
        if include_closed_tickets == False and status == 'Closed':
            continue
        elif len(jira_tickets[index]) > 0:
            ticket = (jira_url + jira_tickets[index]).ljust(50)
            data_value = "  " + ticket + "  :  " + status
            jira_data.append(data_value)

    return jira_data



##############################################################################
#
# retrieveDeviceData(denaliVariables, deviceName)
#

def retrieveDeviceData(denaliVariables, deviceName):

    # If the 'api' variable is None, it means that the SKMS library hasn't been
    # accessed yet.  Do that now so the device_id retrieval will succeed.
    if denaliVariables['api'] is None:
        denali_utility.retrieveAPIAccess(denaliVariables)

    # STEP 1: save the current state
    saveDefault = denaliVariables["defaults"]
    saveMethod  = denaliVariables["method"]
    saveFields  = denaliVariables["fields"]
    saveDao     = denaliVariables["searchCategory"]
    saveTrunc   = denaliVariables["textTruncate"]
    saveWrap    = denaliVariables["textWrap"]
    saveServer  = denaliVariables["serverList"]
    denaliVariables["sqlParameters"] = ''
    denaliVariables['serverList']    = deviceName

    # STEP 2: set the values to do this query
    # remove default setting (showing or not 'decommissioned' hosts) -- leave as set
    # in the submitted query
    #denaliVariables["defaults"]       = True
    denaliVariables["method"]         = "search"
    denaliVariables["fields"]         = "name,device_id,device_state,device_service,model,vendor,jira_url,jira_status"
    denaliVariables["searchCategory"] = 'DeviceDao'
    denaliVariables["textTruncate"]   = False
    denaliVariables["textWrap"]       = False

    dao = 'DeviceDao'

    # STEP 3: build the sql query with the given hosts, and get the results
    (sqlQuery, wildcard) = denali_search.buildGenericQuery(denaliVariables)

    sqlQuery = dao + ':' + sqlQuery
    denaliVariables["serverList"] = []
    counter = 0
    loop    = True

    while loop == True:
        respDictionary = denali_search.constructSQLQuery(denaliVariables, sqlQuery, False)
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
        deviceList = {}
        deviceData = []
        for row in printData:
            if len(row[0].strip()) > 0:
                for (index, host_value) in enumerate(row):
                    if index == 0:
                        continue
                    deviceData.append(host_value.strip())
                deviceList.update({row[0].strip():deviceData})

    # STEP 4: reset to the original state
    denaliVariables["defaults"]       = saveDefault
    denaliVariables["method"]         = saveMethod
    denaliVariables["fields"]         = saveFields
    denaliVariables["searchCategory"] = 'DeviceDao'
    denaliVariables["textTruncate"]   = saveTrunc
    denaliVariables["textWrap"]       = saveWrap

    return deviceList



##############################################################################
#
# gatherDeviceInfo(denaliVariables, deviceName, printLock, mCommandDict, mCommandList)
#
#   Three separate items of data are requested in this function:
#   (1) Monitoring (nagios, etc.) alerts/checks
#   (2) Spots data
#   (3) History
#
#   The request is to gather and then display this information one section
#   at a time for each requested server.  The current implementation of
#   this function is serial, not parallel.  In other words, it works well
#   for < 20 hosts, and will work not quite as well because it takes a long
#   time to gather 3 different things for each requested host ... serially.
#
#   For each host that is displayed, pull out some SKMS data to show as well;
#   device_state, device_service, model, vendor, JIRA tickets/status
#

def gatherDeviceInfo(denaliVariables, deviceName, printLock, mCommandDict, mCommandList):

    # order of the returned data from the lookup request
    DATA_DEVICE_ID           = 0
    DATA_DEVICE_STATE        = 1
    DATA_DEVICE_SERVICE      = 2
    DATA_DEVICE_MODEL        = 3
    DATA_DEVICE_VENDOR       = 4
    DATA_DEVICE_JIRA_TICKETS = 5
    DATA_DEVICE_JIRA_STATUS  = 6

    # retrieve the device data from SKMS
    saveSQLMod  = denaliVariables["sqlParameters"]
    device_data = retrieveDeviceData(denaliVariables, [deviceName])
    denaliVariables["sqlParameters"] = saveSQLMod

    # show the headers for both monitoring and history
    denaliVariables['showHeaders']   = True

    # assign values from SKMS to variables
    device_id           = device_data[deviceName][DATA_DEVICE_ID]
    device_state        = device_data[deviceName][DATA_DEVICE_STATE]
    device_service      = device_data[deviceName][DATA_DEVICE_SERVICE]
    device_model        = device_data[deviceName][DATA_DEVICE_MODEL]
    device_vendor       = device_data[deviceName][DATA_DEVICE_VENDOR]
    device_jira_tickets = device_data[deviceName][DATA_DEVICE_JIRA_TICKETS]
    device_jira_status  = device_data[deviceName][DATA_DEVICE_JIRA_STATUS]

    # save off the current service list and assign it again
    saveDeviceList = list(denaliVariables['serverList'])
    denaliVariables['serverList'] = [deviceName]

    #
    # *** Display Monitoring Data ***
    #
    denaliVariables['monitoring'] = True
    ccode = denali_monitoring.monitoringDataEntryPoint(denaliVariables, 'simple')
    denaliVariables['monitoring'] = False
    print

    #
    # ***   Display Spots Data   ***
    #
    # SPOTS collection items to print
    spots_collection = ['kernel uptime load memory disk']
    spotsData        = retrieveSpotsInfo(denaliVariables, deviceName, printLock, mCommandDict, mCommandList)
    spotsData        = [deviceName, spotsData]
    spotsDictionary  = spotsInfoRecordData(denaliVariables, {}, spotsData)

    spots_errors = ['connection refused', 'unclassified error', 'connection reset',
                    'socket timeout'    , 'connect error']

    if len(spotsData) > 1 and spotsData[1] in spots_errors:
        spots_error = True
        print "spots data unavailable: %s" % spotsData[1]
    else:
        spots_error = False
        spotsInfoPrint(denaliVariables, spotsData, printLock, mCommandDict, mCommandList, spots_collection)
        print

    #
    # ***   Display SKMS data    ***
    #
    if spots_error == False:
        spacing = (len(deviceName) + 4) * ' '
    else:
        spacing = '  '
    not_configured   = 'Not configured'
    device_property = [['Device State    ', device_state  ],
                       ['Device Service  ', device_service],
                       ['Device Model    ', device_model  ],
                       ['Device Vendor   ', device_vendor ]]

    for dProperty in device_property:
        if dProperty[1] == '':
            dProperty[1] = not_configured
        print "%s%s:   %s" % (spacing, dProperty[0], dProperty[1])
    print

    # Massage the JIRA ticket display
    jira_output_data = jiraTicketDataMassage(denaliVariables, device_jira_tickets, device_jira_status)

    if denaliVariables['jira_closed'] == True:
        end_string = "(Open and Closed tickets)"
    else:
        end_string = "(Open tickets)"

    print "JIRA Tickets/Status %s:" % end_string
    if len(jira_output_data) > 0:
        for data in jira_output_data:
            print data
    else:
        print "  No JIRA tickets"
    print

    #
    # ***  Display History Data  ***
    #
    # Save the outputTarget data or everything else will be put to
    # the screen as CSV -- which perhaps the user doesn't want
    saveOutputData = denaliVariables["outputTarget"]
    denaliVariables["outputTarget"] = [denali_types.OutputTarget(               # output format
        type='csv_screen', filename='', append=False)]
    denaliVariables["csvSeparator"] = ' | '                                     # history separator
    denaliVariables['limitCount']   = denaliVariables['historyListLength']      # rows to print (15)
    #denaliVariables['historyFields'] = 'short'                                 # less columns/data

    # save the current state
    saveDefault = denaliVariables["defaults"]
    saveMethod  = denaliVariables["method"]
    saveFields  = denaliVariables["fields"]
    saveDao     = denaliVariables["searchCategory"]
    saveTrunc   = denaliVariables["textTruncate"]
    saveWrap    = denaliVariables["textWrap"]
    saveSQLMod  = denaliVariables["sqlParameters"]
    saveServer  = denaliVariables["serverList"]

    # Craft the subdata dictionary to send -- device_id is required for history access
    subData   = {'status':'success', 'data':{'results':[{'name':deviceName, 'device_id':device_id}]}}
    itemCount = denali_history.deviceHistoryRequest(denaliVariables, subData)
    print

    # reset to the original state
    denaliVariables["defaults"]       = saveDefault
    denaliVariables["method"]         = saveMethod
    denaliVariables["fields"]         = saveFields
    denaliVariables["searchCategory"] = saveDao
    denaliVariables["textTruncate"]   = saveTrunc
    denaliVariables["textWrap"]       = saveWrap
    denaliVariables["sqlParameters"]  = saveSQLMod
    denaliVariables["outputTarget"]   = saveOutputData

    # reset the original hostlist
    denaliVariables['serverList'] = list(saveDeviceList)

    return True



def deviceInfoRecordData(denaliVariables, sshDictionary, infoData):                         return True
def deviceInfoPrint(denaliVariables, infoData, printLock, mcDict, mcList, printParams=[]):  return True
def deviceInfoSummary(denaliVariables, infoDictionary):                                     return True



##############################################################################
#
# performSortOperation(denaliVariables, function)
#

def performSortOperation(denaliVariables, function):

    if function == "sort":
        direction = False       # False means sort ascending (reverse = False)
    else:
        direction = True        # True means sort descending (reverse = True)

    # put the server List into a Set to remove any duplicates
    denaliVariables['serverList'] = list(set(denaliVariables['serverList']))

    # get the naturally sorted list of hosts
    natural_sort_list = denali_utility.natural_sort(denaliVariables['serverList'], direction)
    denaliVariables['serverList'] = natural_sort_list

    if use_natural_sort == True:
        return {}

    # print in newline separated line
    print "Devices in New Line Format:\n%s" % '\r\n'.join(natural_sort_list)
    print

    # print in space separated list
    print "Devices in Space Separated Format:\n%s" % ' '.join(natural_sort_list)
    print

    # print in comma separated list
    print "Devices in Comma Separated Format:\n%s" % ','.join(natural_sort_list)
    print

    print "Total Number of Devices: %s" % len(natural_sort_list)

    return {}



def sortSummary(denaliVariables, sortDictionary):   return True



##############################################################################
#
# Dictionaries of functions to be used generically ---
#
#   Keep this at the bottom of the commands.py file.  All function names
#   defined in this dictionary must be instantiated "above" this dictionary.
#
#   Functions needed when creating a new command:
#   (1) commandFunctionCollect
#       funct_name(denaliVariables, hostname, printLock)
#   (2) commandFunctionRecordData
#       funct_name(denaliVariables, dataDictionary, data)
#   (3) commandFunctionPrint
#       funct_name(denaliVariables, data, printLock, printParameters=[])
#   (4) commandFunctionSummary
#       funct_name(denaliVariables, dataDictionary)
#

commandFunctionCollect = {
    # Requirements:
    #   Input :  denaliVariables, hostname(s), printLock
    #       hostname(s) : a single host or a list of hosts that the function will
    #                     process through.
    #       printLock   : mpSafe lock that is used for console printing
    #
    #   Output:  resulting data from command:  "return data"
    #
    #   Description:  This function collects data (typically from a single host).
    #                 Any collection options will be found in denaliVariables["options"]
    #                 as a string, and are space separated.
    #
    "list"      : listServers,
    "netinfo"   : networkInfo,
    "pdsh"      : performPDSHOperation,
    "ping"      : serverPing,
    "spots"     : retrieveSpotsInfo,
    "info"      : gatherDeviceInfo,
    "scp"       : performSCPOperation,
    "scp-pull"  : performSCPOperation,
    "scp-push"  : performSCPOperation,
    "ssh"       : performSSHOperation,
    "host"      : performHostOperation,
    "sort"      : performSortOperation,
    "sortd"     : performSortOperation,
}

commandFunctionRecordData = {
    # Requirements:
    #   Input :  denaliVariables, dataDictionary, data
    #       dataDictionary : overall dictionary (keyed by host) to store all collected
    #                        data.
    #       data           : individual (or combined) data to be added to the dictionary.
    #
    #   Output:  dataDictionary:  "return dataDictionary"
    #
    #   Description:  This function records the data from the collection function in
    #                 a dictionary.  Because each command is potentially different,
    #                 this function knows specifically how to handle its own data.
    #
    "pdsh"      : pdshInfoRecordData,
    "ping"      : serverPingRecordData,
    "spots"     : spotsInfoRecordData,
    "info"      : deviceInfoRecordData,
    "scp"       : scpInfoRecordData,
    "scp-pull"  : scpInfoRecordData,
    "scp-push"  : scpInfoRecordData,
    "ssh"       : sshInfoRecordData,
    "host"      : hostRecordData,
}

commandFunctionPrint = {
    # Requirements:
    #   Input :  denaliVariables, printData, printLock, printParameters
    #       printData       : data formated specifically to print in this function
    #       printLock       : mpSafe lock that is used for console printing
    #       printParameters : any needed parameters (search criteria, etc.) for
    #                         printing.
    #   Output:  none ... just "return"
    #
    #   Description:  This function prints the data retrieved from the "collect"
    #                 function.  Typically this is one piece of data from a single
    #                 server.
    #
    "pdsh"      : pdshInfoPrint,
    "ping"      : serverPingPrint,
    "spots"     : spotsInfoPrint,
    "info"      : deviceInfoPrint,
    "scp"       : scpInfoPrint,
    "scp-pull"  : scpInfoPrint,
    "scp-push"  : scpInfoPrint,
    "ssh"       : sshInfoPrint,
    "host"      : hostInfoPrint,
}

commandFunctionSummary = {
    # Requirements:
    #   Input :  denaliVariables, dataDictionary
    #       dataDictionary : key/value data stored by hostname
    #
    #   Output:  if denaliVariables["combine"] == False --> just "return"
    #            if denaliVariables["combine"] == True
    #                   "return dataDictionary" with information for combining data
    #                   with other CMDB data is a column format.
    #
    #   Description:  This function summarizes the command (success, failure, etc.)
    #
    "pdsh"      : pdshInfoSummary,
    "ping"      : serverPingSummary,
    "spots"     : spotsInfoSummary,
    "info"      : deviceInfoSummary,
    "scp"       : scpInfoSummary,
    "scp-pull"  : scpInfoSummary,
    "scp-push"  : scpInfoSummary,
    "ssh"       : sshInfoSummary,
    "host"      : hostInfoSummary,
    "sort"      : sortSummary,
    "sortd"     : sortSummary,
}
