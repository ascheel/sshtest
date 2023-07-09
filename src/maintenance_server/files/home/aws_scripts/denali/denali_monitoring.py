#############################################
#
# denali_monitoring.py
#
#############################################
#
#   This module contains the code to allow queries to retrieve and update
#   monitoring information for devices.  Currently this is nagios, but the
#   ability to have multiple monitoring end-points is possible.
#

import os
import sys
import copy
import time
import fnmatch
import getpass
import requests
import subprocess
import denali_authenticate
import denali_history
import denali_location
import denali_search
import denali_utility

# Monitoring api library
import MonApi as monapi

from denali_tty import colors

Connected_Network = "AdobeCorp"


##############################################################################
#
#   definitions for rest interface payloads
#

# Following URL is the initial end-point for monitoring that will be retired July 11, 2018
#base_URL = "https://moningestweb-or1-ext.adobe.net/monapi/v2/"

# MRASEREQ-43848:
# Following URL cannot retrieve information for devices in UT1, DEV.OR1, and DEV.VA7
# Accessible from both the corporate and production networks
base_URL = "https://monapi.or1.goc.adobe.net/v2/"

# Following URL cannot retrieve information for devices in DMZ.UT1
# Accessible only from the corporate network
base_URL_DEV = "https://monapi.dev.or1.goc.adobe.net/v2/"

BULK_URL = "/bulk/entity/svc/"

# retry count for logging in user/pass for Monitoring
RETRY_COUNT         = 3

# max_hostname_length
max_hostname_length = 0

# payload index location
PAYLOAD_LOCATION    = 3

# alert service max character count
as_max_char_count   = 80

# sanity check count for hosts before an agreement is requested
# used only with 'disable', 'enable', and 'downtime'
SANITY_CHECK_COUNT  = 20

# Default number of retries for MonAPI before giving up
RETRY_COUNTER       = 2
RETRY_DEBUG         = False

##############################################################################
##############################################################################
##############################################################################



##############################################################################
#
# prepColumnData(denaliVariables, monitoring_data)
#
#   denaliVariables["columnData"] = [ item #1, item#2, ...]
#       item #1 = ['name', 'name', 'Host Name', 33]
#       item #2 = ['device_state', 'device_state.full_name', 'Device State', 35]
#
#   Each item represents a specific column.  The order of the items in the list
#   is the order of the columns to be printed/displayed.
#
#   Order:  (1) Alias
#           (2) CMDB data name
#           (3) Print Column Title
#           (4) Column width (in characters)
#

def prepColumnData(denaliVariables, monitoring_data):

    if denaliVariables["monitoring_debug"] == True or denaliVariables["debugLog"] == True:
        outputString = "\n++prepColumnData++"
        denali_utility.debugOutput(denaliVariables, outputString)
        outputString = "monitoring_data = %s" % monitoring_data
        denali_utility.debugOutput(denaliVariables, outputString)

    monitoring_column_data = [
        # Alias                 DB Name                             Column Title                  Width
        ['ack',                 'acknowledged',                     'ACK',                           7],        # 0
        ['checks',              'checks',                           'Checks',                        8],        # 1
        ['comments',            'comments',                         'Comments',                     20],        # 2
        ['details',             'details',                          'Check Details',                76],        # 3
        ['maint',               'maintenance',                      'Maintenance',                  13],        # 4
        ['notify',              'notifications',                    'Notify',                        8],        # 5
        ['service',             'alert_service',                    'Service Name',                 30],        # 6
        ['status_code',         'status',                           'Status',                        8],        # 7
        ['status',              'status_string',                    'Status',                       10],        # 8
        ['ok',                  'ok_count',                         'OK Count',                     10],        # 9
        ['warn',                'warn_count',                       'WARN Count',                   12],        # 10
        ['crit',                'crit_count',                       'CRIT Count',                   12],        # 11
        ['unk',                 'unk_count',                        'UNK Count',                    11],        # 12
        ['ack_count',           'ack_count',                        'ACKS',                          7],        # 13
        ['check_count',         'check_count',                      'CHECKS',                        8],        # 14
        ['notify_count',        'notify_count',                     'NOTIFY',                        8],        # 15
        ['last_status_update',  'last_status_update',               'Last Update',                  16],        # 16 (for 'details' view)
        ['last_update',         'last_update',                      'Last Update',                  16],        # 17 (for 'summary' view)
        ['maint_check',         'maint_check',                      'Maintenance (User/End Time)',  35],        # 18 (for 'summary' view)
        ['interval',            'interval_minutes',                 'Intvl',                         7],        # 19 (for 'details' view)
        ['fail_notify',         'failure_count_before_notify',      'NCount',                        8],        # 20 (for 'details' view)
        ['fail_retry',          'failure_retry_interval_minutes',   'Retry',                         7],        # 21 (for 'details' view)
    ]

    if max_hostname_length < 11:
        hostname_length = 11
    else:
        hostname_length = max_hostname_length

    name_column = ['name', 'name', 'Host Name', hostname_length]

    if 'simple' in monitoring_data['commands']:
        # simplified display (host, service, status)
        denaliVariables['columnData'] = [name_column,                       # hostname
                                         monitoring_column_data[6],         # service name
                                         monitoring_column_data[8],         # status
                                    ]

        # the simplified version of monitoring display has NO wrapping.
        # make the service column wider by default to compensate
        denaliVariables['columnData'][1][-1] = 35

        denaliVariables['monitoring_columns'].update({
                                                    'name' : 0, 'service_name' : 1, 'status' : 2,
                                                })

        # For 'simple', turn off wrapping or the check status will
        # look _really_ ugly being displayed in the status column
        denaliVariables["textTruncate"] = False
        denaliVariables["textWrap"]     = False

    elif 'summary' in monitoring_data['commands']:
        # summary columns to display
        denaliVariables['columnData'] = [name_column,                       # hostname
                                         monitoring_column_data[9],         # ok_status
                                         monitoring_column_data[10],        # warning_status
                                         monitoring_column_data[11],        # critical_status
                                         monitoring_column_data[12],        # unknown_status
                                         monitoring_column_data[14],        # checks enabled status count
                                         monitoring_column_data[15],        # notifications enabled status counts
                                         #monitoring_column_data[13],        # ack status counts
                                         monitoring_column_data[17],        # last update (for any check)
                                         monitoring_column_data[18],        # maintenance check -- anything happening?
                                    ]
        denaliVariables['monitoring_columns'].update({
                                                    'name'         : 0, 'ok'        : 1, 'warn'         : 2,
                                                    'crit'         : 3, 'unk'       : 4, 'check_count'  : 5,
                                                    'notify_count' : 6,
                                                    #'ack_count'   : 7,
                                                    'maint_check'  : 8,
                                                    'last_update'  : 9,
                                                })

    elif 'details' in monitoring_data['commands']:
        # columns that will be output
        denaliVariables['columnData'] = [name_column,                       # hostname
                                         monitoring_column_data[6],         # service name
                                         monitoring_column_data[8],         # status
                                         monitoring_column_data[3],         # check detail
                                         monitoring_column_data[1],         # check status
                                         monitoring_column_data[5],         # notify status
                                         #monitoring_column_data[0],         # ack status
                                         monitoring_column_data[16],        # last status update
                                    ]
        denaliVariables['monitoring_columns'].update({
                                                    'name'        : 0, 'service_name' : 1, 'status'   : 2,
                                                    'details'     : 3, 'checks'       : 4, 'notify'   : 5,
                                                    #'ack'        : 6,
                                                    'last_update' : 7,
                                                })

        if 'all' in monitoring_data['commands']:
            denaliVariables['columnData'].extend([monitoring_column_data[19],
                                                  monitoring_column_data[20],
                                                  monitoring_column_data[21]]
                                                )
            denaliVariables['monitoring_columns'].update({'interval':8})
            denaliVariables['monitoring_columns'].update({'fail_notify':9})
            denaliVariables['monitoring_columns'].update({'fail_retry':10})

            # The 0th element in outputTarget is always a csv file type, even
            # when outputting to the screen. Here we're checking the output type
            # of the next element.
            if len(denaliVariables['outputTarget']) > 1 \
                    and 'txt_screen' == denaliVariables['outputTarget'][1].type:
                print "Column [%s]   : Displays the interval on which the check is run" % monitoring_column_data[19][2]
                print "Column [%s]  : Displays the maximum check attempts before a notification is sent" % monitoring_column_data[20][2]
                print "Column [%s]   : Displays the interval after a failure to run the check again" % monitoring_column_data[21][2]
                print

    return True



##############################################################################
#
# getLongestHostname(denaliVariables, serverList)
#
#   This function determines the character length of the largest hostname
#

def getLongestHostname(denaliVariables, serverList):

    hostLength = 0

    if len(denaliVariables['serverList']) == 0:
        # empty list
        return 0

    # Remove the last entry if it is 'denali_host_list'
    # This is a remnant of the marker used to combine lists greater than
    # 5000 host names (denaliVariables['maxSKMSRowReturn']) -- disgard it.
    if denaliVariables['serverList'][-1] == 'denali_host_list':
        denaliVariables['serverList'].remove('denali_host_list')

    # determine the character count of the longest hostname
    for host in serverList:
        length = len(host)

        if length > hostLength:
            hostLength = length

    # add '2' for the start/end spaces of the column
    return (hostLength + 2)



##############################################################################
#
# convertFromDateTimeToEpoch(time_string, pattern='%Y-%m-%d_%H:%M)
#

def convertFromDateTimeToEpoch(time_string, pattern='%Y-%m-%d_%H:%M'):

    try:
        start_time = int(time.mktime(time.strptime(time_string, pattern)))
    except ValueError:
        print "Denali Syntax Error:  Start time format is %s (24-hour clock)" % pattern
        print "     Time submitted:  %s" % time_string
        return False

    # make sure the date specified is not in the past
    if start_time < time.time():
        print "Denali Limit Reached:  Start time is in the past.  Session halted."
        print "      Time submitted:  %s" % time_string
        return False

    # get current date
    current_date = time.strftime('%Y-%m-%d')
    current_date = current_date.split('-')
    year  = int(current_date[0]) + 1
    month = int(current_date[1])
    day   = int(current_date[2])
    # 1 year out epoch
    add_one_year = "%s-%s-%s_00:00" % (year, month, day)
    plus_one = int(time.mktime(time.strptime(add_one_year, pattern)))

    # make sure the date specified is less than 1 year in the future
    if start_time > plus_one:
        print "Denali Limit Reached:  Start time is greater than 1 year in the future.  Session halted."
        print "      Time submitted:  %s" % time_string
        return False

    return start_time



##############################################################################
#
# addHostName(denaliVariables, hostname, category)
#
#   This function adds a hostname to a specified category in denaliVariables.
#

def addHostName(denaliVariables, hostname, category):
    if category in denaliVariables['monitoring_summary']:
        denaliVariables['monitoring_summary'][category].append(hostname)
    else:
        denaliVariables['monitoring_summary'].update({category:[hostname]})



##############################################################################
#
# removeDuplicateHostnames(response_list)
#

def removeDuplicateHostnames(response_list):

    hostname_list = []

    for (index, hostdata) in enumerate(response_list):
        if hostdata['name'] not in hostname_list:
            hostname_list.append(hostdata['name'])
        else:
            response_list[index]['name'] = ''

    return response_list



##############################################################################
#
# printHTMLData(denaliVariables, html_dictionary)
#

def printHTMLData(denaliVariables, html_dictionary):

    column_1_width  = 32
    separator_color = colors.fg.red

    if len(html_dictionary) == 0:
        return

    print
    if denaliVariables['nocolors'] == True:
        print " Nagios Variable Name".ljust(column_1_width) + " |  Data Value (from Nagios webscrape)"
        print ((column_1_width + 1) * '=') + '|' + (68 * '=')
        for data_item in html_dictionary:
            print " %s|  %s" % (data_item.keys()[0].ljust(column_1_width), data_item.values()[0])
    else:
        print " Nagios Variable Name".ljust(column_1_width) + separator_color + " |" + colors.reset + "  Data Value (from Nagios webscrape)"
        print separator_color + ((column_1_width + 1) * '=') + '|' + (68 * '=') + colors.reset

        for data_item in html_dictionary:
            sys.stdout.write(" %s" % data_item.keys()[0].ljust(column_1_width))
            sys.stdout.write(separator_color + "|" + colors.reset)
            print "  %s" % data_item.values()[0]



##############################################################################
#
# webScrapePage(denaliVariables, hostname, alert_service)
#
#   This is the entry function for the screen scraper code to pull data from
#   a localized nagios host concerning a host's alert service specific data.
#

def webScrapePage(denaliVariables, hostname, alert_service):

    authentication_comment = " for Nagios host access"

    if len(hostname) == 0 or len(alert_service) == 0:
        return False

    location = hostname.split('.')[-1]
    if location == "com" or location == "net":
        # if this ends in .com or .net (e.g., c1001.lon5.omniture.com)
        # take the 3rd item from the end (lon5 in the above case)
        location = hostname.split('.')[-3]
    if location.upper() not in denali_location.dc_location:
        if len(denaliVariables['dataCenter']) == 1:
            location = denaliVariables['dataCenter'][0]
        elif len(denaliVariables['dataCenter']) > 1:
            print "Denali syntax error: Only a one data center location allowed for entity debug mode [%s]" % denaliVariables['dataCenter']
            denali_search.cleanUp(denaliVariables)
            exit(1)
        else:
            print "Denali error: Location [%s] not found" % location
            denali_search.cleanUp(denaliVariables)
            exit(1)

    username = denaliVariables['dm_username']
    password = denaliVariables['dm_password']

    if len(username) == 0 or len(password) == 0:
        # if either of these are true, require credentials before proceeding
        if denaliVariables['monitoring_debug'] == True or denaliVariables['debugLog'] == True:
            outputString = "Monitoring debug login required: Digital Marketing username and password"
            denali_utility.debugOutput(denaliVariables, outputString)

        ccode = getDMUsernameAndPassword(denaliVariables, enter_user=False, authentication_comment=" for Nagios host access")
        if ccode == False:
            return False
        username = denaliVariables['dm_username']
        password = denaliVariables['dm_password']

    # construct the URL
    url_host = "nagios." + location + ".goc.adobe.net/"
    url      = "https://" + url_host + "noc/hostinfo.html?command=passcheck&host=" + hostname
    url     += "&service=" + alert_service + "&employee=" + username + "&center=" + location

    try:
        # request the page from the nagios box
        res = requests.get(url, verify=False, auth=(username, password))

    except requests.exceptions.ConnectionError as e:
        print "Denali requests error: %s" % e
        return False

    # check for successful return
    if res.status_code == 200:
        html_source     = res.text
        html_dictionary = parseHTML(denaliVariables, html_source)
        printHTMLData(denaliVariables, html_dictionary)
    else:
        print "Denali requests html get error: [%s] %s" % (res.status_code, res)
        return False

    return True



##############################################################################
#
# parseHTML(denaliVariables, html_source)
#

def parseHTML(denaliVariables, html_source):

    html_dictionary = []
    line            = ''

    for character in html_source:
        if character != '\n':
            line += character
        else:
            #print line
            if line.startswith('<tr><td>'):
                line = line.split()
                if line[0] == '<tr><td>Check':
                    # check name
                    temp_list = ' '.join(line[5:])[:-10]
                    html_dictionary.append({'checkname':temp_list})
                else:
                    # service definition (check settings)
                    temp_list = ' '.join(line[7:])[:-10]
                    html_dictionary.append({line[3].strip():temp_list})

            elif line.startswith('</tr><td>'):
                # maybe nothing -- 'Service definition:'
                line = line.split()
                pass
            elif line.startswith('</td><td>'):
                # command line to run
                line = line.split()
                html_dictionary.append({'command_line':' '.join(line[5:-1])})
            elif line.startswith('No matching service check was found'):
                print
                print "Nagios debug information:"
                line = line.split()
                hostname = line[-2].strip()
                alert_service = line[-1].strip()
                print "No matching service check was found for host [%s] with alert service [%s]" % (hostname, alert_service)
                return []
            line = ''

    return html_dictionary



##############################################################################
#
# outputHTTPError(http_error)
#

def outputHTTPError(http_error):
    if http_error == 400:
        print "Denali: Invalid JSON Payload (http error 400)"
    elif http_error ==  401:
        print "Denali: Unauthorized (http error 401)"
    elif http_error == 500:
        print "Denali: Internal Server Error (http error 500)"
    else:
        print "Denali:  HTTP Error encountered: %s" % http_error



##############################################################################
#
# classifyHosts(denaliVariables, category_list, host, hosts_status, maint_check, last_update_time)
#

def classifyHosts(denaliVariables, category_list, host, hosts_status, maint_check, last_update_time):

    maint_check_string = ''

    category_count = len(category_list)
    if hosts_status['ack'] > 0:
        addHostName(denaliVariables, host, 'acknowledge')
    if hosts_status['check'] < category_count:
        addHostName(denaliVariables, host, 'checks_disabled')
    if hosts_status['notify'] < category_count:
        addHostName(denaliVariables, host, 'notify_disabled')

    hosts_status['ack']    = str(hosts_status['ack'])    + '/' + str(category_count)
    hosts_status['check']  = str(hosts_status['check'])  + '/' + str(category_count)
    hosts_status['notify'] = str(hosts_status['notify']) + '/' + str(category_count)

    if len(maint_check) > 0:
        if len(maint_check) == 1:
            if len(maint_check[0]) > 0:
                maint_check_user   = maint_check[0].get('created_by', '')
                if len(maint_check_user) < 8:
                    maint_check_user = maint_check_user.ljust(8)
                maint_check_time   = maint_check[0].get('end_time', '')
                if maint_check_user != '' and maint_check_time != '':
                    maint_check_string = maint_check_user + ' : ' + time.strftime('%m/%d/%y %H:%M', time.localtime(maint_check_time))
        else:
            for (index, m_check) in enumerate(maint_check):
                if len(m_check) > 0:
                    maint_check_user = m_check.get('created_by', '')
                    if len(maint_check_user) < 8:
                        maint_check_user = maint_check_user.ljust(8)
                    maint_check_time = m_check.get('end_time', '')
                    if maint_check_user != '' and maint_check_time != '':
                        if len(maint_check_string) > 0:
                            maint_check_string += ' '
                        maint_check_string += '(' + (str(index+1)) + ')' + ' ' + maint_check_user + ' : ' + time.strftime('%m/%d/%y %H:%M', time.localtime(maint_check_time))
                else:
                    m_check = ''

    last_update_time = time.strftime('%m/%d/%y %H:%M', time.localtime(last_update_time))
    status_counts = { 'ok_count'     : hosts_status['ok'],     'warn_count'  : hosts_status['warn'],
                      'crit_count'   : hosts_status['crit'],   'unk_count'   : hosts_status['unk'],
                      'ack_count'    : hosts_status['ack'],    'check_count' : hosts_status['check'],
                      'notify_count' : hosts_status['notify'], 'last_update' : last_update_time,
                      'maint_check'  : maint_check_string }

    if denaliVariables['monitoring_debug'] == True or denaliVariables['debugLog'] == True:
        outputString = "status_counts = %s" % status_counts
        denali_utility.debugOutput(denaliVariables, outputString)

    # classify host status for summary printing
    if status_counts['crit_count']   > 0:
        addHostName(denaliVariables, host, 'critical')
    elif status_counts['warn_count'] > 0:
        addHostName(denaliVariables, host, 'warning')
    elif status_counts['unk_count']  > 0:
        addHostName(denaliVariables, host, 'unknown')
    else:
        addHostName(denaliVariables, host, 'ok')

    return status_counts



##############################################################################
#
# performSearchOperation(denaliVariables)
#
#   monitoring_data : information about this run -- commands to execute, search to
#                     perform, REST URL to use, etc.
#   data_dict       : a per-host dictionary containing the response data from the
#                     monitoring system -- with each column as a key.
#   response_list   : data gathered and combined for the host.  All of the counts
#                     for each (ok, crit, warn, ack, etc.)
#   search_lines    : how many lines have been found for the host for this specific
#                     search criteria
#   add_host_dict   : whether or not to print the hostname (do not after the first
#                     line of the host is printed).
#

def performSearchOperation(denaliVariables, monitoring_data, data_dict, response_list, search_lines, add_host_dict):

    # check the search criteria
    # the entire line was just built (of many columns -- above), now search it
    #
    #       monitoring_data = {'commands'      : ['details', 'delete'],
    #                          'search_extras' : ['CRITICAL', 'OK']}

    if '+' in monitoring_data['search_extras']:
        monitoring_data['search_extras'].remove('+')
        and_search = True
    else:
        and_search = False

    # for MonApi v2, the dictionary returned is different than in v1 -- massage it so that
    # it continues to work as needed
    # this pulls out the 'data' key, and in its place lays down all of the data from the
    # 'data' key -- which is how v1 looked.
    data_dict.update(data_dict.pop('data', None))

    if 'summary' not in monitoring_data['commands']:
        data_keys = data_dict.keys()
        if len(monitoring_data['search_extras']) > 0:

            # an 'AND' search
            if and_search == True:
                match_dict = {'total':0}
                for s_criteria in monitoring_data['search_extras']:
                    match_dict.update({s_criteria:0})
                for s_criteria in monitoring_data['search_extras']:
                    for data in data_keys:
                        if str(data_dict[data]).find(s_criteria) != -1:
                            # do not search the details
                            if data == "details":
                                continue
                            match_dict[s_criteria] += 1
                            match_dict['total'] += 1
                            for match_check in match_dict.keys():
                                if match_dict[match_check] == 0:
                                    break
                            else:
                                if add_host_dict == True and len(data_dict['name']) == 0:
                                    data_dict['name'] = host
                                search_lines += 1
                                response_list.append(data_dict)
                                add_host_dict = False
                                break
            else:
                # an 'OR' search
                for s_criteria in monitoring_data['search_extras']:
                    for data in data_keys:
                        if str(data_dict[data]).find(s_criteria) != -1:
                            # do not search the details
                            if data == "details":
                                continue
                            if add_host_dict == True and len(data_dict['name']) == 0:
                                data_dict['name'] = host

                            # add in the "found" line of data
                            if response_list:
                                if response_list[-1] != data_dict:
                                    response_list.append(data_dict)
                                    search_lines += 1
                            else:
                                response_list.append(data_dict)
                                search_lines += 1

                            # set the variable to false -- no more hostname needed
                            add_host_dict = False

                            # Break out of the 'data' for-loop -- once the line is added
                            # we're done.  Without this, a single line could be added
                            # multiple times for each time it matches.
                            break
        else:
            # add the data line in for printing
            response_list.append(data_dict)
    elif 'summary' in monitoring_data['commands']:
        if add_host_dict == True:
            response_list.append(data_dict)
            add_host_dict = False

    # make sure this is put back, or the next round will think it is
    # an 'or' search ... it will mess up the output
    if and_search == True:
        monitoring_data['search_extras'].append('+')

    return (response_list, search_lines, add_host_dict)



##############################################################################
#
# recordCategoryHost(denaliVariables, host, category, category_status)
#

def recordCategoryHost(denaliVariables, host, category, category_status):
    if category in denaliVariables['monitoring_cat']:
        if category_status in denaliVariables['monitoring_cat'][category]:
            denaliVariables['monitoring_cat'][category][category_status].append(host)
        else:
            denaliVariables['monitoring_cat'][category].update({category_status:[host]})
    else:
        denaliVariables['monitoring_cat'].update({category:{category_status:[host]}})



##############################################################################
#
# updateCategoryStatus(denaliVariables, response, host, category, last_update_time, hosts_status, data_dict)
#

def updateCategoryStatus(denaliVariables, response, host, category, last_update_time, hosts_status, data_dict):

    # set to True if the host isn't completely OK
    status_flag = False

    category_data_items = response['data']['results'][host]['alert_services'][category].keys()
    category_status     = response['data']['results'][host]['alert_services'][category]['data']['status_string']
    ack_status          = response['data']['results'][host]['alert_services'][category]['data']['acknowledged']
    check_status        = response['data']['results'][host]['alert_services'][category]['data']['checks']
    notify_status       = response['data']['results'][host]['alert_services'][category]['data']['notifications']

    # get the last update status time (epoch) and translate it to m/d/year h:m (24 hour clock)
    last_update         = response['data']['results'][host]['alert_services'][category]['data']['last_status_update']
    if last_update > last_update_time:
        last_update_time = last_update

    last_update = time.strftime('%m/%d/%y %H:%M', time.localtime(last_update))
    response['data']['results'][host]['alert_services'][category]['data']['last_status_update'] = last_update
    if denaliVariables['monitoring_debug']:
        print "%s  %s  %s" % (ack_status, check_status, notify_status)

    maint_check = len(response['data']['results'][host]['alert_services'][category]['data']['maintenance'])
    if maint_check > 0:
        if 'end_time' in response['data']['results'][host]['alert_services'][category]['data']['maintenance'][0]:
            maint_check = response['data']['results'][host]['alert_services'][category]['data']['maintenance']
        else:
            maint_check = ['']
    else:
        maint_check = ['']

    # count the category status
    if category_status   == "OK":
        hosts_status['ok'] += 1
    elif category_status == "WARNING":
        hosts_status['warn'] += 1
        status_flag = True
    elif category_status == "CRITICAL":
        hosts_status['crit'] += 1
        status_flag = True
    elif category_status == "UNKNOWN":
        hosts_status['unk'] += 1
        status_flag = True

    recordCategoryHost(denaliVariables, host, category, category_status)

    # count the ack, check, and notify counts (per category)
    if ack_status    == True:
        hosts_status['ack'] += 1
    if check_status  == True:
        hosts_status['check'] += 1
    if notify_status == True:
        hosts_status['notify'] += 1

    category_data_items.sort()
    for data_item in category_data_items:
        data_dict.update({data_item:response['data']['results'][host]['alert_services'][category][data_item]})

    return (data_dict, maint_check, hosts_status, last_update_time, status_flag)



##############################################################################
#
# transformMonitoringDictionary(denaliVariables, response, monitoring_data)
#

def transformMonitoringDictionary(denaliVariables, response, monitoring_data):

    denali_utility.addTimingData(denaliVariables, 'transformMonitoringDictionary_start', time.time())

    if denaliVariables["monitoring_debug"] == True or denaliVariables["debugLog"] == True:
        outputString = "\n++transformMonitoringDictionary++"
        denali_utility.debugOutput(denaliVariables, outputString)
        outputString = "monitoring_data = %s" % monitoring_data
        denali_utility.debugOutput(denaliVariables, outputString)

    # u'results': [
    #               {u'device_state.full_name': u'On Duty - Standby', u'name': u'db2255.oak1'},
    #               {u'device_state.full_name': u'On Duty - In Service', u'name': u'dn15.or1'}
    #             ]

    # make sure the overall response from monitoring was successful
    if response['http_code'] != 200:
        outputHTTPError(response['http_code'])
        exit(1)

    if response['data']['success'] == False:
        print "Denali: Failed to retrieve monitoring data successfully"
        print denaliVariables["serverList"]
        return response

    # make the response dictionary match the style of that from SKMS -- mostly
    response_list = []
    response['data']['results'] = response['data'].pop('response', None)

    # loop through the response dictionary, prepping the data for display
    hostnames = response['data']['results'].keys()
    for host in hostnames:
        if response['data']['results'][host]['success'] == True:
            category_list = response['data']['results'][host]['alert_services'].keys()
            category_list.sort()

            # reset host counters
            add_host_dict    = True        # for a single line in a search diplay
            search_lines     = 0
            last_update_time = 0
            hosts_status     = {'ok':0, 'warn':0, 'crit':0, 'unk':0, 'ack':0, 'check':0, 'notify':0}
            status_counts    = {}

            for category in category_list:
                # category_data_items
                #  (1) acknowledged     (4) details         (7) service
                #  (2) checks           (5) maintenance     (8) status
                #  (3) comments         (6) notifications   (9) status_string

                # this puts the hostname on every line -- and is useful for sorting later
                data_dict = {'name':host}

                # add the minutes designator to the end of the interval_mins and failure_retry data
                interval_mins = str(response['data']['results'][host]['alert_services'][category]['data']['interval_minutes']) + 'm'
                failure_retry = str(response['data']['results'][host]['alert_services'][category]['data']['failure_retry_interval_minutes']) + 'm'
                response['data']['results'][host]['alert_services'][category]['data']['interval_minutes'] = interval_mins
                response['data']['results'][host]['alert_services'][category]['data']['failure_retry_interval_minutes'] = failure_retry

                # update counts for ok, crit, warning, etc.
                (data_dict,
                 maint_check,
                 hosts_status,
                 last_update_time,
                 status_flag)      = updateCategoryStatus(denaliVariables, response, host, category,
                                                          last_update_time, hosts_status, data_dict)

                 # For 'simple' display output, include the Check Details with the Status
                if 'simple' in monitoring_data['commands'] and status_flag == True:
                    # combine the status and check details
                    check_details = response['data']['results'][host]['alert_services'][category]['data']['details']
                    check_status  = response['data']['results'][host]['alert_services'][category]['data']['status_string']
                    check_status  = check_status.ljust(8) + ': ' + check_details
                    response['data']['results'][host]['alert_services'][category]['data']['status_string'] = check_status

                # do the search operation
                (response_list,
                 search_lines,
                 add_host_dict) = performSearchOperation(denaliVariables, monitoring_data, data_dict,
                                                         response_list, search_lines, add_host_dict)

            # classify host checks/notifications for summary printing
            status_counts = classifyHosts(denaliVariables, category_list, host, hosts_status, maint_check, last_update_time)

            if ('summary' not in monitoring_data['commands'] and
                len(monitoring_data['search_extras']) > 0 and search_lines == 0):
                # host search through -- no data found
                if denaliVariables["monitoring_debug"] == True or denaliVariables["debugLog"] == True:
                    outputString = "%s :  Search criteria %s not found" % (host, monitoring_data['search_extras'])
                    denali_utility.debugOutput(denaliVariables, outputString)

            # store the counts on the line with the host name
            for (index, host_data) in enumerate(response_list):
                if host_data['name'] == host:
                    response_list[index].update(status_counts)

        elif response['data']['results'][host]['success'] == False:
            # if a search was initiated, do not add this host
            if ('summary' not in monitoring_data['commands'] and len(monitoring_data['search_extras']) > 0):
                continue

            # likely a host not configured -- add it in after verifying
            message   = response['data']['results'][host]['message']
            http_code = response['data']['results'][host]['http_code']

            if message.startswith('Entity not found at expected') and http_code == 404:
                status_counts   = { 'ok_count':0, 'warn_count':0, 'crit_count':0, 'unk_count':0 }
                host_dictionary = {'name':host, 'alert_service':'Configuration Not Found'}
                host_dictionary.update(status_counts)
                response_list.append(host_dictionary)

                # add host to the summary list
                addHostName(denaliVariables, host, 'not_found')
            else:
                # host data not successfully retrieved and wasn't 'not configured'
                # not sure what this is
                if denaliVariables['monitoring_debug'] == True or denaliVariables['debugLog'] == True:
                    outputString = "Error host name : %s" % host
                    denali_utility.debugOutput(denaliVariables, outputString)
                    outputString = "Error host data : %s\n" % response['data']['results'][host]
                    denali_utility.debugOutput(denaliVariables, outputString)
        else:
            print "Denali: Unknown result from a query:"
            print "Host = %s   Success value = %s" % (host, response['data']['results'][host]['success'])
            return response

    # if a summary is requested, only sort the host name
    # if the details are requested, sort by host name and by the alert service
    if 'summary' in monitoring_data['commands']:
        response_list = sorted(response_list, key=lambda k: (k['name']))
    else:
        response_list = sorted(response_list, key=lambda k: (k['name'], k['alert_service']))

    # remove duplicate hostnames
    response_list = removeDuplicateHostnames(response_list)

    # if a mismatch search was asked for -- return the data here
    if 'mismatch' in monitoring_data['commands']:
        response_list = returnMismatchList(denaliVariables, response_list, monitoring_data['commands'])
        recalculateSummaryData(denaliVariables, response_list)

    # assign the response_list to the response dictionary
    response['data']['results'] = response_list

    if denaliVariables['monitoring_debug'] == True or denaliVariables['debugLog'] == True:
        outputString = "response :\n%s" % response_list
        denali_utility.debugOutput(denaliVariables, outputString)

    denali_utility.addTimingData(denaliVariables, 'transformMonitoringDictionary_stop', time.time())

    return response



##############################################################################
#
# returnMismatchList(denaliVariables, response_list, commands, inverse=False)
#
#   MRASETEAM-40489
#
#   This function removes all 'correctly' running hosts.  By correctly it is
#   meant that all checks are enabled and all notifications for those checks
#   are enabled.  Conversely, if a host has 15 out of 16 checks enabled, this
#   host would be moved into the list of hosts to display, because it is not
#   a normal (or full) configuration.
#
#   The 'inverse' parameter allows for the opposite to happen.  Instead of
#   selecting all hosts that don't have every check and notification enabled,
#   it selects all hosts to do have them enabled.  Currently there is not a
#   command that takes advantage of the inverse, but if requested, the flag
#   is available for a quicker code change to be completed.
#
#   The return from this function is a paired down list of hosts that meet the
#   criteria specified.
#

def returnMismatchList(denaliVariables, current_list, commands, inverse=False):

    response_list = []

    # The searching/adding/removing works differently between the 'summary'
    # output, and the 'details' output.  As such, they need to be separated
    # and handled according to the command issued.

    denali_utility.addElapsedTimingData(denaliVariables, 'returnMismatchList_start', time.time())

    if 'summary' in commands:
        for entry in current_list:
            if entry['alert_service'] == 'Configuration Not Found':
                # any CNF host cannot be analyzed, so just continue
                response_list.append(entry)
                continue

            checks   = entry['check_count']
            notifys  = entry['notify_count']
            hostname = entry['name']
            checks   = checks.split('/')
            notifys  = notifys.split('/')

            if checks[0] != checks[1] or notifys[0] != notifys[1]:
                if inverse == False:
                    response_list.append(entry)
            else:
                if inverse == True:
                    response_list.append(entry)

    elif 'details' in commands or 'simple' in commands:
        # This section needs to ensure that the hostname is carried along in
        # the response section.  It is possible it gets removed because of an
        # alert service that is removed (perhaps its the first line which by
        # default has the hostname).  That's why this "new_host" flag is used;
        # it helps ensure the hostname is printed when lines are removed.

        new_host = False

        for entry in current_list:
            if entry['alert_service'] == 'Configuration Not Found':
                # any CNF host cannot be analyzed, so just continue
                #response_list.append(entry)
                continue

            mismatch = False
            check    = entry['checks']
            notify   = entry['notifications']

            if len(entry['name']) != 0:
                hostname = entry['name']
                new_host = True

            if check != notify or (check == False and notify == False):
                mismatch = True

            if mismatch == True:
                if inverse == False:
                    if len(entry['name']) == 0 and new_host == True:
                        entry['name'] = hostname
                    new_host = False
                    response_list.append(entry)
            else:
                if inverse == True:
                    if len(entry['name']) == 0 and new_host == True:
                        entry['name'] = hostname
                    new_host = False
                    response_list.append(entry)
    else:
        denali_utility.addElapsedTimingData(denaliVariables, 'returnMismatchList_stop', time.time())
        return current_list

    denali_utility.addElapsedTimingData(denaliVariables, 'returnMismatchList_stop', time.time())
    return response_list



##############################################################################
#
# recalculateSummaryData(denaliVariables, response_list)
#
#   This go-round is much easier than the initial one.  All of the counters
#   exist in the response_list; they were generated during the first pass
#   through the data.  So all this function has to do is read that existing
#   data and then categorize the host accordingly.
#

def recalculateSummaryData(denaliVariables, response_list):

    # clear out the existing Lists -- they are invalid now
    denaliVariables['monitoring_summary'].pop('acknowledge',     None)
    denaliVariables['monitoring_summary'].pop('checks_disabled', None)
    denaliVariables['monitoring_summary'].pop('notify_disabled', None)
    denaliVariables['monitoring_summary'].pop('critical',        None)
    denaliVariables['monitoring_summary'].pop('warning',         None)
    denaliVariables['monitoring_summary'].pop('unknown',         None)
    denaliVariables['monitoring_summary'].pop('ok',              None)
    denaliVariables['monitoring_summary'].pop('not_found',       None)

    # loop through the response_list and classify the hosts
    for entity in response_list:
        if len(entity['name']) != 0:
            hostname = entity['name']
        else:
            continue

        # check for not configured entities
        #print "hostname = %s" % hostname
        if 'check_count' not in entity:
            addHostName(denaliVariables, hostname, 'not_configured')
            continue

        checks = entity['check_count'].split('/')
        notify = entity['notify_count'].split('/')
        acks   = entity['ack_count'].split('/')

        if checks[0] != checks[1]:
            addHostName(denaliVariables, hostname, 'checks_disabled')
        if notify[0] != notify[1]:
            addHostName(denaliVariables, hostname, 'notify_disabled')
        if int(acks[0]) > 0:
            addHostName(denaliVariables, hostname, 'acknowledge')

        if entity['crit_count'] > 0:
            addHostName(denaliVariables, hostname, 'critical')
            continue
        if entity['warn_count'] > 0:
            addHostName(denaliVariables, hostname, 'warning')
            continue
        if entity['unk_count'] > 0:
            addHostName(denaliVariables, hostname, 'unknown')
            continue
        addHostName(denaliVariables, hostname, 'ok')

    return True



##############################################################################
#
# printServicesData(denaliVariables, response, monitoring_data)
#

def printServicesData(denaliVariables, response, monitoring_data):

    if denaliVariables["monitoring_debug"] == True:
        print "\n++printServicesData++"
        print "monitoring_data = %s" % monitoring_data

    # Successful send_request response
    if response != False:
        pass
        #keys = response.keys()
        #print "json keys = %s" % keys
        #print "https code (200/401/402/403) : %s" % response['http_code']
        #print "response json = %s" % response['data'].keys()

    # transform monitoring response dictionary into one that denali understands
    # and can output (screen/file) from
    response = transformMonitoringDictionary(denaliVariables, response, monitoring_data)

    # make sure the correct columns are included in the output (according to what
    # is initially requested)
    ccode = prepColumnData(denaliVariables, monitoring_data)

    # put the data retrieved in the columnar output format
    (printData, overflowData) = denali_search.generateOutputData(response, denaliVariables)

    if denaliVariables["monitoring_debug"] == True or denaliVariables["debugLog"] == True:
        outputString = "\nprintData    = %s\n" % printData
        denali_utility.debugOutput(denaliVariables, outputString)
        outputString = "overflowData = %s\n" % overflowData
        denali_utility.debugOutput(denaliVariables, outputString)

    page_number = 1
    for item in denaliVariables['outputTarget']:
        item.append = False

    denali_search.prettyPrintData(printData, overflowData, response, denaliVariables)

    if denaliVariables['summary'] == True:
        printMonitoringSummary(denaliVariables)

    if denaliVariables['mon_details'] == True:
        printMonitoringDetails(denaliVariables, monitoring_data)

    return True



##############################################################################
#
# hostPrintOutput(denaliVariables, monitoring_data, response)
#
# {'errors': [],
#  'data': {
#            u'message': u'',
#            u'http_code': 200,
#            u'success': True,
#            u'response': {
#                           u'db1879.or1': {
#                                           u'message': u'',
#                                           u'alert_services': {
#                                                               u'LOAD': {
#                                                                         u'message': u'Request sent',
#                                                                         u'data': {},
#                                                                         u'http_code': 202,
#                                                                         u'success': True
#                                                               },
#                                                               ...
#                                                               u'SYSTEM_DISK_SPACE': {
#                                                                         u'message': u'Request sent',
#                                                                         u'data': {},
#                                                                         u'http_code': 202,
#                                                                         u'success': True
#                                                               }
#                                                              },
#                                           u'http_code': 200,
#                                           u'success': True
#                                          }
#                         }
#          },
# 'http_code': 200}

def hostPrintOutput(denaliVariables, monitoring_data, response):

    alert_service_max_size = 0

    success_hosts = []
    failure_hosts = []

    partial_count = 0
    review_count  = 0

    if 'data' not in response and 'response' not in response['data']:
        print "Denali error: Response dictionary has format problems."
        print "response dictionary = %s" % response
        denali_search.cleanUp(denaliVariables)
        exit(1)

    # loop through the hosts -- identify whether they succeeded or not
    hostname_list = response['data']['response'].keys()
    hostname_list.sort()
    for hostname in hostname_list:
        success_services = []
        failure_services = []
        alert_result     = []

        if hostname not in response['data']['response']:
            print "  %s  %s" % (hostname,ljust(max_hostname_length, 'Not found in response dictionary'))
            failure_hosts.append(hostname)
        else:
            services = response['data']['response'][hostname]['alert_services'].keys()

            if len(services) == 0:
                if denaliVariables['nocolors'] == True:
                    success_failure = 'MONITORING NOT CONFIGURED'
                else:
                    success_failure = colors.bold + colors.fg.blue + 'MONITORING NOT CONFIGURED' + colors.reset
            else:
                success_failure = response['data']['response'][hostname]['success']

                # only do this once
                if alert_service_max_size == 0:
                    for alert_service in services:
                        if len(alert_service) > alert_service_max_size:
                            alert_service_max_size = len(alert_service)

                services.sort()
                for alert_service in services:
                    message   = response['data']['response'][hostname]['alert_services'][alert_service]['message']
                    http_code = response['data']['response'][hostname]['alert_services'][alert_service]['http_code']
                    success   = response['data']['response'][hostname]['alert_services'][alert_service]['success']
                    if 'exit_code' in response['data']['response'][hostname]['alert_services'][alert_service]['data']:
                        exit_code = response['data']['response'][hostname]['alert_services'][alert_service]['data']['exit_code']
                        if exit_code == 0:
                            exit_code = "OK"
                        elif exit_code == 1:
                            exit_code = "WARNING"
                        elif exit_code == 2:
                            exit_code = "CRITICAL"
                        elif exit_code == 3:
                            exit_code = "UNKNOWN"
                        else:
                            exit_code = " "
                    else:
                        # it's possible that the json from MonApi is different, check for different key/value pairs
                        exit_code = response['data']['response'][hostname]['alert_services'][alert_service]['data'].get('status_string', ' ')

                    if 'stdout' in response['data']['response'][hostname]['alert_services'][alert_service]['data']:
                        alert_result.append(response['data']['response'][hostname]['alert_services'][alert_service]['data']['stdout'])
                    else:
                        alert_result.append(response['data']['response'][hostname]['alert_services'][alert_service]['data'].get('details', ''))

                    if ((message == "Request sent" or message == "Result submitted" or message == "No maintenance windows exist") and
                        (http_code >= 200 and http_code <= 210) and
                        success == True):
                        success_services.append(alert_service)

                        # debugging is enabled, call a success a failure so as to show the data during the run
                        if denaliVariables['monitoring_debug'] == True or denaliVariables['mon_details'] == True:
                            alert_service = alert_service + ':' + message + ':' + str(http_code) + ':' + str(success) + ':' + exit_code
                            failure_services.append(alert_service)
                    else:
                        if http_code >= 200 and http_code <= 210 and success == True:
                            success_services.append(alert_service)
                            if denaliVariables['monitoring_debug'] == True or denaliVariables['mon_details'] == True:
                                alert_service = alert_service + ':' + message + ':' + str(http_code) + ':' + str(success) + ':' + exit_code
                                failure_services.append(alert_service)
                        else:
                            alert_service = alert_service + ':' + message + ':' + str(http_code) + ':' + str(success) + ':' + exit_code
                            failure_services.append(alert_service)

                if success_failure == True:
                    success_hosts.append(hostname)
                    if denaliVariables['nocolors'] == True:
                        success_failure = "SUCCESSFUL"
                    else:
                        success_failure = colors.bold + colors.fg.lightgreen + 'SUCCESSFUL' + colors.reset
                elif success_failure.startswith('PARTIAL:'):
                    # PARTIAL is known only when monitoring validate is operational
                    failure_hosts.append(hostname)
                    partial_count += 1
                    # retrieve list of services that did not update as expected
                    failed_services = success_failure.split(':')[-1]
                    if len(failed_services) == 0:
                        failed_services = 'Unknown service list'

                    if denaliVariables['nocolors'] == True:
                        success_failure = 'PARTIALLY SUCCESSFUL : %s' % failed_services
                    else:
                        success_failure  = colors.bold + colors.fg.lightred  + 'PARTIALLY SUCCESSFUL ' + colors.reset + ': '
                        success_failure += colors.bold + colors.fg.lightcyan + '%s' % failed_services + colors.reset
                elif success_failure == 'REVIEW':
                    # REVIEW is known only when monitoring validate is operational
                    failure_hosts.append(hostname)
                    review_count += 1
                    if denaliVariables['nocolors'] == True:
                        success_failure = 'REVIEW MONITORING'
                    else:
                        success_failure = colors.bold + colors.fg.cyan + 'REVIEW MONITORING' + colors.reset
                else:
                    failure_hosts.append(hostname)
                    if denaliVariables['nocolors'] == True:
                        success_failure = "FAILURE"
                    else:
                        success_failure = colors.bold + colors.fg.red + 'FAILURE' + colors.reset

            # for a single check, put it on the same line as the hostname -- cleaner look
            if len(response['data']['response'][hostname]['alert_services']) == 1 and 'passive' in monitoring_data['commands']:
                print "  %s  %s" % (hostname.ljust(max_hostname_length), success_failure),
            else:
                print "  %s  %s" % (hostname.ljust(max_hostname_length), success_failure)

            if len(failure_services) > 0:
                printHostCheckData(denaliVariables, failure_services, alert_service_max_size, alert_result)

    if partial_count > 0:
        print "PARTIALLY SUCCESSFUL entities list service changes that failed to successfully apply"
    if review_count > 0:
        print "REVIEW entities need a monitoring review by an administrator"

    return (success_hosts, failure_hosts)



##############################################################################
#
# printDowntimeOutput(denaliVariables, response, monitoring_data, delete=False)
#

def printDowntimeOutput(denaliVariables, response, monitoring_data, delete=False):

    # [3] is the location in the array where the payload is located
    service_list = monitoring_data['monapi_data'][PAYLOAD_LOCATION]['service_list']

    for hostname in response['data']['response'].keys():
        if len(service_list) == 0:
            continue
        else:
            if service_list[0]:# == '*':
                if delete == False:
                    print "Downtime request sent for all services"
                else:
                    print "Downtime removal request sent for all services"
            else:
                if delete == False:
                    message = "Downtime request re-sent for service(s): "
                    message_strings = arrangeAlertServicesForPrinting(denaliVariables, service_list, message)
                else:
                    message = "Downtime removal request re-sent for service(s): "
                    message_strings = arrangeAlertServicesForPrinting(denaliVariables, service_list, message)
            break

    else:
        print "Monitoring is NOT CONFIGURED on all devices.  No action taken."
        print
        return False

    (success_hosts, failure_hosts) = hostPrintOutput(denaliVariables, monitoring_data, response)

    return (success_hosts, failure_hosts)



##############################################################################
#
# printHostCheckData(denaliVariables, host_list, alert_service_max_size, alert_list=[])
#

def printHostCheckData(denaliVariables, host_list, alert_service_max_size, alert_list=[]):

    for (index, fail_host) in enumerate(host_list):
        fail_host       = fail_host.split(':')
        check_name      = fail_host[0]      # name of the check
        check_message   = fail_host[1]      # says: "Result submitted" with non-passive run
        check_http_code = fail_host[2]      # typically is '200'
        check_success   = fail_host[3]      # typically is 'true'
        exit_code       = fail_host[4]      # ok, critical, warning, unknown

        if exit_code.strip() == 'OK':
            print "      %s     OK" % check_name.ljust(alert_service_max_size)
        else:
            print "      %s     %s   %s" % (check_name.ljust(alert_service_max_size),
                                            exit_code.ljust(8),
                                            alert_list[index].strip())

    return



##############################################################################
#
# arrangeAlertServicesForPrinting(denaliVariables, service_list, alert_message)
#
#   This function attempts to put some order in the output printing of a list
#   of alert services.  There are some commands where this list can span two
#   lines, and it looks ugly.  This code makes the output look a little cleaner
#   by breaking up lines into segments that are <as_max_char_count = 80> long.
#   Then, because any leading message is also sent in, it just prints the result
#   to the screen.

def arrangeAlertServicesForPrinting(denaliVariables, service_list, alert_message):

    string_buffer  = len(alert_message)
    all_strings    = []
    message_string = ''

    for alert_service in service_list:
        if len(message_string) == 0:
            message_string = alert_service
        else:
            if len(message_string) > as_max_char_count:
                all_strings.append(message_string + ',')
                message_string = alert_service
            else:
                message_string += ', ' + alert_service

    # get the last one
    all_strings.append(message_string)

    # put the alert_message at the front of the first string
    # and then buffer the rest
    for (index, message) in enumerate(all_strings):
        if index == 0:
            all_strings[index] = alert_message + all_strings[index]
        else:
            all_strings[index] = (' ' * string_buffer) + all_strings[index]

    for message in all_strings:
        print message

    return



##############################################################################
#
# printCheckNotifyUpdate(denaliVariables, response, monitoring_data)
#

def printCheckNotifyUpdate(denaliVariables, response, monitoring_data):

    # All hosts entered are submitted at the same time with the same command(s).
    # This means that what happens to one, happens to all.  So printing what was
    # requested at the top by investigating the first host is valid.
    if 'enable' in monitoring_data['commands']:
        check_action = 'Enable'
    elif 'disable' in monitoring_data['commands']:
        check_action = 'Disable'
    else:
        check_action = 'Unknown'

    # [3] is the location in the array where the payload is located
    service_list = monitoring_data['monapi_data'][PAYLOAD_LOCATION]['service_list']

    for hostname in response['data']['response'].keys():
        if len(service_list) == 0:
            continue
        else:
            if service_list[0] == '*':
                if 'checks' in monitoring_data['commands']:
                    print "%s checks request sent for all services"        % check_action
                if 'notify' in monitoring_data['commands']:
                    print "%s notifications request sent for all services" % check_action
            else:
                if 'checks' in monitoring_data['commands']:
                    message = "%s checks request sent for service(s)       : " % check_action
                    message_strings = arrangeAlertServicesForPrinting(denaliVariables, service_list, message)
                if 'notify' in monitoring_data['commands']:
                    message = "%s notifications request sent for service(s): " % check_action
                    message_strings = arrangeAlertServicesForPrinting(denaliVariables, service_list, message)
            break
    else:
        print "Monitoring is NOT CONFIGURED on all devices.  No action taken."
        print
        return

    (success_hosts, failure_hosts) = hostPrintOutput(denaliVariables, monitoring_data, response)

    return (success_hosts, failure_hosts)



##############################################################################
#
# printAckOutput(denaliVariables, response, monitoring_data, delete=False)
#

def printAckOutput(denaliVariables, response, monitoring_data, delete=False):

    service_list = monitoring_data['monapi_data'][PAYLOAD_LOCATION]['service_list']
    if delete == True:
        ack_action = 'delete '
    else:
        ack_action = ''

    for hostname in response['data']['response'].keys():
        if len(service_list) == 0:
            continue
        else:
            if service_list[0] == '*':
                print "Ack %saction was requested for all services" % ack_action
            else:
                message = "Ack %saction was requested for services(s): " % ack_action
                message_strings = arrangeAlertServicesForPrinting(denaliVariables, service_list, message)
            break
    else:
        print "Monitoring is NOT CONFIGURED on all devices.  No action taken."
        print
        return

    (success_hosts, failure_hosts) = hostPrintOutput(denaliVariables, monitoring_data, response)

    return (success_hosts, failure_hosts)



##############################################################################
#
# printPassiveOutput(denaliVariables, response, monitoring_data)
#

def printPassiveOutput(denaliVariables, response, monitoring_data):

    service_list = monitoring_data['monapi_data'][PAYLOAD_LOCATION]['service_list']

    for hostname in response['data']['response'].keys():
        if len(service_list) == 0:
            continue
        else:
            # SRE team requested this be enabled by default
            denaliVariables['mon_details'] = True
            if service_list[0] == '*':
                if 'submit' in monitoring_data['commands']:
                    print "Passive check/run [RESULTS SUBMITTED] was requested for all services"
                else:
                    print "Passive check/run [NO SUBMISSION] was requested for all services"
            else:
                if 'submit' in monitoring_data['commands']:
                    message = "Passive check/run [RESULTS SUBMITTED] was requested for service(s): "
                    message_strings = arrangeAlertServicesForPrinting(denaliVariables, service_list, message)
                else:
                    message = "Passive check/run [NO SUBMISSION] was requested for service(s): "
                    message_strings = arrangeAlertServicesForPrinting(denaliVariables, service_list, message)
            break
    else:
        print "Monitoring is NOT CONFIGURED on all devices.  No action taken."
        print
        return

    (success_hosts, failure_hosts) = hostPrintOutput(denaliVariables, monitoring_data, response)

    return (success_hosts, failure_hosts)



##############################################################################
#
# printIndividualSummaryMember(denaliVariables, key, COLOR, printString)
#

def printIndividualSummaryMember(denaliVariables, key, COLOR, printString):

    separator = denaliVariables['mon_output']
    if separator == 'comma':
        separator = ','
    elif separator == 'space':
        separator = ' '

    count = 0

    if key in denaliVariables['monitoring_summary']:
        count = len(denaliVariables['monitoring_summary'][key])

        # sort the list
        denaliVariables['monitoring_summary'][key].sort()

        if denaliVariables["nocolors"] == False:
            print colors.bold + COLOR + "%s [%d]:" % (printString, count) + colors.reset
        else:
            print "%s [%d]:" % (printString, count)

        print "%s" % separator.join(denaliVariables['monitoring_summary'][key])
        print

    return count



##############################################################################
#
# printMonitoringSummary(denaliVariables)
#

def printMonitoringSummary(denaliVariables):

    print_dict = [
                    {'ok'              : '  OK Hosts                     : '},
                    {'critical'        : '  Critical Hosts               : '},
                    {'warning'         : '  Warning Hosts                : '},
                    {'unknown'         : '  Unknown Hosts                : '},
                    {'not_found'       : '  Not Found Hosts              : '},
                    {'acknowledge'     : '  Ack\'d Hosts                  : '},
                    {'checks_disabled' : '  Checks Disabled Hosts        : '},
                    {'notify_disabled' : '  Notifications Disabled Hosts : '},
                 ]

    OK          = getattr(colors.fg, denaliVariables['mon_ok'])
    CRITICAL    = getattr(colors.fg, denaliVariables['mon_critical'])
    WARNING     = getattr(colors.fg, denaliVariables['mon_warning'])
    UNKNOWN     = getattr(colors.fg, denaliVariables['mon_unknown'])
    NOTFOUND    = getattr(colors.fg, denaliVariables['mon_notfound'])
    CHECKS      = colors.fg.cyan
    total_count = 0

    print
    total_count += printIndividualSummaryMember(denaliVariables, 'critical',        CRITICAL, "Critical Hosts")
    total_count += printIndividualSummaryMember(denaliVariables, 'warning',         WARNING,  "Warning Hosts")
    total_count += printIndividualSummaryMember(denaliVariables, 'unknown',         UNKNOWN,  "Unknown Hosts")
    total_count += printIndividualSummaryMember(denaliVariables, 'ok',              OK,       "OK Hosts")
    total_count += printIndividualSummaryMember(denaliVariables, 'not_found',       NOTFOUND, "Configuration Not Found Hosts")
    printIndividualSummaryMember(denaliVariables, 'acknowledge',     CHECKS,   "Host(s) with acknowledged alerts")
    printIndividualSummaryMember(denaliVariables, 'checks_disabled', CHECKS,   "Host(s) with checks disabled")
    printIndividualSummaryMember(denaliVariables, 'notify_disabled', CHECKS,   "Host(s) with notifications disabled")

    print "Total Hosts returned           : %d" % total_count

    for category_dict in print_dict:
        category_key = category_dict.keys()[0]
        if category_key in denaliVariables['monitoring_summary']:
            print category_dict.values()[0] + "%d" % len(denaliVariables['monitoring_summary'][category_key])
    denali_utility.printOverallTimeToRun(denaliVariables)


##############################################################################
#
# printMonitoringDetails(denaliVariables, monitoring_data)
#

def printMonitoringDetails(denaliVariables, monitoring_data):

    OK       = getattr(colors.fg, denaliVariables['mon_ok'])
    CRITICAL = getattr(colors.fg, denaliVariables['mon_critical'])
    WARNING  = getattr(colors.fg, denaliVariables['mon_warning'])
    UNKNOWN  = getattr(colors.fg, denaliVariables['mon_unknown'])
    NOTFOUND = getattr(colors.fg, denaliVariables['mon_notfound'])

    search_term_found = False

    alert_service_list = denaliVariables['monitoring_cat'].keys()
    alert_service_list.sort()

    separator = denaliVariables['mon_output']
    if separator == 'comma':
        separator = ','
    elif separator == 'space':
        separator = ' '

    monitoring_searches = monitoring_data['search_extras']
    mon_search_length   = len(monitoring_searches)
    for alert_service in alert_service_list:

        # account for a summary search -- if a search term is entered
        if mon_search_length > 0 and alert_service not in monitoring_searches:
            continue
        else:
            search_term_found = True

        if denaliVariables['nocolors'] == True:
            print "\n%s" % alert_service
        else:
            print colors.bold + colors.fg.cyan + "\n%s" % alert_service + colors.reset

        category_status_list = denaliVariables['monitoring_cat'][alert_service].keys()
        category_status_list.sort()
        for category_status in category_status_list:
            # print with (or without) colors
            category_count = len(denaliVariables['monitoring_cat'][alert_service][category_status])

            if denaliVariables['nocolors'] == True:
                print "%s [%d]:" % (category_status, category_count)
            else:
                if category_status == "OK":
                    color_output = OK
                elif category_status == "CRITICAL":
                    color_output = CRITICAL
                elif category_status == "WARNING":
                    color_output = WARNING
                elif category_status == "UNKNOWN":
                    color_output = UNKNOWN
                elif category_status == "NOTFOUND":
                    color_output = NOTFOUND
                else:
                    color_output = colors.reset

                print colors.bold + color_output + "%s [%d]:" % (category_status, category_count) + colors.reset

            entity_list = denaliVariables['monitoring_cat'][alert_service][category_status]
            entity_list.sort()
            print "  %s" % (separator.join(entity_list))

    if search_term_found == False:
        # display retrieved categories with error/syntax message
        print
        print "Denali --mondetails: Alert service search term(s) [%s] not found." % ', '.join(monitoring_searches)
        print "Available alert services for this query:\n  %s" % ', '.join(alert_service_list)
        print

    return True



##############################################################################
#
# outputDebugNagiosInformation
#
#   Note:
#   For getting the command_line that has been run, there isn't a real easy
#   way to accomplish this. The only decent way found was to make it a part
#   of the "GET /entity/{entity}/svc/{alert_svc}/run" endpoint. If you use
#   that endpoint now, it will return the command_line that was run as a part
#   of the data.
#

def outputDebugNagiosInformation(denaliVariables, response, monitoring_data):

    column_1_width  = 32
    separator_color = colors.fg.red

    print

    hostname = response['data']['response'].keys()[0]
    check_to_query_for = monitoring_data['search_extras'][0]
    if check_to_query_for in response['data']['response'][hostname]['alert_services'].keys():
        check_list = response['data']['response'][hostname]['alert_services'][check_to_query_for]['data'].keys()
        check_list.sort()
        check_data = response['data']['response'][hostname]['alert_services'][check_to_query_for]['data']
    else:
        return False

    if denaliVariables['nocolors'] == True:
        print " Nagios Variable Name".ljust(column_1_width) + " |  Data Value (from MonApi)"
        print ((column_1_width + 1) * '=') + '|' + (68 * '=')
        for check in check_list:
            if isinstance(check_data[check], list) == True:
                print " %s|  %s" % (check.ljust(column_1_width), ', '.join(check_data[check]))
            else:
                print " %s|  %s" % (check.ljust(column_1_width), check_data[check])
    else:
        print " Nagios Variable Name".ljust(column_1_width) + separator_color + " |" + colors.reset + "  Data Value (from MonApi)"
        print separator_color + ((column_1_width + 1) * '=') + '|' + (68 * '=') + colors.reset
        for check in check_list:
            if isinstance(check_data[check], list) == True:
                print " %s" % check.ljust(column_1_width) + separator_color + '|' + colors.reset + "  %s" % ', '.join(check_data[check])
            else:
                print " %s" % check.ljust(column_1_width) + separator_color + '|' + colors.reset + "  %s" % check_data[check]

    return True



##############################################################################
#
# determineMonitoringDebugData(denaliVariables, response, monitoring_data)
#
#   This function is engaged when 'summary' or 'details' is in the command
#   list _and_ 'debug' as well.  It is meant as the gatekeeper to running
#   a webscrape from a nagios server.
#
#   Qualifications to get through:
#     (1) Single server
#     (2) Single search item (for an alert service)
#
#   If these are met, then the scraper code is executed, with the hostname
#   passed in, along with the search item submitted.
#

def determineMonitoringDebugData(denaliVariables, response, monitoring_data):

    web_scrape = True
    success    = True

    # only search on one host
    if len(denaliVariables['serverList']) > 1:
        print
        print "Denali syntax error: Only one host allowed for 'debug' nagios output."
        success = False

    # only search on one alert service
    if len(monitoring_data['search_extras']) > 1:
        if success == True:
            print
        print "Denali syntax error: Only one alert service allowed for 'debug' nagios output."
        success = False

    # only search if there is an alert service specified
    if len(monitoring_data['search_extras']) == 0:
        if success == True:
            print
        print "Denali syntax error: No alert service was specified for 'debug' nagios output."
        success = False

    if success == False:
        return False

    if web_scrape == True:
        ccode = webScrapePage(denaliVariables,
                              denaliVariables['serverList'][0],
                              monitoring_data['search_extras'][0])
        if ccode == False:
            return False

    # new method exposing some of the same details
    ccode = outputDebugNagiosInformation(denaliVariables, response, monitoring_data)
    if ccode == False:
        return False

    return True



##############################################################################
#
# generateHistoryUpdateString(denaliVariables, monitoring_data, action_type, delete=False)
#

def generateHistoryUpdateString(denaliVariables, monitoring_data, action_type, delete=False):

    ENTITY_DATA        = 3
    update_string      = ''
    MAX_MESSAGE_LENGTH = 100

    # get the current user
    if len(denaliVariables["userName"]) == 0:
        username = getpass.getuser()
    else:
        username = denaliVariables["userName"]

    if len(username) == 0:
        username = 'Denali_API'

    # get the services being updated
    for (data_index, data_item) in enumerate(monitoring_data['monapi_data']):
        if isinstance(data_item, dict) == True:
            ENTITY_DATA = data_index
    services = monitoring_data['monapi_data'][ENTITY_DATA]['service_list']
    if services[0] == '*':
        services = 'ALL Services'
    else:
        if len(services) > 4:
            services = "[%d Services]" % len(services)
        else:
            services = "[%s]" % ','.join(services)

    if action_type == 'ack':
        if delete == True:
            update_string = "%s:ACK delete for service(s): %s" % (username, services)
        else:
            message       = monitoring_data['monapi_data'][ENTITY_DATA]['comment']
            update_string = "%s:\"%s\" for service(s): %s" % (username, message, services)

    elif action_type == 'downtime':
        if delete == True:
            update_string = "%s:Remove downtime event for %s" % (username, services)
        else:
            message       = monitoring_data['monapi_data'][ENTITY_DATA]['comment']
            duration_time = monitoring_data['monapi_data'][ENTITY_DATA]['duration']
            start_time    = monitoring_data['monapi_data'][ENTITY_DATA]['start_time']
            start_time    = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))

            # translate seconds into d:h:m:s
            minutes, seconds = divmod(duration_time, 60)
            hours,   minutes = divmod(minutes, 60)
            days,    hours   = divmod(hours, 24)
            duration_time    = ''
            if days > 0:
                duration_time += "%dd" % days
            if hours > 0:
                if len(duration_time) > 0:
                    duration_time += ':'
                duration_time += "%dh" % hours
            if minutes > 0:
                if len(duration_time) > 0:
                    duration_time += ':'
                duration_time += "%dm" % minutes
            if seconds > 0:
                if len(duration_time) > 0:
                    duration_time += ':'
                duration_time += "%ds" % seconds

            update_string = "%s:DOWNTIME event \"%s\" for %s starting [%s] duration [%s]" % (username, message, services, start_time, duration_time)

    elif action_type == 'enable' or action_type == 'disable':
        check_note = ''
        if 'checks' in monitoring_data['commands']:
            check_note += 'checks'
        if 'notify' in monitoring_data['commands']:
            if len(check_note) > 0:
                check_note += '/notifications'
            else:
                check_note = 'notifications'
        update_string = "%s:%s %s for %s" % (username, action_type.upper(), check_note, services)

        # MRASEREQ-41492: Add customized message to enable/disable requests (if present)
        message = monitoring_data['monapi_data'][ENTITY_DATA].get('comment', '')
        message_length = len(message)
        if message_length > 0:
            if message_length > MAX_MESSAGE_LENGTH:
                print "Denali Syntax Error: Enable/Disable message length must be <= %d characters.  Message of %d characters ignored." % (MAX_MESSAGE_LENGTH, message_length)
            else:
                update_string += ". %s" % message

    return update_string



##############################################################################
#
# outputMonitoringData(denaliVariables, response, monitoring_data)
#

def outputMonitoringData(denaliVariables, response, monitoring_data):

    failure_hosts = []

    # For history update(s), do them in a single batch instead of one by one
    denaliVariables['singleUpdate'] = True

    if denaliVariables["monitoring_debug"] == True or denaliVariables["debugLog"] == True:
        outputString = "\n++outputMonitoringData++"
        denali_utility.debugOutput(denaliVariables, outputString)
        outputString = "monitoring_data = %s" % monitoring_data
        denali_utility.debugOutput(denaliVariables, outputString)

    if "summary" in monitoring_data['commands'] or "details" in monitoring_data['commands'] or "simple" in monitoring_data['commands']:
        response_orig = copy.deepcopy(response)
        ccode = printServicesData(denaliVariables, response, monitoring_data)
        if "debug" in monitoring_data['commands']:
            determineMonitoringDebugData(denaliVariables, response_orig, monitoring_data)

    elif "ack" in monitoring_data['commands']:
        if "delete" in monitoring_data['commands']:
            (success_hosts, failure_hosts) = printAckOutput(denaliVariables, response, monitoring_data, delete=True)
            if len(success_hosts) == 0:
                return False
            denaliVariables['serverList'] = success_hosts
            updateString = generateHistoryUpdateString(denaliVariables, monitoring_data, 'ack', delete=True)
            ccode = denali_history.addHistoryToHostList(denaliVariables, updateString, print_result=False)
        else:
            (success_hosts, failure_hosts) = printAckOutput(denaliVariables, response, monitoring_data)
            if len(success_hosts) == 0:
                return False
            denaliVariables['serverList'] = success_hosts
            updateString = generateHistoryUpdateString(denaliVariables, monitoring_data, 'ack')
            ccode = denali_history.addHistoryToHostList(denaliVariables, updateString, print_result=False)

    elif "downtime" in monitoring_data['commands']:
        if "delete" in monitoring_data['commands']:
            (success_hosts, failure_hosts) = printDowntimeOutput(denaliVariables, response, monitoring_data, delete=True)
            if len(success_hosts) == 0:
                return False
            denaliVariables['serverList'] = success_hosts
            updateString = generateHistoryUpdateString(denaliVariables, monitoring_data, 'downtime', delete=True)
            ccode = denali_history.addHistoryToHostList(denaliVariables, updateString, print_result=False)
        else:
            (success_hosts, failure_hosts) = printDowntimeOutput(denaliVariables, response, monitoring_data)
            if len(success_hosts) == 0:
                return False
            denaliVariables['serverList'] = success_hosts
            updateString = generateHistoryUpdateString(denaliVariables, monitoring_data, 'downtime')
            ccode = denali_history.addHistoryToHostList(denaliVariables, updateString, print_result=False)

    elif "enable" in monitoring_data['commands'] or "disable" in monitoring_data['commands']:
        (success_hosts, failure_hosts) = printCheckNotifyUpdate(denaliVariables, response, monitoring_data)
        if len(success_hosts) == 0:
            return False
        denaliVariables['serverList'] = success_hosts
        if "enable" in monitoring_data['commands']:
            updateString = generateHistoryUpdateString(denaliVariables, monitoring_data, 'enable')
            ccode = denali_history.addHistoryToHostList(denaliVariables, updateString, print_result=False)
        else:
            updateString = generateHistoryUpdateString(denaliVariables, monitoring_data, 'disable')
            ccode = denali_history.addHistoryToHostList(denaliVariables, updateString, print_result=False)

    elif "passive" in monitoring_data['commands']:
        success_hosts = printPassiveOutput(denaliVariables, response, monitoring_data)
        if len(success_hosts) == 0:
            return False

    if len(failure_hosts) > 0:
        return False
    else:
        return True



##############################################################################
#
# errorCheckSubmittedCommands(denaliVariables, monitoring_dictionary)
#

def errorCheckSubmittedCommands(denaliVariables, monitoring_dictionary):

    if 'delete' in monitoring_dictionary['commands']:
        if (len(monitoring_dictionary['commands']) > 2 or
           ('downtime' not in monitoring_dictionary['commands'] and 'ack' not in monitoring_dictionary['commands'])):
            # Syntax error
            print "Denali Syntax Error :  'delete' requires either the 'downtime' or 'ack' command.  Session halted."
            print "  Commands submitted:  %s" % monitoring_dictionary['commands']
            return False
        else:
            # Command(s) accepted
            if denaliVariables['monitoring_debug'] == True or denaliVariables['debugLog'] == True:
                outputString = "ACCEPTED :  Found 'downtime' or 'ack' with 'delete' in command data"
                denali_utility.debugOutput(denaliVariables, outputString)

    elif 'disable' in monitoring_dictionary['commands'] or 'enable' in monitoring_dictionary['commands']:
        command_length = len(monitoring_dictionary['commands'])

        # check for both -- error out
        if 'disable' in monitoring_dictionary['commands'] and 'enable' in monitoring_dictionary['commands']:
            # Syntax error
            print "Denali Syntax Error :  'enable' and 'disable' commands cannot be used together."
            print "  Commands submitted:  %s" % monitoring_dictionary['commands']
            return False

        total = 1

        if 'checks' in monitoring_dictionary['commands']:
            total += 1
        if 'notify' in monitoring_dictionary['commands']:
            total += 1

        if command_length > total:
            # Syntax error
            print "Denali Syntax Error :  'enable' or 'disable' with 'checks' and/or 'notify' cannot process extra commands."
            print "  Commands submitted:  %s" % monitoring_dictionary['commands']
            return False
        else:
            if denaliVariables['monitoring_debug'] == True or denaliVariables['debugLog'] == True:
                outputString = "ACCEPTED :  Found proper enable/disable syntax"
                denali_utility.debugOutput(denaliVariables, outputString)

    elif 'passive' in monitoring_dictionary['commands']:
        if len(monitoring_dictionary['commands']) == 1:
            pass
        elif 'submit' in monitoring_dictionary['commands'] and len(monitoring_dictionary['commands']) <= 2:
            if denaliVariables['monitoring_debug'] == True or denaliVariables['debugLog'] == True:
                outputString = "ACCEPTED :  Found proper passive [submit] syntax"
                denali_utility.debugOutput(denaliVariables, outputString)
        else:
            print "Denali Syntax Error :  'passive' may only be used with 'submit', no other commands are allowed."
            print "  Commands submitted:  %s" % monitoring_dictionary['commands']
            return False

    elif 'all' in monitoring_dictionary['commands'] and len(monitoring_dictionary['commands']) == 1:
        monitoring_dictionary['commands'].append('details')

    elif 'debug' in monitoring_dictionary['commands']:
        # have any 'debug' nagios request show the summary data by default
        mon_commands = ['details', 'summary', 'simple']
        if ('details' not in monitoring_dictionary['commands'] and
            'summary' not in monitoring_dictionary['commands'] and
            'simple'  not in monitoring_dictionary['commands']):
            monitoring_dictionary['commands'].insert(0,'summary')
            denaliVariables['monitoring_default'] = 'summary'

    elif 'mismatch' in monitoring_dictionary['commands']:
        if len(monitoring_dictionary['commands']) == 1:
            monitoring_dictionary['commands'].insert(0, 'summary')
        else:
            if (len(monitoring_dictionary['commands']) == 2 and ('summary' in monitoring_dictionary['commands'] or
                                                                 'details' in monitoring_dictionary['commands'])):
                pass
            else:
                print "Denali Syntax Error :  'mismatch' may only be used with 'summary' or 'details', no other commands are allowed."
                print "  Commands submitted:  %s" % monitoring_dictionary['commands']
                return False

    elif 'details' in monitoring_dictionary['commands']:
        if len(monitoring_dictionary['commands']) == 1:
            pass
        elif 'all' in monitoring_dictionary['commands'] and len(monitoring_dictionary['commands']) <= 2:
            if denaliVariables['monitoring_debug'] == True or denaliVariables['debugLog'] == True:
                outputString = "ACCEPTED :  Found proper details [all] syntax"
                denali_utility.debugOutput(denaliVariables, outputString)

        else:
            print "Denali Syntax Error :  'details' may only be used with 'all', no other commands are allowed."
            print "  Commands submitted:  %s" % monitoring_dictionary['commands']
            return False

    elif len(monitoring_dictionary['commands']) > 1:
        # Syntax error
        print "Denali Syntax Error :  Only one command may be processed at a time.  Session halted."
        print "  Commands submitted:  %s" % monitoring_dictionary['commands']
        return False

    else:
        if denaliVariables['monitoring_debug'] == True or denaliVariables['debugLog'] == True:
            outputString = "ACCEPTED"
            denali_utility.debugOutput(denaliVariables, outputString)

    # determine the command and check if the necessary parameters are included
    if 'downtime' in monitoring_dictionary['commands']:
        if len(monitoring_dictionary['search_extras']) < 2 and 'delete' not in monitoring_dictionary['commands']:
            # no comment submitted
            print "Denali Syntax Error:  Downtime maintenance requires a comment and length of time.  Session halted."
            print "            Example:  denali ... --mon downtime 'scheduled maintenance on host per demouser' d:1h"
            return False
        elif len(monitoring_dictionary['search_extras']) > 3 and 'delete' not in monitoring_dictionary['commands']:
            # 3 is the max length -- (1) comment, (2) start time, (3) duration
            print "Denali Syntax Error :  Downtime maintenance has a maximum of 3 parameters.  Session halted."
            print "  Commands submitted:  %s" % monitoring_dictionary['search_extras']
            return False

    elif 'ack' in monitoring_dictionary['commands']:
        pass

    return True



##############################################################################
#
# separateMonitoringCallParms(denaliVariables, monitoring_data)
#
#   Example dictionary returned:
#       monitoring_dictionary = {'commands': ['details', 'delete'],
#                                'search'  : ['CRITICAL', 'OK']}
#
#   For this example, two commands were entered after "--mon", and two
#   search criteria were entered.
#

def separateMonitoringCallParms(denaliVariables, monitoring_data):

    if denaliVariables["monitoring_debug"] == True or denaliVariables["debugLog"] == True:
        outputString = "\n++separateMonitoringCallParms++"
        denali_utility.debugOutput(denaliVariables, outputString)
        outputString = "monitoring_data = %s" % monitoring_data
        denali_utility.debugOutput(denaliVariables, outputString)


    monitoring_dictionary = {'commands' : [], 'search_extras' : []}

    # search terms for monitoring checks
    search_terms    =   {
                            'c'             : 'CRITICAL',
                            'crit'          : 'CRITICAL',
                            'w'             : 'WARNING',
                            'warn'          : 'WARNING',
                            'u'             : 'UNKNOWN',
                            'unk'           : 'UNKNOWN',
                            'o'             : 'OK',
                            'ok'            : 'OK',
                            '+'             : '+',
                            'cu'            : 'cu',
                            'uc'            : 'cu',
                            'wu'            : 'wu',
                            'uw'            : 'uw',
                            'cw'            : 'cw',
                            'wc'            : 'cw',
                            'cwu'           : 'cwu',
                            'wcu'           : 'cwu',
                            'cuw'           : 'cwu',
                            'ucw'           : 'cwu',
                            'uwc'           : 'cwu',
                        }

    # commands for monitoring queries/manipulation
    monitoring_commands = {
                            # acknowledge command
                            'ack'           : 'ack',

                            # maintenance/downtime command
                            'down'          : 'downtime',
                            'downtime'      : 'downtime',
                            'maint'         : 'downtime',
                            'maintenance'   : 'downtime',

                            # enable/disable checks/nofitications
                            'check'         : 'checks',
                            'checks'        : 'checks',
                            'disable'       : 'disable',
                            'enable'        : 'enable',
                            'notify'        : 'notify',
                            'notification'  : 'notify',
                            'notifications' : 'notify',

                            # ack/maintenance delete command
                            'delete'        : 'delete',

                            # query commands
                            'all'           : 'all',
                            'cn'            : 'mismatch',
                            'debug'         : 'debug',
                            'detail'        : 'details',
                            'details'       : 'details',
                            'mismatch'      : 'mismatch',
                            'simple'        : 'simple',
                            'summary'       : 'summary',

                            # passive check execution
                            'passive'       : 'passive',
                            'run'           : 'passive',
                            'save'          : 'submit',
                            'submit'        : 'submit',

                            #
                            'service'       : 'service',
                            'services'      : 'service',

                          }

    monitoring_data = monitoring_data.split(',')
    if monitoring_data[0] == 'Waiting':
        # only the default command needed -- nothing behind --mon
        #monitoring_dictionary['command']       = denaliVariables['monitoring_default']
        monitoring_dictionary['search_extras'] = []
    else:
        for term in monitoring_data:
            if term.lower() in monitoring_commands:
                monitoring_dictionary['commands'].append(monitoring_commands[term.lower()])
            elif term.lower() in search_terms:
                if term.lower() == 'cw' or term.lower() == 'wc':
                    monitoring_dictionary['search_extras'].extend(['CRITICAL', 'WARNING'])
                elif (term.lower() == 'cwu' or term.lower() == 'cuw' or
                      term.lower() == 'wcu' or term.lower() == 'wuc' or
                      term.lower() == 'ucw' or term.lower() == 'uwc'):
                    monitoring_dictionary['search_extras'].extend(['CRITICAL', 'WARNING', 'UNKNOWN'])
                elif term.lower() == 'cu' or term.lower() == 'uc':
                    monitoring_dictionary['search_extras'].extend(['CRITICAL', 'UNKNOWN'])
                elif term.lower() == 'wu' or term.lower() == 'uw':
                    monitoring_dictionary['search_extras'].extend(['WARNING', 'UNKNOWN'])
                else:
                    monitoring_dictionary['search_extras'].append(search_terms[term.lower()])
            else:
                # add any other search term from the user -- where any column
                # can be searched
                monitoring_dictionary['search_extras'].append(term)

    #
    # Error checking for command(s) submitted
    #
    if denaliVariables['monitoring_debug'] == True or denaliVariables['debugLog'] == True:
        outputString = "monitoring_dictionary = %s\n" % monitoring_dictionary
        denali_utility.debugOutput(denaliVariables, outputString)

    ccode = errorCheckSubmittedCommands(denaliVariables, monitoring_dictionary)
    if ccode == False:
        return False

    if len(monitoring_dictionary['commands']) == 0:
        # no command was specified -- put in the default
        monitoring_dictionary['commands'] = denaliVariables['monitoring_default']
    else:
        detail_list = [ 'details', 'simple', 'summary' ]
        if monitoring_dictionary['commands'][0] in detail_list:
            denaliVariables['monitoring_default'] = monitoring_dictionary['commands'][0]

    if 'summary' in monitoring_dictionary['commands'] and len(monitoring_dictionary['search_extras']) > 0:
        # if the summary is included -- the search criteria does not work
        # just delete it
        #print "Denali: Criteria search on summary display does not work, use '--mon details <search_criteria>'"
        #print
        #monitoring_dictionary['search_extras'] = ''
        pass

    return monitoring_dictionary



##############################################################################
#
# dataCenterRequired(denaliVariables, monitoring_data)
#

def dataCenterRequired(denaliVariables, monitoring_data):

    domain_extensions = ['.com', '.net', '.org']
    data_center       = denaliVariables['dataCenter']
    hostname_list     = denaliVariables['serverList']
    entity_list       = []

    for host in hostname_list:
        if host.find('.omniture.com') == -1 and host.find('.adobe.net') == -1:
            if host[-4:] in domain_extensions:
                if len(data_center) == 0:
                    entity_list.append(host)

    return entity_list



##############################################################################
#
# printDataCenterRequiredMessage(denaliVariables, entity_list)
#

def printDataCenterRequiredMessage(denaliVariables, entity_list):

    print "Devices/entities entered that require a data center location (use --dc=<location>)"

    for entity in entity_list:
        print " %s" % entity,

    exit(1)



##############################################################################
#
# pullMessageFromData(denaliVariables, monitoring_parms)
#
#   MRASEREQ-41492:
#   This function pulls out a customized message for enabling/disabling alerts.
#

def pullMessageFromData(denaliVariables, monitoring_parms):

    message = ''

    # Pull out any text that has a colon for the 2nd character and assign it as
    # the message.  If the user submits multiple messages, then only the last will
    # be used (why would anyone do that?)
    for index, parameter in enumerate(monitoring_parms):
        if parameter[1] == (':') and len(parameter) > 2:
            message = monitoring_parms.pop(index)[2:]

    # If removing the message(s) leaves an empty List, it means that no individual
    # services were targeted; rather, ALL SERVICES were targeted.  Add an asterisk
    # to the List to indicate this reality.  The asterisk typically exists when no
    # services are specifically targeted; however, because of the message being
    # submitted, the code could not tell (initially) whether the message was a SERVICE
    # or a message.  It assumed a service, and therefore, no asterisk was included.
    # Hopefully the next time I read this it is more clear.
    if len(monitoring_parms) == 0:
        monitoring_parms.append('*')

    return message



##############################################################################
#
# extractDowntimeParameters(denaliVariables, monitoring_data['search_extras'])
#
#   This function analyzes the parameters submitted and determines which one
#   is the comment (a string), and which one is a time parameter (returned
#   in minutes, but potentially submitted in days/hours/minutes)
#
#   The comment and duration are required.  A start time is optional and will
#   be assumed to be the current time if it doesn't exist.
#

def extractDowntimeParameters(denaliVariables, monitoring_parms):

    downtime_parameters = ['','','']

    days_to_minutes  = 0
    hours_to_minutes = 0
    minutes          = 0

    # separate parameters
    for parameter in monitoring_parms:
        if parameter.startswith('s:'):
            # start time
            start_time = convertFromDateTimeToEpoch(parameter.split(':',1)[1])
            if start_time == False:
                return False
            downtime_parameters[2] = start_time

        elif parameter.startswith('d:'):
            # time duration
            duration = parameter.split(':')[1]

            # change into minutes
            # days?
            days_find    = duration.find('d')
            hours_find   = duration.find('h')
            minutes_find = duration.find('m')

            if days_find == -1 and hours_find == -1 and minutes_find == -1:
                print "Denali Syntax error:  Time duration format is [days]d[hours]h[minutes]m; i.e., 'd:1d2h45m' or 'd:30m'"
                print "     Time submitted:  d:%s" % duration
                return False

            if days_find != -1:
                days = duration.split('d')
                duration = ''.join(days[1:])
                days_to_minutes = int(days[0]) * 1440

            if hours_find != -1:
                hours = duration.split('h')
                duration = ''.join(hours[1:])
                hours_to_minutes = int(hours[0]) * 60

            if minutes_find != -1:
                minutes = int(duration.split('m')[0])

            # output is in seconds, multiply by 60 to get minutes
            time_duration = (days_to_minutes + hours_to_minutes + minutes) * 60
            downtime_parameters[1] = time_duration

        else:
            # comment?  or start date/time parameter?
            if len(parameter) > 1 and len(parameter) < 300:
                integers = 0
                alphas   = 0
                # count alphas/integers
                for char in parameter:
                    if char.isdigit():
                        integers += 1
                    else:
                        alphas += 1

                value = float(len(parameter) - integers)/float(len(parameter)) * 100

                if denaliVariables['monitoring_debug'] == True or denaliVariables['debugLog'] == True:
                    outputString = "value = %f" % value
                    denali_utility.debugOutput(denaliVariables, outputString)
                if value > 30:
                    # likely a string comment (>30% are not digits) -- assume it is
                    downtime_parameters[0] = parameter
                    continue

                # check for a date/time string -- 4 digits at the beginning or 2 digits and a dash
                if len(parameter) > 4:
                    if parameter[0].isdigit() and parameter[1].isdigit() and parameter[2].isdigit() and parameter[3].isdigit():
                        # likely a date/time string
                        start_time = convertFromDateTimeToEpoch(parameter)
                        if start_time == False:
                            return False
                        else:
                            downtime_parameters[2] = start_time
                    if parameter[0].isdigit() and parameter[1].isdigit() and parameter[2] == '-':
                        # likely a date/time string
                        start_time = convertFromDateTimeToEpoch(parameter, pattern='%d-%m-%Y_%H:%M')
                        if start_time == False:
                            return False
                        else:
                            downtime_parameters[2] = start_time

            else:
                print "Denali: Cannot determine if this is the comment string.  The length is unusual [%d]." % len(parameter)
                return False

    if downtime_parameters[2] == '':
        downtime_parameters[2] = int(time.time())

    return downtime_parameters



##############################################################################
#
# check_notify_determination(mon_commands, enable=True)
#
#   This function sets checks/notifications correctly according to what is
#   given at the command line.  It allows just checks (or notifications, or
#   both) to be enabled or disabled on a host or with a specific alert service.
#

def check_notify_determination(mon_commands, enable=True):

    cn_add        = False
    checks_notify = []

    if enable == True:
        if 'notify' in mon_commands and 'checks' in mon_commands:
            checks = True
            notify = True
        elif 'checks' in mon_commands:
            checks = True
            notify = None
        elif 'notify' in mon_commands:
            checks = None
            notify = True
        else:
            cn_add = True
            checks = True
            notify = True

        if checks == True:
            checks_notify.append({'enable_checks':True})
        if notify == True:
            checks_notify.append({'notify':True})

    else:
        if 'notify' in mon_commands and 'checks' in mon_commands:
            checks = False
            notify = False
        elif 'checks' in mon_commands:
            checks = False
            notify = None
        elif 'notify' in mon_commands:
            checks = None
            notify = False
        else:
            cn_add = True
            checks = False
            notify = False

        if checks == False:
            checks_notify.append({'enable_checks':False})
        if notify == False:
            checks_notify.append({'notify':False})

    return (checks_notify, cn_add)



##############################################################################
#
# determineMonitoringCall(denaliVariables, monitoring_data)
#

def determineMonitoringCall(denaliVariables, monitoring_data):

    if denaliVariables["monitoring_debug"] == True or denaliVariables["debugLog"] == True:
        outputString = "\n++determineMonitoringCall++"
        denali_utility.debugOutput(denaliVariables, outputString)
        outputString = "monitoring_data = %s" % monitoring_data
        denali_utility.debugOutput(denaliVariables, outputString)

    # separate monitoring data members
    monitoring_data = separateMonitoringCallParms(denaliVariables, monitoring_data)
    if monitoring_data == False:
        return False

    # determine if a location is required
    entity_list = dataCenterRequired(denaliVariables, monitoring_data)
    if len(entity_list) > 0:
        printDataCenterRequiredMessage(denaliVariables, entity_list)
        return False

    # Fill out the basics for the monitoring payload to submit.
    # Keep this order, payload and then service_list determination
    # and keep service_list = '*' -- the query breaks without it.
    payload = {
                'entities'     : denaliVariables['serverList'],
                'service_list' : ['*']
              }

    if len(monitoring_data['search_extras']) > 0:
        service_list = monitoring_data['search_extras']
    else:
        service_list = ['*']

    #print "service_list    = %s" % service_list
    #print "monitoring_data = %s" % monitoring_data

    #
    # query host monitoring information/services
    if 'summary' in monitoring_data['commands'] or 'details' in monitoring_data['commands'] or 'simple' in monitoring_data['commands']:
        action = 'query'
        method = 'post'
        monitoring_data.update({'monapi_data' : [BULK_URL + action, method, action, payload]})

    #
    # apply or remove an 'ack'
    elif 'ack' in monitoring_data['commands']:
        action = 'ack'
        payload['service_list'] = service_list
        if 'delete' in monitoring_data['commands']:
            method = 'delete'
            monitoring_data.update({'monapi_data' : [BULK_URL + action, method, action, payload]})
        else:
            method = 'post'
            payload.update({ 'comment' : 'User [%s] acknowledged alert using Denali/MonApi v2' % denaliVariables['userName']})
            monitoring_data.update({'monapi_data' : [BULK_URL + action, method, action, payload]})

        # MRASEREQ-41295
        denaliVariables['monitoring_auth'] = True

    #
    # schedule or remove a maintenance/downtime event
    elif 'downtime' in monitoring_data['commands']:
        action = 'maint'
        payload['service_list'] = ['*']     # required for downtime actions/events
        if 'delete' in monitoring_data['commands']:
            method = 'delete'
            monitoring_data.update({'monapi_data' : [BULK_URL + action, method, action, payload]})
        else:
            downtime_parms = extractDowntimeParameters(denaliVariables, monitoring_data['search_extras'])
            if downtime_parms == False:
                return False
            method = 'post'
            payload.update({ 'comment'    : downtime_parms[0] })
            payload.update({ 'duration'   : downtime_parms[1] })
            payload.update({ 'start_time' : downtime_parms[2] })
            monitoring_data.update({'monapi_data' : [BULK_URL + action, method, action, payload]})

        # MRASEREQ-41295
        denaliVariables['monitoring_auth'] = True

    #
    # disable check(s)/notification(s)
    elif "disable" in monitoring_data['commands']:
        action  = 'modify'
        method  = 'put'
        payload = {
                    'entities'      : denaliVariables['serverList'],
                    'service_list'  : service_list,
                  }

        comment = pullMessageFromData(denaliVariables, monitoring_data['search_extras'])
        (checks_notify, add_both) = check_notify_determination(monitoring_data['commands'], False)
        for check in checks_notify:
            payload.update(check)

        # The output for enable/disable looks at the command(s), and prints
        # according to what it finds -- so add the commands in as if they
        # were entered -- this is only the case where 'enable' or 'disable'
        # were submitted without 'checks' or 'notify'.
        if add_both == True:
            monitoring_data['commands'].extend(['checks', 'notify'])

        # MRASEREQ-41492
        payload.update({ 'comment' : comment })
        monitoring_data.update({
                                 'monapi_data' : [BULK_URL + action, method, action, payload],
                                 'filter'      : {}
                              })

        # MRASEREQ-41295
        denaliVariables['monitoring_auth'] = True

    #
    # enable check(s)/notification(s)
    elif "enable" in monitoring_data['commands']:
        action  = 'modify'
        method  = 'put'
        payload = {
                    'entities'      : denaliVariables['serverList'],
                    'service_list'  : service_list,
                  }

        comment = pullMessageFromData(denaliVariables, monitoring_data['search_extras'])
        (checks_notify, add_both) = check_notify_determination(monitoring_data['commands'], True)
        for check in checks_notify:
            payload.update(check)

        if add_both == True:
            monitoring_data['commands'].extend(['checks', 'notify'])

        # MRASEREQ-41492
        payload.update({ 'comment' : comment })
        monitoring_data.update({
                                 'monapi_data' : [BULK_URL + action, method, action, payload],
                                 'filter'      : {}
                              })

        # MRASEREQ-41295
        denaliVariables['monitoring_auth'] = True

    #
    # run a passive check on the submitted hosts/entities
    #   "put"  = run and submit the results
    #   "post" = run and do not submit the results
    elif "passive" in monitoring_data['commands']:
        action  = 'run'
        if "submit" in monitoring_data['commands']:
            method = 'put'
        else:
            method = 'post'
        payload = {
                    'entities'      : denaliVariables['serverList'],
                    'service_list'  : service_list,
                  }
        monitoring_data.update({
                                 'monapi_data' : [BULK_URL + action, method, action, payload],
                                 'filter'      : {}
                              })

    else:
        print "Denali Syntax Error: Undefined monitoring method submitted [%s]" % monitoring_data
        return False

    return monitoring_data



##############################################################################
#
# monitoringSearchRequest(denaliVariables)
#

def monitoringSearchRequest(denaliVariables):

    entity_list = denaliVariables['serverList']

    for entity in entity_list:
        if entity.count('?') > 0 or entity.count('*') > 0:
            return True

    return False



##############################################################################
#
# entitySearchMonitorList(denaliVariables)
#

def entitySearchMonitorList(denaliVariables):

    found_list = []
    location   = denaliVariables['dataCenter'][0].upper()
    entity_location_list  = denaliVariables['monitoring_list']
    entity_list_submitted = denaliVariables['serverList']

    for entity in entity_list_submitted:
        matches = fnmatch.filter(entity_location_list, entity)
        if len(matches) > 0:
            found_list.extend(matches)

    denaliVariables['serverList'] = found_list
    return



##############################################################################
#
# cachedMonitoredDirectoryCreation(denaliVariables, location)
#

def cachedMonitoredDirectoryCreation(denaliVariables, location):

    file_name = "/%s-entity-cache.txt" % location

    home_directory = denali_utility.returnHomeDirectory(denaliVariables)
    if home_directory == '':
        # environment didn't return a result -- store in /tmp
        cache_file = "/tmp/" + file_name
        return cache_file

    directory_path = denaliVariables['mon_e_cache_dir']
    if len(directory_path) == 0:
        directory_path = "%s/.denali/entity_cache" % home_directory

    # does the cache directory exist?
    if not os.path.exists(directory_path):
        # try and create the directory structure for the cache file
        try:
            os.makedirs(directory_path)
        except error as e:
            if denaliVariables['monitoring_debug'] == True or denaliVariables['debugLog'] == True:
                outputString = "Denali: makedirs() error: %s" % e
                denali_utility.debugOutput(denaliVariables, outputString)
                outputString = "Cache files cannot be stored."
                denali_utility.debugOutput(denaliVariables, outputString)
            return False

    cache_file = directory_path + file_name

    return cache_file



##############################################################################
#
# writeCachedMonitoredEntities(denaliVariables, location)
#

def writeCachedMonitoredEntities(denaliVariables, location):

    cache_file = cachedMonitoredDirectoryCreation(denaliVariables, location)
    if cache_file == False:
        return False

    with open(cache_file, 'w') as cache_output:
        for host in denaliVariables['monitoring_list']:
            cache_output.write(host + '\n')

    return True



##############################################################################
#
# retrieveCachedMonitoredEntities(denaliVariables, location)
#
#   Return True:  If the file exists -- load contents of the file into
#                 memory.
#   Return False: If the file does not exist, or is too old and needs to
#                 be refreshed.
#

def retrieveCachedMonitoredEntities(denaliVariables, location):

    DELTA_TIME = 4 * 60 * 60      # hours * minutes * seconds
    host_list  = []

    # was --refresh entered?  If yes, return False to refresh the file
    if denaliVariables['refresh'] == True:
        return False

    # does the cache file for the location exist?
    cache_file = cachedMonitoredDirectoryCreation(denaliVariables, location)
    if cache_file == False:
        return False

    if not os.path.exists(cache_file):
        # file does not exist
        return False

    # Cached file exists.  Is the file older than <x>?
    # retrieve modification timestamp
    mtime_stamp = os.path.getmtime(cache_file)

    # is the time older than 4 hours?
    current_time = time.time()
    time_diff    = int(current_time) - DELTA_TIME

    if time_diff > int(mtime_stamp):
        # new file needed -- time expired
        return False

    # load the file contents into memory
    denaliVariables['monitoring_list'] = []
    with open(cache_file, 'r') as cache_input:
        for line in cache_input:
            denaliVariables['monitoring_list'].append(line.strip())

    return True



##############################################################################
#
# retrieveAllMonitoredEntities(denaliVariables):
#

def retrieveAllMonitoredEntities(denaliVariables):

    url         = '/location/{location}/entities'
    method      = 'get'
    action      = 'query'
    payload     = {}

    if len(denaliVariables['dataCenter']) == 0:
        print "Denali: Entity search requires a data center location (--dc=<location>)."
        return False
    elif len(denaliVariables['dataCenter']) > 1:
        print "Denali: Monitoring Data Center searches are limited to a single location, not %s" % denaliVariables['dataCenter']
        return False

    # replace '{location}' with the location
    location = denaliVariables['dataCenter'][0].upper()
    if location not in denali_location.dc_location:
        print "Denali: Location specified [%s] is an invalid location." % location
        return False

    # determine if a 'cache' file of entities for the location exists
    ccode = retrieveCachedMonitoredEntities(denaliVariables, location)
    if ccode == True:
        return True

    url = url.replace('{location}', location)
    monitoring_data = {'monapi_data':[url, method, action, payload]}

    (ccode, api_response) = monitoringAPICall(denaliVariables, monitoring_data)
    if ccode == False:
        return False

    if api_response['http_code'] == 200 and api_response['data']['success'] == True:
        if (api_response['data']['response'][location]['http_code'] != 200 and
            api_response['data']['response'][location]['success'] != True):

            http_code = api_response['data']['response'][location]['http_code']
            message   = api_response['data']['response'][location]['message']

            print "Denali: Monitoring error [%s] message: %s" % (http_code, message)
            return False
        else:
            denaliVariables['monitoring_list'] = api_response['data']['response'][location]['data']

        # write cached file to disk
        ccode = writeCachedMonitoredEntities(denaliVariables, location)
        if ccode == False:
            # cache file couldn't be written
            if denaliVariables['monitoring_debug'] == True or denaliVariables['debugLog'] == True:
                outputString = "Denali: cached file for [%s] couldn't be written." % location
                denali_utility.debugOutput(denaliVariables, outputString)

    return True



##############################################################################
#
# deleteSessionFile(denaliVariables)
#

def deleteSessionFile(denaliVariables):

    home_directory = denali_utility.returnHomeDirectory(denaliVariables)
    username       = denaliVariables["userName"]

    sessionPath = home_directory + "/.monapi/sess_"

    if username == '':
        username = str(getpass.getuser())

    filename = sessionPath + username + '.json'

    try:
        if os.path.isfile(filename) == True:
            os.remove(filename)
            return True
        else:
            # if the file doesn't exist, then return True
            # so the user can try to authenticate
            return True
    except:
        return False



##############################################################################
#
# acknowledgeMonitoringRequest(denaliVariables, m_entities)
#

def acknowledgeMonitoringRequest(denaliVariables, m_entities):

    nr_entities = len(m_entities)

    print
    print colors.bold + colors.fg.yellow + "!!    " + colors.reset,
    print colors.bold + colors.fg.red    + "WARNING :" + colors.reset,
    print colors.bold + colors.fg.yellow + "                                                     !!" + colors.reset
    print colors.bold + colors.fg.yellow + "!!    " + colors.reset,
    print colors.bold + colors.fg.red    + "A request to update %s entities with a monitoring change" % nr_entities + colors.reset,

    # calculate the spaces at the end of the line to put in
    diff = len(str(nr_entities))
    print " " * (7-diff),

    print colors.bold + colors.fg.yellow + "!!" + colors.reset
    print colors.bold + colors.fg.yellow + "!!    " + colors.reset,
    print colors.bold + colors.fg.red    + "was issued.  Updating more than %s entities requires an       " % SANITY_CHECK_COUNT + colors.reset,
    print colors.bold + colors.fg.yellow + "!!" + colors.reset
    print colors.bold + colors.fg.yellow + "!!    " + colors.reset,
    print colors.bold + colors.fg.red    + "acknowledgement.                                              " + colors.reset,
    print colors.bold + colors.fg.yellow + "!!" + colors.reset
    print

    print "  Press <ENTER> to exit out of this process"
    print

    stdin_backup = sys.stdin
    sys.stdin    = open("/dev/tty")
    answer       = raw_input("  Enter 'I Agree' to proceed with the monitoring command: ")
    sys.stdin    = stdin_backup
    if answer != "I Agree":
        print "  Monitoring change to all entities cancelled."
        return False
    else:
        # "I Agree" was typed -- do the command
        return True



##############################################################################
#
# monitoringSanityCheck(denaliVariables, monitoring_data)
#

def monitoringSanityCheck(denaliVariables, monitoring_data):

    # don't check this if the user requested to by-pass it
    if denaliVariables['autoConfirm'] == True:
        return True

    command_list = ['disable', 'enable', 'downtime']
    mon_proceed  = False

    mon_commands = monitoring_data['commands']
    mon_entities = monitoring_data['monapi_data'][3]['entities']

    for command in mon_commands:
        if command in command_list:
            mon_proceed = True
            break
    else:
        return True

    if mon_proceed == True:
        # found one of the commands to watch for
        if len(mon_entities) > SANITY_CHECK_COUNT:
            ccode = acknowledgeMonitoringRequest(denaliVariables, mon_entities)
            if ccode == False:
                return False

    return True



##############################################################################
#
# monitoringDataEntryPoint(denaliVariables, monitoring_call)
#
#   Function call where all monitoring requests start.

def monitoringDataEntryPoint(denaliVariables, monitoring_call):

    global max_hostname_length
    oStream = denaliVariables['stream']['output']

    denaliVariables['time']['monitoring_start'].append(time.time())

    if denaliVariables["monitoring_debug"] == True or denaliVariables["debugLog"] == True:
        outputString = "\n++monitoringDataEntryPoint++"
        denali_utility.debugOutput(denaliVariables, outputString)
        outputString = "monitoring_call = %s" % monitoring_call
        denali_utility.debugOutput(denaliVariables, outputString)

    # Check to make sure an updated version of python-requests is running; otherwise
    # exit out with a contextual error
    if denaliVariables['importModules']['requests_to'] == False:
        oStream.write('Denali Error: python-requests module does not contain exceptions.ReadTimeout method.\n')
        oStream.write('              Update the module to allow Denali monitoring to function.\n')
        return False

    if len(denaliVariables['serverList']) == 1 and denaliVariables['serverList'][0] == 'denali_host_list':
        # reset the entity list to the originally submitted list and see if
        # any of the requested entities are only in the monitoring subsystem
        denaliVariables['serverList'] = denaliVariables['serverListOrig']

    if denaliVariables["relogin"] == True:
        # MRASEREQ-41495
        if denaliVariables['skms_monapi_auth'] == False:
            ccode = deleteSessionFile(denaliVariables)
            # even if this returns false (failure to delete), don't alert,
            # let the code below handle it

    # Entity wildcard search (fpssl certs, etc.)
    ccode = monitoringSearchRequest(denaliVariables)
    if ccode == True:
        api_response = retrieveAllMonitoredEntities(denaliVariables)
        if api_response == False:
            denaliVariables['time']['monitoring_stop'].append(time.time())
            return False
        else:
            # list retrieved, now search it for the entity name(s)
            # function populates found entries into dv['serverList']
            entitySearchMonitorList(denaliVariables)

    max_hostname_length = getLongestHostname(denaliVariables, denaliVariables['serverList'])
    if max_hostname_length == 0:
        # there is no host list -- exit out.
        denaliVariables['time']['monitoring_stop'].append(time.time())
        print "Denali: Entity list is empty.  This likely means a search was made for a"
        print "        host or entity that does not exist in the monitoring infrastructure."
        return False

    # get the url and method
    monitoring_data = determineMonitoringCall(denaliVariables, monitoring_call)
    if monitoring_data == False:
        denaliVariables['time']['monitoring_stop'].append(time.time())
        return False

    # do a sanity check here
    ccode = monitoringSanityCheck(denaliVariables, monitoring_data)
    if ccode == False:
        return False

    # MRASEREQ-41295
    # Check to see if SKMS authentication is required because of the request/commands
    # submitted to the monitoring API.  'monitoring_auth' is set to True in the above function
    # call to determineMonitoringCall().  If True, authenticate the user.  If False, just
    # continue -- authentication to SKMS not required.
    if denaliVariables['monitoring_auth'] == True:
        if denaliVariables["credsFileUsed"] == True:
            method = "credentials"
        else:
            method = "username"
        ccode = denali_authenticate.authenticateAgainstSKMS(denaliVariables, method)
        if ccode == False:
            # authentication failed -- exit
            return False

    # send the request off -- get the response
    (ccode, api_response) = monitoringAPICall(denaliVariables, monitoring_data)
    if ccode == False:
        denaliVariables['time']['monitoring_stop'].append(time.time())
        return False

    if denaliVariables['monitoring_debug'] == True or denaliVariables['debugLog'] == True:
        outputString = "\nMonitoring response dictionary:\n%s\n" % api_response
        denali_utility.debugOutput(denaliVariables, outputString)

    # call the print/output function to determine what to show on the screen
    # depending upon the monitoring function call submitted
    ccode = outputMonitoringData(denaliVariables, api_response, monitoring_data)

    denaliVariables['time']['monitoring_stop'].append(time.time())

    return True



##############################################################################
#
# httpAuthenticationError(denaliVariables, retry_count, e):
#

def httpAuthenticationError(denaliVariables, retry_count, e):

    oStream = denaliVariables['stream']['output']

    e = str(e)
    if e.split(':')[1].strip().startswith('UNAUTHORIZED'):

        # reason? (1) session file has expired or (2) doesn't exist
        if retry_count < RETRY_COUNT:
            oStream.write("\nDenali: Monitoring login unsuccessful (bad username or password)\n")
            oStream.flush()
            if denaliVariables['monitoring_debug'] == True or denaliVariables['debugLog'] == True:
                outputString = "\nDenali: Monitoring login unsuccessful (bad username or password) -- retry code engaged"
                denali_utility.debugOutput(denaliVariables, outputString)
                outputString = "Monitoring retry count = %s" % RETRY_COUNT
                denali_utility.debugOutput(denaliVariables, outputString)
            auth_payload = getDMUsernameAndPassword(denaliVariables, True)
        else:
            if denaliVariables['monitoring_debug'] == True or denaliVariables['debugLog'] == True:
                outputString = "\nDenali: Monitoring initial login"
                denali_utility.debugOutput(denaliVariables, outputString)
            auth_payload = getDMUsernameAndPassword(denaliVariables, False)

        if auth_payload == False:
            return -5

        # decrement the loop counter
        retry_count -= 1
    else:
        # another type of error -- investigation needed
        oStream.write("Denali / Monitoring Error: %s\n" % str(e))
        oStream.flush()
        return (False, False)

    return (retry_count, auth_payload)



##############################################################################
#
# checkForFailedQuery(denaliVariables, response)
#
#   It is possible that the query was successful, but the response for that
#   query was a failure.  Check and make sure there is valid data to display
#   for this.
#

def checkForFailedQuery(denaliVariables, response):

    error_count    = 0
    error_messages = []
    LINE_COUNT     = 20

    oStream = denaliVariables['stream']['output']

    if response['http_code'] != 200:
        print "Denali monitoring error: %s" % response['errors']
        return False

    host_list  = response['data']['response'].keys()
    host_count = len(host_list)
    host_list.sort()

    for host in host_list:
        if response['data']['response'][host]['success'] == False:
            error_count += 1
            message  = str(response['data']['response'][host]['http_code'])
            message += ':' + response['data']['response'][host]['message']

            if message not in error_messages:
                error_messages.append(message)

    # If the total number of errors equals the total number of hosts, it means
    # that nothing will be displayed as a return value from monitoring, so put
    # a message (or messages) on the screen explaining the problem.
    if error_count == host_count:
        #oStream.write("Denali: Monitoring error message(s) received:\n")
        print "Denali: Monitoring error message(s) received:\n"
        for message in error_messages:
            message = message.split(':',1)
            #oStream.write("  [%s] : %s\n" % (message[0], message[1]))
            if len(message[1].split('\n')) > LINE_COUNT:
                print "  Error: [%s]  Length of message (lines) [%i]:" % (message[0], len(message[1].split('\n')))
                message_lines = message[1].split('\n')
                if (message_lines[3].strip() == "* live.php - Standalone PHP script to serve the unix socket of the" and
                    message_lines[6].strip() == "* Copyright (c) 2010,2011 Lars Michelsen <lm@larsmichelsen.com>" and
                    len(message_lines) > 1490):
                    print "  Nagios Web Interface Error.  Contact monitoring team concerning nagios issues.\n"
                else:
                    print
                for line in message_lines[:LINE_COUNT]:
                    print "  %s" % (line)
                print
            else:
                print "  [%s] : %s\n" % (message[0], message[1])
        oStream.flush()
        return False

    return True



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
# determineConnectedNetwork(denaliVariables)
#
#   Test for network availability: Adobe Corporate or Production or External

def determineConnectedNetwork(denaliVariables):

    ## test for production network availability
    prod_destination = "mirror1.or1.omniture.com"
    prod_result, prod_timeDiff = pingTest(denaliVariables, prod_destination, '1')
    if prod_result == 0:
        return "AdobeProd"
    else:
        ## test for corporate network availability
        corp_destination = "lb-ctrl1.ut1.ne.adobe.net"
        corp_result, corp_timeDiff = pingTest(denaliVariables, corp_destination, '1')
        if corp_result == 0:
            return "AdobeCorp"
        else:
            ## must be an external network (no Adobe connectivity)
            return "Non-Adobe"



##############################################################################
#
# monitoringAPICall(denaliVariables, monitoring_data, username=None, password=None, use_ssl=True)
#

def monitoringAPICall(denaliVariables, monitoring_data, username=None, password=None, use_ssl=True):

    global Connected_Network

    domain      = 'monapi.or1.goc.adobe.net'
    dev_domain  = "monapi.dev.or1.goc.adobe.net"
    uri         = '/v2'
    url         = monitoring_data['monapi_data'][0]
    method      = monitoring_data['monapi_data'][1]
    action      = monitoring_data['monapi_data'][2]
    payload     = monitoring_data['monapi_data'][3]

    oStream = denaliVariables['stream']['output']

    # MonApi read timeout amount (in seconds)
    read_request_timeout = 0

    if 'filter' in monitoring_data['monapi_data']:
        sr_filter = monitoring_data['monapi_data']['filter']
    else:
        sr_filter = {}

    # if DM user/pass given, use it
    if denaliVariables['dm_username'] != '':
        username = denaliVariables['dm_username']
    if denaliVariables['dm_password'] != '':
        password = denaliVariables['dm_password']

    denaliVariables['time']['monapi_start'].append(time.time())

    # set the global "Connected_Network"
    Connected_Network = determineConnectedNetwork(denaliVariables)
    if Connected_Network == "AdobeCorp" or Connected_Network == "Non-Adobe":
        domain = dev_domain
    elif Connected_Network == "AdobeProd":
        domain = domain

    if denaliVariables['debug'] == True:
        print "MonApi domain = %s" % domain

    while True:
        # initiate the REST interface -- get the api call entry point
        mon_api = monapi.MonApiClient(username, password, domain, uri, use_ssl)

        if read_request_timeout != 0:
            # change has been requested after a read timeout failure
            # the 'set' happens here because it immediately follows the
            # reinitialization of the client library class.
            mon_api.set_request_timeout(read_request_timeout)

        if len(denaliVariables['dataCenter']) > 0:
            entity_filter = ','.join(denaliVariables['dataCenter'])
            entity_filter = {'location':entity_filter}
            sr_filter.update(entity_filter)

        if denaliVariables["monitoring_debug"] == True or denaliVariables["debugLog"] == True:
            outputString = "url       = %s" % url
            denali_utility.debugOutput(denaliVariables, outputString)
            # MRASEREQ-41495
            # Remove the password from showing -- too sensitive to show
            # on-screen even during a debug session
            if 'password' in payload:
                payload_password = payload['password']
                payload['password'] = 'xxxxx'
                outputString = "payload   = %s" % payload
                denali_utility.debugOutput(denaliVariables, outputString)
                payload['password'] = payload_password
            else:
                outputString = "payload   = %s" % payload
                denali_utility.debugOutput(denaliVariables, outputString)
            outputString = "method    = %s" % method
            denali_utility.debugOutput(denaliVariables, outputString)
            outputString = "sr_filter = %s" % sr_filter
            denali_utility.debugOutput(denaliVariables, outputString)

        (ccode, response, api_success, read_request_timeout) = callMonAPI(denaliVariables, mon_api, url, payload, method,
                                                                          sr_filter, monitoring_data, read_request_timeout)
        if ccode == "success":
            break
        elif ccode == "continue":
            if 'username' in response and 'password' in response:
                username = response['username']
                password = response['password']
            continue
        else:
            # This will catch both 'True' and 'False' returns.
            return (ccode, response)

    denaliVariables['time']['monapi_stop'].append(time.time())
    if api_success == False:
        # failed authentication 3 times
        oStream.write("Denali: Adobe Digital Marketing username/password authentication failed 3 times.\n")
        oStream.flush()
        return (False, False)

    ccode = checkForFailedQuery(denaliVariables, response)
    if ccode == False:
        return (False, False)

    return (True, response)



##############################################################################
#
# callMonAPI(denaliVariables, mon_api, url, payload, method, sr_filter, monitoring_data, read_request_timeout)
#

def callMonAPI(denaliVariables, mon_api, url, payload, method, sr_filter, monitoring_data, read_request_timeout):

    retry_count = RETRY_COUNT
    oStream     = denaliVariables['stream']['output']
    api_success = False
    response    = {}

    # read request timeout changes
    read_request_timeout_increment  = 60
    read_request_timeout_limit      = 180

    # try the request
    try:

        #
        response = mon_api.send_request(url, payload, method, sr_filter)
        #

        api_success = True

    except KeyError as e:
        # MRASEREQ-41495
        if denaliVariables['skms_monapi_auth'] == True:
            # The mon_api.send_request MUST be called to correctly create a session
            # file for the user; however, when just a username/password is requested,
            # the above call returns a KeyError for 'response' because there isn't any
            # viable data returned.  In this specific case, identify the return code and
            # continue processing.
            denaliVariables['time']['monapi_stop'].append(time.time())
            return (True, response, api_success, read_request_timeout)
        else:
            denaliVariables['time']['monapi_stop'].append(time.time())
            #oStream.write("Denali Error:  KeyError %s during MonAPI authentication process\n" % e)
            #oStream.flush()
            return (False, response, api_success, read_request_timeout)

    except requests.exceptions.HTTPError as e:
        # check the loop counter, before asking for a password, but after
        # the last username/password entry was attemped against the api
        if retry_count <= 0:
            #break
            return ("success", response, api_success, read_request_timeout)

        (retry_count, auth_payload) = httpAuthenticationError(denaliVariables, retry_count, e)
        # -5 because a '0' is also False, but '0' is the last try, so this is
        # a hacky work-around
        if retry_count == -5:
            #break
            return ("success", response, api_success, read_request_timeout)
        if auth_payload == False:
            denaliVariables['time']['monapi_stop'].append(time.time())
            #return False
            return (False, response, api_success, read_request_timeout)

        username = auth_payload['username']
        password = auth_payload['password']
        return ("continue", {'username':username, 'password':password}, api_success, read_request_timeout)

    except requests.exceptions.ConnectionError as e:
        # can happen when not on the corporate network -- no connection allowed
        denaliVariables['time']['monapi_stop'].append(time.time())
        oStream.write("Denali Error : Connection failed to monitoring host.\n")
        oStream.write("API Response : %s\n" % e)
        oStream.flush()
        #return False
        return (False, response, api_success, read_request_timeout)

    except requests.exceptions.ReadTimeout as e:
        # Exception happens when the query request to monitoring takes too long to retrieve
        # This happens because the monitoring infrastructure is slow to respond, or the query
        # is extremely large; thus making it slow to respond, or some other problem with the
        # infrastructure responding in a timely manner.

        if denaliVariables['mon_to_retry'] == True:
            # add the increment to the timeout, and try again
            if read_request_timeout == 0:
                # rrt will be zero because it is only set after the first
                # read timeout failure, and it is set to whatever the class
                # instantiation has internally.
                read_request_timeout = mon_api.get_request_timeout()
            read_request_timeout += read_request_timeout_increment
        else:
            read_request_timeout = read_request_timeout_limit + 1

        if read_request_timeout > read_request_timeout_limit:
            # query is too large, or something else is going on.
            denaliVariables['time']['monapi_stop'].append(time.time())
            oStream.write("Denali: Monitoring read timeout.\n")
            oStream.write("API Response : %s\n" % e)
            oStream.flush()
            #return False
            return (False, response, api_success, read_request_timeout)
        else:
            if denaliVariables['mon_details'] == True or denaliVariables['monitoring_debug'] == True:
                print "Denali: Retry send_request with read_request_timeout + %ds => %ds" % (read_request_timeout_increment, read_request_timeout)
            return ("continue", response, api_success, read_request_timeout)

    else:
        if denaliVariables['monitorResponseValidate'] == True:
            # If the request is for 'enable', 'disable', or 'downtime', then do a check and make sure
            # that the request was successful.  MonAPI will report success when it really isn't; i.e.,
            # a disable event for a host (all services), and the result is all but one is disabled.
            # This will check and make sure that the request was successful.
            if ('enable'   in monitoring_data['commands'] or
                'disable'  in monitoring_data['commands'] or
                'downtime' in monitoring_data['commands']):

                # turn off further looping validation checks ... this is it, only one
                denaliVariables['monitorResponseValidate'] = False

                # validate the command completed successfully
                (ccode, response, api_success, read_request_timeout) = validateMonitoringRequestResponse(denaliVariables, mon_api, monitoring_data, response, url,
                                                                                                         payload, method, sr_filter, read_request_timeout)
                if ccode == "success":
                    return ("success", response, api_success, read_request_timeout)
                else:
                    return (ccode, response, api_success, read_request_timeout)

    return ("success", response, api_success, read_request_timeout)



##############################################################################
#
# modifyResponseDataForFailures(response, monitoring_data, host_data, validation_data)
#
#   This function receives two inputs:
#     (1) response  : original response dictionary to be modified
#     (2) host_data : details of the hosts (failed, succeeded, etc.)
#
#   Spin through the host_data one host at a time.  If any hosts are marked with
#   a full or partial failure (or a review status) then change the response
#   dictionary accordingly.  This will show up on the output the user see when
#   the monitoring run is completed.
#
#   The 'success' dictionary key is the same one looked at when printing the
#   result for the host to the user at the end.
#

def modifyResponseDataForFailures(response, monitoring_data, host_data, validation_data):

    SUCCESS = 0     # all checks/notifications or downtime events are set as expected
    FAILURE = 1     # all checks/notifications or downtime events are NOT set as expected
    PARTIAL = 2     # one or more checks/nofitications or downtime events are NOT set as expected
    INITIAL = 3     # initialization ... only valid when the dictionary host key is created
    REVIEW  = 4     # administrator should review this ... denali won't touch it for now

    for hostname in host_data.keys():
        result = host_data[hostname]['overall']
        if result == FAILURE:
            response['data']['response'][hostname]['success'] = False
        elif result == PARTIAL:
            if 'enable' in monitoring_data['commands'] or 'disable' in monitoring_data['commands']:
                # Collect the checks/notifications that failed, then combine them into
                # a single List for use in the screen output.  This attaches the List as
                # a string behind a colon (:) in the string 'PARTIAL'.  This is a bit of
                # a reach, and will be confusing when I look at it in a month.  The output
                # code, hostPrintOutput(), will look for "PARTIAL:" and then split on the
                # colon with the second element being the List of failed services.
                check_failures  = set(host_data[hostname]['check_failure'])
                notify_failures = set(host_data[hostname]['notify_failure'])
                failure_list    = check_failures | notify_failures
                response['data']['response'][hostname]['success'] = 'PARTIAL:%s' % ', '.join(failure_list)

            elif 'downtime' in monitoring_data['commands']:
                failure_list = validation_data['hosts_and_services'][hostname]
                response['data']['response'][hostname]['success'] = 'PARTIAL:%s' % ', '.join(failure_list)

        elif result == REVIEW:
            response['data']['response'][hostname]['success'] = 'REVIEW'

    return response



##############################################################################
#
# checkResults(denaliVariables, ccode, monitoring_data, response, payload, saved_response, retry_loop_counter=None)
#

def checkResults(denaliVariables, ccode, monitoring_data, response, payload, saved_response, retry_loop_counter=None):

    SUCCESS = 0     # all checks/notifications or downtime events are set as expected
    FAILURE = 1     # all checks/notifications or downtime events are NOT set as expected
    PARTIAL = 2     # one or more checks/nofitications or downtime events are NOT set as expected
    INITIAL = 3     # initialization ... only valid when the dictionary host key is created
    REVIEW  = 4     # administrator should review this ... denali won't touch it for now

    # check the validation results
    if ccode == "success":

        if RETRY_DEBUG == True:
            print "    cr #1: monapi call succeeded ... validate results now."
        (host_data, validation_data) = validateResultsHub(denaliVariables, response, monitoring_data)

        (ccode, payload) = checkValidationResults(denaliVariables, host_data, monitoring_data, payload, validation_data, retry_loop_counter)

        if ccode == True:
            if RETRY_DEBUG == True:
                print "    cr #2: ccode is True, validation successful, no further retries needed."
            return ("success", payload, response)
        elif ccode == False:
            if RETRY_DEBUG == True:
                print "    cr #3: ccode is False, validation failed, see if retries are needed."

            for host in host_data.keys():
                if host_data[host]['overall'] != SUCCESS:
                    if RETRY_DEBUG == True:
                        print "    cr #4: found a host failure condition ... run the modify code."
                    saved_response = modifyResponseDataForFailures(saved_response, monitoring_data, host_data, validation_data)
                    break
            else:
                if RETRY_DEBUG == True:
                    print "    cr #5: no errored host found; check for failures failed."
                saved_response = response

            if payload == True:
                # ccode being False and payload being True means there are only REIVEW hosts
                if RETRY_DEBUG == True:
                    print "    cr #6: ccode is False and payload is True (REVIEW hosts only)"
                return ("success", payload, saved_response)
            elif payload == False:
                # ccode being False and payload being False means a weird condition was found
                # where the data doesn't match ... do nothing.
                if RETRY_DEBUG == True:
                    print "    cr #7: ccode is False and payload is False ... do nothing."
                return ("success", payload, saved_response)

            if retry_loop_counter is None:
                if RETRY_DEBUG == True:
                    print "    cr #8: initial check ... mark as a failure; ready for potential retries."
                return ("failure", payload, saved_response)
            else:
                if RETRY_DEBUG == True:
                    print "    cr #9: > 1st check; see if there are still failures."
                for host in host_data.keys():
                    if host_data[host]['overall'] != SUCCESS:
                        if RETRY_DEBUG == True:
                            print "    cr #10: found a failure ... mark for retry."
                        return ("failure", payload, saved_response)
                else:
                    if RETRY_DEBUG == True:
                        print "    cr #11: no failures found ... why?"
                    return ("failure", payload, saved_response)
    else:
        if RETRY_DEBUG == True:
            print "    cr #12: monapi call failed ... try the exact same request again"
        return ("failure", payload, saved_response)



##############################################################################
#
# checkValidationResults(denaliVariables, ccode, monitoring_data, payload, validation_data, retry_loop_counter)
#

def checkValidationResults(denaliVariables, ccode, monitoring_data, payload, validation_data, retry_loop_counter):

    SUCCESS = "!!! VALIDATION SUCCESS !!!"
    FAILURE = "!!! VALIDATION FAILURE !!!"

    if ccode == True:
        if RETRY_DEBUG == True:
            print colors.bold + colors.fg.lightgreen + SUCCESS + colors.reset
            if retry_loop_counter is not None and retry_loop_counter != RETRY_COUNTER:
                print "# of retries before success: %i" % (RETRY_COUNTER - retry_loop_counter)
                print
        return (True, payload)
    else:
        if RETRY_DEBUG == True:
            print colors.bold + colors.fg.red + FAILURE + colors.reset,
            if retry_loop_counter is not None:
                print "  (Retry #%s)" % str(RETRY_COUNTER - retry_loop_counter)
            else:
                print
        else:
            if retry_loop_counter is None:
                sys.stdout.write("Validating MonAPI results...\r")
                sys.stdout.flush()
            else:
                sys.stdout.write("Resubmit MonAPI request (retry #%i)\r" % (RETRY_COUNTER - retry_loop_counter))
                sys.stdout.flush()

        # The validation_data results are handled differently depending on whether the
        # return is from an 'enable/disable' command or a 'downtime' command
        if 'enable' in monitoring_data['commands'] or 'disable' in monitoring_data['commands']:
            # Adjust the payload entities list with new data (or keep the old
            # if the List is empty)
            #if len(validation_data['entities']):
            #    payload['entities'] = list(validation_data['entities'])

            # If the service_list is an asterisk, leave the list as is.  In other words,
            # only change the service_list if specific services were submitted.
            #if payload['service_list'][0] != '*':
            #    if len(validation_data['service_list']):
            #        payload['service_list'] = list(validation_data['service_list'])

            if len(validation_data['service_list']) == 0:
                if len(validation_data['entities']):
                    # entities without services
                    # This happens with a REVIEW state
                    return (False, True)
                else:
                    # no entities, no services: do nothing
                    return (False, False)
            else:
                if len(validation_data['entities']):
                    # entities and services
                    payload['entities'] = list(validation_data['entities'])
                    if '*' not in payload['service_list']:
                        if len(validation_data['service_list']):
                            payload['service_list'] = list(validation_data['service_list'])
                    return (False, payload)
                else:
                    # services without entities: do nothing
                    return (False, False)

        elif 'downtime' in monitoring_data['commands']:
            # If 'downtime' is requested, the service_list will be an asterisk
            # already (denali doesn't allow downtime for individual services from
            # the command line), and with the 'downtime' command issued again, it
            # will be changed to specific services that need their downtime set
            # again, which is a NEW way to do things in Denali.

            if len(validation_data['service_list']) == 0:
                if len(validation_data['entities']):
                    # entities without services
                    # This happens with a REVIEW state
                    return (False, True)
                else:
                    # no entities, no services: do nothing
                    return (False, False)
            else:
                if len(validation_data['entities']):
                    # entities and services
                    payload['entities']     = list(validation_data['hosts_and_services'].keys())
                    payload['service_list'] = list(validation_data['service_list'])
                    return (False, payload)
                else:
                    # services without entities: do nothing
                    return (False, False)

        return (False, False)



##############################################################################
#
# validateMonitoringRequestResponse(denaliVariables, mon_api, monitoring_data, response, url, payload, method, sr_filter, read_request_timeout)
#
#   This function will implement retry logic if a specific monitoring command
#   did not finish as expected.  Validate the response according to the command
#   sent.  If it did not complete successfully, resend the same command and
#   check again.  The number of checks to perform is retry_loop_counter.
#

def validateMonitoringRequestResponse(denaliVariables, mon_api, monitoring_data, response, url, payload, method, sr_filter, read_request_timeout):

    #if debug == True:
    #    print "monitoring_data = %s" % monitoring_data
    #    print
    #    print "url       = %s" % url
    #    print "payload   = %s" % payload
    #    print "method    = %s" % method
    #    print "sr_filter = %s" % sr_filter
    #    print

    retry_loop_counter = RETRY_COUNTER

    # save values to pass back
    saved_response = dict(response)
    saved_mon_data = monitoring_data

    validate_query = {
                        'url'       : '/bulk/entity/svc/query',
                        'payload'   : {
                                        'service_list'    : [],
                                        'entities'        : [],
                                      },
                        'method'    : 'post',
                        'sr_filter' : {},
                     }

    validate_query['payload']['service_list'] = monitoring_data['monapi_data'][3]['service_list']
    validate_query['payload']['entities']     = monitoring_data['monapi_data'][3]['entities']

    # prep the variables for the validation query
    val_url       = validate_query['url']
    val_payload   = validate_query['payload']
    val_method    = validate_query['method']
    val_sr_filter = validate_query['sr_filter']

    #
    # This is the MonAPI retry loop logic/code
    #
    # (1)   Collect the validation data with the first query below (this query is essentially
    #       a "--mon details" on the list of entities)
    # (2)   Check to see if the original request was satisfied
    # (3)   If the request succeeded, the function successfully exits
    #
    #
    # Retry loop starts here (original submission/request was not successful)
    #
    # (4)   If retry_loop_counter > 0
    # (5)   Decrement the retry_loop_counter variable
    # (6)   Create a modified version of the original request and resubmit to MonAPI
    # (7)   Collect the validataion data from the resubmission
    # (8)   Check to see if the request was satisfied
    # (9)   If the request was satisfied, exit the loop
    # (10)  If the request was not satisfied, repeat the loop for retry_loop_counter times
    #       [[ Loop back to #4 ]]
    #
    # This entire piece of code is in-place because sometimes MonAPI does not successfully
    # carry out requests given to it the first time.  So, a 2nd and potentially 3rd try
    # are done here, where the chance of success is now closer to 100%.
    #
    # When the MonAPI code is fixed, this piece of code can be disabled by setting:
    #
    #   denaliVariables['monitorResponseValidate'] = False
    #
    # Until the code problems with MonAPI are addressed, this code is a necessary evil.
    # It will prevent assumptions that checks are disabled, or downtimes are are properly
    # submitted ... because that's the response back from MonAPI (success, when in fact it
    # is actually not successful).
    #

    #
    # Collect the "details" data for a validation check
    #
    if RETRY_DEBUG == True:
        print "1 : callMonAPI() - get the validation response"
    (ccode, response, api_success, read_request_timeout) = callMonAPI(denaliVariables, mon_api, val_url, val_payload, val_method, val_sr_filter, monitoring_data, read_request_timeout)
    if ccode != "success":
        # failure talking to MonAPI
        if RETRY_DEBUG == True:
            print "2 : callMonAPI() initial validation attempt failed to successfully complete."
        return (ccode, saved_response, api_success, read_request_timeout)

    #
    # Do the validation check
    #
    if RETRY_DEBUG == True:
        print "3 : checkResults() - initial check"
    (ccode, payload, saved_response) = checkResults(denaliVariables, ccode, monitoring_data, response, payload, saved_response)
    if ccode == "success":
        if RETRY_DEBUG == True:
            print "4 : checkResults() returned successful, all hosts are correct. Exit."
        return ("success", saved_response, api_success, read_request_timeout)

    if RETRY_DEBUG == True:
        print "5 : checkResults() returned a failure, one or more hosts failed."

    #
    # Retry Loop
    #

    def printLoopCounter(loop_counter):
        counter = RETRY_COUNTER - loop_counter
        if counter != 0:
            print "Retry count: " + colors.bold + colors.fg.lightgreen + str(counter) + colors.reset + "                     "

    while (retry_loop_counter > 0):
        if RETRY_DEBUG == True:
            print "6 : In the retry loop  " + colors.bold + colors.fg.lightred + '[#' + str((RETRY_COUNTER - retry_loop_counter)+1) + ']' + colors.reset
        retry_loop_counter -= 1

        #
        # Resubmit any changes for checks/notifications/downtimes to fix
        #
        if RETRY_DEBUG == True:
            print "7 : retry_loop_counter decremented by one"
        (ccode, response, api_success, read_request_timeout) = callMonAPI(denaliVariables, mon_api, url, payload, method, sr_filter, monitoring_data, read_request_timeout)
        if ccode != "success":
            if RETRY_DEBUG == True:
                print "8 : callMonAPI() with update data failed ... error out."
            printLoopCounter(retry_loop_counter)
            return (ccode, saved_response, api_success, read_request_timeout)

        #
        # Collect the "details" data for a validation check
        #
        if RETRY_DEBUG == True:
            print "9 : callMonAPI() with update data succeeded ... continue"
        (ccode, response, api_success, read_request_timeout) = callMonAPI(denaliVariables, mon_api, val_url, val_payload, val_method, val_sr_filter, monitoring_data, read_request_timeout)
        if ccode != "success":
            if RETRY_DEBUG == True:
                print "10: callMonAPI() re-validation attempt failed ... error out."
            printLoopCounter(retry_loop_counter)
            return ("success", saved_response, api_success, read_request_timeout)

        #
        # Do the validation check
        #
        if RETRY_DEBUG == True:
            print "11: callMonAPI() validation succeeded ... continue"
        (ccode, payload, saved_response) = checkResults(denaliVariables, ccode, monitoring_data, response, payload, saved_response, retry_loop_counter)
        if ccode == "success":
            if RETRY_DEBUG == True:
                print "12: checkResults() returned successful, all hosts are correct. Exit."
            printLoopCounter(retry_loop_counter)
            return ("success", saved_response, api_success, read_request_timeout)

    if RETRY_DEBUG == True:
        print "13: checkResults() returned a failure, one or more hosts failed.  Retries expired, exit loop."

    printLoopCounter(retry_loop_counter)
    return (ccode, saved_response, api_success, read_request_timeout)



##############################################################################
#
# validateResultsHub(denaliVariables, response, monitoring_data)
#
#   Distribution starting point for calling the correct validation function.
#   All results will come back the same, but the function is different because
#   of the different types of monitoring calls that can be submitted.
#

def validateResultsHub(denaliVariables, response, monitoring_data):

    # Set to True so any weird flow through here defaults to the normal
    # code handling routeins
    host_results = True

    if 'enable' in monitoring_data['commands']:
        (host_results, validation_data) = validateCheckNotifyResults(denaliVariables, response, monitoring_data, value=True)
    elif 'disable' in monitoring_data['commands']:
        (host_results, validation_data) = validateCheckNotifyResults(denaliVariables, response, monitoring_data, value=False)
    elif 'downtime' in monitoring_data['commands']:
        (host_results, validation_data) = validateDowntimeResults(denaliVariables, response, monitoring_data)

    return (host_results, validation_data)



##############################################################################
#
# validateDowtimeResults(denaliVariables, response, monitoring_data)
#

def validateDowntimeResults(denaliVariables, response, monitoring_data):

    host_validation = {}
    service_events  = {'counts':{}, 'host_services':{}}

    # this is the final list that will be sent for an update
    final_service_list = set()

    # This dictionary stores only host data that is deemed a failure
    # 'entities' is a list of hosts
    # 'service_list' is a list of alert services that failed
    # 'hostlist_w_services' is a dictionary of hosts and their associated services
    validation_data = {
                       'entities'           :set(),     # generic : hosts
                       'service_list'       :set(),     # generic : services
                       'hosts_and_services' :{},        # specific: hosts + services
                       'counts'             :{}         # generic : count of events + services
                                                        # 'counts' is used per-host (reset every
                                                        #    loop, don't trust for final data)
                      }

    SUCCESS = 0     # all downtime events are set as expected
    FAILURE = 1     # all downtime events are NOT set as expected
    PARTIAL = 2     # one or more of the downtime events are NOT set as expected
    INITIAL = 3     # initialization ... only valid when the dictionary host key is created
    REVIEW  = 4     # administrator should review this ... denali won't touch it for now

    hostList = response['data']['response'].keys()
    hostList.sort()

    #
    # Debugging statements
    #
    import random
    random.seed()
    rNum                  = random.randint(0,10)        # choose the server?
    rNum2                 = random.randint(0,10)        # choose the alert service?
    use_random            = False
    inject_failure_data   = False

    # downtime works different than checks ... the services listed here are assumed to
    # be good.  the inverse services need updating
    failure_data_services = [   'Coffer file count check',
                                'Coffer inode check',
                                'DATA_DISK_SPACE',
                                'HOST',
                                'Inode_Disk_space',
                                'Network_Health',
                                'PUCK',
                                'Read Only Filesystem',
                                'SYSTEM_DISK_SPACE',
                                'Salt Minion Eng','VAR_DISK_SPACE'  ]


    for host in hostList:
        # reset in-function dictionaries for next host usage
        host_validation.update({host:{'overall' : INITIAL}})
        validation_data['counts'] = {}

        # Add each host automatically ... they will be removed if needed
        validation_data['entities'].add(host)

        alert_services = response['data']['response'][host]['alert_services'].keys()
        alert_services.sort()

        # spin through all of the servics on this specific host
        for service in alert_services:

            # Assign all of the maintenance events here, they are in the 'maintenance'
            # key (which is a List of dictionaries).
            maintenance_events = response['data']['response'][host]['alert_services'][service]['data']['maintenance']
            event_count = len(maintenance_events)

            #
            # INJECT Failure data as a test case
            #
            if inject_failure_data == True and RETRY_DEBUG == True:
            #if 1:
                if use_random == False:
                    if service in failure_data_services:
                        if len(maintenance_events):
                            add_one = maintenance_events[-1]
                            maintenance_events.append(add_one)
                        if host.startswith('scvm96'):
                            event_count += 3
                        elif host.startswith('scvm97'):
                            event_count += 1
                else:
                    #
                    # Randomize the failure
                    # Random server chosen, then a random alert service chosen
                    #
                    if rNum > 5 and rNum2 > 5:
                        if len(maintenance_events):
                            add_one = maintenance_events[-1]
                            maintenance_events.append(add_one)
                        event_count += 1

            # Add the count for the service (generic method of checking)
            if event_count not in validation_data['counts']:
                validation_data['counts'].update({event_count:[service]})
            else:
                validation_data['counts'][event_count].append(service)

            # Add the count for the host by the alert service (specific method of checking)
            if host not in validation_data['hosts_and_services']:
                validation_data['hosts_and_services'].update({host:{service:event_count}})
            else:
                validation_data['hosts_and_services'][host].update({service:event_count})

        #
        # Downtime Validation Check
        #

        # All services have been reviewed with the data stored in validation_data.  Using
        # this dictionary, determine which services (if any) need updating.
        event_keys = validation_data['counts'].keys()
        key_length = len(event_keys)
        event_keys.sort()                               # sort it, so [0] is less than [1]

        if key_length == 1:
            # Every alert service has an identical count of maintenance events.
            # No action is required for this host (the assumption here is that
            # the downtime event was successfully applied to every alert service)
            if RETRY_DEBUG == True:
                print "All services for %s have an identical maintenance event count (length = %i)." % (host, key_length)
            host_validation[host]['overall'] = SUCCESS

            # Remove the host (and associated data) from the dictionary
            # Remaining hosts in this key will have a round of updates done for them.
            validation_data['hosts_and_services'].pop(host)
            validation_data['entities'].discard(host)
            continue

        elif key_length > 2:
            # An unusual situation here ... not normal.
            # This means that there are 3 (or more) alert services that have a different
            # number (count) of maintenance events registered against them.  The code will
            # alert the administrator to this fact and take no specific action for these.
            if RETRY_DEBUG == True:
                print "Denali Warning:  There are multiple alert services that have differing counts for maintenance events.  Please investigate."
                print "                 Host:  %s" % host
            host_validation[host]['overall'] = REVIEW
            validation_data['hosts_and_services'].pop(host)
            continue

        elif key_length > 1:
            # !! There can be ONLY one !!
            # Highlander, 1986 / Connor MacLeod
            #
            # This means there are 2 different groupings of alert services; one with a larger
            # count of maintenance events, and one with a smaller count of events.  This code
            # selects the smaller one for an update via the API.
            #
            # Only do an update if the difference between the two group counts is exactly
            # one (1); otherwise, punt again to the administrator to investigate further.
            if int(event_keys[1]) - int(event_keys[0]) > 1:
                if RETRY_DEBUG == True:
                    print "Denali Warning:  The difference between maintenance counts is greater than one.  Please investigate."
                    print "                 Host:  %s" % host
                host_validation[host]['overall'] = REVIEW
                validation_data['hosts_and_services'].pop(host)
                continue

            elif int(event_keys[1]) - int(event_keys[0]) == 1:
                # This 'elif' catches two cases:
                #   (1) When the count is 0 and 1: This means that most of the services received the
                #       downtime event, but a few (maybe one) did not.  This is hopefully the typical
                #       case and will be easily resolved with another MonAPI pass/submission.
                #   (2) When the count is x and (x+1), where x > 0.  This likely means that there were
                #       or are previous maintenance events on this host.  Pick the smaller count list
                #       of services and assume (yes, I know) they need the update.  Hopefully this case
                #       is atypical and doesn't occur with any frequency.
                if RETRY_DEBUG == True:
                    print "Denali Update:  Found alert services for host [%s] that need another update pass:" % host
                    print "                ==> %s" % ', '.join(validation_data['counts'][event_keys[0]])
                host_validation[host]['overall'] = PARTIAL

                # Watch this:
                # Replace existing host/service data with only the services that are required
                # for another round of updates.  This changes it from a Dict to a List format.
                validation_data['hosts_and_services'][host] = validation_data['counts'][event_keys[0]]
                continue

            else:
                # negative?  what happened?
                if RETRY_DEBUG == True:
                    print "Denali Warning:  Negative count number for maintenance events: %s" % host
                    print "Services :  %s" % host_validation['hosts_and_services'][host]
                    print "Counts   :  %s" % host_validation['counts']
                    print
                host_validation[host]['overall'] = REVIEW
                validation_data['hosts_and_services'].pop(host)
                continue

        else:
            # anything that falls to here, remove the host
            if RETRY_DEBUG == True:
                print ":: Denali Debugging Data ::"
                print "==========================="
                print "Host     :  %s" % host
                print "Services :  %s" % host_validation['hosts_and_services'][host]
                print "Counts   :  %s" % host_validation['counts']
                print
            host_validation[host]['overall'] = REVIEW
            validation_data['hosts_and_services'].pop(host)
            continue

    for host in validation_data['hosts_and_services']:
        # Now that all of the host data-aggregation has completed, review all of it for
        # consistency.  The code wants to make a SINGLE update request.  To do this,
        # the alert services that need an update need to be identical across all hosts
        # requiring this update.
        #
        # If the services are the same, do the update.
        # If the services are not the same, adjust them until they are.
        #   - Do set arithmetic <intersection> : only what services is/are included
        #     for every host.
        #   - Do set arithmetic <difference>   : determine if any elements were included
        #     in the final alert service set.

        host_service_list = validation_data['hosts_and_services'][host]

        if len(final_service_list) == 0:
            # first one ... add it in
            final_service_list.update(host_service_list)
        else:
            # make it a set
            host_service_list = set(host_service_list)

            # do an intersection with the existing set
            final_service_list = final_service_list & set(host_service_list)

            # Determine if any of the host's services are included in the final list.
            # If not, remove this host from the update list.  Oh well.
            #
            # Set difference: if the difference is the same length as the original,
            # then no services were added; therefore, remove the host.
            if len(host_service_list - final_service_list) == len(host_service_list):
                host_validation[host]['overall'] = REVIEW
                validation_data['hosts_and_services'].pop(host)
                validation_data['entities'].discard(host)

    if len(final_service_list) and validation_data['entities']:
        # Add the final_service_list to the validation_data dictionary
        validation_data['service_list'] = final_service_list
        # validation_data['entities'] contains every host that will get an update
        # validation_data['service_list'] contains the service list that will be updated
        return (host_validation, validation_data)
    elif validation_data['entities']:
        # Hosts are in the list, but there are no services attached.  This means
        # they are likely REVIEW hosts.
        return (host_validation, validation_data)

    # best scenario -- nothing to do ... everything succeeded
    return (True, True)



##############################################################################
#
# validateCheckNotifyResults(denaliVariables, response, monitoring_data, value='')
#

def validateCheckNotifyResults(denaliVariables, response, monitoring_data, value=''):

    host_validation = {}
    validation_data = {'entities':set(), 'service_list':set()}

    SUCCESS = 0     # all checks/notifications are enabled/disabled as expected
    FAILURE = 1     # all checks/notifications are NOT enabled/disabled as expected
    PARTIAL = 2     # one or more of the checks/notifications are NOT enabled/disabled as expected
    INITIAL = 3     # initialization ... only valid when the dictionary host key is created

    checks  = False
    notify  = False

    hostList = response['data']['response'].keys()
    hostList.sort()

    #
    # Debugging statements
    #
    import random
    random.seed()
    rNum                  = random.randint(0,10)        # choose the server?
    rNum2                 = random.randint(0,10)        # choose the alert service?
    use_random            = False
    inject_failure_data   = False
    failure_data_services = ['TIME', 'SSH']

    # determine if the 'checks' and 'notify' flags are requested
    if 'checks' in monitoring_data['commands']:
        checks = True
    if 'notify' in monitoring_data['commands']:
        notify = True

    # The response variable only contains data from requested services.  This means
    # the code needs to only check every service listed, and that will be every piece
    # of data that needs investigation.
    for host in hostList:

        host_validation.update({host:{'overall'       : INITIAL,
                                      'check_success' : [],
                                      'check_failure' : [],
                                      'notify_success': [],
                                      'notify_failure': []}})

        alert_services = response['data']['response'][host]['alert_services'].keys()
        alert_services.sort()
        for service in alert_services:
            service_check  = response['data']['response'][host]['alert_services'][service]['data'].get('checks', None)
            service_notify = response['data']['response'][host]['alert_services'][service]['data'].get('notifications',None)

            if service_check is None or service_notify is None:
                # This code prevents a python stack when an check/nofication
                # is requested that doesn't exist.
                # The problem is that it doesn't notify the user that there
                # is a problem.  Will fix that later.
                continue

            #
            # INJECT Failure data as a test case
            #
            if inject_failure_data == True and RETRY_DEBUG == True:
            #if 1:
                if use_random == False:
                    if service in failure_data_services:
                        if value == True:
                            service_check = False
                        else:
                            service_check = True
                else:
                    #
                    # Randomize the failure
                    # Random server chosen, then a random alert service chosen
                    #

                    if rNum > 5 and rNum2 > 5:
                        if value == True:
                            service_check = False
                        else:
                            service_check = True

            #
            # Alert Check and/or Notify Validation
            #

            # Check and see if the values retrieved are what was expected;
            # record the results.  On update, the information if it was
            # requested in the original submission (checks/notify == True)
            if checks == True:
                if service_check == value:
                    host_validation[host]['check_success'].append(service)
                else:
                    host_validation[host]['check_failure'].append(service)
                    #if RETRY_DEBUG == True:
                    #    print "Host: %s   Service : %s" % (host, service)
                    #    print "  Expected Check to be %s, but it was %s" % (value, service_check)

            if notify == True:
                if service_notify == value:
                    host_validation[host]['notify_success'].append(service)
                else:
                    host_validation[host]['notify_failure'].append(service)
                    #if RETRY_DEBUG == True:
                    #    print "Host: %s   Service : %s" % (host, service)
                    #    print "  Expected Notify to be %s, but it was %s" % (value, service_notify)

        if len(host_validation[host]['check_failure']) or len(host_validation[host]['notify_failure']):
            # we have a failure ... see if it is full or partial
            if len(host_validation[host]['check_success']) or len(host_validation[host]['notify_success']):
                host_validation[host]['overall'] = PARTIAL
            else:
                host_validation[host]['overall'] = FAILURE

            # add the host to the entities set
            validation_data['entities'].add(host)

            # add the service(s) to the service_list set
            if len(host_validation[host]['check_failure']):
                for check_service in host_validation[host]['check_failure']:
                    validation_data['service_list'].add(check_service)
            if len(host_validation[host]['notify_failure']):
                for notify_service in host_validation[host]['notify_failure']:
                    validation_data['service_list'].add(notify_service)
        else:
            host_validation[host]['overall'] = SUCCESS

    for host in hostList:
        # if there is one or more failures (full or partial), return
        # the dictionary with the needed information
        if host_validation[host]['overall'] != SUCCESS:
            return (host_validation, validation_data)

    # otherwise, return True
    return (True, True)



##############################################################################
#
# getDMUsernameAndPassword(denaliVariables, enter_user=False, authentication_comment='')
#

def getDMUsernameAndPassword(denaliVariables, enter_user=False, authentication_comment=''):

    auth_payload = {'username':None, 'password':None}

    oStream = denaliVariables['stream']['output']
    iStream = denaliVariables['stream']['input']

    # backup the stdin pointer -- whatever it is at this point.
    stdin_backup = sys.stdin

    # set that pointer to /dev/tty -- to allow user input (authentication with
    # username/password
    sys.stdin = open("/dev/tty")

    if len(denaliVariables["userName"]) == 0:
        detected_user = getpass.getuser()
    else:
        detected_user = denaliVariables["userName"]

    if len(detected_user) > 1:
        denaliVariables["userNameSupplied"] = True

    oStream.write("\nAuthentication required (Digital Marketing Password%s)\n" % authentication_comment)
    oStream.flush()
    if denaliVariables["userNameSupplied"] == False or enter_user == True:
        username = getpass._raw_input("  Username [detected user: %s]: " % detected_user, oStream, iStream)
    else:
        oStream.write("  Username [supplied user: %s]: \n" % detected_user)
        oStream.flush()
        username = detected_user

    if username == '':
        # Empty username, use the username detected
        username = detected_user
    if username == '':
        oStream.write("Denali: Authentication error - empty username\n")
        oStream.flush()
        sys.stdin = stdin_backup
        return False

    password = getpass.getpass("  Password: ")

    # now restore the stdin pointer to whatever it was before.  This should allow
    # the processing to continue as expected
    sys.stdin = stdin_backup

    auth_payload["username"]       = username
    auth_payload["password"]       = password
    denaliVariables['dm_username'] = username
    denaliVariables['dm_password'] = password

    return auth_payload
