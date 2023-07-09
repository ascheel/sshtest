#! /usr/bin/env python

import os
import socket, fcntl, struct
import json
import time
import subprocess

#import MySQLdb as mysql

from datetime import datetime

# disable the https warning messages for urllib3
import requests

if "packages" in dir(requests) and "urllib3" in dir(requests.packages) and "disable_warnings" in dir(requests.packages.urllib3):
    requests.packages.urllib3.disable_warnings()



#################################################
##
## REST API Location / URL
##

# Zenith host
rest_url = "http://zenith.dmz.ut1.omniture.com:80/denali/denali"



##############################################################################
#
# determineMYSQLConnectivity(denaliVariables)
#
#   This function determines the location where denali is running and the
#   access it has to analytics collecting hosts.  If the ping for the mysql
#   host running on the production network returns positive, that is used.
#   And conversely, if that ping is negative, then the development mysql host
#   is checked (and returned if positive).  If both fail, then the function
#   returns False and expects the calling function to act on this information
#   appropriately (i.e., do not try and send analytics data).
#
#   Required to execute this are two ip addresses/dns names.  The first stored
#   in "prod_mysql" and the second in "dev_mysql" -- both as strings.
#

def determineMYSQLConnectivity(denaliVariables):

    hostname = prod_mysql
    response = os.system("ping -c1 -w2 " + hostname + " > /dev/null 2>&1")

    if response == 0:
        if denaliVariables["debug"] == True:
            print "Production network MySQL will be used."
        return prod_mysql
    else:
        hostname = dev_mysql
        response = os.system("ping -c1 -w2 " + hostname + " > /dev/null 2>&1")

        if response == 0:
            if denaliVariables["debug"] == True:
                print "Development network MySQL will be used."
            return dev_mysql
        else:
            if denaliVariables["debug"] == True:
                print "No viable connection to MySQL server established."
            return False



##############################################################################
#
# mysqlConnect(mysqlHost, name, info, db="")
#
#   This function establishes a connection to a mysql database with the
#   provided information.
#

def mysqlConnect(mysqlHost, name, info, db=""):

    database  = mysql.connect(mysqlHost, name, info, db)
    db_cursor = database.cursor()

    return (db_cursor, database)



##############################################################################
#
# writeAnalyticsToMySQL(denaliVariables, payload)
#
#   The purpose of this function is to write a payload of data (received in
#   dictionary format) to a mysql host.
#   1. Connectivity to the host is verified (determineMYSQLConnectivity) and
#      a viable address is returned for use.
#   2. The connection is made.
#   3. The data manipulated to an SQL statement of execution.
#   4. Update is sent.
#   5. Everything is closed (cursor, database, etc.)
#
#   Currently this function isn't used directly in Denali; however, it is kept
#   here -- because the code may prove useful in the future.  Denali will make
#   contact with a REST interface and from that server the MYSQL database will
#   be updated (with this function here -- just running on the server itself
#   and not directly part of denali).
#

def writeAnalyticsToMySQL(denaliVariables, payload):

    # determine which mysql host the denali code should connect to (production/development)
    mysqlHost = determineMYSQLConnectivity(denaliVariables)
    if mysqlHost == False:
        # Failed to contact either mysql host (prod or dev)
        # No analytics can be recorded, just exit out.
        return False

    # connect to the database, returning the cursor and database objects
    (cursor, database) = mysqlConnect(mysqlHost, database_user, database_info, database_name)

    # Insert the information into the denali.analytics database/table
    # The use of \" is because some data fields have single quotes in them and commas -- so the data
    # needs to be completely enclosed in quotations
    values = "\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\"" % (
                payload["date"], payload["time"],   payload["timezone"],  payload["user"], payload["version"],
                payload["dao"],  payload["method"], payload["sql_query"], payload["rows"], payload["search_time"],
                payload["fields"], payload["module"], payload["host_address"], payload["request_type"])

    statement = """INSERT INTO analytics(Date,Time,Timezone,Username,Version,DAO,Method,SQL_Query,Rows,Search_Time,Fields,EXT_Module,HOST_IP,Query_Type)
                   VALUES(%s)""" % values

    if denaliVariables["debug"] == True:
        print "cursor = %s" % cursor
        print "values = %s" % values
        print "statement = %s" % statement

    error = False

    try:
        cursor.execute(statement)

    except database.Warning:
        print "Database Warning received"
    except database.OperationalError, e:
        error = True
        print "Database Operational Error: %s" % e
    except database.ProgrammingError, e:
        error = True
        print "Database Programming Error: %s" % e
    except database.IntegrityError, e:
        error = True
        print "Database Integrity Error: %s" % e
    except:
        error = True
        print "Denali:  Unexpected Error while writing to MYSQL."

    # close out the cursor, commit the changes, close the database
    cursor.close()
    database.commit()
    database.close()

    if error == True:
        return False
    else:
        return True



##############################################################################
#
# postDataToRESTAPI(denaliVariables, payload)
#
#   This function "posts" the payload data to the REST URL.
#

def postDataToRESTAPI(denaliVariables, payload):

    # signify that this is a json data dump -- not needed with older method
    headers = {'Context-Type':'application/json'}

    # convert the payload so it can be sent over http
    payload = json.dumps(payload)

    try:
        # requests.post should only support 2 parameters (in early versions)
        # since early versions are running across the network, use that paradigm
        # response = requests.post(rest_url, headers, payload)
        response = requests.post(rest_url, data=payload)
        if response.status_code == 200:
            if denaliVariables["debug"] == True:
                print "Denali POST/MySQL request: Successful\n"
        else:
            if denaliVariables["debug"] == True:
                print "Denali POST/MySQL request Failure: %s" % response
                print "  Error = %s" % response.json()
            return False
    except Exception as e:
        if denaliVariables["debug"] == True:
            print "Denali POST/MySQL request:"
            print "Error: Problem in data \"post\" method: %s" % e
        return False

    return True



##############################################################################
#
# createProcessForAnalyticsData(denaliVariables, request_type, sql_query, searchCategory, method, rows, search_time)
#
#   This function forks off from the parent to store the analytics information
#   via a REST API call to MySQL.  In case this thread hangs or has problems,
#   the main (parent) process continues on and displays the requested information
#   as expected while this process can hang/die/fold-over and it will not show
#   in the parent or the user-experience.
#
#   The draw-back to this is that the parent-process has no idea if the database
#   update succeeded or not.  In fact, is it entirely possible for the parent
#   to have exited and been cleaned up by the operating system before the child
#   finishes (if there are/were problems).  This means that the retrieval of
#   SKMS/CMDB data is more paramount than the recording of it for analytics
#   purposes.
#

def createProcessForAnalyticsData(denaliVariables, request_type, sql_query='', searchCategory='', method='',
                                  rows=0, search_time=0, error_message=''):

    pid = os.fork()
    if pid == 0:
        # child fork -- store analytics data in a database
        if denaliVariables["debug"] == True:
            print "Denali [Analytics] child process: %s" % os.getpid()

        ccode = storeAnalyticsData(denaliVariables, request_type, sql_query, searchCategory, method, rows,
                                   search_time, error_message)

        # exit the forked process successfully (0) or with an error condition (1)
        # use os._exit(#); not os.exit(#) or the program will terminate without completing
        if ccode == True:
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
# storeAnalyticsData(denaliVariables, request_type, sql_query, searchCategory, method, rows, search_time)
#
#   This function receives the meta-data for the denali query and organizes
#   it into a "payload" to send off for a database INSERT.
#
#   It has two possibilities (currently):
#   (1) MYSQL
#   (2) REST API
#
#   The MySQL interface is disabled (commented out) so the REST API interface
#   is the default (only choice) in this function.
#

def storeAnalyticsData(denaliVariables, request_type, sql_query='', searchCategory='', method='',
                       rows=0, search_time=0, error_message=''):

    payload = {}
    fields  = ''

    # get the date/time
    date_time = str(datetime.now()).split(' ')
    date = date_time[0]
    current_time = (date_time[1].split('.'))[0]

    # get the time zone
    timezone = time.tzname[time.daylight]

    # get the host's ip address ("eth0"/"eth1", etc.)
    ip_address = get_ip_address(denaliVariables)

    #print "request_type = %s" % request_type
    #print "sql_query    = %s" % sql_query

    if len(sql_query) == 0:
        return False

    if request_type == "Update":
        try:
            fields = ','.join(sql_query["field_value_arr"].keys())
        except KeyError:
            new_fields = sql_query.get("attributes", '')
            if len(new_fields) > 0:
                fields = ','.join(new_fields)
    elif request_type == "Attribute Comparison":
        try:
            fields = ','.join(sql_query["attribute_names"])
        except KeyError:
            new_fields = sql_query.get("attributes", '')
            if len(new_fields) > 0:
                fields = ','.join(new_fields)
    else:
        if denaliVariables["method"] == "getCurrentOnCallInfo":
            fields = "on_call_queue_list"
            sql_query = sql_query[0]
        else:
            if sql_query.find("SELECT name WHERE") != -1:
                fields = "name"
            else:
                fields = denaliVariables["fields"]

    if searchCategory == '':
        searchCategory = denaliVariables["searchCategory"]

    if method == '':
        method = denaliVariables["method"]


    # store the data in a dictionary (for "easy" access when referencing)
    payload["dao"]          = denaliVariables["searchCategory"]
    #payload["date"]         = date
    payload["time"]         = current_time
    payload["user"]         = denaliVariables["userName"]
    payload["rows"]         = rows
    payload["fields"]       = fields
    payload["module"]       = denaliVariables["externalModule"]
    payload["method"]       = denaliVariables["method"]
    payload["version"]      = denaliVariables["version"]
    payload["timezone"]     = timezone
    if len(error_message):
        payload["query_status"] = False
        payload["skms_error"]   = error_message
    else:
        payload["query_status"] = True
        payload["skms_error"]   = ''

    # the version if given with multiple dashes will cause the updating of data
    # to not work correctly; i.e., 1.83-r1-beta2:November 13, 2017
    # For the above example, if the "-beta2" string is removed, it works correctly.
    if payload["version"].count('-') > 1:
        version_split        = payload["version"].split(':')
        denali_version_split = version_split[0].split('-')
        payload["version"]   = (denali_version_split[0] + '-' +
                                denali_version_split[1] + ':' + version_split[1])

    # handle the case where the query could be a dictionary (e.g., CMDB update)
    if isinstance(sql_query, dict) == True:
        payload["sql_query"] = sql_query
    else:
        payload["sql_query"] = sql_query.strip()

    payload["search_time"]  = search_time
    payload["host_address"] = ip_address.strip()
    payload["request_type"] = request_type

    pattern     = "%Y-%m-%d %H:%M:%S %Z"
    time_string = date + " " + current_time + " " + timezone
    unix_epoch  = int(time.mktime(time.strptime(time_string, pattern)))

    payload["unix_epoch"] = unix_epoch

    if denaliVariables["debug"] == True:
        print
        print "Analytics Payload Data:"
        print "  Request Type    = %s" % request_type
        print "  Date            = %s" % date
        print "  Time            = %s" % current_time
        print "  Time Zone       = %s" % timezone
        print "  Unix Epoch      = %s" % unix_epoch
        print "  User            = %s" % denaliVariables["userName"]
        print "  Version         = %s" % denaliVariables["version"]
        print "  Dao             = %s" % searchCategory
        print "  Ext. Module     = %s" % denaliVariables["externalModule"]
        print "  Method          = %s" % method
        print "  sql query       = %s" % sql_query
        print "  response (rows) = %s" % rows
        print "  search time     = %s" % search_time
        print "  fields          = %s" % fields
        print "  host ip address = %s" % ip_address.strip()
        print "  Query Status    = %s" % payload['query_status']
        print "  Error Message   = %s" % payload['skms_error']
        print

    # Take the current payload and write it out to mysql
    # Only possible/necessary if:
    #   (1) Denali has direct access to a mysql host (port 3306)
    #   (2) A secondary mysql host is needed.  The primary host
    #       is reached via the 'post' method below.
    #ccode = writeAnalyticsToMySQL(denaliVariables, payload)

    # Take the current payload and push it out to a REST URL
    ccode = postDataToRESTAPI(denaliVariables, payload)

    if ccode == True:
        return True
    else:
        return False



##############################################################################
#
# get_ip_address(denaliVariables)
#
#   This function uses a list of ethernet devices to check which one returns
#   a valid IP address.
#

def get_ip_address(denaliVariables):

    device_exceptions     = 0
    (device_list, output) = generateNetworkDeviceList(denaliVariables)

    if denaliVariables["debug"] == True:
        print "Denali:  DeviceList = %s" % device_list

    if len(device_list) == 0:
        # empty list of network devices -- how is this possible?
        if denaliVariables["debug"] == True:
            print "Denali: DeviceList for IP Address is empty."
        return "0.0.0.0"

    for ifname in device_list:

        # Example:
        #       get_ip_address('eth0') --- returns "192.168.0.110"

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            address = socket.inet_ntoa(fcntl.ioctl(s.fileno(),
                                                   0x8915,
                                                   struct.pack('256s', ifname[:15])
                                                  )[20:24])
        except:
            device_exceptions += 1
            continue
        else:
            return address

    os_name = os.uname()[0]

    if device_exceptions == len(device_list) and os_name == "Darwin":
        # assume MACOS, investigate en0 data
        device_data = []
        data_line   = ''

        for character in output:
            if character == '\n':
                device_data.append(data_line)
                data_line = ''
            else:
                data_line += character

        device_dict = {}
        devicename  = None
        for line in device_data:
            if line.startswith('en') == True:
                devicename = line.split(':')[0]
                device_dict.update({devicename:[]})
            elif devicename is not None:
                device_dict[devicename].append(line.strip())

        # At this point, search the configured device output for
        # all 'en*' devices, and then for an IPv4 addresses that
        # are 10.x.x.x.  Any 10.x.x.x address is correct, so grab
        # the first one and return it.
        device_list = device_dict.keys()
        device_list.sort()
        for device in device_list:
            for line in device_dict[device]:
                line = line.split()
                if line[0] == 'inet':
                    address = line[1]
                    if address.startswith('10.') == True:
                        return address

    if denaliVariables["debug"] == True:
        print "Denali: DeviceList not empty, but IP Address(es) not found."

    # If this is returned, it means that a non-empty device list was
    # created from "ip a", but none of the returned devices in that
    # list successfully allowed this code to retieve an ip address
    #
    # So, send back a bogus one (better than nothing)
    return "1.1.1.1"



##############################################################################
#
# generateNetworkDeviceList()
#
#   This function does a Linux "ip a", parses the output and finds all of
#   the devices (ethernet) connected to the machine, returning that as a List
#   of sorted names:  ['eth0','eth1',...]
#

def generateNetworkDeviceList(denaliVariables):

    LINUX = "Linux"
    MACOS = "Darwin"
    BSD   = "FreeBSD"

    # empty list to store "found" devices
    device_list = []

    # get the operating system name
    os_name = os.uname()[0]

    # get the path defined
    os.environ['PATH'] += ':' + denaliVariables['utilityPath']

    # depending upon if this is Linux or MAC/FreeBSD, get the LAN interface
    if os_name == LINUX:
        p = subprocess.Popen(['ip', 'a'], stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)

    elif os_name == MACOS or os_name == BSG:
        p = subprocess.Popen(['ifconfig'], stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)

    else:
        # return an empty list
        return device_list

    (output, error) = p.communicate()
    line = ''

    for character in output:
        if character != '\n':
            line = line + character
            continue

        if line.startswith(' ') or line.startswith('\t'):
            line = ''
            continue

        device = line.split(':')

        if os_name == LINUX:
            lan_device = device[1].strip()
        elif os_name == MACOS or os_name == BSD:
            lan_device = device[0].strip()
        else:
            lan_device = ' '

        # gather either eth[x] devices or en[x] devices (Linux / OS X / FreeBSD)
        if lan_device.startswith("eth") or lan_device.startswith("en") or lan_device.startswith("em"):
            device_list.append(lan_device)


        line = ''

    # sort the list -- the first device is used first, then second, etc.
    device_list.sort()

    return (device_list, output)



##############################################################################
##############################################################################
##############################################################################
##############################################################################
##############################################################################

if __name__ == "__main__":
    pass
