#! /usr/bin/env python

#   Denali code
#
#   Author      :  Mike Hasleton
#   Company     :  Adobe Systems, Inc.
#
#   Denali is a set of python scripts/modules that interact with a mysql database
#   called CMDB through the SKMS Web API.  It is designed to be used with scripts
#   on Linux hosts (bash, perl, etc.) so as to help automate redundant CMDB queries.
#
#   The help page (denali --help) is fairly good; although it could always use more
#   in the way of examples and a more flushed out description of "HOW TO USE".
#   More help can be found on the SKMS wiki page for Denali.
#


import time
denali_start_time = time.time()
import os
import sys
import copy
import json
import select
import signal
import getpass
import datetime
import platform
import subprocess


denali_libs = False         # library directory
urllib_err1 = False         # requests imported, warnings disabled
urllib_err2 = False         # requests urllib3 warnings disabled
urllib_err3 = False         # urllib3 imported, warnings disabled
req_readto  = False         # requests.exceptions.ReadTimeout

initial_debug  = False

denali_config  = False
denali_aliases = False

# Allow relative path module importing
#   Add the current directory's library path to the system path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'denali_libs')))

# MRASEREQ-41241
# Add the default RPM install library directory -- if it exists and wasn't
# already added with the above command.  This helps if someone has created
# a softlink to the RPM install location (not an alias).
if os.path.isdir('/opt/netops/denali_libs'):
    denali_libs = True
    if not os.path.exists('/opt/netops/denali_libs'):
        sys.path.append('/opt/netops/denali_libs')


# Denali functionality modules
import denali_arguments
import denali_authenticate
import denali_commands
import denali_gauntlet
import denali_groups
import denali_help
import denali_history
import denali_location
import denali_monitoring
import denali_search
import denali_sis_integration
import denali_update
import denali_utility
import denali_types
import denali_variables

from denali_tty import colors

denali_vars = denali_variables.denaliVariables
home_dir = denali_utility.returnHomeDirectory(denali_vars)
if not os.path.exists(home_dir):
    os.mkdir(home_dir)

# disable the https warning messages for urllib3
try:
    import requests
except:
    # module doesn't exist -- denali requires this
    print "Denali Error:  python-requests module not available.  Execution cannot continue."
    exit(1)

if "packages" in dir(requests) and "urllib3" in dir(requests.packages) and "disable_warnings" in dir(requests.packages.urllib3):
    requests.packages.urllib3.disable_warnings()
    urllib_err1 = True

    # if InsecureRequestWarning module is loaded, disable requests there as well
    if "exceptions" in dir(requests.packages.urllib3) and "InsecureRequestWarning" in dir(requests.packages.urllib3.exceptions):
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
        urllib_err2 = True
elif "packages" not in dir(requests):
    # an older version of python-requests is installed -- it doesn't have the disable functionality
    urllib_err1 = "old_package"
    urllib_err2 = "old_package"

# Handle urllib3 errors in a Cygwin environment and with some python versions (disable error messages)
# putting the disable_warnings call under the 'try' also protects against a potential non-existent
# function or method (no python stack for these), which is nice.
try:
    import urllib3
    if "disable_warnings" not in dir(urllib3):
        urllib_err3 = "old_package"
    else:
        urllib3.disable_warnings()
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        urllib_err3 = True
except:
    # module doesn't exist
    pass

# This check affects monitoring -- where the ReadTimeout exception is used
if "exceptions" in dir(requests) and "ReadTimeout" in dir(requests.exceptions):
    req_readto = True



##############################################################################
#
# showAliasedColumnNames(denaliVariables, arguments)
#

def showAliasedColumnNames(denaliVariables, arguments):

    show_specific_daos    = False
    show_specific_aliases = False
    dao_search_keys       = []
    dao_alias_search_keys = []
    alias_search          = []
    daos_found            = 0
    searches_found        = 0
    column_width          = 28
    cmdb_def_keys         = denali_search.cmdb_defs.keys()
    cmdb_def_keys.sort()

    # if a dash is an argument, then just return -- no dao/alias display
    if '-' in arguments:
        return

    # only print a list of DAOs if requested, and then return
    if 'dao' in arguments or 'daos' in arguments or 'DAO' in arguments or 'DAOS' in arguments:
        alias_count = 0
        for key in cmdb_def_keys:
            alias_count += len(denali_search.cmdb_defs[key])
        print
        print "List of defined DAOs [%d] and their individual count of defined aliases [%d] in denali:" % (len(cmdb_def_keys), alias_count)
        print
        print "    DAO Name                  Alias Count"
        print "==========================================="
        for key in cmdb_def_keys:
            print "  + %s [%3d]" % (key.ljust(column_width), len(denali_search.cmdb_defs[key]))
        return

    print
    print "\"Column Name\"    :  Column title displayed on screen or in a file (txt and csv) at the top of an individual data column."
    print "\"Aliased Name\"   :  Can be used in the \"--fields\" or \"-f\" denali switch instead of the CMDB name (which is in the 3rd column)."
    print "\"CMDB Reference\" :  CMDB DAO reference which can be used in the \"--fields\" or \"-f\" switch."
    print

    # remove '--aliases' from the argument list (first parameter)
    arguments = arguments[1:]

    # Remove all arguments from the index to the end when a "--" is found
    # This fixes a problem where a credentials file is specified and thought
    # to be a search term by denali.  The result is that nothing is shown
    # and that is not right.
    if len(arguments):
        for (index, argument_value) in enumerate(arguments):
            if argument_value.startswith('--'):
                arguments = arguments[:index]
                break

    if len(arguments):
        for (sIndex, search_dao) in enumerate(arguments):
            for (dIndex, defined_dao) in enumerate(cmdb_def_keys):
                if defined_dao.lower() == search_dao.lower():
                    # Replace the submitted argument (potentially lowercase) with the correct
                    # case of the found/defined DAO name; append the found DAO to a new List.
                    arguments[sIndex] = defined_dao
                    dao_search_keys.append(defined_dao)

        if len(dao_search_keys):
            show_specific_daos = True

            # Replace the master dao list with the submitted search dao list
            cmdb_def_keys = dao_search_keys
            dao_search_keys.sort()

        # Determine if anything was submitted that wasn't a DAO name -- search parameter
        # within the DAOs to display (use a 'set' difference calculation)
        alias_search = list(set(arguments) - set(dao_search_keys))
        if len(alias_search) > 0:
            show_specific_aliases = True

    def printAliasHeader(dao_name, printHeader=True):
        if printHeader == True:
            print
            print "%s:" % key
            print "    Column Name                              Aliased Name                     CMDB Reference"
            print "    " + ("=" * 120)
        return False

    def printAliasInformation(key, index):
        print "    %-38s   %-30s   %s" % (denali_search.cmdb_defs[key][index][2],
                                          denali_search.cmdb_defs[key][index][0],
                                          denali_search.cmdb_defs[key][index][1])

    def printDaoList(daos_found, dao_alias_search_keys):
        starting_position = 37
        ending_position   = 75
        sys.stdout.write("    DAOs where matches are found  :  [%d] " % len(dao_alias_search_keys))
        total_length = 0
        for dao in dao_alias_search_keys:
            total_length += len(dao)
            if total_length > ending_position:
                # Add the trailing comma, and a newline for the next set of data
                print ","
                sys.stdout.write(" " * starting_position)
                total_length = len(dao)
            if total_length == len(dao):
                sys.stdout.write("%s" % dao)
            else:
                sys.stdout.write(", %s" % dao)
        print

    for key in cmdb_def_keys:
        # printHeader is set to TRUE for each new DAO
        printHeader = True

        # if this is false it means all DAOs or specific DAOs were targeted
        if show_specific_aliases == False:
            printAliasHeader(key)

        # Loop through all of the CMDB definitions (different options shown here):
        #   (1) Print all of them   ('--aliases' with no parameters after)
        #   (2) Print specific DAOs ('--aliases [dao name 1] [dn2] ...')
        #   (3) Print specific DAOs with search  ('--aliases [dao name 1] [dn2] [search item 1] [si2] ...')
        #   (4) Print search criter for all daos ('--aliases [search item 1] [si2] ...')
        for (index, row) in enumerate(denali_search.cmdb_defs[key]):
            if show_specific_aliases == True:
                for search_criteria in alias_search:
                    if (denali_search.cmdb_defs[key][index][0].lower().find(search_criteria.lower()) != -1 or
                        denali_search.cmdb_defs[key][index][1].lower().find(search_criteria.lower()) != -1 or
                        denali_search.cmdb_defs[key][index][2].lower().find(search_criteria.lower()) != -1):
                        if printHeader == True:
                            daos_found += 1
                            dao_alias_search_keys.append(key)
                        printHeader = printAliasHeader(key, printHeader)
                        printAliasInformation(key, index)
                        searches_found += 1
            else:
                printAliasInformation(key, index)

    # summary information
    if len(dao_search_keys) or len(alias_search):
        print
        print "Search Summary Information:"
        if len(dao_search_keys):
            print "  DAOs submitted to search for    :  [%d] %s" % (len(dao_search_keys), ', '.join(dao_search_keys))
        if len(alias_search):
            print "  Search criteria within DAOs     :  [%d] %s" % (len(alias_search), ', '.join(alias_search))
            printDaoList(daos_found, dao_alias_search_keys)
            print "    Matching items found          :  %3d" % searches_found


##############################################################################
#
# outputJSONFormat(denaliVariables, outputDictionary, targetType)
#

def outputJSONFormat(denaliVariables, outputDictionary, targetType):

    #denaliVariables["jsonPageOutput"] -- if True, print results
    #                                  -- if False, probably an intermediate
    #                                     result, do not print yet

    if denaliVariables["jsonPageOutput"] == True:

        # only output json if there's something to output
        if len(outputDictionary['results']) == 0:
            return

        if 'json' in targetType.type:
            # Should the output contain the "extra" information returned via
            # the web api?  (status, paging info, error_type, messages)?
            # For now, I'll remove it.
            outputDictionary = {"results":outputDictionary["results"]}
        else:
            return

        # For SMA integration -- if the location is specified as a field to output,
        # add a new field 'data_center' with a human-readable location; i.e., SIN2
        for (index, device) in enumerate(outputDictionary['results']):
            if 'location_id' in device:
                location_index = int(device['location_id'])
                outputDictionary['results'][index].update({'datacenter':denali_location.dc_location[location_index]})

        if targetType.type == 'json_file':            # JSON file output
            mode = 'a' if targetType.append else 'w'

            with open(targetType.filename, mode) as outFile:
                json.dump(outputDictionary, outFile, ensure_ascii=True, encoding='ascii')
                outFile.write('\n')

        elif targetType.type == 'json_screen':        # JSON screen output
            print json.dumps(outputDictionary, ensure_ascii=True, encoding='ascii')



##############################################################################
#
# outputYAMLFormat(denaliVariables, outputDictionary, targetType)
#
#   This format is used primarily (so far) for creating an update file that
#   Denali can use.  The idea would be you could request an update file prior
#   to doing an upgrade, and then manually edit the file and submit it back
#   to Denali to actually do the update.
#

def outputYAMLFormat(denaliVariables, outputDictionary, targetType):


    if 'yaml' in targetType.type or 'update' in targetType.type:
        if 'data' in outputDictionary and 'results' in outputDictionary['data']:
            outputDictionary = {"results":outputDictionary['data']['results']}
        else:
            return
    else:
        return

    # gather the fields to show/output
    fieldsOrig = denaliVariables["fields"].split(',')

    if targetType.type.startswith("update_"):
        # if an "update" file is wanted -- the fields need to be aliased correctly
        # e.g., CMDB's "device_service.full_name" won't work, but Updates "device_service" will, etc.
        fields = denali_update.useUpdateAliasesForFieldNames(fieldsOrig)

    # only output yaml if there's something to output
    if len(outputDictionary['results']) == 0:
        return True

    # output to a file
    if targetType.type == "yaml_file" or targetType.type == "update_file":

        try:
            if not targetType.append:
                outFile = open(targetType.filename, 'w')
            else:
                outFile = open(targetType.filename, 'a')
        except:
            # failure to open a file -- not a good sign.
            fileType = targetType.type[:targetType.type.find('_')]
            print "Denali error:  Could not open file: %s for writing in \"%s\" format." % (targetType.type, fileType)

        yamlItems = outputDictionary["results"][0].keys()

        for hostIndex in range(len(outputDictionary["results"])):
            hostname = "\nhost : %s\n" % outputDictionary["results"][hostIndex]["name"]
            outFile.write(hostname)

            if targetType.type == "yaml_file":
                for dataItem in outputDictionary["results"][hostIndex]:

                    # check and see if the data attribute is in the original field list (and it isn't
                    # the hostname -- that was already added)
                    if dataItem in fieldsOrig and dataItem != "name":
                        if dataItem == "location_id":
                            outputDictionary["results"][hostIndex][dataItem] = denali_location.dc_location[int(outputDictionary["results"][hostIndex][dataItem])]
                        hostData = "  %s : %s\n" % (dataItem, outputDictionary["results"][hostIndex][dataItem])
                        outFile.write(hostData)

            else:
                for dataItem in outputDictionary["results"][hostIndex]:
                    if dataItem in fieldsOrig and dataItem != "name":
                        data = outputDictionary["results"][hostIndex][dataItem]
                        fieldName = ''.join(denali_update.useUpdateAliasesForFieldNames([dataItem]))

                        if fieldName in fields:
                            hostData = "  %s : %s\n" % (fieldName, data)
                            outFile.write(hostData)

        outFile.close()

    # output to the screen
    elif targetType.type == "yaml_screen" or targetType.type == "update_screen":
        yamlItems = outputDictionary["results"][0].keys()

        for hostIndex in range(len(outputDictionary["results"])):
            print "\nhost : %s" % outputDictionary["results"][hostIndex]["name"]

            if targetType.type == "yaml_screen":
                for dataItem in outputDictionary["results"][hostIndex]:
                    if dataItem in fieldsOrig and dataItem != "name":
                        if dataItem == "location_id":
                            outputDictionary["results"][hostIndex][dataItem] = denali_location.dc_location[int(outputDictionary["results"][hostIndex][dataItem])]
                        print "  %s : %s" % (dataItem, outputDictionary["results"][hostIndex][dataItem])

            else:
                for dataItem in outputDictionary["results"][hostIndex]:
                    if dataItem in fieldsOrig and dataItem != "name":
                        data = outputDictionary["results"][hostIndex][dataItem]
                        fieldName = ''.join(denali_update.useUpdateAliasesForFieldNames([dataItem]))

                        if fieldName in fields:
                            print "  %s : %s" % (fieldName, data)

    return True



##############################################################################
#
# outputGenericFormat(denaliVariables, outputList, targetType, columnInfo, headers)
#

def outputGenericFormat(denaliVariables, outputList, targetType, columnInfo, headers):

    column_name_pos    = 2

    #print "targetType = %s" % targetType

    if 'file' in targetType.type:
        # check to make sure the directory path specified is valid.
        if targetType.filename.find('/') != -1:
            location = targetType.filename.rfind('/')
            file_target = targetType.filename[:location]

            # MRASEREQ-41019
            # this directory check need only run when a path is specified
            if os.path.isdir(file_target) == False:
                print "Denali Error: Directory path for file output does not exist [%s]." % file_target
                cleanUp(denaliVariables)
                exit(1)
        else:
            file_target = targetType.filename

        if not targetType.append:
            outFile = open(targetType.filename, 'w')
        else:
            outFile = open(targetType.filename, 'a')

    # include the column headers (for CSV files only)?
    if headers == True and not targetType.append:
        line = ''
        for column in columnInfo:
            if 'csv' in targetType.type:
                #line += "%s" % (column[column_name_pos] + ',')
                line += "%s%s" % (column[column_name_pos], denaliVariables["csvSeparator"])
        #else:
        if targetType.type == 'csv_screen':
            length = len(denaliVariables["csvSeparator"])
            print line[:-length]
        elif targetType.type == 'csv_file':
            length = len(denaliVariables["csvSeparator"])
            output = u'%s\n' % line[:-length]
            outFile.write(output.encode("UTF-8"))
            #outFile.write(line[:-1] + '\n')

    lineCount = len(outputList)
    for (count, outputLine) in enumerate(outputList):
        line = ''
        for dataItem in outputLine:
            # remove typical hidden characters
            dataItem = dataItem.replace('\t', " ")
            dataItem = dataItem.replace('\r', " ")
            dataItem = dataItem.replace('\n', " ")

            if 'csv' in targetType.type:              # CSV delimited output type

                # sometimes a column element is multi-valued (separated by
                # a comma -- which makes CSV output look wrong).  This code
                # fixes that problem.
                if dataItem.find(",") != -1:
                    dataItem = dataItem.replace(",", "/")

                if 'screen' in targetType.type:
                    #line += "%s," % dataItem.strip()
                    line += "%s%s" % (dataItem.strip(), denaliVariables["csvSeparator"])
                elif 'file' in targetType.type:
                    #line += "%s," % dataItem.strip()
                    line += "%s%s" % (dataItem.strip(), denaliVariables["csvSeparator"])

            elif 'space' in targetType.type:          # SPACE delimited output type
                if 'screen' in targetType.type:
                    # trailing space e.g., "%s " isn't necessary as the print operation
                    # automatically includes a space after each statement
                    print "%s" % dataItem.strip().encode("UTF-8"),
                elif 'file' in targetType.type:
                    output = u'%s ' % dataItem.strip()
                    outFile.write(output.encode("UTF-8"))
                    #outFile.write((dataItem.strip() + ' '),)

            elif 'comma' in targetType.type:          # COMMA delimited output type
                if 'screen' in targetType.type:
                    # Use sys.stdout.write to not create a newline for all hosts that
                    # precede the last (with a comma).  On the last, just print it.
                    if count == (lineCount - 1):
                        print "%s" % dataItem.strip().encode("UTF-8")
                    else:
                        sys.stdout.write("%s," % dataItem.strip())
                elif 'file' in targetType.type:
                    if count == (lineCount - 1):
                        output = u'%s' % dataItem.strip()
                    else:
                        output = u'%s,' % dataItem.strip()
                    outFile.write(output.encode("UTF-8"))

            elif 'newline' in targetType.type:        # NEWLINE delimited output type
                if 'screen' in targetType.type:
                    print "%s" % dataItem.strip().encode("UTF-8")
                elif 'file' in targetType.type:
                    output = u'%s\n' % dataItem.strip()
                    outFile.write(output.encode("UTF-8"))

        #else:
        if 'csv' in targetType.type:              # Handle newline output for type CSV
            length = len(denaliVariables["csvSeparator"])
            if 'screen' in targetType.type:
                print "%s" % line[:-length].encode("UTF-8")
            elif 'file' in targetType.type:
                output = u'%s\n' % line[:-length]
                outFile.write(output.encode("UTF-8"))
                #outFile.write(line[:-1] + '\n')

    if 'file' in targetType.type:
        outFile.close()
    else:
        # these print statements just make outputs on the screen look nicer
        # by providing a newline after the output finishes (space_screen)
        # gets one extra newline than the others.
        if "space_screen" in targetType.type:
            pass
            #print
        pass
        #print



##############################################################################
#
# prioritizeOutput(outputTypes)
#

def prioritizeOutput(denaliVariables, origOutputTypes):
    # Search through the output list.  See if there is an output type for
    # csv file.  If not, add it.

    # Make a copy of the original input list so we don't modify it in-place.
    otypes = copy.deepcopy(origOutputTypes)

    csv_files = [item for item in otypes if item.type == 'csv_file']

    if not csv_files:
        PID = os.getpid()
        time = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
        fileName = '/tmp/denali-tmp-%s-%s.csv' % (PID, time)
        denaliVariables["tmpFilesCreated"].append(fileName)
        otypes.insert(0, denali_types.OutputTarget(type='csv_file', filename=fileName, append=False))
    # Only reorder items if some are NOT csv_file type.
    elif len(csv_files) < len(otypes):
        # reversed() here ensures that multiple csv_file items keep their
        # ordering respective to each other.
        for item in reversed(csv_files):
            otypes.remove(item)
            otypes.insert(0, item)

    return otypes


##############################################################################
#
# outputTargetDetermination(argument)
#

def outputTargetDetermination(denaliVariables, outputVariable, over_write_existing_file=True):
    # output can be to multiple places; i.e., screen(txt), and file(csv,json)
    # Handle all of these cases
    outputTypes = []

    FORMATS = ('txt', 'csv', 'json', 'space', 'newline', 'comma', 'update', 'yaml')

    targets = [t.strip() for t in outputVariable.split(',')]
    for target in targets:
        if '.' in target:
            # Treat as a file
            target = os.path.expanduser(target)
            if os.path.isfile(target) and not over_write_existing_file:
                continue
            else:
                ext = target.split('.')[-1].lower()
                name = ext+'_file' if ext in FORMATS else 'txt_file'
                outputTypes.append(denali_types.OutputTarget(type=name, filename=target, append=False))
        else:
            target = target.lower()
            name = target+'_screen' if target in FORMATS else 'txt_screen'
            outputTypes.append(denali_types.OutputTarget(type=name, filename='', append=False))

    # prioritize the output types -- files first, followed by screen output
    outputTypes = prioritizeOutput(denaliVariables, outputTypes)

    #print "outputTypes = %s" % outputTypes

    return outputTypes



##############################################################################
#
# generateServerRange(server1, server2)
#

def generateServerRange(server1, server2):

    serverRange = []

    # get the servers and their locations (from the name)
    if server1.count('.') == 0 or server2.count('.') == 0:
        print
        print "A range of hosts was requested between %s and %s." % (server1, server2)
        print "However, there is no data center identifier on the host name(s)."
        print "The range syntax requires an identical DC location between the"
        print "two host end-points.  This range is excluded from the current"
        print "search pattern."
        print

        return False

    server1_location = server1.split('.')
    server2_location = server2.split('.')

    if server1_location[1] != server2_location[1]:
        print
        print "A range of hosts was requested between %s and %s." % (server1, server2)
        print "However, the data center locations of the two hosts are different,"
        print "so the range feature is disabled for this host pair.  Adding each"
        print "host individually."
        print

        return [server1, server2]

    #
    # determine the class and number in the server name
    #
    # most corporate production servers have a basic name configuration:
    #   [a-z][0-9].[location]
    #   The first part of the name is alphabetic characters
    #   The second part of the name is numeric characters
    #   The third part of the name represents the data center where the server is located
    #

    digits = [ '0', '1', '2', '3', '4', '5', '6', '7', '8', '9' ]

    for (index, char) in enumerate(server1_location[0]):
        if char not in digits:
            continue
        else:
            # found the first digit
            server1_alpha = str(server1_location[0])[:index]
            server1_num   = str(server1_location[0])[index:]
            break

    for (index, char) in enumerate(server2_location[0]):
        if char not in digits:
            continue
        else:
            # found the first digit
            server2_alpha = str(server2_location[0])[:index]
            server2_num   = str(server2_location[0])[index:]
            break

    if server1_alpha != server2_alpha:
        print "Server names are not sequentially compatible.  The names must be identical"
        print "except for the numbers.  Name prefixes discovered: (1) %s  and  (2) %s" % (server1_alpha, server2_alpha)
        print
        return False

    # get the length of the string number (just in case it needs to be zero-filled)
    zpad = len(server1_num)

    start = int(server1_num)
    stop  = int(server2_num) + 1    # add 1 to the 'stop' because a range doesn't include the stop number.

    if int(server1_num) > int(server2_num):
        step = -1
    elif int(server2_num) > int(server1_num):
        step = 1
    else:
        step = 1


    # build the server names based on the range given
    for number in range(start, stop, step):
        serverRange.append(server1_alpha + str(number).zfill(zpad) + '.' + server1_location[1])

    return serverRange


##############################################################################
#
# compileServerRange(inputList)
#

def compileServerRange(inputList):

    finalServerRange  = []
    standAloneServers = []
    rangeServers      = []


    # multiple ranges supplied?
    for server in inputList:
        if server.count('..') == 0:
            # we have a single, stand-alone server (not paired/ranged)
            standAloneServers.append(server)
        else:
            rangeServers.append(server)

    # add the stand-alone server(s) to the list
    if len(standAloneServers) > 0:
        for server in standAloneServers:

            # search for 'sets' of data
            if '[' in server and ']' in server:
                # found a 'set' query in the server name
                start = server.find('[')
                end   = server.find(']')
                if (end - start) > 11:
                    print "Perhaps a different method is needed to query"
                    print "for servers with a %d character set." % (end - start)
                    print "The code allows for 10 characters or less in"
                    print "a single set."
                    print
                    continue
                else:
                    if start == 0:
                        beginning = ''
                    else:
                        beginning = server[:start]

                    middle_chars = server[(start + 1):end]
                    ending       = server[(end + 1):]

                    for (count, char) in enumerate(middle_chars):
                        new_server = beginning + char + ending
                        finalServerRange.append(new_server)
                        #print "#%d: new_server = %s" % (count, new_server)
            else:
                finalServerRange.append(server)

    # process through the serverPaired list
    for servers in rangeServers:

        # search for wildcards -- they aren't supported in ranges
        if '*' in servers or '?' in servers or '_' in servers:
            print
            print "Server syntax submitted: %s" % servers
            print
            print "Wildcard characters (*,?, etc.), are not supported in a range request."
            print "Please re-enter the range without wildcard characters."
            print
            return False

        countDots = servers.count('..')

        if countDots > 0:
            serverList = servers.split('..')
            server1 = serverList[0]
            server2 = serverList[1]

            rValue = generateServerRange(server1, server2)
            if rValue != False:
                #print "rValue = %s" % rValue
                finalServerRange.extend(rValue)

    return finalServerRange



##############################################################################
#
# readInServerList(denaliVariables, inputData, file_or_stdin)
#
#   If file_or_stdin == True, then process as a file
#   If file_or_stdin == False, then process as stdin

def readInServerList(denaliVariables, inputData, file_or_stdin):

    serverList    = []
    host_commands = False

    if denaliVariables['hostCommands']['active'] == True:
        host_commands = True

    # In-function/function to separate lines of a file or stdin
    def separateServers(serverLines):

        serversFound = []
        serverLines  = serverLines.splitlines()     # put it in a list of lines

        for line in serverLines:

            # eliminate duplicates or other potential problem characters from the line
            line = line.replace(",", " ")
            line = line.replace("..", ".")

            while "  " in line:
                line = line.replace("  ", " ")

            # check for an empty line -- don't include it in the server list returned
            if line == ' \n' or line == '' or line == ' ' or line.strip().startswith('#'):
                continue

            # eliminate "white space" (spaces/tabs, etc.) at the beginning or end of
            # the server name
            line = line.strip()

            if host_commands == True:
                # Assume the file is constructed orderly -- one host per line and one command
                # for the host per line following a colon
                # This assumption allows host commands to have spaces imbedded; however, if the
                # user makes a 'crazy' file, it will fail.
                length = 1
            else:
                # Typical run-through -- able to accommodate a messy file with multiple hosts
                # on the same line (separated by a least a single space)
                length = len(line.split(' '))

            if length > 1:
                # found multiple servers on the same line
                line = line.split(' ')
                serversFound.extend(line)
            else:
                # found a single server on the line
                serversFound.append(line)

        return serversFound


    if file_or_stdin == True:                       # file list of servers

        if os.path.isfile(inputData) == True:
            # open the file in read mode
            serverFile = open(inputData, 'r')       # open the file for reading
            servers = serverFile.read()             # read in the entire file
            serverList = separateServers(servers)   # separate out the servers
            serverFile.close()                      # close the file
        else:
            # requested file doesn't exist -- error out.
            print "File missing:  Specified server file [%s] doesn't exist." % inputData
            print "               Halting execution."
            return False

        serverList = denali_utility.stripServerName(serverList, denaliVariables)

        if denaliVariables['hostCommands']['active'] == True:
            serverList = denali_utility.fillOutHostCommandList(denaliVariables, serverList)

        return list(set(serverList))

    elif file_or_stdin == False:                    # stdin list of servers
        serverList = separateServers(inputData)
        serverList = denali_utility.stripServerName(serverList, denaliVariables)

        if denaliVariables['hostCommands']['active'] == True:
            serverList = denali_utility.fillOutHostCommandList(denaliVariables, serverList)

        return list(set(serverList))

    return False



##############################################################################
#
# process_arguments(argument, arguments, denaliVariables)
#
#   This function takes an argument pair, (1) --file   (2) server.txt,
#   and calls the proper function to handle the argument (file input,
#   searching, etc.).
#

def process_arguments(arg_pair, arguments, denaliVariables):

    # debugging time information for each argument processed
    denali_utility.addElapsedTimingData(denaliVariables, arg_pair[0] + '_start', time.time())
    denali_utility.addElapsedTimingData(denaliVariables, 'process_arguments_start', time.time())

    global searchArgument

    missing_value = False

    #print "Process:  arg_values = %s" % arg_pair
    if arg_pair[1] == "Waiting":    # In the argument pair, the 2nd value doesn't exist;
                                    # this may (or may not) be bad -- the criticality is
                                    # based on the parameter used/missing.
        missing_value = True

    # convert the first value to lowercase (just in case there are any fat-fingered
    # mistakes inside of the argument pair; e.g., --iNtErAcTiVe)
    arg0 = arg_pair[0].lower()

    if arg0 == "--showsql":
        # verbosity is requested -- enable/toggle the switch to turn this on.
        denaliVariables["showsql"] = True
        return True

    elif arg0 == "--help":
        help_subsection = []
        for parameter in denaliVariables['cliParameters']:
            help_subsection.extend(parameter)
        denali_help.denaliHelpDisplay(denaliVariables, help_subsection)
        return False

    elif arg0 == "--version":
        denaliVersionDisplay(denaliVariables)
        return False

    elif arg0 == "--aliases":
        denali_arguments.showDefaultAliases(denaliVariables)
        showAliasedColumnNames(denaliVariables, arguments)
        # clean up (if needed) and exit with the success value (0)
        cleanUp(denaliVariables)
        exit(0)

    elif arg0 == "--aliasheaders":
        denaliVariables['aliasHeaders'] = True
        return True

    elif arg0 == "--config":
        # make sure the argument is a valid file/directory combination
        ccode = denali_utility.loadConfigFile(denaliVariables, arg_pair[1], user_submitted=True)
        return True

    elif arg0 == "--debug":
        denaliVariables["debug"] = True
        return True

    elif arg0 == "--monitoringdebug":
        denaliVariables["monitoring_debug"] = True
        return True

    elif arg0 == "--mondetails":
        denaliVariables['mon_details'] = True
        return True

    elif arg0 == "--monvalidate":
        denaliVariables['monitorResponseValidate'] = True
        return True

    elif arg0 == "--updatedebug":
        denaliVariables["updateDebug"] = True
        return True

    elif arg0 == "--sisdebug":
        denaliVariables["sis_debug"] = True
        return True

    elif "--showdecomm" in arg0:
        denaliVariables["defaults"] = False
        return True

    elif arg0 == "--summary":
        denaliVariables["summary"] = True
        return True

    elif arg0 == "--nosummary":
        denaliVariables["noSummary"] = True
        return True

    elif arg0 == "--truncate":
        denaliVariables["textTruncate"] = True
        return True

    elif arg0 == "--nowrap":
        denaliVariables["textTruncate"] = False
        denaliVariables["textWrap"]     = False
        return True

    elif arg0 == "--quiet":
        denaliVariables["showInfoMessages"] = False
        return True

    elif arg0 == "--verify" or arg0 == "-v":
        denaliVariables["devServiceVerify"] = True
        if len(arg_pair) > 1 and arg_pair[1] and arg_pair[1] != 'Waiting':
            denaliVariables['devServiceVerifyData'].update({'verify_command':arg_pair[1]})
        return True

    elif arg0 == "--verify_hosts" or arg0 == "--vh":
        # quick test to make sure the value is an integer
        try:
            int(arg_pair[1])
        except ValueError:
            print "Denali Error: --verify_hosts given a non-integer value.  Execution stopped."
            return False
        denaliVariables["devServiceVerifyData"]['verify_host_count'] = int(arg_pair[1])
        return True

    elif arg0 == "--attrcolumns":
        denaliVariables["attributesStacked"] = False
        return True

    elif arg0 == "--clearoverrides":
        # Single parameter (no --updateattr=<...> needed), and it will take care of the entire process
        # of finding, and then clearing any overridden attributes.
        denaliVariables["clearOverrides"] = True

        # update CMDB data records
        if denaliVariables["allowUpdates"] == False:
            print "CMDB updating functionality is not enabled."
            return False

        ccode = denali_update.validateRollbackDirectory(denaliVariables)
        if ccode == False:
            # there's a problem here -- do not proceed with any updates
            return False

        # massage the passed in parameters; put the results in denaliVariables["updateParameters"]
        refresh = True
        denaliVariables["updateMethod"] = "attribute"

        # Fill in the denaliVariables["updateParameters"] location with the update parameter(s)
        # This function creates a dictionary that looks like this:
        #   denaliVariables['updateParameters']={'all': ['COBBLER_PROFILE=techos-7-an', 'RAID_SETTINGS=10']}
        #   for the clearattributes setting, it may be that some hosts have 1 attributes that is overridden,
        #   and other hosts have 5.  This has to be a new function ... similar structure as above, but with
        #   hosts separated, instead of in the 'all' category.
        ccode = denali_update.organizeOverriddenAttributes(denaliVariables)
        if ccode == False:
            print "No devices found for the query submitted (6)."
            return False

        if denaliVariables['autoConfirm'] == False:
            while (refresh == True):
                refresh = False
                ccode = denali_update.updateListOfServers(denaliVariables)
                if ccode == False:
                    if denaliVariables["updateDebug"] == True:
                        api = denaliVariables["api"]
                        print "\nERROR:"
                        print "   STATUS : " + api.get_response_status()
                        print "   TYPE   : " + str(api.get_error_type())
                        print "   MESSAGE: " + api.get_error_message()
                        print
                    return False

                elif ccode == "refresh":
                    refresh = True
                    denaliVariables["updatePreview"] = True
                elif ccode == "quit":
                    return True
        else:
            ccode = denali_update.updateListOfServers(denaliVariables)
            if ccode == False:
                if denaliVariables["updateDebug"] == True:
                    api = denaliVariables["api"]
                    print "\nERROR:"
                    print "   STATUS : " + api.get_response_status()
                    print "   TYPE   : " + str(api.get_error_type())
                    print "   MESSAGE: " + api.get_error_message()
                    print
                return False
            return True

        return True

    elif arg0 == "--showoverrides":
        denaliVariables["attributeOverride"] = True
        return True

    elif arg0 == "--showinherit":
        denaliVariables["attributeInherit"] = True
        return True

    elif arg0 == "--autoresize" or arg0 == "--ar":
        denaliVariables["autoColumnResize"] = True
        return True

    elif arg0 == "--separator":
        denaliVariables["csvSeparator"] = arg_pair[1]
        return True

    elif arg0 == "--yes":
        # for CMDB SOR updates
        denaliVariables["autoConfirm"] = True
        return True

    elif arg0 == "--yes_sis":
        # for SIS SOR updates
        denaliVariables["autoConfirm"]       = True     # for CMDB code loop
        denaliVariables["autoConfirmSIS"]    = True     # for SIS fingerprint code loop
        denaliVariables["updateSISAccepted"] = True     # check if fingerprint was accepted
        denaliVariables["autoConfirmAllSIS"] = True     # by-pass all checks -- accept all
        return True

    elif arg0 == "--nostdin":
        # disable checking for stdin -- typically used when denali is launched from within
        # a shell script or another program
        denaliVariables['nostdin'] = True
        return True

    elif arg0 == "--list":
        denaliVariables["listToggle"] = True
        denaliVariables["textWrap"] = False
        return True

    elif arg0 == "--nocolors":
        denaliVariables["nocolors"] = True
        return True

    elif arg0 == "--refresh":
        denaliVariables["refresh"] = True
        return True

    elif arg0 == "--relogin":
        denaliVariables["relogin"] = True
        return True

    elif arg0 == "--testauth":
        denaliVariables["testAuth"] = True
        return True

    elif arg0 == "--auth":
        denaliVariables["authenticateOnly"] = True
        return True

    elif arg0 == "--time":
        denaliVariables["time_display"] = True
        return True

    elif arg0 == "--m_separator":
        denaliVariables["mon_output"] = arg_pair[1]
        return True

    # MRASEREQ-40937
    elif arg0 == "--jira_closed":
        denaliVariables["jira_closed"] = True
        return True

    # add to help determine who is going to be oncall with a forwarding schedule
    elif arg0 == "--check_forwarding_schedule":
        denaliVariables["checkForwardingOnCall"] = True
        return True

    elif arg0 == "--singleupdate":
        denaliVariables["singleUpdate"] = True
        return True

    elif arg0 == "--screen":
        denaliVariables["pdshScreen"] = True
        return True

    elif arg0 == "--screendm":
        denaliVariables["pdshScreenDM"] = True
        return True

    elif arg0 == "--noanalytics":
        denaliVariables["analytics"] = False
        return True

    elif arg0 == "--validate":
        denaliVariables["validateData"] = True
        return True

    elif arg0 == "--combine":
        denaliVariables["combine"] = True
        return True

    elif arg0 == "--nofork":
        denaliVariables["nofork"] = True
        return True

    elif arg0 == "--nolog":
        if denaliVariables['debug'] == True:
            print "Denali PDSH/SSH Logging Disabled"
        denaliVariables["noLogging"] = True
        return True

    elif arg0 == "--spots_grep":
        denaliVariables["spotsGrep"] = True
        return True

    elif arg0 == "--src" or arg0 == "--source":
        denaliVariables["scpSource"] = arg_pair[1]
        return True

    elif arg0 == "--dest" or arg0 == "--destination":
        denaliVariables["scpDestination"] = arg_pair[1]
        return True

    elif arg0 == "-i" or arg0 == "--interactive":
        denaliVariables["interactive"] = True
        return True

    elif arg0 == "--orch" or arg0 == "--orchestration":
        denaliVariables["orchFilename"] = arg_pair[1]
        return True

    elif arg0 == "--symlink":
        denaliVariables["commandOutputSymlink"] = arg_pair[1]
        # If the file (symlink) already exists, delete it
        # If the symlink requested is a file, do not touch it; error out and continue
        try:
            ccode = os.path.islink(denaliVariables['commandOutputSymlink'])
            if ccode == True:
                os.remove(arg_pair[1])
                return True

            ccode = os.path.isfile(denaliVariables['commandOutputSymlink'])
            if ccode == True:
                print "Denali Warning: Symlink not created.  File of the same name exists [%s]." % denaliVariables['commandOutputSymlink']

                # clear out the symlink data -- this will prevent creation in the command module
                denaliVariables['commandOutputSymlink'] = ''
        except:
            pass
        return True

    elif arg0 == "--sis" or arg0 == "--omnitool" or arg0 == "--ot":
        if arg_pair[1] == "Waiting":
            print "Denali Syntax Error:  SIS Integration command [%s] requires submitted data to continue.  Execution halted." % arg0
            cleanUp(denaliVariables)
            exit(1)

        # assign the variable
        denaliVariables['sis_command'] = arg_pair[1]

        # call the function to process the request
        ccode = denali_sis_integration.entryPoint(denaliVariables)
        cleanUp(denaliVariables)
        if ccode == True:
            exit(0)
        else:
            exit(1)
        return True

    elif arg0 == "--retry":
        if arg_pair[1] == "Waiting":
            denaliVariables['commandRetry'] = denaliVariables['commandRetryDefault']
        else:
            if arg_pair[1].isdigit() == True:
                denaliVariables['commandRetry'] = int(arg_pair[1])
            else:
                print "Denali Syntax Error:  Retry count must not contain a string or character."
                cleanUp(denaliVariables)
                exit(1)

        return True

    elif arg0 == "--updatesor":
        if arg_pair[1] == "Waiting":
            sor_destination = denaliVariables['sorDefault']
        else:
            sor_destination = arg_pair[1]

        denaliVariables['sorUpdateTo'] = denali_utility.sorTranslate(denaliVariables, sor_destination)
        if denaliVariables['sorUpdateTo'] == -1:
            # failure -- exit out
            cleanUp(denaliVariables)
            exit(1)

        # get list of devices to update
        ccode = denali_utility.createServerListFromArbitraryQuery(denaliVariables)
        if ccode == False:
            print "Denali Error: Failed to find requested devices.  Exiting."
            cleanUp(denaliVariables)
            exit(1)

        # do the Source of Record update
        ccode = denali_update.doSourceOfRecordUpdate(denaliVariables)
        if ccode == False:
            cleanUp(denaliVariables)
            exit(1)

        # completed -- exit out
        cleanUp(denaliVariables)
        exit(0)

        return True

    elif arg0 == "--track":
        # gauntlet track specified
        if denaliVariables['gauntletPromotion'] == -1 and arg_pair[1] not in ['all', 'list']:
            # not entered -- reject this request with a contextual error message
            print "Denali Error: To use \'--track\', the \'--promotion-level\' switch must also be used to specify the target environment."
            print "  Example:  denali --track=amps --promotion-level=beta"
            cleanUp(denaliVariables)
            exit(1)

        ccode = denali_gauntlet.retrieveDeviceServiceAndEnvironmentList(denaliVariables, arg_pair[1])
        if ccode == False:
            return False

        # Without this piece of code, denali would attempt to query the whole environment after
        # the list of tracks is displayed (this is probably not what the user wants)
        if arg_pair[1] in ['all', 'list']:
            cleanUp(denaliVariables)
            exit(0)

        return True

    elif arg0 == "--promotion-level":
        # based on the retrieved data (--track) limit the targeted hosts to whatever
        # the value specified here is (this is an environment: dev, qe, etc.)
        denaliVariables['gauntletPromotion'] = arg_pair[1]
        return True

    elif arg0 == "--logoutput":
        logoutput_set = set()
        output_arguments = arg_pair[1].split(',')
        # accept first letter arguments for:
        #   [s]uccess
        #   [f]ailure
        #   [n]ormal
        # The presence of these values in the List is what triggers whether
        # or not the log type is shown.  If nothing is here, everything is
        # shown.  If something is here, only what is present is displayed.
        for value in output_arguments:
            if value.lower().startswith('f'):
                logoutput_set.update(['failure'])
            elif value.lower().startswith('s'):
                logoutput_set.update(['success'])
            elif value.lower().startswith('n'):
                logoutput_set.update(['normal'])
        denaliVariables['commandOutput'] = list(logoutput_set)
        return True

    elif arg0 == "--progress":
        if arg_pair[1] == '0' or arg_pair[1].lower() == 'percent' or arg_pair[1].lower() == 'default':
            denaliVariables['commandProgressBar'] = 0
        elif arg_pair[1] == '1' or arg_pair[1].lower() == 'plus' or arg_pair[1].lower().startswith('adv'):
            denaliVariables['commandProgressBar'] = 1
        elif arg_pair[1] == '2' or arg_pair[1].lower() == 'bar':
            denaliVariables['commandProgressBar'] = 2
        elif arg_pair[1] == '4' or arg_pair[1].lower() == 'test':
            denaliVariables['commandProgressBar'] = 3
        elif arg_pair[1] == '3' or arg_pair[1].lower() == 'none' or arg_pair[1].lower().startswith('disable'):
            denaliVariables['commandProgressBar'] = 4
        return True

    elif arg0 == "--rcode":
        denaliVariables["pdshDshbakLog"] = False
        return True

    elif arg0.startswith("--pdsh_apps"):
        if arg_pair[1] < 0:
            arg_pair[1] = -1
        denaliVariables["pdshAppCount"] = arg_pair[1]

        # if the app count was given, show the nice summary table
        denaliVariables["summary"] = True
        return True

    elif arg0.startswith("--ssh_comm") or arg0 == "--sc":
        # MRASEREQ-41586
        if arg_pair[1] == "Waiting":
            print "Denali syntax error:  ssh command [%s] missing argument value" % arg0
            return False
        denaliVariables["sshCommand"] = arg_pair[1]
        return True

    elif arg0.startswith("--ssh_opt"):
        # MRASEREQ-41586
        if arg_pair[1] == "Waiting":
            print "Denali syntax error:  ssh options [%s] missing argument value" % arg0
            return False
        denaliVariables["sshOptions"] = arg_pair[1]
        return True

    elif arg0.startswith("--retry_comm") or arg0 == "--rc":
        if arg_pair[1] == "Waiting":
            print "Denali syntax error:  retry command [%s] missing argument value" % arg0
            return False
        denaliVariables["retryCommand"] = arg_pair[1]
        return True

    elif arg0.startswith("--pdsh_comm") or arg0 == "--pc":
        # MRASEREQ-41586
        if arg_pair[1] == "Waiting":
            print "Denali syntax error:  pdsh command [%s] missing argument value" % arg0
            return False
        denaliVariables["pdshCommand"] = arg_pair[1]
        return True

    elif arg0 == "--pci":
        # interactive entry of pdsh command
        ccode = denali_commands.retrieveInteractivePDSHCommand(denaliVariables)
        return ccode

    elif arg0.startswith("--pdsh_opt") or arg0 == "--po":
        # MRASEREQ-41586
        if arg_pair[1] == "Waiting":
            print "Denali syntax error:  pdsh options [%s] missing argument value" % arg0
            return False
        denaliVariables["pdshOptions"] = arg_pair[1]
        return True

    elif arg0 == "--pdsh_offset" or arg0 == "--offset":
        if arg_pair[1] == "Waiting":
            print "Denali syntax error:  pdsh offset [%s] missing argument value" % arg0
            return False
        denaliVariables["pdshOffset"] = int(arg_pair[1])
        return True

    elif ((arg0 == "--pdsh_separator" or
           arg0 == "--pdsh_separate"  or
           arg0 == "--ps")            and denaliVariables['hostCommands']['active'] == False):
        # only set the separator value if --host_commands isn't being used (that would mess up the segments)
        if arg_pair[1] == "Waiting":
            print "Denali syntax error:  pdsh separate is missing the argument value [%s]" % arg0
            return False
        denaliVariables['pdshSeparate'] = {'separator':arg_pair[1]}
        return True

    elif arg0.startswith("--scp_opt") or arg0 == "--so":
        # MRASEREQ-41586
        if arg_pair[1] == "Waiting":
            print "Denali syntax error:  [%s] missing argument value" % arg0
            return False
        denaliVariables["scpOptions"] = arg_pair[1]
        denaliVariables["sshOptions"] = arg_pair[1]
        return True

    elif arg0 == "--scp_norename":
        denaliVariables["scpRenameDestFile"] = False
        return True

    elif arg0 == "--sudo":
        # MRASEREQ-41775
        denaliVariables['sudoUser'] = arg_pair[1]
        return True

    elif arg0.startswith("--num_procs"):
        if int(arg_pair[1]) < 1:
            return True
        if int(arg_pair[1]) > denaliVariables["maxProcesses"]:
            # maximum exceeded -- throw an error and exit out
            print "Denali Syntax Error:  Number of processes requested has exceeded the maximum hard-coded value of [%i]." % denaliVariables['maxProcesses']
            print "                      Choose a number at or below the maximum and resubmit the request."
            return False
        denaliVariables["num_procs"] = int(arg_pair[1])
        return True

    elif arg0.startswith("--conn_timeout"):
        if int(arg_pair[1]) < 1 or int(arg_pair[1]) > denaliVariables["maxConnTimeout"]:
            # if an unreasonable number is given, do not set it to anything
            # this will leave it as the maximum value
            return True

        denaliVariables['connectTimeout'] = int(arg_pair[1])
        return True

    elif arg0.startswith("--proc_timeout"):
        if int(arg_pair[1]) < 1:
            return True

        denaliVariables["processTimeout"] = int(arg_pair[1])
        return True

    elif arg0 == "--non-interactive" or arg0 == "--ni":
        denaliVariables["non_interact"] = True
        return True

    elif arg0.startswith("--slack"):
        # if run from slack, do not allow updates
        denaliVariables["allowUpdates"] = False
        return True

    elif arg0 == "--update_key":
        # if this is used, it means that an update will happen with a non-hostname
        # database/SKMS key for device searching.
        denaliVariables["updateKey"] = arg_pair[1]
        return True

    elif arg0 == "--defupdate":
        if arg_pair[1].lower() == "remove":
            denaliVariables["updateDefault"] = "remove"
        elif arg_pair[1].lower() == "replace":
            denaliVariables["updateDefault"] = "replace"
        return True

    elif "--creds" in arg0:
        # if denaliVariables["noSearchNeeded"] is set, no authentication is needed either
        if denaliVariables["noSearchNeeded"] == True:
            if denaliVariables["debug"] == True:
                print "Credentials Login by-passed due to \"no search required\" parameter being set"
            return True

        # mark this setting to True (in case the creds file fails -- for whatever reason)
        denaliVariables["credsFileUsed"] = True

        if missing_value == True:
            # Missing credentials value (no file value found)
            # Treat the login attempt as if it were a user.

            # Any "--user" should have already been removed, so adding this one will cause
            # the next parameter processed to treat this like an empty user.
            cliParameters.append(["--user", "Waiting"])
            return False
        else:
            # branch off to handle the file operation to read the credentials file.
            (username, password) = denali_authenticate.readCredentialsFile(arg_pair[1], denaliVariables)
            denaliVariables['time']['skms_auth_start'].append(time.time())
            ccode = denali_authenticate.authenticateAgainstSKMS(denaliVariables, "credentials", username, password)
            denaliVariables['time']['skms_auth_stop'].append(time.time())
            if ccode == False:
                # authentication failed -- exit
                return False
            else:
                return True

    elif "--mon_creds" in arg0:
        if missing_value == True:
            return False
        else:
            (mon_username, mon_password) = denali_authenticate.readCredentialsFile(arg_pair[1], denaliVariables)

            # authenticate right now -- to make sure this works
            url     = '/auth'
            method  = 'post'
            action  = ''
            payload = {"username":mon_username.strip(), "password":mon_password.strip()}

            # Only the username is kept, because the session file creation obviates the need to store the password
            denaliVariables['dm_username'] = mon_username.strip()
            monitoring_data = {'monapi_data':[url, method, action, payload]}
            (ccode, response) = denali_monitoring.monitoringAPICall(denaliVariables, monitoring_data, mon_username, mon_password)
            if denaliVariables['debug'] == True or denaliVariables["debugLog"] == True:
                if ccode == True:
                    outputString = "Login debug: Authentication against the Monitoring API: SUCCESSFUL"
                else:
                    outputString = "Login debug: Authentication against the Monitoring API: FAILED"
                denali_utility.debugOutput(denaliVariables, outputString)
            return True

    elif arg0 == "-u" or arg0 == "--user":
        # if denaliVariables["noSearchNeeded"] is set, no authentication is needed either
        if denaliVariables["noSearchNeeded"] == True:
            if denaliVariables["debug"] == True:
                print "User Login by-passed due to \"no search required\" parameter being set"
            if arg_pair[1] != "Waiting":
                denaliVariables["userName"] = arg_pair[1]
            return True

        # Check if "--creds" and "--user" were both submitted to denali.
        # The web API will be filled out if a request was made (for creds)
        # if so, do nothing here.
        if denaliVariables["api"] != False and denaliVariables["api"] != None:
            # check if a group was requested, if so, continue
            if len(denaliVariables['groupList']) == 0:
                return False

        # set the username variable in denaliVariables to the --user=<name>
        if arg_pair[1] != "Waiting":
            # if "Waiting", it means no username or credentials were given
            denaliVariables["userName"] = arg_pair[1]

        denaliVariables['time']['skms_auth_start'].append(time.time())
        ccode = denali_authenticate.authenticateAgainstSKMS(denaliVariables, "username")
        denaliVariables['time']['skms_auth_stop'].append(time.time())
        if ccode == False:
            # authentication failed -- exit
            return False

        if denaliVariables['authenticateOnly'] == True:
            cleanUp(denaliVariables)
            if ccode == False:
                exit(1)
            else:
                exit(0)

    elif arg0 == "--stdin":
        denaliVariables["stdinData"] = arg_pair[1]
        return True

    elif arg0 == "--history":
        denaliVariables["historyList"]  = True
        if arg_pair[1] != "--history":
            denaliVariables["historyQuery"] = arg_pair[1]
        else:
            denaliVariables["historyQuery"] = ''
        ccode = denali_arguments.generateHistoryQuery(denaliVariables)
        if ccode == False:
            pass
        return True

    elif arg0 == '-' or arg0 == "--":
        stdin_list = ''
        for line in sys.stdin:
            stdin_list += line

        # redirect stdin to the console (so that raw_input works if needed)
        #sys.stdin = open("/dev/tty")
        # this fails to find /dev/tty unless the console is accessed.

        if len(denaliVariables["stdinData"]) == 0:
            # default method -- the stdin is assumed to be a list of hosts
            if len(denaliVariables["serverList"]) > 0:
                denaliVariables["serverList"] += readInServerList(denaliVariables, stdin_list, False)
            else:
                denaliVariables["serverList"]  = readInServerList(denaliVariables, stdin_list, False)

            serverList = denaliVariables["serverList"]
            if denaliVariables['aliasReplace'] == True:
                ccode = denali_utility.determineHostAliases(denaliVariables)
            denaliVariables["serverList"] = denali_utility.stripServerName(serverList, denaliVariables)

            # determine if IP addresses were added as part of the server list
            denaliVariables['serverList'] = denali_utility.findServerIPHosts(denaliVariables)
            if denaliVariables['serverList'] == "False":
                return False

            if len(denaliVariables["serverList"]) == 0:
                print "Denali Error:  Host list is empty.  Halting execution."
                return False

            # determine if SKMS search is required (-c/--command)
            noSearchNeededCheck(denaliVariables)

            # batch code -- break it up into max slices for SKMS to consume
            denali_utility.batchDeviceList(denaliVariables)

        else:
            # additional method -- stdin can be representative of any CMDB data field
            originalDataName = "--" + denaliVariables["stdinData"]

            # every piece of data here could potentially be a match in CMDB, so this is one
            # big "OR" list.
            denaliVariables["stdinData"] = ' OR '.join(readInServerList(denaliVariables, stdin_list, False))

            if len(denaliVariables["stdinData"]) == 0:
                print "%s list problem:  The list is empty." % originalDataName
                print "Halting execution."
                return False

            #
            # put this data on the end of the sql modified list(s)
            # it will automatically be manipulated into the sql search parameter set.
            #

            denaliVariables["sqlParameters"].append([originalDataName,denaliVariables["stdinData"]])

    elif arg0 == "-l" or arg0 == "--load":
        if missing_value == True:
            # Oops.  Missing value of file to open.
            # Assume syntax error, print message stating such, and exit.
            print "Denali Syntax Error:  '-l'/'--load' switch specified without a file.  Halting execution."
            return False

        if len(denaliVariables['stdinData']):
            stdin_list = ''

            # additional method -- stdin can be representative of any CMDB data field
            originalDataName = "--" + denaliVariables["stdinData"]

            # every piece of data here could potentially be a match in CMDB, so this is one
            # big "OR" list.
            denaliVariables["stdinData"] = ' OR '.join(readInServerList(denaliVariables, arg_pair[1], True))

            if len(denaliVariables["stdinData"]) == 0:
                print "%s list problem:  The list is empty." % originalDataName
                print "Halting execution."
                return False

            #
            # put this data on the end of the sql modified list(s)
            # it will automatically be manipulated into the sql search parameter set.
            #
            denaliVariables["sqlParameters"].append([originalDataName,denaliVariables["stdinData"]])

        else:
            # branch off to handle file operations for reading server names.
            if len(denaliVariables["serverList"]) > 0:
                denaliVariables["serverList"] += readInServerList(denaliVariables, arg_pair[1], True)
            else:
                denaliVariables["serverList"] = readInServerList(denaliVariables, arg_pair[1], True)

            if denaliVariables["serverList"] == False:
                return False

            if len(denaliVariables["serverList"]) == 0:
                print "Denali Error:  Host list is empty.  Halting execution."
                return False

        # determine if IP addresses were added as part of the server list
        denaliVariables['serverList'] = denali_utility.findServerIPHosts(denaliVariables)
        if denaliVariables['serverList'] == "False":
            return False

        serverList = denaliVariables["serverList"]

        if denaliVariables['aliasReplace'] == True:
            ccode = denali_utility.determineHostAliases(denaliVariables)
        denaliVariables["serverList"] = denali_utility.stripServerName(serverList, denaliVariables)

        # determine if SKMS search is required (-c/--command)
        noSearchNeededCheck(denaliVariables)

        # batch code -- break it up into max slices for SKMS to consume
        denali_utility.batchDeviceList(denaliVariables)

    elif arg0 == "--limit":
        if missing_value == True:
            print "Denali Syntax Error:  '--limit' specified without associated limit count value.  Halting execution."
            return False
        else:
            # treat the arg1 value as a limiting value for what is to be printed
            # MRASEREQ-41219
            if arg_pair[1].isdigit():
                denaliVariables["limitCount"] = int(arg_pair[1])
            else:
                # special case where the request is to limit by a column variable
                if arg_pair[1].find(':') != -1:
                    # Make sure the limit syntax order is correct; if not, fix it
                    #   <integer>:<field_to_limit>
                    limit_pair = arg_pair[1].split(':')
                    if limit_pair[0].isdigit() == True:
                        limit_pair[1] = denali_search.returnAllAliasedNames(denaliVariables, limit_pair[1], single=True)
                        denaliVariables["limitData"].update({'definition':limit_pair[0] + ':' + limit_pair[1]})
                    else:
                        limit_pair[0] = denali_search.returnAllAliasedNames(denaliVariables, limit_pair[0], single=True)
                        denaliVariables["limitData"].update({'definition':limit_pair[1] + ':' + limit_pair[0]})

    elif arg0 == "-h" or arg0 == "--hosts":
        if missing_value == True:
            print "Denali Syntax Error:  '-h'/'--hosts' specified without associated host name(s).  Halting execution."
            return False
        else:
            # If the host list is actually a group list because of an attribute update
            if denaliVariables['attributeUpdate'] == True:
                denaliVariables['serverList'] = denaliVariables['serverList'].split(',')
                return True

            # the host list should be comma separated, no spaces
            if len(denaliVariables["serverList"]) > 0:
                if len(denaliVariables['groupList']) > 0:
                    group_hosts = compileServerRange(arg_pair[1].split(','))
                    # If there is only a single host to add, make sure the comma makes
                    # it into the list (so split(',') can work, otherwise it will show
                    # two hosts back-to-back without a comma and that will be a host not
                    # found)
                    denaliVariables['serverList'] += ',' + ','.join(group_hosts)
                    denaliVariables['serverList']  = denaliVariables['serverList'].split(',')
                else:
                    denaliVariables["serverList"] += compileServerRange(arg_pair[1].split(','))
            else:
                denaliVariables["serverList"] = compileServerRange(arg_pair[1].split(','))

            if denaliVariables["serverList"] == False:
                return False

            if len(denaliVariables["serverList"]) == 0:
                print "Denali Error:  Host list is empty.  Halting execution."
                return False

        # determine if IP addresses were added as part of the server list
        denaliVariables['serverList'] = denali_utility.findServerIPHosts(denaliVariables)
        if denaliVariables['serverList'] == "False":
            return False

        serverList = denaliVariables["serverList"]

        if denaliVariables['aliasReplace'] == True:
            ccode = denali_utility.determineHostAliases(denaliVariables)
        denaliVariables["serverList"] = denali_utility.stripServerName(serverList, denaliVariables)

        # copy the original list
        denaliVariables['serverListOrig'] = list(denaliVariables['serverList'])

        # determine if SKMS search is required (-c/--command)
        noSearchNeededCheck(denaliVariables)

        # batch code -- break it up into max slices for SKMS to consume
        denali_utility.batchDeviceList(denaliVariables)

    elif arg0 == "-g" or arg0 == "--groups":
        if missing_value == True:
            print "Denali Syntax Error:  '-g/--groups' specified without associated group name(s).  Halting execution."
            return False
        else:
            denaliVariables['groupList'] = arg_pair[1].split(',')

            if len(denaliVariables['groupList']) == 0:
                print "Denali Syntax Error:  Group list is empty.  Halting execution."
                return False

            # set the dao to DeviceGroupDao
            denaliVariables['searchCategory'] = 'DeviceGroupDao'

            # get the hosts in each specified group
            ccode = denali_groups.returnGroupList(denaliVariables)

            if len(denaliVariables['serverList']) == 0:
                print "Denali Error:  Host list is empty.  Halting execution."
                return False

            if ccode == False:
                return False

        for (index, parm) in enumerate(denaliVariables["cliParameters"]):
            if parm[0] == "--hosts":
                denaliVariables['cliParameters'][index][1] = denaliVariables['serverList']

    elif arg0 == "--up" or arg0 == "--update" or arg0 == "--updatefile" or arg0 == "--updateattr":
        # update CMDB data records
        if denaliVariables["allowUpdates"] == False:
            print "CMDB updating functionality is not enabled."
            return False

        ccode = denali_update.validateRollbackDirectory(denaliVariables)
        if ccode == False:
            # there's a problem here -- do not proceed with any updates
            return False

        if arg0 == "--updatefile":
            # file with updates for CMDB
            if missing_value == True:
                # Oops.  Missing value of file to open.
                # Assume syntax error, print message stating such, and exit.
                print "Denali Syntax Error:  '--updatefile' switch specified without a file.  Halting execution."
                return False
            else:
                # branch off to validate the file
                denaliVariables["updateMethod"] = "file"
                ccode = denali_update.validateUpdateFile(denaliVariables, arg_pair[1])
                if ccode == False:
                    # Syntax error is likely
                    print "Update file problem (%s)" % arg_pair[1]

                    if denaliVariables["debug"] == False and denaliVariables["updateDebug"] == False:
                        print "Run again with \"--updatedebug\" to see a list of hosts from the update file marked bad."

                    return False

                # use the file to do updates
                ccode = denali_update.updateCMDBWithFile(denaliVariables, arg_pair[1])
                if ccode == False:
                    # update(s) failed
                    return False

        else:
            # massage the passed in parameters; put the results in denaliVariables["updateParameters"]
            refresh = True
            if arg0 == "--updateattr":
                # set state variables for an attribute query and update
                denaliVariables["updateMethod"] = "attribute"
            else:
                denaliVariables["updateMethod"] = "console"

            if denaliVariables['attributeUpdate'] == False:
                # This flag identifies DeviceGroup updates, not host updates -- which is a little confusing here
                # Expand the host list -- all servers known (not an arbitrary list after this call)
                ccode = denali_utility.expandServerList(denaliVariables)
                if ccode == False:
                    # failure to "expand" the host list
                    return False

            if len(denaliVariables["serverList"]) == 0:
                # all submitted hosts do not exist -- nothing to do here
                print "No devices found for the query submitted (1)."
                return False

            # fill in the denaliVariables["updateParameters"] location with the update parameter(s)
            ccode = denali_update.organizeUpdateParameters(denaliVariables, "all", arg_pair[1])
            if ccode == False:
                # Syntax error is likely; i.e., brackets don't match, or something like that
                return False

            # Check and see if multiple hosts are submitted with an update to the hostname
            # if so, fail the update and print a message stating the reason.
            hostLength = len(denaliVariables["serverList"])
            for parameter in denaliVariables["updateParameters"]["all"]:
                if parameter.startswith("name=") and parameter.find('<hostname>') == -1 and hostLength > 1:
                    print "Denali Update Syntax Error:  Multiple hosts (%d) were requested to update their hostname to the same value.  Denali exiting." % hostLength
                    print "                             Use --update=name=<hostname>-[what you want] for this request to update multiple hosts."
                    return False

            if denaliVariables['autoConfirm'] == False:
                while (refresh == True):
                    refresh = False
                    ccode = denali_update.updateListOfServers(denaliVariables)
                    if ccode == False:
                        if denaliVariables["updateDebug"] == True:
                            api = denaliVariables["api"]
                            print "\nERROR:"
                            print "   STATUS : " + api.get_response_status()
                            print "   TYPE   : " + str(api.get_error_type())
                            print "   MESSAGE: " + api.get_error_message()
                            print
                        return False

                    elif ccode == "refresh":
                        refresh = True
                        denaliVariables["updatePreview"] = True
                    elif ccode == "quit":
                        return True
            else:
                ccode = denali_update.updateListOfServers(denaliVariables)
                if ccode == False:
                    if denaliVariables["updateDebug"] == True:
                        api = denaliVariables["api"]
                        print "\nERROR:"
                        print "   STATUS : " + api.get_response_status()
                        print "   TYPE   : " + str(api.get_error_type())
                        print "   MESSAGE: " + api.get_error_message()
                        print
                    return False
                return True

    elif arg0 == "--ag" or arg0 == "--addgroup" or arg0 == "--dg" or arg0 == "--delgroup":
        ccode = denali_groups.modifyHostGroupList(denaliVariables, arg_pair[1], arg0[2:])
        return ccode

    elif arg0 == "--newgroup":
        ccode = denali_groups.addNewHostGroup(denaliVariables, arg_pair[1])
        return ccode

    elif arg0 == "--addhistory":
        ccode = denali_history.addHistoryToHostList(denaliVariables, arg_pair[1])
        return ccode

    elif arg0 == "--grphistory":
        ccode = denali_history.addHistoryToGroup(denaliVariables, arg_pair[1])
        return ccode

    elif arg0 == "--mon":
        if denaliVariables['batchDevices'] == True:
            # If 'batch mode' is on, we've finished processing a number of device batches
            # and now those groups of hosts need to be combined in one for monitoring
            # to work with.
            ccode = denali_utility.combineBatchedDeviceNames(denaliVariables)
        ccode = denali_monitoring.monitoringDataEntryPoint(denaliVariables, arg_pair[1])
        if ccode == False:
            return False
        return True

    elif arg0 == "--polaris":
        import denali_polaris
        # if there is no argument (i.e., 'Waiting', clear it out for handling by polaris)
        if arg_pair[1] == "Waiting":
            arg_pair[1] = ''
        ccode = denali_polaris.main(denaliVariables, arg_pair[1])
        if ccode == False:
            return False
        return True

    elif arg0 == "--getsecrets":
        denaliVariables["getSecrets"] = True
        denaliVariables["method"]     = "getSecrets"

        # Assign the secret store name to search in
        if missing_value == True:
            denaliVariables["getSecretsStore"] = "Analytics"
        else:
            denaliVariables["getSecretsStore"] = arg_pair[1]

        # narrow the list to one server per device service
        ccode = denali_utility.narrowHostListByDeviceService(denaliVariables)
        if ccode == False:
            # problem narrowing in on the host list
            return False

        if denaliVariables["debug"] == True:
            print "Narrowed hostname list = %s" % denaliVariables["serverList"]

        return True

    elif arg0 == "--dc":
        # data center location
        if missing_value == True:
            denaliVariables["dataCenter"] = ''
        else:
            denaliVariables["dataCenter"] = denali_arguments.validateDataCenter(arg_pair[1])

    elif arg0 == "--obj" or arg0 == "--object" or arg0 == "--dao":
        if missing_value == True:
            # Missing the name value -- assume DeviceDao
            denaliVariables["searchCategory"] = "DeviceDao"
        else:
            denaliVariables["searchCategory"] = arg_pair[1]

    elif arg0.startswith('--dao_'):
        if missing_value == True:
            # Missing the search parameter -- bail out
            print "Denali Syntax Error:  %s parameter is missing its argument" % arg0
            print "   Example:  --dao_service=\"Analytics - Reporting*\""
            return False
        else:
            dao = arg0.split('_')[1]
            # assign dao specific items
            # comma necessary if >1 field columns requested

            search_field_dict = {}

            # Hard-coded defaults for the --dao_<category>.  These only take effect if
            # no other parameters of the same name are specified, otherwise, those would
            # override anything here.

            # --dao_service
            if dao == 'service':
                denaliVariables['searchCategory'] = 'DeviceServiceDao'
                default_field = 'full_name'
                search_field  = '--full_name'
                sort_field    = 'full_name'

            if dao == 'role':
                denaliVariables['searchCategory'] = 'DeviceRoleDao'
                default_field = 'full_name'
                search_field  = '--full_name'
                sort_field    = 'full_name'

            # --dao_state
            elif dao == 'state':
                denaliVariables['searchCategory'] = 'DeviceStateDao'
                default_field = 'full_name'
                search_field  = '--full_name'
                sort_field    = 'full_name'

            # --dao_cmr
            elif dao == 'cmr':
                denaliVariables['searchCategory'] = 'CmrDao'
                default_field     = 'id,start_date,duration,priority,risk,impact,executor,summary'
                search_field      = '--start_date'
                search_field_dict = {'--cmr_service'  : 'Adobe Marketing Cloud - Adobe Analytics* OR Adobe Mobile Services - Mobile Analytics*',
                                     '--id'           : '*'}
                if arg_pair[1].strip().startswith('-'):
                    # Looking in the past -- show the CMR state for this query
                    default_field = 'id,start_date,duration,priority,risk,impact,cmr_state,executor,summary'
                else:
                    # 2 = pending, 3 = on-going, 5 = completed, 6 = canceled
                    search_field_dict.update({'--cmr_state_id' : '2 OR 3'})

                search_field_keys = ['--cmr_service', '--id']
                sort_field        = 'start_date'

            # --dao_group
            elif dao == 'group':
                denaliVariables['searchCategory'] = 'DeviceGroupDao'
                default_field     = 'name'
                search_field      = '--name'
                sort_field        = 'name'

            # --dao_environment / --dao_env
            elif dao.startswith('env'):
                denaliVariables['searchCategory'] = 'EnvironmentDao'
                default_field     = 'full_name'
                search_field      = '--full_name'
                sort_field        = 'full_name'

            # put the items in the cliParameters and sqlParameters as needed
            sort_command_found   = False
            fields_command_index = -1       # default is 1 back from the end
            for (index, parameter) in enumerate(denaliVariables['cliParameters']):
                if parameter[0] == '--fields':
                    fields_command_index = index
                    if parameter[1] == 'Empty':
                        denaliVariables['cliParameters'][index][1] = default_field
                if parameter[0] == '--sort':
                    sort_command_found = True

            # insert the 'sort' command before 'fields' (or it won't work)
            if sort_command_found == False:
                denaliVariables['cliParameters'].insert(fields_command_index, ['--sort', sort_field])

            # fill out the sql parameter search criteria
            if len(denaliVariables['sqlParameters']):
                # add main sql searching criteria
                for parameter in denaliVariables['sqlParameters']:
                    if parameter[0] == search_field:
                        break
                else:
                    denaliVariables['sqlParameters'].append([search_field, arg_pair[1]])
                # add secondary searching criteria -- if specified
                if len(search_field_dict):
                    for sf_key in search_field_keys:
                        for parameter in denaliVariables['sqlParameters']:
                            if parameter[0] == sf_key:
                                break
                        else:
                            denaliVariables['sqlParameters'].append([sf_key, search_field_dict[sf_key]])
            else:
                denaliVariables['sqlParameters'].append([search_field, arg_pair[1]])
                if len(search_field_dict):
                    for sf_key in search_field_dict:
                        denaliVariables['sqlParameters'].append([sf_key, search_field_dict[sf_key]])

        return True

    elif arg0 == "-s" or arg0 == "--search":
        if missing_value == True:
            # No search criteria specified
            searchArgument = ''
        else:
            searchArgument = arg_pair[1]

    elif arg0 == "-f" or arg0 == "--fields":
        # determine if a query (for hosts) is necessary or not based upon
        # denaliVariables["noSearchNeeded"].
        if denaliVariables["noSearchNeeded"] == True:
            return True

        if len(denaliVariables['serverList']) and denaliVariables["serverList"][0] == '*':
            if denaliVariables["monitoring"] == True and len(denaliVariables['sqlParameters']) == 0:
                # Do not pass along a wildcard search for every host in the environment to monitoring.
                # This will just error out when data centers aren't found for SSL certs; however, it will
                # take 10 seconds or so to collect the host/entity list, during which time the user will
                # look at their request, and begin to worry about potentially breaking something.
                # Just exit out here with this error and it should solve that issue.
                print "Denali Error:  Wildcard host/entity search of ALL hosts in the environment initiated for monitoring."
                print "               The search needs to be narrowed before it will be passed along.  Exiting."
                return False

        if missing_value == True or arg_pair[1] == "Empty":
            if denaliVariables["getSecrets"] == True:
                # Default fields associated with secret store display
                arg_pair[1] = "SECRET"
            else:
                # Field not specified, use the default field assignment
                arg_pair[1] = "DEFAULT"

        else:
            # Check if the user entered '-f/--fields' without any data
            # If so, clear out the Empty in the search criteria
            if arg_pair[1] == "Empty":
                arg_pair[1] = "DEFAULT"
            else:
                if denali_arguments.checkForAttributeField(arg_pair[1]) == True:
                    ccode = denali_arguments.getAttributeFields(arg_pair[1], denaliVariables)
                    denaliVariables["attributes"] = True

                denaliVariables["fields"] = arg_pair[1]

        # if the host list isn't a single wildcard and summary is enabled, or if attributes
        # are the requested search parameter, or "--validate" was submitted, then validate the device list
        if ((denaliVariables["summary"] == True and denaliVariables["searchCategory"] == "DeviceDao") or
            (denaliVariables["validateData"] == True)):

            if len(denaliVariables["serverList"]) == 1 and denaliVariables["serverList"][0] == '*':
                # disabling validation on every host across the enterprise  ==>  --hosts='*'
                denaliVariables["validateData"] == False
            else:
                # save off the limit (if not zero) -- to prevent performance issue
                saveLimit = denaliVariables["limitCount"]
                denaliVariables["limitCount"] = 0

                ccode = denali_utility.validateDeviceList(denaliVariables, arg_pair[1])

                # restore the limit
                denaliVariables["limitCount"] = saveLimit

                # There shouldn't be a need to exit out here.  If there are non-existant
                # hosts, just show them at the end of the query as requested.

        # check for substitution field name (and replace it/them with the correct
        # column name for the field variable -- this is the ALIAS(ES) name replacement function)
        denaliVariables["fields"] = denali_arguments.fieldSubstitutionCheck(denaliVariables, arg_pair[1])

        # if a custom module was asked to run, do not run a query here (the check is for 'False')
        # instead, pass control to the custom module for further instructions
        if denaliVariables["external"] == False:

            numDevices = len(denaliVariables["serverList"])

            if numDevices == 0 and denaliVariables["searchCategory"] == "DeviceDao":
                print "No devices/records found for the query submitted (2)."
                cleanUp(denaliVariables)
                exit(1)

            if denaliVariables['batchDevices'] == True:
                batch_key_list = denaliVariables['batchDeviceList'].keys()
                batch_key_list.sort()
                last_batch_key = batch_key_list[-1]
                for batch_key in batch_key_list:
                    # signal to the count method to output data -- search won't use this
                    if batch_key == last_batch_key:
                        denaliVariables['batchDeviceList'].update({'final_key':None})
                    denaliVariables['serverList'] = denaliVariables['batchDeviceList'][batch_key]

                    # methodData is saved or the 'count' method doesn't work
                    methodData = denaliVariables["methodData"]
                    ccode = denali_search.constructSimpleQuery(denaliVariables)
                    denaliVariables["methodData"] = methodData
                    if ccode == False:
                        return False
            else:
                if denali_search.constructSimpleQuery(denaliVariables) == False:
                    return False

    elif arg0 == "-o" or arg0 == "--out":
        if missing_value == True:
            # ignore the output -- send to stdout as usual
            denaliVariables["outputTarget"] = [denali_types.OutputTarget(type='txt_screen', filename='', append=False)]
        else:
            # determine the type of output file wanted (txt, csv, json)
            denaliVariables["outputTarget"] = outputTargetDetermination(denaliVariables, arg_pair[1])

    elif arg0 == "--power":
        if missing_value == True:
            return False

        rCode = denali_search.searchPowerNameInformation(denaliVariables, arg_pair[1])
        return rCode

    elif arg0 == "--powerid":
        if missing_value == True:
            return False

        rCode = denali_search.searchPowerIDInformation(denaliVariables, arg_pair[1])
        return rCode

    elif arg0 == "--rack":
        if missing_value == True:
            return False

        rCode = denali_search.searchRackNameInformation(denaliVariables, arg_pair[1])
        return rCode

    elif arg0 == "--rackid":
        if missing_value == True:
            return False

        rCode = denali_search.searchRackIDInformation(denaliVariables, arg_pair[1])
        return rCode

    elif arg0 == "--switch":
        if missing_value == True:
            return False

        denaliVariables["sortColumnsFirst"] = True
        rCode = denali_search.searchSwitchNameInformation(denaliVariables, arg_pair[1])

    elif arg0 == "--switchid":
        if missing_value == True:
            return False

        denaliVariables["sortColumnsFirst"] = True
        rCode = denali_search.searchSwitchIDInformation(denaliVariables, arg_pair[1])

    elif arg0 == "--sql":
        sql_query = arg_pair[1]
        if denali_search.constructSQLQuery(denaliVariables, sql_query, True) == False:
            return False

    elif arg0 == "--noheaders":
        # whether or not to show the column headers when printing to a file or screen
        if (arg_pair[1].lower() == "on" or arg_pair[1].lower() == "show" or arg_pair[1].lower() == "true"):
            denaliVariables["showHeaders"] = True
        else:
            denaliVariables["showHeaders"] = False

    elif arg0 == "--headers":
        if arg_pair[1].lower() == "on" or arg_pair[1].lower() == "show" or arg_pair[1].lower() == "yes":
            denaliVariables["showHeaders"] = True
        elif arg_pair[1].lower() == "off" or arg_pair[1].lower() == "no" or arg_pair[1].lower() == "false":
            denaliVariables["showHeaders"] = False
        else:
            denaliVariables["showHeaders"] = True

    elif arg0 == "--mheaders":
        denaliVariables["multiHostHeader"] = True

    elif arg0 == "--sort":
        if missing_value == True:
            # do nothing, sql will sort on the first column by default
            pass
        else:
            # set the sort flag(s) appropriately -- run it through like a normal
            # sort on the name alone
            if arg_pair[1] == 'dc':
                denaliVariables['data_center_sort'] = True
                arg_pair[1] = 'name'

            # load the sort statement into the variable store
            denaliVariables["sqlSort"] = arg_pair[1]

            # replace any aliased name(s) in the sort statement with the proper cmdb name(s)
            denaliVariables["sqlSort"] = denali_search.replaceAliasedNames(denaliVariables, "sqlSort")

            # create the SQL statement from the sort data passed in
            denaliVariables["sqlSort"] = denali_utility.createSortSQLStatement(denaliVariables["sqlSort"])

    elif arg0 == "-c" or arg0 == "--command":
        #if denaliVariables["noSearchNeeded"] == True:
        ccode = denali_commands.processArguments(denaliVariables, arg_pair[1], denaliVariables['jsonResponseDict'])
        if ccode == False:
            return False

    elif arg0 == "-e" or arg0 == "--ext" or arg0 == "-m":
        if arg_pair[1] != '':

            # import module dynamically
            moduleCall = arg_pair[1]
            functLocation = moduleCall.find('.')
            parmLocation  = moduleCall.find(':')

            if parmLocation != -1:
                parameters = moduleCall[(parmLocation + 1):]
                moduleCall = moduleCall[:parmLocation]
                parameters = parameters.split(',')
            else:
                parameters = ''

            if functLocation != -1:
                function   = moduleCall[(functLocation +  1):]
                moduleCall = moduleCall[:functLocation]
            else:
                # if no specific function call is defined, call "main"
                function = "main"

            if denaliVariables["debug"] == True:
                print
                print "Module Information"
                print "Module name:  %s" % moduleCall
                print "Function   :  %s" % function
                print "Parameters :  %s" % parameters

            module = moduleCall

            # import the module
            try:
                mod = __import__(module, fromlist=[''])
            except ImportError as error:
                print "Error importing module \"%s\"" % module
                print "Error returned:  %s" % error
                return False

            # save the module name
            denaliVariables["externalModule"] = module

            # call the module.function
            try:
                functionCall = getattr(mod, str(function))
            except AttributeError:
                print "Error:"
                print "The function definition of \"%s\" was not found in the \"%s\" module." % (function, module)
                return False

            ccode = functionCall(denaliVariables, *parameters)
            if ccode == False:
                return False

        else:
            # no module name given
            print "Required module name for --explain not provided."
            print "Denali code execution stopped."
            return False

    # return 'True' (success) for everything that doesn't return 'False' in its segment
    return True



##############################################################################
#
# deviceLimitError(numDevices)
#

def deviceLimitError(numDevices):
    print
    print "Error: Device Limit Exceeded"
    print "%s devices were submitted to Denali.  The SKMS web api can only handle" % numDevices
    print "a little over 950 devices per query (entered in the WHERE statement). "
    print
    print "Problem:"
    print "More devices than this causes a delay in the SKMS SQL parsing library,"
    print "which leads to a timeout (default 25 seconds) from SKMS.  This results"
    print "in a failed query."
    print
    print "Resolution:"
    print "Reduce the number of devices submitted and re-run the query."
    print



##############################################################################
#
# separateCMDBandSIS(denaliVariables)
#

def separateCMDBandSIS(denaliVariables):

    tempSQL = []
    tempCLI = []

    # remove the SIS sql parameters from the CMDB variable
    for parameter in denaliVariables["sqlParameters"]:
        if parameter[0].startswith("--sis_"):
            denaliVariables["sis_SQLParameters"].append(parameter)
        else:
            tempSQL.append(parameter)

    # copy the completed CMDB list back
    denaliVariables["sqlParameters"] = tempSQL[:]

    # remove the SIS fields from the CMDB variable
    for (index, parameter) in enumerate(denaliVariables["cliParameters"]):
        if parameter[0] == "--fields" or parameter[0] == "-f":
            tempFields = parameter[1].split(',')

            # store the original field parameter order
            if "fields" not in denaliVariables["sis_OriginalData"]:
                denaliVariables["sis_OriginalData"].update({"fields":tempFields[:]})

            for field in tempFields:
                if field.startswith("sis_"):
                    if len(denaliVariables["sis_Fields"]) == 0:
                        denaliVariables["sis_Fields"] = field
                    else:
                        denaliVariables["sis_Fields"] += ',' + field
                else:
                    tempCLI.append(field)

    # copy the completed CMDB field List back (and convert it to a string)
    tempCLI = ','.join(tempCLI)
    denaliVariables["cliParameters"][index] = ["--fields", tempCLI]

    return True



##############################################################################
#
# cleanUp(denaliVariables)
#

def cleanUp(denaliVariables):

    # get rid of any temp files created/used during the denali run
    for tmpFile in denaliVariables["tmpFilesCreated"]:
        # does the file exist?  if so, try and delete it
        if os.path.isfile(tmpFile) == True:
            if denaliVariables["debug"] == True:
                print "\nRemoving temp file: %s" % tmpFile
            try:
                os.remove(tmpFile)
            except:
                if denaliVariables["debug"] == True:
                    print "   FAILURE"
            else:
                if denaliVariables["debug"] == True:
                    print "   SUCCESS"

    denaliVariables['time']['denali_stop'].append(time.time())

    if denaliVariables['time_display'] == True:
        denali_utility.printTimingInformation(denaliVariables)



##############################################################################
#
# signal_handler(signal,frame)
#

def signal_handler(signal, frame):

    from denali_variables import denaliVariables

    print
    print "Control-C pressed.  Denali exited."
    print

    if denaliVariables['pdshExecuting'] == True:
        # Print out any log file name(s) so that the user can at least have
        # a summary of what happened up to this point in time.
        if denaliVariables['pdsh_log_file'].find('.txt') != -1:
            print "Partial Data PDSH log file: %s" % denaliVariables['pdsh_log_file']

    # get rid of any temp files created/used during the denali run
    for tmpFile in denaliVariables["tmpFilesCreated"]:
        # does the file exist?  if so, try and delete it
        if os.path.isfile(tmpFile) == True:
            if denaliVariables["debug"] == True:
                print "\nRemoving temp file: %s" % tmpFile
            try:
                os.remove(tmpFile)
            except:
                if denaliVariables["debug"] == True:
                    print "   FAILURE"
            else:
                if denaliVariables["debug"] == True:
                    print "   SUCCESS"
    exit(0)



##############################################################################
#
# checkForHostEntry(denaliVariables)
#

def checkForHostEntry(denaliVariables):

    for argument in denaliVariables["cliParameters"]:
        if (
            argument[0] == "-"  or
            argument[0] == "--" or
            argument[0].startswith("-l") or "--load"  in argument[0] or
            argument[0].startswith("-h") or "--host"  in argument[0]
           ):
            # there is a list of hosts specified
            return True
    else:
        # check the dao
        if denaliVariables["searchCategory"] == "DeviceDao":
            denaliVariables["cliParameters"].append(["--hosts", '*'])
            return False



##############################################################################
#
# noSearchNeededCheck(denaliVariables)
#
#   Skip login if the host list is complete and the cli requests either a
#   command execution (-c/--command) or monitoring query (--mon)
#
#   set denaliVariables['noSearchNeeded'] = True
#       skip SKMS search, no [SKMS] search is needed
#   set denaliVariables['noSearchNeeded'] = False
#       do the SKMS search
#

def noSearchNeededCheck(denaliVariables):

    # This 'return' is back (again) because of the monitoring requirement to
    # add a history update for every host modified (checks/ack/downtime, etc.).
    # To accomplish that, an SKMS login is required; meaning, a search is needed
    # for any hosts submitted.  Until this can be worked around, it will stay
    # here for the time being.

    # MRASEREQ-41295
    # Commented this out -- monitoring now checks for specific commands and then
    # calls the authentication function to make sure the user can update SKMS
    # when required.

    #return

    check_list = [ '-c', '--command', '--mon' ]
    return_list = [ '--combine' ]

    # MRASETEAM-40445 -- disable this feature if there are any sql parameters
    if len(denaliVariables['sqlParameters']) > 0:
        return

    # determine if login/skms search is required (if -c is given with host list)
    for parameters in denaliVariables["cliParameters"]:
        # any parameter in this list requires SKMS access
        if parameters[0] in return_list:
            return
        # parameters in this list or ok, with certain checks
        if parameters[0] in check_list:
            if parameters[1].find('info') != -1:
                # -c info requires authentication (monitoring, skms access, etc.)
                # So independent of whether there is a complete hostlist or not,
                # make sure authentication/SKMS access is mandated here.
                return
            ccode = checkForCompleteHostList(denaliVariables)
            if ccode == True:
                denaliVariables["noSearchNeeded"] = True

        # check to see if a data center/location was entered
        if parameters[0] == "--dc":
            if parameters[1].upper() in denali_location.dc_location:
                denaliVariables["noSearchNeeded"] = True



##############################################################################
#
# checkForCompleteHostList(denaliVariables)
#
#   This function goes through the list of hosts given to denali and ensures
#   that there are no wildcards (or that the list is empty).  The reason for
#   this is that if the "-c" is used, there is no need to search SKMS for a
#   list of hosts if one is given to it -- just use it as is.  So this function
#   will ensure that the list is complete and usable before giving the 'ok'
#   to skip the search.  If an empty list is given, or a wildcard search is
#   needed, then a search will be required and that list will be handed over
#   to the '-c' command processing.
#

def checkForCompleteHostList(denaliVariables):

    hostlist   = []
    host_parms = [ '--hosts', '--host', '-hosts', '-host', '-h', '--h'        ]
    load_parms = [ '--loads', '--load', '-loads', '-load', '-l', '--l',  '--' ]

    # if pdsh separate code is running, return False to initiate a query
    if denaliVariables['pdshSeparate'] != False:
        return False

    # if the verify code is requested, always initiate a query
    if denaliVariables['devServiceVerify'] == True:
        return False

    # get the hostlist
    for parameters in denaliVariables["cliParameters"]:
        if parameters[0].startswith('--limit'):
            return False
        if parameters[0] in host_parms:
            hostlist = parameters[1]
        if parameters[0] in load_parms:
            hostlist = denaliVariables["serverList"]

    # check for an empty list
    if len(hostlist) == 0:
        return False

    # check for a wildcard character in each hostname
        # '?'  = single character wildcard
        # '*'  = multi-character wildcard
        # '%'  = multi-character wildcard for SQL
    for host in hostlist:
        if (host.count('?') > 0 or
            host.count('*') > 0 or
            host.count('%') > 0):

            if ((host.count('?') > 0 or host.count('*') > 0) and
               (len(denaliVariables['dataCenter']) > 0 and denaliVariables['monitoring'] == True)):
                return True
            return False

    return True



##############################################################################
#
# prepopulateVariables(denaliVariables, argv)
#
#   There are some variable definitions that need to be populated before the
#   program starts going through the main loop.  Included in this function
#   are the variables that fit this criteria.
#
#   The 'argument' loop variable has the entire argument, equal-sign and all
#   if included.  Use 'startswith()' to catch these cases.
#

def prepopulateVariables(denaliVariables, argv):

    group_query = False

    # store the location of the denali executable for later use
    denaliVariables["denaliLocation"] = argv[0]

    for (index, argument) in enumerate(argv):
        if argument == "--slack":
            # Determine if slack called denali.  If so, toggle the slack data switch
            denaliVariables["slack"] = True

        elif argument == '--mon':
            # Set the monitoring switch if submitted
            denaliVariables["monitoring"] = True

        elif argument.startswith("--profile"):
            # If a profile was requested -- store the name; handle the equal sign
            if argument.find('=') != -1:
                denaliVariables['profile'] = argument.split('=')[1].strip()
            else:
                if len(argv) >= (index + 1):
                    denaliVariables['profile'] = argv[index + 1].strip()

        elif argument == "--noprofile":
            # Make sure no profiles are added to the query
            denaliVariables['noProfile'] = True

        elif ((argument.startswith('--pdsh_separator') or
               argument.startswith('--pdsh_separate')  or
               argument.startswith('--ps'))            and denaliVariables['hostCommands']['active'] == False):
            # only set the separator value if --host_commands isn't being used (that would mess up the segments)
            if argument.find('=') != -1:
                denaliVariables['pdshSeparate'] = {'separator':argument.split('=')[1].strip()}
            else:
                if len(argv) >= (index + 1):
                    denaliVariables['pdshSeparate'] = {'separator':argv[index + 1].strip()}

        elif (argument.startswith("-e=") or argument.startswith("--ext=") or
              argument.startswith("-e")  or argument.startswith("--ext") or
              argument.startswith("-m")  or argument.startswith("-m=")):
            # Determine if a custom module was requested
            denaliVariables["external"] = True

        elif argument.startswith("--dao"):
            # dao will be needed if a profile is used
            if argument.find('=') != -1:
                denaliVariables['searchCategory'] = argument.split('=')[1].strip()
            else:
                if len(argv) >= (index + 1):
                    denaliVariables['searchCategory'] = argv[index + 1].strip()

        elif argument == "--nocolors":
            denaliVariables['nocolors'] = True

        elif argument == "--host_commands" or argument == "--hc":
            denaliVariables['hostCommands']['active'] = True
            denaliVariables['pdshSeparate'] = {'separator':'_single_'}

        elif argument == "-g" or argument.startswith("--groups"):
            group_query = True

        elif argument.startswith('--updateattr'):
            # flag to let the code know an attribute update is requested
            denaliVariables['attributeUpdate'] = True

        elif argument.startswith('--config'):
            # flag to let the code know a user config file was specified
            denaliVariables['userConfig'] = True

        elif argument.startswith('--pol'):
            # flag to let the code know that polaris will be run,
            # check for proper sql definitions before assigning
            denaliVariables['polarisExecution'] = True

        elif argument == "--verify" or argument == "-v":
            # flag to let the code know that a verify operation will happen
            denaliVariables['devServiceVerify'] = True

    # Make sure this flag is only set when groups are specified, otherwise, any normal host attribute
    # update will fail miserably
    if group_query == False:
        denaliVariables['attributeUpdate'] = False



##############################################################################
#
# determineStreamSettings(denaliVariables)
#

def determineStreamSettings(denaliVariables):

    # Code lifted from getpass.py
    #
    # It determines if tty is readable/writeable and sets the input/output
    # streams according to the response.

    try:
        # Always try reading and writing directly on the tty first.
        fd  = os.open('/dev/tty', os.O_RDWR|os.O_NOCTTY)
        tty = os.fdopen(fd, 'w+', 1)
        denaliVariables['stream'].update({'input' :tty})
        denaliVariables['stream'].update({'output':tty})
    except EnvironmentError, e:
        denaliVariables['stream'].update({'input' :sys.stdin})
        denaliVariables['stream'].update({'output':sys.stderr})

    return



##############################################################################
#
# programDisplay(denaliVariables, program_name, message, path_message='')
#

def programDisplay(denaliVariables, program_name, message, path_message=''):

    display_width = 22
    avail_width   = 14
    CYAN          = colors.fg.cyan
    WHITE         = colors.bold + colors.fg.white
    GREEN         = colors.fg.lightgreen
    RED           = colors.bold + colors.fg.lightred
    RESET         = colors.reset
    SUCCESS       = False

    # success_messages are printed in GREEN (if colorized)
    # anything that isn't a success message, is assumed to
    # be a type of failure, and is printed in RED.
    success_messages =  [
                            'Available', 'Silence',   'Logged In',
                            'AdobeProd', 'AdobeCorp', 'Non-Adobe'
                        ]

    if message in success_messages:
        SUCCESS = True

    if len(message) < avail_width:
        difference = (avail_width - len(message)) / 2
        message = (" " * difference) + message + (" " * difference)

    if denaliVariables['nocolors'] == True:
        #if available == 'Available' or available == ' Silence ':
        if SUCCESS == True:
            sys.stdout.write("  %s[%s]" % (program_name.ljust(display_width), message))
        else:
            sys.stdout.write("  %s[%s]" % (program_name.ljust(display_width), message))

    else:
        #if available == 'Available' or available == ' Silence ':
        if SUCCESS == True:
            sys.stdout.write("  " + CYAN + "%s" % program_name.ljust(display_width))
            sys.stdout.write(WHITE + "[" + RESET + GREEN + "%s" % message + WHITE + "]" + RESET)
        else:
            sys.stdout.write("  " + CYAN + "%s" % program_name.ljust(display_width))
            sys.stdout.write(WHITE + "[" + RESET + RED + "%s" % message + WHITE + "]" + RESET)

    if len(path_message):
        sys.stdout.write("  %s\n" % path_message)
    else:
        print

    sys.stdout.flush()

    return



##############################################################################
#
# pingTest(denaliVariables, destination, timeout_value)
#

def pingTest(denaliVariables, destination, timeout_value):

    startTime = time.time()
    result = subprocess.Popen(["ping", "-c", "1", "-n", "-W", timeout_value, destination], stdout=subprocess.PIPE, stderr=subprocess.STDOUT).wait()
    timeDiff  = str(time.time() - startTime)[:6]

    return result, timeDiff



##############################################################################
#
# authAvailability(denaliVariables)
#

def authAvailability(denaliVariables):

    curl_errors = {
                    '3'  : 'URL malformed. The syntax was not correct',
                    '6'  : 'Couldn\'t resolve host. The given remote host was not resolved.',
                    '7'  : 'Failed to connect to host.',
                    '22' : 'HTTP page not retrieved. The requested url was not found or returned another error with the HTTP error code being 400 or above.',
                    '27' : 'Out of memory. A memory allocation request failed.',
                    '28' : 'Operation timeout. The specified time-out period was reached according to the conditions.',
                    '35' : 'SSL connect eerror. The SSL handshaking failed.',
                    '47' : 'Too many redirects. When following redirects, curl hit the maximum amount.',
                    '52' : 'The server didn\'t reply anything, which here is considered an error.',
                    '55' : 'Failed sending network data.',
                    '56' : 'Failure in receiving network data.',
                    '78' : 'The resource referenced in the URL does not exist.',
                    '89' : 'No connection available, the session will be queued.',
                  }

    TIMEOUT   = "2"
    MON_API   = False

    print "Authentication/availability:"

    #
    # PING the SKMS api endpoint
    #
    result, timeDiff = pingTest(denaliVariables, denaliVariables['apiURL'], TIMEOUT)
    if result == 0:
        #result = " (%ss)" % timeDiff
        #programDisplay(denaliVariables, 'SKMS availability', 'Available', 'Location : %s | ping response: %ss' % (denaliVariables['apiURL'], timeDiff))
        programDisplay(denaliVariables, 'SKMS availability', 'Available')
    else:
        programDisplay(denaliVariables, 'SKMS availability', 'Not Available', 'Location : %s' % denaliVariables['apiURL'])

    #
    # Test SKMS user authentication
    #
    if result == 0:
        # SKMS endpoint responded -- test authentication
        denaliVariables['testAuth'] = True
        denaliVariables['version']  = "True"
        ccode = denali_authenticate.authenticateAgainstSKMS(denaliVariables, "username")
        if ccode:
            programDisplay(denaliVariables, 'SKMS authentication', 'Logged In')
        else:
            programDisplay(denaliVariables, 'SKMS authentication', 'Auth Failed', 'AdobeNET username/password login required')

    #
    # ping the monitoring end-point first
    #
    prod_destination = "monapi.or1.goc.adobe.net"
    prod_result, prod_timeDiff = pingTest(denaliVariables, prod_destination, '1')
    if prod_result == 0:
        # successful ping response, now curl it
        #
        # CURL the monitoring API endpoint
        #
        destination = "https://monapi.or1.goc.adobe.net/v2/"
        parms = ['curl', '-L', '-I', '--connect-timeout', TIMEOUT, destination]
        startTime = time.time()
        proc  = subprocess.Popen(parms, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, shell=False)
        proc.wait()
        timeDiff  = str(time.time() - startTime)[:6]
        rcode = proc.returncode

        # check the curl return code, and print an error message if needed
        if int(rcode) != 0:
            if str(rcode) in curl_errors:
                curl_check_error = """Location : %s
                                                        Curl Error: [%i] %s""" % (destination, rcode, curl_errors[str(rcode)])
            else:
                curl_check_error = """Location : %s
                                                        Curl Error: [%i] see \"man curl\" for further information""" % (destination, rcode)

            programDisplay(denaliVariables, 'MonAPI availability', 'Not Available', curl_check_error)
        else:
            # check if the site successfully communicated, but if the web page is wrong or doesn't respond
            header_return = proc.stdout.readlines()[0]
            if header_return.find('200 OK') == -1:
                # problem contacting REST interface
                programDisplay(denaliVariables, 'MonAPI availability', 'Not Available', 'Location : %s | %s' % (destination, header_return))
            else:
                MON_API = True
                programDisplay(denaliVariables, 'MonAPI availability', 'Available')

        #
        # Test MonAPI user authentication
        #
        # The end-point responded successfully to a ping and curl request ... see if the user is authenticated
        # Don't run this code if an older version of python-requests is loaded
        #
        if MON_API == True and urllib_err1 == True:
            import MonApi as monapi

            # data needed to do an authentication check with MonApi
            username  = None
            password  = None
            domain    = 'monapi.or1.goc.adobe.net'
            uri       = '/v2'
            use_ssl   = True
            url       = "/bulk/entity/svc/query"
            payload   = {'service_list': ['*'], 'entities': ['eng1.or1']}
            method    = "post"
            sr_filter = {}

            if denaliVariables['dm_username'] != '':
                username = denaliVariables['dm_username']
            if denaliVariables['dm_password'] != '':
                password = denaliVariables['dm_password']

            mon_api = monapi.MonApiClient(username, password, domain, uri, use_ssl)
            try:
                response = mon_api.send_request(url, payload, method, sr_filter)
            except requests.exceptions.HTTPError as e:
                programDisplay(denaliVariables, 'MonAPI authentication', 'Auth Failed', 'AdobeNET username/password login required')
            else:
                programDisplay(denaliVariables, 'MonAPI authentication', 'Logged In')
    else:
        # can't ping the monapi interface, no sense in trying to curl it -- just fail
        programDisplay(denaliVariables, 'MonAPI availability', 'Not Available')

    #
    # Network availability (Adobe {corporate, production}, or external)?
    #
    ## test for production network availability
    prod_destination = "eng1.or1.omniture.com"
    prod_result, prod_timeDiff = pingTest(denaliVariables, prod_destination, '1')
    if prod_result == 0:
        programDisplay(denaliVariables, 'Network availability', 'AdobeProd')
    else:
        ## test for corporate network availability
        corp_destination = "lb-d-2.dev.ut1.omniture.com"
        corp_result, corp_timeDiff = pingTest(denaliVariables, corp_destination, '1')
        if corp_result == 0:
            programDisplay(denaliVariables, 'Network availability', 'AdobeCorp')
        else:
            ## must be an external network (no Adobe connectivity)
            programDisplay(denaliVariables, 'Network availability', 'Non-Adobe')

    print

    return True



##############################################################################
#
# denaliVersionDisplay(denaliVariables)
#

def denaliVersionDisplay(denaliVariables):

    version = denaliVariables["version"]
    date = denaliVariables["date"]
    print "Version              : %s" % version
    print "Build Date           : %s" % date
    print "Executable Location  : %s" % denaliVariables['denaliLocation']
    print

    # check for current authentication and SKMS availability
    ccode = authAvailability(denaliVariables)

    # check for modules/paths denali uses
    print "Basic functionality check:"
    if denali_libs == True:
        programDisplay(denaliVariables, 'denali_libs path', 'Available')
    else:
        programDisplay(denaliVariables, 'denali_libs path', 'Not Available', 'Libraries supplied locally (non-rpm install)')

    if denali_config == True:
        programDisplay(denaliVariables, 'denali config file', 'Available', '~/.denali/config')
    else:
        programDisplay(denaliVariables, 'denali config file', 'Not Available', 'No config file at ~/.denali/config')

    if denali_aliases == True:
        programDisplay(denaliVariables, 'denali aliases file', 'Available', '~/.denali/aliases')
    else:
        programDisplay(denaliVariables, 'denali aliases file', 'Not Available', 'No aliases file at ~/.denali/aliases')

    if urllib_err1 == True:
        programDisplay(denaliVariables, 'requests warnings', 'Silence')
    elif urllib_err1 == "old_package":
        programDisplay(denaliVariables, 'requests warnings', 'Old RPM')
    else:
        programDisplay(denaliVariables, 'requests warnings', 'Activated', 'python requests warnings not suppressed')

    if urllib_err2 == True:
        programDisplay(denaliVariables, 'requests/urllib3', 'Silence')
    elif urllib_err2 == "old_package":
        programDisplay(denaliVariables, 'requests/urllib3', 'Old RPM')
    else:
        programDisplay(denaliVariables, 'requests/urllib3', 'Activated', 'python requests.urllib3 warnings not suppressed')

    if urllib_err3 == True:
        programDisplay(denaliVariables, 'urllib3 warnings', 'Silence')
    elif urllib_err3 == "old_package":
        programDisplay(denaliVariables, 'urllib3 warnings', 'Old RPM')
    else:
        programDisplay(denaliVariables, 'urllib3 warnings', 'Activated', 'python urllib3 warnings not suppressed')

    # check for installed utilities on the host where denali is running
    ssh_path     = "/usr/bin/ssh"
    ssh_path_1   = """Location: /usr/bin/ssh
                                         Used with -c ssh for command distribution
                                         Install "openssh" to resolve."""
    scp_path     = "/usr/bin/scp"
    scp_path_1   = """Location: /usr/bin/scp
                                         Used with -c scp for parallel secure file copy
                                         Install "openssh" to resolve."""
    pdsh_path    = """Location: /usr/bin/pdsh or /usr/local/bin/pdsh
                                         Used with -c pdsh for parallel command distribution
                                         Install "pdsh" rpm to resolve."""
    dshbak_path  = """Location: /usr/bin/dshbak or /usr/local/bin/dshbak
                                         Used with -c pdsh for output/log analysis
                                         Install "pdsh" rpm to resolve."""
    sshpass_path = """Location: /usr/bin/sshpass or /usr/local/bin/sshpass
                                         Used with --ni for password passing with -c {scp,pdsh,ssh}
                                         Install "sshpass" rpm to resolve."""
    nmap_path    = "/usr/bin/nmap"
    nmap_path_1  = """Location: /usr/bin/nmap
                                         Used with -c ping for port discovery
                                         Install "nmap" rpm to resolve."""
    omnitool_path   = "/opt/netops/omnitool"
    omnitool_path_1 = """Location: /opt/netops/omnitool
                                         Used with --sis for SIS database integration with the omnitool
                                         utility.  Requires localConfig environment to be configured
                                         properly to function."""

    print
    print "Program availability:"

    # ssh
    if os.path.isfile(ssh_path) == True:
        programDisplay(denaliVariables, 'SSH', 'Available')
    else:
        programDisplay(denaliVariables, 'SSH', 'Not Available', ssh_path_1)

    # scp
    if os.path.isfile(scp_path) == True:
        programDisplay(denaliVariables, 'SCP', 'Available')
    else:
        programDisplay(denaliVariables, 'SCP', 'Not Available', scp_path_1)

    # nmap
    if os.path.isfile(nmap_path) == True:
        programDisplay(denaliVariables, 'NMAP', 'Available')
    else:
        programDisplay(denaliVariables, 'NMAP', 'Not Available', nmap_path_1)

    # pdsh and dshbak
    (pdsh_avail, dshbak_avail) = denali_commands.verifyPDSHRequirements(denaliVariables)
    if pdsh_avail == True:
        programDisplay(denaliVariables, 'PDSH', 'Available')
    else:
        programDisplay(denaliVariables, 'PDSH', 'Not Available', pdsh_path)

    if dshbak_avail == True:
        programDisplay(denaliVariables, 'DSHBAK', 'Available')
    else:
        programDisplay(denaliVariables, 'DSHBAK', 'Not Available', dshbak_path)


    # sshpass
    sshpass_avail = denali_commands.verifySSHRequirements(denaliVariables)
    if sshpass_avail == True:
        programDisplay(denaliVariables, 'SSHPASS', 'Available')
    else:
        programDisplay(denaliVariables, 'SSHPASS', 'Not Available', sshpass_path)

    # omnitool
    if os.path.isfile(omnitool_path) == True:
        programDisplay(denaliVariables, 'OMNITOOL', 'Available')
    else:
        programDisplay(denaliVariables, 'OMNITOOL', 'Not Available', omnitool_path_1)



##############################################################################
##############################################################################
##############################################################################


##############################################################################
#
# Main execution starting point
#


def main():

    # debug timing for main function
    main_start = time.time()

    # bring in the variable definitions for the code
    from denali_variables import denaliVariables

    # make these variables global for other function uses
    global denali_config
    global denali_aliases

    # the searching filter
    searchArgument  = ''

    #initial_debug  = True

    # register the signal handler for CTRL-C keyboard interrupts
    signal.signal(signal.SIGINT, signal_handler)

    # initialize the time variables
    denaliVariables['time'] = {
                                'denali_start'     :[], 'skms_auth_start'   :[], 'skms_start'   :[],
                                'denali_stop'      :[], 'skms_auth_stop'    :[], 'skms_stop'    :[],
                                'update_start'     :[], 'monitoring_start'  :[], 'monapi_start' :[],
                                'update_stop'      :[], 'monitoring_stop'   :[], 'monapi_stop'  :[],
                                'skms_auth_start'  :[], 'skms_auth_stop'    :[],

                                'f_transformMonitoringDictionary_start' :[],
                                'f_transformMonitoringDictionary_stop'  :[]
                              }

    # debug timing for main function
    main_stop = time.time()
    denali_utility.addElapsedTimingData(denaliVariables, 'main_start', main_start)
    denali_utility.addElapsedTimingData(denaliVariables, 'main_stop' , main_stop)

    # overall denali timing
    denaliVariables['time']['denali_start'].append(denali_start_time)

    # set the environment path for everyone
    os.environ['PATH'] += ':' + denaliVariables['utilityPath']

    if initial_debug == True:
        print "denali argument list = %s" % sys.argv

    denaliVariables['argumentList'] = ' '.join(sys.argv)

    # record the module finding from the initial load
    denaliVariables['importModules'].update({'denali_libs': denali_libs})
    denaliVariables['importModules'].update({'requests'   : [urllib_err1, urllib_err2]})
    denaliVariables['importModules'].update({'requests_to': req_readto})
    denaliVariables['importModules'].update({'urllib3'    : urllib_err3})

    # if no arguments are entered (the '1' is the path of the denali.py file),
    # then append "--help" to the argument list so it can be displayed.
    if len(sys.argv) == 1:
        sys.argv.append("--help")

    # determine input/output stream location
    determineStreamSettings(denaliVariables)

    # Search arguments for values that need to be added to denaliVariables before
    # the main loop runs below
    ccode = prepopulateVariables(denaliVariables, sys.argv)

    if denaliVariables['userConfig'] == False:
        # read the [current user $HOME]/.denali/config file
        rCode = denali_utility.loadConfigFile(denaliVariables, sys.argv[0])
        if rCode == True:
            # check for config file existence shown with --version
            denali_config = True

        # 'start' is in the utility function -- 'stop' is here because of so many return branches
        denali_utility.addElapsedTimingData(denaliVariables, 'loadConfigFile_stop', time.time())

        if rCode == -1:
            # Error condition found in the config file data
            # The error message is displayed in the function
            cleanUp(denaliVariables)
            exit(1)
        else:
            if initial_debug == True:
                print
                print ":: .denali/config file information ::"
                print "Alias Location   : %s" % denaliVariables["aliasLocation"]
                print "User Name        : %s" % denaliVariables["userName"]
                print "Session Path     : %s" % denaliVariables["sessionPath"]
                print "Domains to Strip : %s" % denaliVariables["domainsToStrip"]
                print "API URL          : %s" % denaliVariables["apiURL"]


    # MRASEREQ-41388
    # Credentials file addition in denali config file
    # Just bolt the creds data on the end of the sys.argv array
    # Filename is stored in the credsFileUsed variable
    if denaliVariables['credsFileUsed'] != False:
        sys.argv.append('--creds')
        sys.argv.append(denaliVariables['credsFileUsed'])
        denaliVariables['credsFileUsed'] = False

    # read the [current user $HOME]/.denali/aliases file
    rCode = denali_utility.loadAliasesFile(denaliVariables)
    denali_utility.addElapsedTimingData(denaliVariables, 'loadAliasesFile_stop', time.time())
    if rCode != False:
        if len(rCode):
            # check for alias file existence shown with --version
            denali_aliases = True
        if rCode == -1:
            # Error condition found in the aliases file data
            # The error message is displayed in the function
            cleanUp(denaliVariables)
            exit(1)
        elif rCode != False:
            denaliVariables["userAliases"] = rCode

            if initial_debug == True:
                print
                print ":: .denali/aliases file information ::"
                aliasKeys = denaliVariables["userAliases"].keys()
                for key in aliasKeys:
                    print "%-10s : %s" % (key, denaliVariables["userAliases"][key])
                print

    # See if the user submitted data via stdin, and if so, make sure the
    # double-dash is put in as a parameter.  This allows for denali to
    # automatically check and see if stdin has data waiting right when
    # denali launches (make it work like other linux programs in that sense).
    if select.select([sys.stdin,],[],[],0.0)[0]:
        # data is waiting on stdin
        try:
            # if no arguments were submitted, there will automatically be
            # a "--help" included ... remove it.
            if len(sys.argv):
                sys.argv.remove('--help')
        except ValueError:
            # tried to remove "--help", but it wasn't there ... move along
            pass

        # insert "--" as a parameter if it wasn't already submitted
        for parameter in sys.argv:
            if (parameter == '--' or parameter == '-' or
                parameter == '-l' or parameter == '--load' or parameter == "--nostdin"):
                break
        else:
            sys.argv.insert(1, '--')

    # parse through the command line argument list
    (denaliVariables["cliParameters"],
     denaliVariables["sqlParameters"],
     denaliVariables["simpleSearch"]   ) = denali_arguments.parseArgumentList(sys.argv, denaliVariables)

    if (denaliVariables["cliParameters"] == False and
        denaliVariables["sqlParameters"] == False and
        denaliVariables["simpleSearch"]  == False):
        cleanUp(denaliVariables)
        exit(1)

    # expand any short-cut sql parameters for use
    ccode = denali_arguments.expandSQLShortCutParameters(denaliVariables)

    # copy the sql parameters to save for future use
    denaliVariables["sqlParmsOriginal"] = list(denaliVariables["sqlParameters"])

    if initial_debug == True:
        print "cliparms          = %s" % denaliVariables["cliParameters"]
        print "sqlparms          = %s" % denaliVariables["sqlParameters"]
        print "methoddata        = %s" % denaliVariables["methodData"]
        print "ssearch           = %s" % denaliVariables["simpleSearch"]

    if denaliVariables["simpleSearch"] == True:
        if initial_debug == True:
            print
            print "[[ Simple Search Activated ]]"
            print

        # Simple search requires a list of servers to act against
        # If this list isn't given to denali, stop processing and
        # exit the program
        hostsSupplied = checkForHostEntry(denaliVariables)

        if hostsSupplied == False:
            # Assume complex syntax
            if initial_debug == True:
                print
                print "[[ Compex SQL Construction/Search Activated ]]"

    else:
        denaliVariables["simpleSearch"] = False
        if initial_debug == True:
            print
            print "[[ Complex Search Activated ]]"

    if initial_debug == True:
        print "CLI Parameters = %s" % denaliVariables["cliParameters"]
        print "SQL Parameters = %s" % denaliVariables["sqlParameters"]

    # take the CLI parameters (one at a time) and process them
    for parameters in denaliVariables["cliParameters"]:
        if initial_debug == True:
            print "cli parameter to process = %s" % parameters

        rValue = process_arguments(parameters, sys.argv, denaliVariables)
        denali_utility.addElapsedTimingData(denaliVariables, parameters[0] + '_stop', time.time())
        denali_utility.addElapsedTimingData(denaliVariables, 'process_arguments_stop', time.time())
        if rValue == False:
            # display return error message from web api
            if denaliVariables["debug"] == True:
                api = denaliVariables["api"]
                print "\nERROR:"
                print "   STATUS  : " + api.get_response_status()
                print "   TYPE    : " + str(api.get_error_type())
                print "   MESSAGE : " + api.get_error_message()

            cleanUp(denaliVariables)
            exit(1)

    cleanUp(denaliVariables)
    exit(0)


if __name__ == "__main__":
    main()

