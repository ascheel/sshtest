##############################################################################
#
# Denali Analytics Server-Side code
#
#   Version     : 1.0
#   Author      : Mike Hasleton
#   Last Update : June 3, 2019
#   Company     : Adobe Systems, Inc.
#
#   This code serves as the condiut through which meta-data from a denali
#   query is written to a mysql database.
#
#   It uses the bottle API rest functionality to redirect POST-ed data from
#   denali (coming in on http://zenith.dmz.ut1.omniture.com/denali/denali)
#   to the mysql instance at denali.db.sjo.omniture.com.
#
#   After the request is received at the web server, a new fork of the process
#   is spun off (after checking to make sure not too many are already existing)
#   and it then uses the MySQLdb library to connect and INSERT data to mysql.
#

from bottle import route, request

import MySQLdb as mysql
import json
import os
import time
import datetime
import subprocess
import fcntl


######################################
##
## MYSQL database information
##

database_name = "denali"
database_info = "denali"
database_user = "denali"


######################################
##
## Max WSGI Daemon Processes
##   Configured in Apache
##

MAX_WSGI_PROCESSES = 5


######################################
##
## Maximum forks allowed by this code
##

MAX_FORKS_ALLOWED  = 20


######################################
##
## Debugging toggle switch
##

DEBUG = False


######################################
##
## Denali Log Location
##

LOGFILE_NAME = "/var/log/denali.log"


##############################################################################
#
# determineMYSQLConnectivity()
#
#   This function determines the location where denali is running and the
#   access it has to analytics collecting hosts.  If the ping for the mysql
#   host running on the production network returns positive, that is used.
#   And conversely, if that ping is negative, then the development mysql host
#   is checked (and returned if positive).  If both fail, then the function
#   returns False and expects the calling function to act on this information
#   appropriately (i.e., do not try and send analytics data).
#
#   Ping command gives me this error:
#       ping: icmp open socket: Permission denied
#
#   Typically this is because the /bin/ping binary doesn't have the setuid
#   bit set -- but that's not true in my case.  Currently can't work-around
#   the issue; therefore, this function won't be called.  The DNS name and/or
#   IP address of the mysql host will be provided (and trusted that it is
#   both online and accessible).
#

def determineMYSQLConnectivity():

    for hostname in mysql_server_address:
        print "Try host: %s" % hostname
        #response = os.system("/bin/ping -c1 -w2 " + hostname + " > /dev/null 2>&1")
        response = os.system("ping -c1 -w2 " + hostname)

        if response == 0:
            print "Succeed -- found %s is up" % hostname
            return hostname
        else:
            print "Failed -- host %s is not up" % hostname

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
# currentDenaliWrites()
#
#   This function counts the current number of processes running that have
#   been forked for writing SQL requests at the behest of denali.
#
#   This is to help prevent a run-away fork-bomb (by accident or on purpose)
#   to allow the server (httpd server) to stay operational to serve other
#   requests.
#

def currentDenaliWrites():

    # simple grep on the process list for denali processes
    ps = subprocess.Popen("ps aux | grep 'wsgi:denali' | grep -v grep", shell=True, stdout=subprocess.PIPE)
    output = ps.stdout.read()
    ps.stdout.close()
    ps.wait()

    # count the number of lines in the output that contain the string "wsgi:denali"
    # because that is the group name employed in the apache configuration file
    number = output.count("wsgi:denali")

    # uncomment (and watch /var/log/http/error_log) for debugging purposes
    #print "output = %s" % output
    #print "number = %i" % number

    # Take the number found (via the 'ps' command) and subtract from it the maximum
    # wsgi processes (found in /etc/http/conf/httpd.conf in the virtual server section)
    # to get a true number of "forked" threads -- that may not have completed their
    # transaction yet.  Send this number back.
    number = number - MAX_WSGI_PROCESSES
    if number < 0:
        number = 0

    return number



##############################################################################
#
# createDBWriteProcess(payload)
#
#   This function creates a new forked process to handle the actual write, and
#   returns the wsgi process back to apache.
#
#   The forked process is only created if there are 20 (or less) number of
#   processes created (forked) by this code -- hopefully to prevent an intentional
#   or unintentional fork-bomb denial of service on the apache host.  I doubt
#   there will ever be this many, but the code needs to check and make sure so
#   as not to be party to a fork-bomb.
#
#   Spin off the fork, and call the sql write function with the payload that
#   was passed in.
#

def createDBWriteProcess(payload):

    # a number that will cause the loop to execute
    wait = True

    # initial value for sleeping
    SLEEP = 1

    while (wait == True):
        # before forking, count the current number of threads processing
        # denali sql writes
        count = currentDenaliWrites()

        if count > MAX_FORKS_ALLOWED:
            print "Denali: SQL sleep (%s sec)" % SLEEP
            time.sleep(SLEEP)

            #
            # To Do:
            # Of the forked processes, find the oldest one, and if it exceeds a
            # certain time (5 minutes?), kill it.  This would be a new function
            # to handle the logic of this.  The hope here is that by killing off
            # a process (or two or three), it will allow the current one to
            # put itself in line to write to the database.
            #

            # increment the sleep time by 1 second (for the next period
            # of waiting, if needed)
            SLEEP += 1

            if SLEEP >= 10:
                # fail the request -- the server is too busy
                # this puts the search meta-data for analytics in the bit bucket -- oh well
                # 10 + 9 + 8 + 7 + 6 + 5 + 4 + 3 + 2 + 1 = 55 seconds of waiting (long enough)
                print "Denali: MYSQL write timed out (55 seconds) -- too many processes [%i]" % count
                return False
        else:
            wait = False


    # There are MAX_FORKS_ALLOWED (20) or less currently forked processes
    # Go ahead and create a new one
    pid = os.fork()
    if pid == 0:
        # child fork

        # append to the denali log file
        ccode = logPayloadEntry(payload)
        if ccode == True:
            print "Denali: LOG write successful"
        else:
            print "Denali: LOG write failure"

        # write the data
        ccode = writeAnalyticsToMySQL(payload)
        if ccode == 0 or ccode == True:
            print "Denali: MYSQL write successful"
            os._exit(0)
        else:
            print "Denali: MYSQL write failed"
            os._exit(1)
    else:
        # parent fork -- wait for the child(ren) to finish so it doesn't become
        # a defunct Zombie process in the server's process list (then reap it).
        (child_pid, status) = os.waitpid(-1, 0)

        return True



##############################################################################
#
# logPayloadEntry(payload)
#
#   The purpose of this function is to write the data received out to a log file
#   for splunk to capture and forward.
#
#   The request from the security team is to have each query from a user be a
#   single line json block; i.e., {'username':'','timestamp':'', etc.}
#
#   Create a new json object, copying specific elements of the original payload
#   into this one.
#

def logPayloadEntry(payload):

    log_payload = {}

    # turn the string into a json object
    payload = json.loads(payload)

    if payload["host_address"] == "0.0.0.0":
        source_address = ''
    else:
        source_address = payload['host_address']

    if 'query_status' not in payload:
        payload.update({ 'query_status'     : True })
        payload.update({ 'skms_error'       : ''   })

    log_payload.update({ 'dao'              : payload['dao']          })
    log_payload.update({ 'dao_method'       : payload['method']       })
    log_payload.update({ 'instance_version' : payload['version']      })
    log_payload.update({ 'query'            : payload['sql_query']    })
    log_payload.update({ 'query_error'      : payload['skms_error']   })
    log_payload.update({ 'query_status'     : payload['query_status'] })
    log_payload.update({ 'records_affected' : payload['rows']         })
    log_payload.update({ 'request_type'     : payload['request_type'] })
    log_payload.update({ 'src_ip'           : source_address          })
    log_payload.update({ 'user'             : payload['user']         })

    if 'unix_epoch' in payload:
        log_payload.update({ 'query_time' : payload['unix_epoch'] })
    else:
        # Older version of the denali client ... make a unix epoch out of
        # the current time.  This isn't perfect, but for now this is close
        # enough to the time the query was submitted.
        log_payload.update({ 'query_time' : int(time.time()) })

    # turn the json object into a string
    log_payload = json.dumps(log_payload)
    payload     = json.dumps(payload)

    try:
        with open(LOGFILE_NAME, "a") as logfile:
            fcntl.flock(logfile, fcntl.LOCK_EX)
            logfile.write(log_payload)
            logfile.write("\n")
            fcntl.flock(logfile, fcntl.LOCK_UN)
    except Exception as e:
        try:
            print e
        except:
            print "Denali: Error printing exception message"
        return False

    return True



##############################################################################
#
# validatePayload(payload)
#
#   The purpose of this function is to verify that the data included in the
#   payload submitted is valid (and not garbage) before writing it out to the
#   database.
#
#   The checks are the following:
#       1. Are all keys in the payload?
#       2. Basic data integrity checks
#

def validatePayload(payload):

    payload = json.loads(payload)

    query_type = ["Anomoly Authentication", "Attribute Comparison", "Authentication", "Normal", "Update"]

    # check #1:  presence of proper keys
    if ("user"      not in payload or "version"      not in payload or "dao"          not in payload or "method"   not in payload or
        "sql_query" not in payload or "rows"         not in payload or "search_time"  not in payload or "fields"   not in payload or
        "module"    not in payload or "host_address" not in payload or "request_type" not in payload or "timezone" not in payload or
        "time"      not in payload):
        return False

    # check #2:  basic data integrity checks
    if len(payload["user"]) > 50:
        if DEBUG == True:
            print "Username length failed validation check"
            print "user = %s" % payload["user"]
        return False
    if len(payload["version"]) > 30:
        if DEBUG == True:
            print "Version length failed validation check"
            print "version = %s" % payload["version"]
        return False
    if len(payload["dao"]) > 30:
        if DEBUG == True:
            print "DAO length failed validation check"
            print "dao = %s" % payload["dao"]
        return False
    if len(payload["method"]) > 20:
        if DEBUG == True:
            print "Method length failed validation check"
            print "method = %s" % payload["method"]
        return False
    if len(payload["host_address"]) > 15:
        if DEBUG == True:
            print "Host Address length failed validation check"
            print "host address = %s" % payload["host_address"]
        return False
    else:
        ip_address = payload["host_address"].split('.')
        if len(ip_address) != 4:
            if DEBUG == True:
                print "Host Address segment numbers failed validation check"
                print "host address = %s" % payload["host_address"]
            return False
        if len(ip_address[0]) == 0 or len(ip_address[0]) > 3:
            if DEBUG == True:
                print "Host Address first segment failed validation check"
                print "host address segment = %s" % ip_address[0]
            return False
        if len(ip_address[1]) == 0 or len(ip_address[1]) > 3:
            if DEBUG == True:
                print "Host Address second segment failed validation check"
                print "host address segment = %s" % ip_address[1]
            return False
        if len(ip_address[2]) == 0 or len(ip_address[2]) > 3:
            if DEBUG == True:
                print "Host Address third segment failed validation check"
                print "host address segment = %s" % ip_address[2]
            return False
        if len(ip_address[3]) == 0 or len(ip_address[3]) > 3:
            if DEBUG == True:
                print "Host Address fourth segment failed validation check"
                print "host address segment = %s" % ip_address[3]
            return False

    if payload["request_type"] not in query_type:
        if DEBUG == True:
            print "Request Type failed validation check"
            print "request type = %s" % payload["request_type"]
        return False

    # check the rows value -- make sure it is legitimate
    # (integer within a reasonable range)
    try:
        nbr_rows = int(payload["rows"])
    except:
        if DEBUG == True:
            print "Row count failed validation check"
            print "row count = %s" % payload["rows"]
        return False

    if nbr_rows < 0 or nbr_rows > 100000:
        if DEBUG == True:
            print "Row count failed validation check"
            print "row count = %s" % payload["rows"]
        return False


    return True



##############################################################################
#
# writeAnalyticsToMySQL(payload)
#
#   Main function where the write to the mysql database takes place.
#   The return from the function is "true" if the write was successful, and
#   "false" if it failed.
#

def writeAnalyticsToMySQL(payload):

    print "Denali: MYSQL python write enagaged"
    # determine which mysql host the denali code should connect to (production/development)
    #mysqlHost = determineMYSQLConnectivity()
    mysqlHost = "denali.db.pnw.omniture.com"
    database_info = "s5F@!WM@pXyU"

    if mysqlHost == False:
        # Failed to contact either mysql host (prod or dev)
        # No analytics can be recorded, just exit out.
        return False

    # for sending (from client) -- in denali
    #payload = json.dumps(payload)

    # for receiving (at server) -- here at the server from a POST action
    #payload = json.loads(payload)

    # validate the payload before proceeding to write it
    ccode = validatePayload(payload)
    if ccode == False:
        print "Denali: Supplied payload failed a validation check -- not written to mysql"
        return False

    # record the start time for database connection and inserting
    start_time = time.time()

    # connect to the database, returning the cursor and database objects
    try:
        (cursor, database) = mysqlConnect(mysqlHost, database_user, database_info, database_name)

        elapsed_time = time.time() - start_time
    except Exception as e:
        elapsed_time = time.time() - start_time
        print "Denali: Analytics (ERROR): Could not successfully connect to the database @ %s:3306 [time: %s]" % (mysqlHost, elapsed_time)
        print "Error: %s" % e
        return False

    # Insert the information into the denali.analytics database/table
    # The use of \" is because some data fields have single quotes in them and commas -- so the data
    # needs to be completely enclosed in quotations

    payload = json.loads(payload)

    values = "\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\",\"%s\"" % (
             payload["user"],           payload["version"],         payload["dao"],
             payload["method"],         payload["sql_query"],       payload["rows"],
             payload["search_time"],    payload["fields"],          payload["module"],
             payload["host_address"],   payload["request_type"],    payload["timezone"])

    values = values.encode('ascii', 'ignore')
    statement = """INSERT INTO analytics(username,version,dao,\
                                         method,sql_query,`rows`,\
                                         search_time,fields,ext_module,\
                                         host_ip,query_type,timezone) VALUES(%s)""" % values

    # debugging statements -- comment out when released
    #print "cursor   = %s" % cursor
    #print "database = %s" % database
    #print "values = %s" % values
    #print "statement = %s" % statement

    error = False

    try:
        db_write_time = time.time()

        # execute the INSERT statement
        cursor.execute(statement)

        db_elapsed_time    = time.time() - db_write_time
        total_elapsed_time = time.time() - start_time

    except database.Warning:
        print "Denali analytics (INFO): Database Warning received"
        print "Denali analytics (INFO): Database execution time      : %s" % db_elapsed_time
        print "Denali analytics (INFO): Database total elapsed time  : %s" % total_elapsed_time
    except database.OperationalError, e:
        error = True
        print "Denali analytics (ERROR): Database Operational Error  : %s" % e
        print "Denali analytics (INFO) : Database execution time     : %s" % db_elapsed_time
        print "Denali analytics (INFO) : Database total elapsed time : %s" % total_elapsed_time
    except database.ProgrammingError, e:
        error = True
        print "Denali analytics (ERROR): Database Programming Error  : %s" % e
        print "Denali analytics (INFO) : Database execution time     : %s" % db_elapsed_time
        print "Denali analytics (INFO) : Database total elapsed time : %s" % total_elapsed_time
    else:
        print "Denali analytics (INFO): Database DB Conn/DB Exec/Total time : %s / %s / %s" % (elapsed_time, db_elapsed_time, total_elapsed_time)
        database.commit()

    # close out the cursor, commit the changes, close the database
    cursor.close()
    database.close()

    if error == True:
        return False
    else:
        return True



##############################################################################
#
# POST method route to http://<web_server>/denali
#
#   Main entry point from apache.  This function takes the POST method data
#   and calls the createDBWriteProcess function to create a new forked process
#   which then calls the write method to mysql.
#
#   Depending upon whether the write was successful or not, a status of '200'
#   is returned (or not).  I know '200' for a successful write isn't exactly
#   appropriate for an Apache status and that the response itself isn't complete
#   for web standards.
#

@route('/denali', method='POST')
def denali_analytics_entry():

    # guarantee the payload is in json format
    payload = request.json

    # This if statement takes into account the possibility that the data sent
    # here may not come in as expected.  If it comes empty, then check for the
    # potential that it is a StringIO object.
    if payload is not None:
        print "Denali: json payload instance"
    else:
        # check and see if this is a stringIO instance
        payload = request.body.read()
        if len(payload) > 0:
            print "Denali: stringIO payload instance."
        else:
            print "Denali: Analytics submitted payload is EMPTY"
            return {'status':'Failure'}

    # fork off a thread to handle this
    ccode = createDBWriteProcess(payload)

    # old method -- just a straight write on the apache daemon/denali process
    #ccode = writeAnalyticsToMySQL(payload)

    if ccode == True:
        return {'status':'200'}
    else:
        return {'status':'Failure'}



##############################################################################
##############################################################################
##############################################################################
