#! /usr/bin/env python

#######################
#                     #
# Authenticate Module #
#                     #
#######################

import getpass
import os
import sys
import time
import SKMS
import datetime
import denali
import denali_analytics
import denali_monitoring
import denali_utility



##############################################################################
#
# authenticateAgainstSKMS(denaliVariables, method)
#
#   The "method" passed in can be one of two:
#       (1) username
#           This is typically the ADOBENET username/password
#       (2) credentials
#           This is typically an api_user, or it could be an ADOBENET
#           username/password combination
#
#   These methods are really close to being similar in order of calls, etc.;
#   however, I separated them so that each could have it's own logic around
#   the authentication method (instead of mixing both and having to detect in
#   multiple places which is which).
#

def authenticateAgainstSKMS(denaliVariables, method, username='', password=''):

    # mark the start time for analytics measurement
    if denaliVariables["analyticsSTime"] == 0.00:
        denaliVariables["analyticsSTime"] = time.time()

    oStream = denaliVariables['stream']['output']

    # check and see if the session file was requested to be cleared
    if denaliVariables["relogin"] == True:
        ccode = deleteSessionFile(denaliVariables)
        # even if this returns false (failure to delete), don't alert,
        # let the code below handle it

        # MRASEREQ-41495
        # SKMS session file deleted above, if this variable is true, whack the
        # monitoring session file as well.
        if denaliVariables['skms_monapi_auth'] == True:
            ccode = denali_monitoring.deleteSessionFile(denaliVariables)

    if method == "username":
        # determine if a username was provided
        #   1.  cli:  --user=<username>?
        #       The userName will be populated with the --user before this function is run.
        #   2.  ~/.denali/config/  user=<username>?
        #       The userName will be populated with this config file user information before
        #       this function is run.
        if len(denaliVariables["userName"]) == 0:
            # no username provided -- assume the username is the logged in user
            denaliVariables["userName"] = getpass.getuser()

            if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                outputString = "Login debug: No username provided -- assume logged in user [%s] as username" % denaliVariables["userName"]
                denali_utility.debugOutput(denaliVariables, outputString)
        else:
            denaliVariables["userNameSupplied"] = True

        #
        # Step #1: Ask SKMS if the user is already authenticated
        ccode = testSKMSAuthentication(denaliVariables, username, password)
        if denaliVariables['testAuth'] == True:
            # state check used if 'denali --version' requested
            if denaliVariables['version'] == "True":
                return ccode

            # default handling of authentication testing (just return true/false)
            if ccode == True:
                denaliVariables['time']['skms_auth_stop'].append(time.time())
                denali.cleanUp(denaliVariables)
                exit(0)
            else:
                if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                    outputString = "Login debug: Failed SKMS authentication test. '--test' enabled.  Exiting."
                    denali_utility.debugOutput(denaliVariables, outputString)
                denaliVariables['time']['skms_auth_stop'].append(time.time())
                denali.cleanUp(denaliVariables)
                exit(1)
        else:
            if ccode == True:
                # authentication successful
                if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                    outputString = "Login debug: SKMS validated user [%s] as authenticated" % username
                    denali_utility.debugOutput(denaliVariables, outputString)
                return True

        #
        # Step #2: Try session file authentication
        ccode = sessionFileAuthentication(denaliVariables)
        if ccode == True:
            # authentication successful
            if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                outputString = "Login debug: Session file authentication was successful."
                denali_utility.debugOutput(denaliVariables, outputString)
            return True

        elif ccode == "Failure":
            # likely a failure in the session file -- cannot delete it
            if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                outputString = "Login debug: Session file could not be deleted."
                denali_utility.debugOutput(denaliVariables, outputString)
            return False

        else:
            if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                outputString = "Login debug: Session file authentication failed -- trying username/password authentication."
                denali_utility.debugOutput(denaliVariables, outputString)

        #
        # Step #3: Session file authentication failed, try username/password
        if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
            outputString = "Login debug: Request SKMS username and password credentials."
            denali_utility.debugOutput(denaliVariables, outputString)

        (username, password) = getUsernameAndPassword(denaliVariables)
        ccode = usernameAndPasswordAuthentication(denaliVariables, username, password)
        if ccode == True:
            # authentication successful
            if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                outputString = "Login debug: Username/Password authentication was successful."
                denali_utility.debugOutput(denaliVariables, outputString)
            if denaliVariables["relogin"] == True:
                hosts_flag = False
                field_flag = False
                for parameter in denaliVariables['cliParameters']:
                    if parameter == ['--hosts', '*']:
                        hosts_flag = True
                    if parameter == ['--fields', 'Empty']:
                        field_flag = True

                # If both flags are true, it means that no search criteria was submitted.
                # This is a test auth only, so just cleanup and exit.
                if hosts_flag == True and field_flag == True:
                    denaliVariables['time']['skms_auth_stop'].append(time.time())
                    denali.cleanUp(denaliVariables)
                    exit(0)

            #
            # MRASEREQ-41495
            # Step #4: Authenticate against MonAPI if requested
            if denaliVariables['skms_monapi_auth'] == True:
                if denaliVariables['debug'] == True or denaliVariables["debugLog"] == True:
                    outputString = "Login debug: Authenticate against the Monitoring API with supplied username/password"
                    denali_utility.debugOutput(denaliVariables, outputString)

                url     = '/auth'
                method  = 'post'
                action  = ''
                payload = {"username":username, "password":password}
                monitoring_data = {'monapi_data':[url, method, action, payload]}
                ccode = denali_monitoring.monitoringAPICall(denaliVariables, monitoring_data, username, password)
                if denaliVariables['debug'] == True or denaliVariables["debugLog"] == True:
                    if ccode == True:
                        outputString = "Login debug: Authentication against the Monitoring API: SUCCESSFUL"
                    else:
                        outputString = "Login debug: Authentication against the Monitoring API: FAILED"
                    denali_utility.debugOutput(denaliVariables, outputString)

            return True
        else:
            # authentication failed
            oStream.write("SKMS Username/Password authentication failed.\n")
            oStream.flush()
            outputString = "SKMS Username/Password authentication failed."
            if denaliVariables['debugLog'] == True:
                denali_utility.debugOutput(denaliVariables, outputString)

            if denaliVariables["analytics"] == True:
                sql_fast = "SELECT name WHERE name = '%s' PAGE 1, 1" % denaliVariables["testHost"]
                request_type = "Authentication"
                elapsed_time = time.time() - denaliVariables["analyticsSTime"]
                denali_analytics.createProcessForAnalyticsData(denaliVariables, request_type, sql_fast, "DeviceDao", "search", 1, elapsed_time, outputString)
                denaliVariables["analyticsSTime"] = 0.00

            return False

    elif method == "credentials":
        # if credentials were submitted (an API key), then disable MFA
        denaliVariables['performMFA'] = False

        # determine if a credentials username/password was obtained
        # FNF = credential "File Not Found"
        if username == "FNF" or username == False or password == False:
            username = ''
            password = ''

        if len(username) > 0:
            denaliVariables["userName"] = username

            if len(password) > 0:
                if denaliVariables["debug"] == True or denaliVariables['debugLog'] == True:
                    outputString = "Login debug: Credentials file username/password will be used."
                    denali_utility.debugOutput(denaliVariables, outputString)
                useCreds = True
            else:
                if denaliVariables["debug"] == True or denaliVariables['debugLog'] == True:
                    outputString = "Login debug: Credentials file password is invalid (length of zero)."
                    denali_utility.debugOutput(denaliVariables, outputString)
                    outputString = "Login debug: Credentials file will not be used."
                    denali_utility.debugOutput(denaliVariables, outputString)
                useCreds = False
        else:
            if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                outputString = "Login debug: Credentials file username is invalid (length of zero)."
                denali_utility.debugOutput(denaliVariables, outputString)
                outputString = "Login debug: Credentials file will not be used."
                denali_utility.debugOutput(denaliVariables, outputString)
            useCreds = False

        # check to see if this username (whether from creds file or --user/config)
        # appears valid.
        # denaliVariables["userName"] will already be populated at this time
        if len(denaliVariables["userName"]) == 0:
            # no username provided -- assume the username is the logged in user
            denaliVariables["userName"] = getpass.getuser()

            if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                outputString = "Login debug: No username provided -- assume logged in user [%s] as username" % denaliVariables["userName"]
                denali_utility.debugOutput(denaliVariables, outputString)

        #
        # Step #1: Ask SKMS if the credential user is already authenticated
        ccode = testSKMSAuthentication(denaliVariables, username, password)
        if denaliVariables['testAuth'] == True:
            denali.cleanUp(denaliVariables)
            if ccode == True:
                denaliVariables['time']['skms_auth_stop'].append(time.time())
                exit(0)
            else:
                if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                    outputString = "Login debug: Failed SKMS authentication test. '--test' enabled.  Exiting."
                    denali_utility.debugOutput(denaliVariables, outputString)
                denaliVariables['time']['skms_auth_stop'].append(time.time())
                exit(1)
        else:
            if ccode == True:
                # authentication successful
                if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                    outputString = "Login debug: SKMS validated user [%s] as authenticated" % username
                    denali_utility.debugOutput(denaliVariables, outputString)
                return True

        #
        # Step #2: Try session file authentication
        ccode = sessionFileAuthentication(denaliVariables)
        if ccode == True:
            # authentication successful
            if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                outputString = "Login debug: Session file authentication was successful."
                denali_utility.debugOutput(denaliVariables, outputString)
            return True

        elif ccode == "Failure":
            # likely a failure in the session file -- cannot delete it
            if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                outputString = "Login debug: Session file could not be deleted."
                denali_utility.debugOutput(denaliVariables, outputString)
            return False

        else:
            if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                outputString = "Login debug: Session file authentication failed -- trying username/password authentication."
                denali_utility.debugOutput(denaliVariables, outputString)

        #
        # Step #3: Session file authentication failed, try username/password
        if useCreds == False:
            # only request a new username/password if the creds file didn't
            # have them for us.
            if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                outputString = "Login debug: Request SKMS username and password credentials."
                denali_utility.debugOutput(denaliVariables, outputString)
            (username, password) = getUsernameAndPassword(denaliVariables)

        ccode = usernameAndPasswordAuthentication(denaliVariables, username, password)
        if ccode == True:
            # authentication successful
            if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                if useCreds == True:
                    outputString = "Login debug: Credentials Username/Password authentication was successful."
                else:
                    outputString = "Login debug: Username/Password authentication was successful."
                denali_utility.debugOutput(denaliVariables, outputString)
            return True
        else:
            # authentication failed
            if useCreds == True:
                outputString = "Login debug: Credentials Username/Password authentication failed."
            else:
                outputString = "Login debug: Username/Password authentication failed."

            if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                denali_utility.debugOutput(denaliVariables, outputString)

            if denaliVariables["analytics"] == True:
                sql_fast = "SELECT name WHERE name = '%s' PAGE 1, 1" % denaliVariables["testHost"]
                request_type = "Authentication"
                elapsed_time = time.time() - denaliVariables["analyticsSTime"]
                denali_analytics.createProcessForAnalyticsData(denaliVariables, request_type, sql_fast, "DeviceDao", "search", 1, elapsed_time, outputString)
                denaliVariables["analyticsSTime"] = 0.00
            return False

    else:
        return False



##############################################################################
#
# customizeSKMSClientStrings(denaliVariables, api)
#

def customizeSKMSClientStrings(denaliVariables, api):

    client_version = denaliVariables['version'].split(':')[0]
    client_type    = "denali-python-requests"

    api.set_custom_client_type(client_type)
    api.set_custom_client_version(client_version)



##############################################################################
#
# testSKMSAuthentication(denaliVariables, username, password)
#
#   Ask SKMS if the user running denali is already authenticated against SKMS.
#   The 'getLoginInfo' method returns True/False depending upon the currently
#   requested user's authentication status.  True is authenticated; False is not.
#

def testSKMSAuthentication(denaliVariables, username, password):

    if username == '':
        username = denaliVariables['userName']

    # if the session file doesn't exist, then the test will fail with a
    # python stack.
    if checkSessionFileStatus(denaliVariables) == True:
        if denaliVariables['debug'] == True or denaliVariables['debugLog'] == True:
            outputString = "Login debug: API URL = %s" % denaliVariables['apiURL']
            denali_utility.debugOutput(denaliVariables, outputString)

        api_url = denaliVariables["apiURL"]
        api = SKMS.WebApiClient(username, password, api_url, True)
        customizeSKMSClientStrings(denaliVariables, api)
        api.disable_ssl_chain_verification()
        returnValue = api.send_request('SkmsWebApi', 'getLoginInfo')
        denaliVariables['api'] = api
    else:
        return False

    return returnValue



##############################################################################
#
# sessionFileAuthentication(denaliVariables)
#
#   See if the user has an existing (valid) session file.
#

def sessionFileAuthentication(denaliVariables):

    # Do not automatically run denali commands with 'root', 'netsaint', or 'httpd' users.
    # This means that authentication via a session file is restricted from these users.
    detected_user = getpass.getuser()
    if (detected_user == "root" or detected_user == "netsaint" or detected_user == "httpd"):
        if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
            outputString = "Login debug: [%s] user detected -- session file not used; authentication required." % detected_user
            denali_utility.debugOutput(denaliVariables, outputString)

        return False

    # Does a user session file exist?
    if checkSessionFileStatus(denaliVariables) == True:

        # authenticate against the database
        if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
            outputString = "Login debug: Session file found for user [%s]" % denaliVariables["userName"]
            denali_utility.debugOutput(denaliVariables, outputString)

        ccode = validateSKMSAuthentication(denaliVariables["userName"], '', False, denaliVariables)
        if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
            outputString = "Login debug: (1) ccode = %s" % ccode
            denali_utility.debugOutput(denaliVariables, outputString)

        if ccode == "KeyError":
            if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                outputString = "Login debug: Session file expired -- handle appropriately"
                denali_utility.debugOutput(denaliVariables, outputString)

            ccode = deleteSessionFile(denaliVariables)
            if ccode == False:
                # problem deleting the session file -- fail this run
                if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                    outputString = "\nERROR:  SKMS KeyError"
                    denali_utility.debugOutput(denaliVariables, outputString)
                    outputString = "        Could not delete user session file (~/.skms/sess_%s.json) to work-around this issue." % denaliVariables["userName"]
                    denali_utility.debugOutput(denaliVariables, outputString)

                    # Return "Failure" so the appropriate error message (if debug is on) can be displayed
                    # "Failure" also indicates to the calling code that the session file deletion failed.
                    #
                    # In this case, only if "debug" is set to True will the authentication completely fail
                    # if the deletion of the session file fails.  Otherwise (debug is False), the code will
                    # attempt authentication via username/password (fingers crossed that the session file
                    # can be overwritten by the SKMS methods -- or it will probably completely fail to go
                    # any further at that point).
                    #
                    # May need to revisit this choice (only fail in debug-mode) in the future if there are
                    # problems with this.
                    return "Failure"

            # If the session file deletion succeeds (or fails), now the user needs to login with their
            # (username/password).  The code signals this is the next step with a return of "False";
            # meaning that the status of the session file is "False" (cannot be used).  The calling code
            # then automatically falls through to the request for a username/password authentication.
            return False

        else:
            return ccode

    else:
        if denaliVariables["debug"] == True or denaliVariables["debugLog"]:
            outputString = "Login debug: Session file for user [%s] doesn't exist" % denaliVariables["userName"]
            denali_utility.debugOutput(denaliVariables, outputString)

        return False



##############################################################################
#
# printInitialMFAMessage(denaliVariables, mfaDictionary)
#
#   Print the message first seen by the user when using MFA.  This should list
#   all of the available methods for the user, and give them basic help on
#   what to do next.
#

def printInitialMFAMessage(denaliVariables, mfaDictionary):

    supported_methods = 0
    allowed_tokens    = ['okta_push', 'okta_token', 'symantec_token']
    oStream           = denaliVariables['stream']['output']

    # only return back if 'push' is an available method for the user
    if denaliVariables['mfa_auto_push'] == True:
        if 'okta_push' in mfaDictionary['data']['mfa_methods']:
            if denaliVariables['debug'] == True or denaliVariables['debugLog']:
                outputString = "Login debug: MFA Auto Push enabled"
                denali_utility.debugOutput(denaliVariables, outputString)
            oStream.write("  Initiating automatic token push for OKTA\n")
            oStream.flush()
            return

    oStream.write("\nMulti-Factor Authentication is required for SKMS.  User available methods:\n")
    mfaDictionary['data']['mfa_methods'].sort()
    for method in mfaDictionary['data']['mfa_methods']:
        if method in allowed_tokens:
            oStream.write("  %s\n" % method)
            supported_methods += 1
        else:
            oStream.write("  %s    (Not Supported)\n" % method)

    # no sense in proceeding if there are no supported methods -- check and make sure
    if supported_methods == 0:
        oStream.write("Denali:  No supported MFA methods are available. Authentication refused.\n")
        oStream.flush()
        denali.cleanUp(denaliVariables)
        exit(1)

    if 'okta_push' in mfaDictionary['data']['mfa_methods']:
        oStream.write("Hit enter to send Okta Verify push notification")
        if supported_methods > 1:
            oStream.write(" (")
    else:
        oStream.write("Use ")

    if 'okta_token' in mfaDictionary['data']['mfa_methods']:
        oStream.write("o=<OTP> for Okta token")

    if 'symantec_token' in mfaDictionary['data']['mfa_methods']:
        if 'okta_token' in mfaDictionary['data']['mfa_methods']:
            oStream.write(' or ')
        oStream.write("s=<OTP> for Symantec token")

    if supported_methods > 1 and 'okta_push' in mfaDictionary['data']['mfa_methods']:
        oStream.write("):")
    else:
        oStream.write(":")

    oStream.flush()



##############################################################################
#
# validateMFAResponse(denaliVariables, mfa_response, username, mfaDictionary)
#
#   Make sure that the response entered by the user is consistent with the
#   methods available to them and that the format is correct.
#
#   If either of these (format/method) is incorrect, print a syntax error
#   message stating that, and then exit denali.
#

def validateMFAResponse(denaliVariables, mfa_response, username, mfaDictionary):

    oStream = denaliVariables['stream']['output']

    mfa_response.replace(' ','')

    if len(mfa_response) == 0:
        okta_type  = 'okta_push'
        okta_value = ''

    elif mfa_response.startswith('o='):
        okta_type  = 'okta_token'
        okta_value = mfa_response.split('=')[1]

    elif mfa_response.startswith('s='):
        okta_type  = 'symantec_token'
        okta_value = mfa_response.split('=')[1]

    else:
        oStream.write("Denali MFA Error:  Denali does not recognize the MFA method submitted: %s\n" % mfa_response)
        oStream.flush()
        denali.cleanUp(denaliVariables)
        exit(1)

    if okta_type not in mfaDictionary['data']['mfa_methods']:
        oStream.write("SKMS MFA Error:  %s is not a valid method for user %s\n" % (okta_type, username))
        oStream.flush()
        denali.cleanUp(denaliVariables)
        exit(1)

    return (okta_type, okta_value)



##############################################################################
#
# getUserMFAResponse(denaliVariables, mfaDictionary, username)
#
#   Get the response from the user; <ENTER> or the token value.
#

def getUserMFAResponse(denaliVariables, mfaDictionary, username):

    oStream = denaliVariables['stream']['output']
    iStream = denaliVariables['stream']['input']

    if denaliVariables['mfa_auto_push'] == True:
        if 'okta_push' in mfaDictionary['data']['mfa_methods']:
            return ('okta_push', '')
        else:
            # user has mfa_auto_push enabled, but that isn't an accepted method for
            # them -- sorry, user input required.
            if denaliVariables['debug'] == True or denaliVariables['debugLog'] == True:
                outputString = "MFA:  mfa_auto_push enabled.  okta_push isn't accepted method for %s" % username
                denali_utility.debugOutput(denaliVariables, outputString)

    # MRASETEAM-40472
    stdin_backup = sys.stdin
    sys.stdin    = open("/dev/tty")
    mfa_response = getpass._raw_input(" ", oStream, iStream)
    sys.stdin    = stdin_backup

    (okta_type, okta_value) = validateMFAResponse(denaliVariables, mfa_response, username, mfaDictionary)

    return (okta_type, okta_value)



##############################################################################
#
# processOTP(denaliVariables, otp_type, otp_value, username)
#
#   This function does the processing of the token to verify if the user is
#   allowed access to SKMS.  If 'push' is used, it has a 30 second timeout
#   after sending the request to SKMS before it will give up.  If this timeout
#   is hit, it means one of two things (1) the user didn't acknowledge the
#   push request on their phone/device, or (2) SKMS did not respond or get a
#   response to the request.  In either case, 30 seconds is a long enough wait
#   before giving up.
#

def processOTP(denaliVariables, otp_type, otp_value, username):

    TIMEOUT_DELAY      = 30     # seconds
    PAUSE_DELAY        = 1      # seconds
    USER_ENTERTAINMENT = True   # print dots as each second passes while waiting
    oStream            = denaliVariables['stream']['output']

    payload = {
                'mfa_method' : otp_type,
                'mfa_token'  : otp_value,
                'username'   : username
              }

    api = denaliVariables['api']

    if otp_type == 'okta_push':
        status     = False
        total_time = 0

        if USER_ENTERTAINMENT == True:
            oStream.write("  Waiting for OKTA push acceptance .")
            oStream.flush()

        while (status != 'success'):
            ccode = api.send_request('SkmsWebApi', 'performMfa', payload)
            if ccode != True:
                displaySKMSMFAErrorMessage(denaliVariables, api)

            mfaDictionary = api.get_response_dictionary()

            if 'status' in mfaDictionary:
                if mfaDictionary['status'] == 'success':
                    # result sent successfully to SKMS, now check the return
                    # status for the otp push action
                    if 'status' in mfaDictionary['data']:
                        status = mfaDictionary['data']['status']

                    if status == 'success':
                        if USER_ENTERTAINMENT == True:
                            oStream.write(". Accepted!\n")
                            oStream.flush()
                        return True
                    elif status == 'waiting' or status == False:
                        # sleep ... waiting for user acknowledgment, or system to respond
                        if USER_ENTERTAINMENT == True:
                            oStream.write(".")
                            oStream.flush()
                        time.sleep(PAUSE_DELAY)
                        total_time += 1
                        if total_time > TIMEOUT_DELAY:
                            oStream.write("\n  Denali: MFA Authentication halted (%ss timeout expired)\n" % TIMEOUT_DELAY)
                            oStream.flush()
                            denali.cleanUp(denaliVariables)
                            exit(1)
                    else:
                        # Some unexpected status -- print it for further investigation
                        oStream.write("Denali: Unexpected MFA status of [%s] received\n" % status)
                        oStream.flush()
                        denali.cleanUp(denaliVariables)
                        exit(1)
                else:
                    # Failure of SKMS to successfully respond to MFA request
                    oStream.write("Denali: MFA status failure of [%s] received\n" % mfaDictionary['status'])
                    oStream.flush()
                    denali.cleanUp(denaliVariables)
                    exit(1)
            else:
                # malformed response (no 'status' key) -- exit instead of spinning
                oStream.write("Denali: Unexpected MFA response from SKMS\nmfaDictionary: %s\n" % mfaDictionary)
                oStream.flush()
                denali.cleanUp(denaliVariables)
                exit(1)

    else:
        ccode = api.send_request('SkmsWebApi', 'performMfa', payload)
        if ccode != True:
            displaySKMSMFAErrorMessage(denaliVariables, api)

        mfaDictionary = api.get_response_dictionary()

        if 'data' in mfaDictionary and 'status' in mfaDictionary['data']:
            if mfaDictionary['data']['status'] == 'success':
                if denaliVariables['debug'] == True or denaliVariables['debugLog'] == True:
                    outputString = "Denali: MFA status = %s" % mfaDictionary['data']['status']
                    denali_utility.debugOutput(denaliVariables, outputString)
                return True
            else:
                oStream.write("Denali: MFA authentication failure\n")
                oStream.flush()
                denali.cleanUp(denaliVariables)
                exit(1)
        else:
            oStream.write("Denali: Malformed dictionary returned from SKMS MFA attempt\nmfaDictionary: %s\n" % mfaDictionary)
            oStream.flush()
            denali.cleanUp(denaliVariables)
            exit(1)



##############################################################################
#
# displaySKMSMFAErrorMessage(denaliVariables, api)
#

def displaySKMSMFAErrorMessage(denaliVariables, api):

    oStream       = denaliVariables['stream']['output']
    mfaDictionary = api.get_response_dictionary()

    try:
        if 'messages' in mfaDictionary and 'message' in mfaDictionary['messages'][0]:
            error_message = mfaDictionary['messages'][0]['message']
        else:
            error_message = "Denali: Error sending/receiving MFA response from SKMS"
    except Exception as e:
        error_message  = "Denali: Error sending/receiving MFA response from SKMS\n"
        error_message += "mfaDictionary = %s\n" % mfaDictionary
        error_message += str(e)

    oStream.write("SKMS Error: " + error_message + '\n')
    oStream.flush()
    denali.cleanUp(denaliVariables)
    exit(1)



##############################################################################
#
# performMFA(denaliVariables, username, password)
#
#   Entry point to perform the user MFA authentication.  The code does 4
#   basic things:
#       (1) Ask SKMS about the user (mfa methods supported)
#       (2) Print out the message(s) about the supported methods
#       (3) Get the MFA response (what the user types in)
#       (4) Process the submitted data to allow authentication
#

def performMFA(denaliVariables, username, password):

    payload = {'username':username, 'password':password}
    api_url = denaliVariables["apiURL"]
    oStream = denaliVariables['stream']['output']

    if denaliVariables['debug'] == True:
        print "++Entered performMFA\n"
        print "Login debug: API URL = %s" % api_url

    api = SKMS.WebApiClient(username, password, api_url, True)
    customizeSKMSClientStrings(denaliVariables, api)
    api.disable_ssl_chain_verification()
    denaliVariables['api'] = api
    ccode = api.send_request('SkmsWebApi', 'performAuth', payload)
    if ccode != True:
        displaySKMSMFAErrorMessage(denaliVariables, api)

    mfaDictionary = api.get_response_dictionary()

    # Fix for improper SKMS API return during an authentication process that made the error
    # return from Denali appear as a Denali problem, when in fact it was an SKMS issue.
    # The mfaDictionary came back as 'False' even though the api.send_request() came back
    # as 'True'.  This will catch that case and handle it as expected.
    if isinstance(mfaDictionary, bool):
        displaySKMSMFAErrorMessage(denaliVariables, api)

    if denaliVariables['debug'] == True or denaliVariables['debugLog'] == True:
        outputString = "mfaDictionary = %s" % mfaDictionary
        denali_utility.debugOutput(denaliVariables, outputString)

    # Validate that the SKMS authentication was successful before continuing
    if len(mfaDictionary['messages']) and 'message' in mfaDictionary['messages'][0]:
        if mfaDictionary['messages'][0]['message'] == 'Authentication failed':
            return False

    # Current MFA Methods supported:
    #   - okta_push
    #   - okta_token
    #   - symantec_token

    if mfaDictionary['status'] == 'success':
        if mfaDictionary['data']['status'] == 'mfa_required':

            printInitialMFAMessage(denaliVariables, mfaDictionary)
            (otp_type, otp_value) = getUserMFAResponse(denaliVariables, mfaDictionary, username)
            mfaRetValue = processOTP(denaliVariables, otp_type, otp_value, username)

            if mfaRetValue == True:
                return True
            else:
                if denaliVariables['debug'] == True or denaliVariables['debugLog'] == True:
                    outputString = "MFA Return Value = %s" % mfaRetValue
                    denali_utility.debugOutput(denaliVariables, outputString)
                return False
        else:
            # mfa not required for the user
            if denaliVariables['debug'] == True or denaliVariables['debugLog'] == True:
                outputString = "Login debug: MFA data status = %s" % mfaDictionary['data']['status']
                denali_utility.debugOutput(denaliVariables, outputString)
            return True
    else:
        oStream.write("SKMS problem    : SKMS is not responding to MFA data requests\n")
        oStream.write("SKMS MFA status : %s\n" % mfaDictionary['status'])
        oStream.flush()
        denali.cleanUp(denaliVariables)
        exit(1)



##############################################################################
#
# usernameAndPasswordAuthentication(denaliVariables, username, password)
#
#   This function will attempt to authenticate the user against SKMS when
#   provided with a username and password.
#

def usernameAndPasswordAuthentication(denaliVariables, username, password):

    # mark the start time for analytics measurement
    if denaliVariables["analyticsSTime"] == 0.00:
        denaliVariables["analyticsSTime"] = time.time()

    oStream = denaliVariables['stream']['output']

    # New username/password + MFA required for SKMS authentication
    if denaliVariables['performMFA'] == True:
        # perform multi-factor authentication process
        ccode = performMFA(denaliVariables, username, password)
        return ccode

    else:
        # Old username/password required for SKMS authentication
        ccode = validateSKMSAuthentication(username, password, '', denaliVariables)
        if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
            outputString = "Login debug: (2) ccode = %s" % ccode
            denali_utility.debugOutput(denaliVariables, outputString)

        if ccode == "KeyError":
            if str(denaliVariables["api"].get_error_type()) == "False":
                oStream.write("Login debug: \"KeyError\": Incorrect SKMS username and/or password entered.\n")
            else:
                printSKMSReturnMessage(denaliVariables, api, False)
            return False
        elif ccode == False:
            # if skms authentication fails, bail out.
            return False
        else:
            return True



##############################################################################
#
# validateSKMSAuthentication(username, password, silent_run, denaliVariables)
#

def validateSKMSAuthentication(username, password, silent_run, denaliVariables):

    # mark the start time for analytics measurement
    if denaliVariables["analyticsSTime"] == 0.00:
        denaliVariables["analyticsSTime"] = time.time()

    denaliVariables['time']['skms_auth_start'].append(time.time())
    api_url = denaliVariables["apiURL"]
    oStream = denaliVariables['stream']['output']

    if denaliVariables['debug'] == True or denaliVariables['debugLog'] == True:
        outputString = "Login debug: API URL = %s" % denaliVariables['apiURL']
        denali_utility.debugOutput(denaliVariables, outputString)

    try:
        api = SKMS.WebApiClient(username, password, api_url, True)
    except AttributeError as e:
        e = str(e)
        if e == "'NoneType' object has no attribute 'strip'":
            print "Denali Error: Problem with the credentials file syntax for session_path"
        else:
            print "SKMS Error: %s" % e
        denali.cleanUp(denaliVariables)
        exit(1)

    customizeSKMSClientStrings(denaliVariables, api)
    api.disable_ssl_chain_verification()
    denaliVariables['time']['skms_auth_stop'].append(time.time())

    # assign the API value to denaliVariables
    denaliVariables["api"] = api

    if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
        outputString = "Login debug: API URL    = %s" % denaliVariables["apiURL"]
        denali_utility.debugOutput(denaliVariables, outputString)
        outputString = "Login debug: api return = %s" % api
        denali_utility.debugOutput(denaliVariables, outputString)

    # Run a simple query to validate database access
    # Use the = 'host_name' query -- it's faster (it is likely indexed) than a
    # LIKE query; although I doubt the difference will be noticed, if at all.
    # The hope is that the fast query succeedes (unless the host is removed
    # from the database); failing that, a generic wildcard query is issued as
    # a catch-all (just in case all else fails).

    sql_fast = "SELECT name WHERE name = '%s' PAGE 1, 1" % denaliVariables["testHost"]
    sql_slow = "SELECT name WHERE name LIKE '%b%' PAGE 1, 1"
    request_type = "Authentication"

    param_dict_fast = { "query" : "SELECT name WHERE name = '%s' PAGE 1, 1" % denaliVariables["testHost"] }
    param_dict_slow = { "query" : "SELECT name WHERE name LIKE '%b%' PAGE 1, 1" }

    try:
        # try the fast (hopefully indexed) query first
        #if denaliVariables["debug"] == True:
        #    print "Login debug: Fast query issued against [%s]" % denaliVariables["testHost"]

            # send the "fast" authentication request check off (verify the username/password can access SKMS)
            # this is only checked when the --debug switch is used
        #    ccode = api.send_request('DeviceDao', 'search', param_dict_fast)
        #else:
            # unless --debug is used, just return with "True" without a separate host query validation
        #    ccode = True

        # put the original authentication code-flow back as it created problems when the session
        # file expired (it wouldn't ask for a new user/password in this case until the session
        # file was deleted).
        denaliVariables['time']['skms_start'].append(time.time())
        ccode = api.send_request('DeviceDao', 'search', param_dict_fast)
        denaliVariables['time']['skms_stop'].append(time.time())

        # check to see if an SKMS error was returned (outside of an exception)
        if len(api.get_error_message()) > 0:
            printSKMSReturnMessage(denaliVariables, api, False, True)
            return False

        # record analytics for the authentication attempt
        if denaliVariables["analytics"] == True:
            elapsed_time = time.time() - denaliVariables["analyticsSTime"]
            denali_analytics.createProcessForAnalyticsData(denaliVariables, request_type, sql_fast, "DeviceDao", "search", 1, elapsed_time)
            denaliVariables["analyticsSTime"] = 0.00

            if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                outputString = "Analytics debug: Fast query initiated"
                denali_utility.debugOutput(denaliVariables, outputString)

        if ccode != True:
            # the specific host search failed -- try a LIKE search for all hosts that
            # have a 'b' in the name somewhere (obviously a slower search criteria)
            if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                outputString = "Login debug: Fast query failed."
                denali_utility.debugOutput(denaliVariables, outputString)
                outputString = "Login debug: Slow query issued against [%b%]"
                denali_utility.debugOutput(denaliVariables, outputString)

            # send the "slow" authentication request check off (verify the username/password can access SKMS)
            ccode = api.send_request('DeviceDao', 'search', param_dict_slow)

            # check to see if an SKMS error was returned (outside of an exception)
            if len(api.get_error_message()) > 0:
                printSKMSReturnMessage(denaliVariables, api, False)
                return False

            # record analytics for the authentication attempt
            if denaliVariables["analytics"] == True:
                elapsed_time = time.time() - denaliVariables["analyticsSTime"]
                denali_analytics.createProcessForAnalyticsData(denaliVariables, request_type, sql_slow, "DeviceDao", "search", 1, elapsed_time)
                denaliVariables["analyticsSTime"] = 0.00

            if ccode == True:
                # set this "authentication was successful" flag
                denaliVariables["authSuccessful"] = True
                return True
            else:
                # still failed -- fail the entire request now
                if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                    outputString = "Login debug: Slow query failed."
                    denali_utility.debugOutput(denaliVariables, outputString)
                    outputString = "Login debug: api ccode = %s" % ccode
                    denali_utility.debugOutput(denaliVariables, outputString)
                printSKMSReturnMessage(denaliVariables, api, silent_run)
                return False

        # set this "authentication was successful" flag
        denaliVariables["authSuccessful"] = True
        return True

    except KeyError:
        return "KeyError"
    except:
        oStream.write("Denali: Unexpected SKMS Error\n")
        oStream.flush()
        printSKMSReturnMessage(denaliVariables, api, silent_run)
        return False

    else:
        # catch all -- any other errors
        printSKMSReturnMessage(denaliVariables, api, silent_run)
        return False



##############################################################################
#
# printSKMSReturnMessage(denaliVariables, api, silent_run, first_run=False)
#

def printSKMSReturnMessage(denaliVariables, api, silent_run, first_run=False):

    oStream = denaliVariables['stream']['output']

    if silent_run == False:
        # print error message stating reason for the failure
        if first_run == True and (api.get_error_message().startswith("You must log in in order") or
                                  api.get_error_message().startswith("Unable to JSON decode the response string")):
            return

        oStream.write("\nERROR:\n")
        oStream.write("   STATUS: "  + api.get_response_status() + '\n')
        oStream.write("   TYPE: "    + str(api.get_error_type()) + '\n')
        oStream.write("   MESSAGE: " + api.get_error_message()   + '\n')
        oStream.write('\n')
        oStream.flush()

        error_message = (str(api.get_response_status()) + ' :: ' +
                         str(api.get_error_type())      + ' :: ' +
                         str(api.get_error_message()))

    if denaliVariables["analytics"] == True:
        sql_fast = "SELECT name WHERE name = '%s' PAGE 1, 1" % denaliVariables["testHost"]
        request_type = "Authentication"
        elapsed_time = time.time() - denaliVariables["analyticsSTime"]
        denali_analytics.createProcessForAnalyticsData(denaliVariables, request_type, sql_fast, "DeviceDao", "search", 1, elapsed_time)
        denaliVariables["analyticsSTime"] = 0.00



##############################################################################
#
# getUsernameAndPassword(denaliVariables)
#

def getUsernameAndPassword(denaliVariables):

    # set the start time to zero -- because of user input
    denaliVariables["analyticsSTime"] = 0.00

    oStream = denaliVariables['stream']['output']
    iStream = denaliVariables['stream']['input']

    if len(denaliVariables["userName"]) == 0:
        detected_user = getpass.getuser()
    else:
        detected_user = denaliVariables["userName"]

    # if the user's session has timed out, and they don't have a configuration
    # file (.denali/config) and they asked for stdin reading, then this should
    # help fix a problem with the authentication.
    #
    # backup the stdin pointer -- whatever it is at this point.
    stdin_backup = sys.stdin

    # set that pointer to /dev/tty -- to allow user input (authentication with
    # username/password
    sys.stdin = open("/dev/tty")

    if denaliVariables['skms_monapi_auth'] == True:
        oStream.write("\nSKMS Authentication required (ADOBENET/Digital Marketing Password)\n")
    else:
        oStream.write("\nSKMS Authentication required (ADOBENET Password)\n")

    if denaliVariables["userNameSupplied"] == False or denaliVariables['authenticateOnly'] == True:
        username = getpass._raw_input("  Username [detected user: %s]: " % detected_user, oStream, iStream)
    else:
        oStream.write("  Username [supplied user: %s]: \n" % detected_user)
        oStream.flush()
        username = detected_user

    if username == '':
        # Empty username, use the username detected
        username = detected_user

    password = getpass.getpass("  Password: ")

    # now restore the stdin pointer to whatever it was before.  This should allow
    # the processing to continue as expected
    sys.stdin=stdin_backup

    return (username, password)



##############################################################################
##############################################################################
##############################################################################
##############################################################################
##############################################################################



##############################################################################
#
# searchForValidSessionFile(denaliVariables)
#

def searchForValidSessionFile(denaliVariables):

    modifyTimes = []

    # get the current time
    currentTime = time.strftime("%a %m %d %H %M %S %Y")
    currentTime = currentTime.split(' ')

    sessionFiles = collectListOfSessionFiles(denaliVariables)

    if sessionFiles == False or len(sessionFiles) == 0:
        # no session files found -- authenticate manually
        return False

    # get the session file(s) last modify time
    for sFile in sessionFiles:
        (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(sFile)
        mtime = time.ctime(mtime)
        mtime = mtime.replace("Last modified: ", '')
        mtime = mtime.replace(':', ' ')
        mtime = mtime.strip()
        mtime = mtime.split(' ')
        modifyTimes.append(mtime)

    # if there are no modify times, then return False
    if len(modifyTimes) == 0:
        # modify times are non-existant, authenticate manually
        return False

    # get an mtime ordered list of session files
    sessionFiles = orderSessionList(sessionFiles, currentTime, modifyTimes)

    # the ordered list can return False under the following circumstances:
    #   (1) there are no session files
    #   (2) there are session files, but they have expired
    if sessionFiles == False:
        return False

    for sFile in sessionFiles:
        username = returnUserName(sFile)

        rCode = validateAuthentication(username, '', True, denaliVariables)
        if rCode == False:
            # authentication failed; try the next session file
            continue
        else:
            # authentication succeeded; continue running the query
            return rCode

    return False



##############################################################################
#
# returnUserName(sessionFile)
#

def returnUserName(sessionFile):

    location = sessionFile.find("sess_")
    fileName = sessionFile[location:]

    location = fileName.find('_')
    username = fileName[(location + 1):]

    location = username.find('.json')
    username = username[:location]

    return username



##############################################################################
#
# orderSessionList(sessionFiles, currentTime, modifyTimes)
#

def orderSessionList(sessionFiles, currentTime, modifyTimes):

    # order of operations for this
    #
    # 1. file must have mtime within the last _24_ hours
    # 2. username session file
    # 3. any other session file in the .skms directory

    SKMS_SESSION_INTERVAL = 24      # hours
    orderedList = []
    sessionList = []

    months = {'Jan':1, 'Feb':2, 'Mar':3, 'Apr':4,  'May':5,  'Jun':6,
              'Jul':7, 'Aug':8, 'Sep':9, 'Oct':10, 'Nov':11, 'Dec':12}

    cYear   = int(currentTime[6])
    cMonth  = int(currentTime[1])
    cDay    = int(currentTime[2])
    cHour   = int(currentTime[3])
    cMinute = int(currentTime[4])

    currTime = datetime.datetime(year=cYear, month=cMonth, day=cDay, hour=cHour, minute=cMinute)

    # 10 hour calculations
    for (index, mtime) in enumerate(modifyTimes):
        mMonth  = mtime[1]
        mMonth  = months[mMonth]

        # this is bad -- I've seen this length vary (sometimes '7', sometimes '8')
        if len(mtime) == 7:
            mDay    = int(mtime[2])
            mHour   = int(mtime[3])
            mMinute = int(mtime[4])
            mYear   = int(mtime[6])
        elif len(mtime) == 8:
            mDay    = int(mtime[3])
            mHour   = int(mtime[4])
            mMinute = int(mtime[5])
            mYear   = int(mtime[7])

        modTime = datetime.datetime(year=mYear, month=mMonth, day=mDay, hour=mHour, minute=mMinute)
        delta = str(currTime - modTime)

        if 'day' in delta:
            # anything with 'day' in it has expired, just move along
            # skms session files have a 10 hour timeout window
            continue
        else:
            delta = timePadZeros(delta)
            hours = int(delta[:2].strip())
            if hours < SKMS_SESSION_INTERVAL:
                orderedList.append([delta, index])

    if len(orderedList) == 0:
        return False

    else:
        # sort the list
        orderedList.sort(key=lambda x: x[0])

        for timeIndex in orderedList:
            sessionList.append(sessionFiles[timeIndex[1]])

    return sessionList



##############################################################################
#
# timePadZeros(delta)
#

def timePadZeros(delta):

    time = delta.split(':')

    newTime = ''

    for (index, value) in enumerate(time):
        if len(value) == 1:
            value = '0' + value

        if len(newTime) == 0:
            newTime = value
        else:
            newTime += ':' +  value

    return newTime



##############################################################################
#
# collectListOfSessionFiles(denaliVariables)
#

def collectListOfSessionFiles(denaliVariables):

    sessionFiles   = []
    home_directory = denali_utility.returnHomeDirectory(denaliVariables)
    sessionPath    = denaliVariables["sessionPath"]

    if sessionPath == '':
        sessionPath = home_directory + "/.skms"

    if os.path.isdir(sessionPath) == True:

        filenames = os.listdir(sessionPath)

        for session_file in filenames:
            if "sess_" in session_file and ".json" in session_file:
                sessionFiles.append(sessionPath + '/' + session_file)

    else:
        print "session directory (user/.skms) not found."
        return False

    return sessionFiles



##############################################################################
#
# obtainUserPassword(username, denaliVariables)
#

def obtainUserPassword(username, denaliVariables):

    # Look in the user's home directory for [[ ~/.skms/sess_<user>.json ]]
    #
    # If the file exists authenticate against the database with the
    # given username.
    #
    # If the authentication fails, loop back around and ask for a password
    # to SKMS before continuing.

    if denaliVariables["credsFileUsed"] == True:
        # If the creds file was used, and this function's code is running, it means that
        # the creds authentication failed.  At this point the username should be changed
        # from what was found in the creds file to what is found in the ~/.denali/config
        # file (if it exists), or to whatever the user entered (if --user was used).  If
        # the userName setting is empty, then a full authentication (username/password)
        # will be required.
        #
        # Side note:  Running this against the production SKMS DB seems to work fine.
        #             Running this against "stage" doesn't work as expected, as a valid
        #             creds file will fail to authenticate (oops).

        if len(denaliVariables["userName"]) != 0:
            username = denaliVariables["userName"]
        else:
            username = ''

    # Does a user session file exist (and is it not aged out)?
    if checkSessionFileStatus(denaliVariables) == True:
        # authenticate against the database
        rCode = validateAuthentication(username, '', False, denaliVariables)

        if rCode == False:
            # The username for the session cannot successfully authenticate
            # against the database.  Give the user another chance by prompting
            # them to enter their username/password combination and try again.
            print "Username: %s" % username
            password = getpass.getpass(" Password: ")
            rCode = validateAuthentication(username, password, False, denaliVariables)

            if rCode == False:
                print "Authentication Failed (bad username/password)."
                denali.cleanUp(denaliVariables)
                exit(1)
            else:
                # authentication successful with username/password
                return rCode
        else:
            # authentication successful with existing session file
            return rCode

    else:
        # session file for the user does not exist
        rCode = authenticateUser(denaliVariables)

        '''
        print "\nSKMS Authentication required"

        # backup the stdin pointer -- whatever it is at this point.
        stdin_backup=sys.stdin
        sys.stdin = open("/dev/tty")

        if len(username) == 0:
            username = raw_input("  Username: ")
        else:
            print "  Username: %s" % username
        password = getpass.getpass("  Password: ")

        # restore the stdin pointer
        sys.stdin=stdin_backup

        rCode = validateAuthentication(username, password, False, denaliVariables)
        '''

        if rCode == False:
            return False
        else:
            # authentication successful with username/password
            return rCode

    return False



##############################################################################
#
# authenticateUser(denaliVariables)
#

def authenticateUser(denaliVariables):

    detected_user = getpass.getuser()

    # if the user's session has timed out, and they don't have a configuration
    # file (.denali/config) and they asked for stdin reading, then this should
    # help fix a problem with the authentication.
    #
    # backup the stdin pointer -- whatever it is at this point.
    stdin_backup=sys.stdin

    # set that pointer to /dev/tty -- to allow user input (authentication with
    # username/password
    sys.stdin = open("/dev/tty")

    print "\nSKMS Authentication required"
    username = raw_input("  Username [detected user: %s]: " % detected_user)

    if username == '':
        # Empty username, use the username detected
        username = detected_user

    password = getpass.getpass("  Password: ")

    # now restore the stdin pointer to whatever it was before.  This should allow
    # the processing to continue as expected
    sys.stdin=stdin_backup

    return (validateAuthentication(username, password, False, denaliVariables))



##############################################################################
#
# validateAuthentication(username, password, silent_run, denaliVariables)
#

def validateAuthentication(username, password, silent_run, denaliVariables):

    api_url = denaliVariables["apiURL"]
    api = SKMS.WebApiClient(username, password, api_url, True)
    customizeSKMSClientStrings(denaliVariables, api)
    #api = SKMS.WebApiClient(username, password, 'api.skms.adobe.com', enable_session_optimization=False)
    api.disable_ssl_chain_verification()

    if denaliVariables["debug"] == True:
        print "API URL = %s" % denaliVariables["apiURL"]

    # run a simple query to validate database access
    request_type = "Authentication"
    sql_query = "SELECT name WHERE name = 'db2255.oak1' PAGE 1, 1"
    param_dict = {"query": "SELECT name WHERE name = 'db2255.oak1' PAGE 1, 1"}
    try:
        #if api.send_request('DeviceDao', 'search', param_dict) == True:
        ccode = api.send_request('DeviceDao', 'search', param_dict)
        if denaliVariables["analytics"] == True:
            denali_analytics.createProcessForAnalyticsData(denaliVariables, "Anomoly Authentication", sql_query, "DeviceDao", "search", 1)
        if ccode == True:
            # assign the API value to denaliVariables
            denaliVariables["api"] = api
            return True
        else:
            if silent_run == False:
                # print error message stating reason for the failure
                print "\nERROR:"
                print "   STATUS: "  + api.get_response_status()
                print "   TYPE: "    + str(api.get_error_type())
                print "   MESSAGE: " + api.get_error_message()
                print
            return False

    except KeyError:
        # The last time I saw this error in this function, it was because of an update
        # to SKMS that caused the session file to be bad (needing deletion, and then
        # recreation with a new login -- enter username/password).
        ccode = deleteSessionFile(denaliVariables)
        if ccode == False:
            # problem deleting the session file -- fail this run
            print "\nERROR:  SKMS KeyError"
            print "        Could not delete user session file (~/.skms/*.json) to work-around this issue."
            return False

        # This code checks for a session file (which was just deleted), and if it isn't
        # there, it requests the user's password and authenticates against SKMS.
        ccode = obtainUserPassword(username, denaliVariables)
        if ccode == False:
            # failure again ... just return false
            if silent_run == False:
                # print error message stating reason for the failure
                print "\nERROR:"
                print "   STATUS: "  + api.get_response_status()
                print "   TYPE: "    + str(api.get_error_type())
                print "   MESSAGE: " + api.get_error_message()
                print
            return False
        else:
            return ccode
    else:
        if silent_run == False:
            # print error message stating reason for the failure
            print "\nERROR:"
            print "   STATUS: "  + api.get_response_status()
            print "   TYPE: "    + str(api.get_error_type())
            print "   MESSAGE: " + api.get_error_message()
            print
        return False



##############################################################################
#
# checkSessionFileStatus(denaliVariables)
#
#   If a session file exists, return True
#   If a session file does not exist, return False
#

def checkSessionFileStatus(denaliVariables):

    home_directory = denali_utility.returnHomeDirectory(denaliVariables)
    sessionPath    = denaliVariables["sessionPath"]
    userName       = denaliVariables["userName"]

    if sessionPath == '':
        if home_directory == '':
            # environment didn't return a result -- must exit
            print "Denali: $HOME environment variable not reachable.  Exiting."
            denali.cleanUp(denaliVariables)
            exit(1)
        sessionPath = home_directory + "/.skms/sess_"
    else:
        if sessionPath[-1] == '/':
            sessionPath += "sess_"
        else:
            sessionPath += "/sess_"

    if userName == '':
        userName = str(getpass.getuser())

    fileName = sessionPath + userName + '.json'

    if os.path.isfile(fileName) != True:
        return False

    ccode = checkSessionFileIntegrity(denaliVariables, fileName)
    if ccode == True:
        return True
    else:
        # file is corrupted -- delete it
        return False



##############################################################################
#
# checkSessionFileIntegrity(denaliVariables, fileName)
#
#   Check the integrity of the user's session file.
#   Make sure the csrf and session id values are there and legitimate.
#

def checkSessionFileIntegrity(denaliVariables, fileName):

    session_file_corrupted = False

    # read the file in and see if it is legitimate
    sessionFile = open(fileName, 'r')

    skms_csrf_token = ''
    skms_session_id = ''

    try:
        for line in sessionFile:
            if line.find("skms_csrf_token") != -1 and line.find("skms_session_id") != -1:
                # found a legitimate session file -- check for data integrity
                if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
                    outputString = "Login debug: session file = %s" % line
                    denali_utility.debugOutput(denaliVariables, outputString)

                # remove spaces and quotation marks
                line = line.replace(' ','')
                line = line.replace("\"",'')

                # split on the comma
                contents = line.split(',')

                # remove the beginning '{' and ending '}' squiggly
                contents[0] = contents[0][1:]
                contents[1] = contents[1][:-1]

                # split each piece on the colon -- should be ready now
                contents[0] = contents[0].split(':')
                contents[1] = contents[1].split(':')

                # get the csrf token
                if "skms_csrf_token" in contents[0][0] and len(contents[0][1]) > 0:
                    skms_csrf_token = contents[0][1]
                elif len(contents[1][1]) > 0:
                    skms_csrf_token = contents[1][1]

                # get the session ID
                if "skms_session_id" in contents[1][0] and len(contents[1][1]) > 0:
                    skms_session_id = contents[1][1]
                elif len(contents[0][1]) > 0:
                    skms_session_id = contents[0][1]

    except:
        # problem getting data from the session file
        # assume it is corrupted.  Return False.

        # close the file
        sessionFile.close()
        session_file_corrupted = True

    else:
        # close the file
        sessionFile.close()

    if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
        outputString = "Login debug: skms_csrf_token = %s" % skms_csrf_token
        denali_utility.debugOutput(denaliVariables, outputString)
        outputString = "Login debug: skms_session_id = %s" % skms_session_id
        denali_utility.debugOutput(denaliVariables, outputString)

    if session_file_corrupted == True or skms_session_id.lower() == "null":
        # The skms_csrf_token is not checked for null.  When doing MFA, the csrf token appears
        # to be null -- all the time, so this cannot be a check for correctness.
        # Invalid session file (cookie).  Return False
        if denaliVariables["debug"] == True or denaliVariables["debugLog"] == True:
            outputString = "Login debug: Session file corrupted; delete the old one; request a new one."
            denali_utility.debugOutput(denaliVariables, outputString)

        ccode = deleteSessionFile(denaliVariables)
        if ccode == True:
            # session file deleted as expected.
            # return False, because the session file filed
            return False
        else:
            # session file delete failed.
            print "Denali Session File:  Corrupted and cannot delete [%s]" % fileName
            print "Denali exiting."
            exit(1)

    # all tests pass -- the file exists and the data inside looks legitimate
    # return True
    return True



##############################################################################
#
# deleteSessionFile(denaliVariables)
#

def deleteSessionFile(denaliVariables):

    home_directory = denali_utility.returnHomeDirectory(denaliVariables)
    sessionPath    = denaliVariables["sessionPath"]
    userName       = denaliVariables["userName"]

    if sessionPath == '':
        sessionPath = home_directory + "/.skms/sess_"
    else:
        if sessionPath[-1] == '/':
            sessionPath += "sess_"
        else:
            sessionPath += "/sess_"
    if userName == '':
        userName = str(getpass.getuser())

    fileName = sessionPath + userName + '.json'

    try:
        if os.path.isfile(fileName) == True:
            os.remove(fileName)
            return True
        else:
            # if the file doesn't exist, then return True
            # so the user can try to authenticate
            return True
    except:
        return False



##############################################################################
#
# readCredentialsFile(filename, denaliVariables)
#
#   Credentials file syntax:
#       username:<username>
#       password:<password>
#
#   The syntax is a little more forgiving than the above.  You can include
#   commas, dashes, spaces, etc., and the code will remove them all.  However,
#   to make a "clean" credentials file -- use the above syntax.
#

def readCredentialsFile(fileName, denaliVariables):
    fileName = fileName.strip()
    username = ['None', 'None']
    password = ['None', 'None']

    oStream  = denaliVariables['stream']['output']

    if os.path.isfile(fileName) == True:
        credFile = open(fileName, 'r')

        for line in credFile:
            line = line.strip()
            line = line.replace(" ", ":", 1)    # if the user has a space
            line = line.replace("=", ":", 1)    # if the user has an equal sign
            while "::" in line:
                line = line.replace("::", ":")

            # look for keywords "username" and "password" -- do a str.lower() on them
            # and then split the line into a List on the ":" character
            lineLow = line.lower()

            if lineLow.startswith("username") or lineLow.startswith("user:"):
                username = line.strip().split(':')
            elif lineLow.startswith("password") or lineLow.startswith("pass:"):
                password = line.strip().split(':')
            elif lineLow.startswith("session_path"):
                # MRASEREQ-40801
                # Fixed additional bug (the [0] on the end was missing)
                #   This problem caused a creds file with session_path
                #   in it to python stack because the code expected a
                #   string, and got a List (oops).
                denaliVariables["sessionPath"] = line.strip().split(':')[0]

        if username[0] == 'None' or username[1] == 'None':
            oStream.write("A valid username was not supplied.\n")
            username[1] = False

        if password[0] == 'None' or password[1] == 'None':
            oStream.write("A valid password was not supplied.\n")
            password[1] = False

    else:
        oStream.write("\nError:  Credentials File name \"%s\" doesn't exist.\n" % fileName)
        oStream.write("        Initiating manual authentication process.\n\n")
        username[1] = 'FNF'
        password[1] = 'FNF'

    oStream.flush()

    return username[1], password[1]



##############################################################################
##############################################################################
##############################################################################

if __name__ == '__main__':

    pass