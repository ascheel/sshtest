#
# denali_variables.py
#
import denali_types

#
# Version information for the code
__version__ = '1.94.1'

#
# Date of latest update (manually tracked)
#
__date__ = 'April 29, 2020'


#
# Variables used all over the code -- in a single dictionary / location
# I pass this dictionary around to make parameter passing between
# function calls as easy/painless as possible.
#
# Additionally, if another variable is needed (for whatever reason), it
# can be added here at this central location, and then referenced in the
# function(s) where appropriate to read the value or set/change it.
#
denaliVariables = {
                        "addColumn"                 : False,                        # special case -- for the --power/id switch
                        "addColumnData"             : {},                           # column data to add
                        "aliasHeaders"              : False,                        # print alias names for column titles
                        "aliasHostCount"            : 100,                          # max number of hosts to use with alias search/replace
                        "aliasLocation"             : '',                           # aliases file location
                        "aliasReplace"              : False,                        # whether a host alias lookup/replace is done
                        "allowUpdates"              : True,                         # (dis)allow CMDB update code to function
                        "analytics"                 : True,                         # Whether or not denali analytics is enabled (true) or disabled (false)
                        "analyticsSTime"            : 0.00,                         # Start time of processes using denali analytics
                        "api"                       : None,                         # SKMS web api return value
                        "apiURL"                    : "api.skms.adobe.com",         # web url for the api interface to SKMS
                        "advAttribute"              : {},                           # advanced attribute searching data
                        "argumentList"              : "",                           # the full denali argument list
                        "attributes"                : False,                        # whether or not host attributes are being output
                        "attribute_count"           : 0,                            # count of attributes in attrib.py searched for
                        "attributeUpdate"           : False,                        # whether or not an attribute update is requested
                        "attr_columns"              : [],                           # attribute column name for DeviceDao attribute retrieval
                        "attributeColumns"          : [],                           # this variable stores the print columns (and order) for attributes
                        "attributeColumnSizes"      : {},                           # store attribute column sizing information / used with --attrcolumns and --ar
                        "attributeNames"            : "NULL",                       # if the method is getAttributes, this stores attribute names (if specified)
                        "attributeOverride"         : False,                        # toggle whether to display attribute overrides or not
                        "attributeInherit"          : False,                        # toggle whether to display attribute inheritance or not
                        "attributesStacked"         : True,                         # stack attributes in up to 3 columns, or (if false), a column per attribute
                        "authenticateOnly"          : False,                        # create session instance only
                        "authSuccessful"            : False,                        # true/false if authentication was successful against SKMS
                        "autoColumnResize"          : False,                        # automatically resize field columns (for < 5000 devices)
                        "autoConfirm"               : False,                        # automatic confirmation on updates if accepted for all similar SIS updates
                        "autoConfirmSIS"            : False,                        # automatic confirmation on updates for SIS
                        "autoConfirmAllSIS"         : False,                        # used if the --yes_sis switch is submitted
                        "batchTotalCount"           : 0,                            # initial host/device list count -- set only once
                        "batchDeviceData"           : {},                           # data from a batch submission (used to reconstruct entire data-set)
                        "batchDeviceList"           : {},                           # batched up device lists (if total > maxSKMSRow)
                        "batchDevices"              : False,                        # whether to use a batched list, or not
                        "checkForwardingOnCall"     : False,                        # whether or not to check forwarding on-call schedule
                        "clearOverrides"            : False,                        # whether or not an attribute update will clear all overridden values
                        "cliParameters"             : [],                           # cli switch entered
                        "cmrData"                   : ['',''],                      # CMR data for date delta conversion
                        "combine"                   : False,                        # if false, show "--command" data live.  if true, show it integrated.
                        "commOptions"               : "",                           # command options
                        "commandExecuting"          : False,                        # has a command option been specified?
                        "commandFunction"           : '',                           # current command function executing
                        "commandOutput"             : [],                           # whether or not to ONLY show failures with commands (pdsh, etc.)
                        "commandOutputSymlink"      : '',                           # if populated, create a symlink to the command output with this name
                        "commandProgress"           : True,                         # command progress indicator -- use it (True) or not (False)
                        "commandProgressBar"        : 0,                            # what progress indicator is used: 0 = percent only, 1 = percent-plus, 2 = bar only
                        "commandProgressID"         : {},                           # command progress ID dictionary
                        "commandRetry"              : 0,                            # number of retries for pdsh, ssh commands
                        "commandRetryCount"         : 0,                            # what is the current retry number?
                        "commandRetryDefault"       : 1,                            # number of retries, by default, to do
                        "commandSpinner"            : 0,                            # what spinning character to print
                        "commandTimeValues"         : {},                           # command start/stop time values (different from --time settings)
                        "connectTimeout"            : -1,                           # number of seconds to wait for SSH connection
                        "columnData"                : [],                           # column data (name, width, cmdb name, etc.)
                        "credsFileUsed"             : False,                        # flip to true if a credentials file is used
                        "csvSeparator"              : ',',                          # separator used for CSV output (default is comma)
                        "daoDictionary"             : {},                           # dictionary storing default search settings from .denali/aliases file
                        "dataCenter"                : [],                           # data center location list
                        "data_center_sort"          : False,                        # sort by the data center first, then name second
                        "date"                      : __date__,                     # Date of the latest denali release
                        "db_flatscan"               : False,                        # whether the user requested a full scan of all devices
                        "debug"                     : False,                        # status of the debugging flag
                        "debugLog"                  : False,                        # whether to log to a file
                        "debugLogFile"              : "debug.log",                  # debug log file name
                        "defaults"                  : True,                         # status of the default setting (decommissioned, etc.)
                        "denaliLocation"            : '',                           # location of the denali script
                        "devServiceVerify"          : False,                        # whether or not to verify device service after command run
                        "devServiceVerifyData"      : {'verify_host_count':1},      # name and device service storage
                        "devicesNotFound"           : [],                           # devices submitted, but not found in CMDB
                        "dm_password"               : '',                           # Digital Marketing password -- used by monitoring authentication
                        "dm_username"               : '',                           # Digital Marketing Username -- used by monitoring authentication
                        "dnfPrintList"              : [],                           # list of columns to print for the devices not found (if "--validate" used)
                        "domainsToStrip"            : [],                           # domain names to strip from a submitted host list
                        "external"                  : False,                        # custom module to run?
                        "externalModule"            : '',                           # external module name
                        "fields"                    : '',                           # columns to display
                        "gauntletPromotion"         : -1,                           # gauntlet promotion level
                        "gauntletTrackData"         : {},                           # gauntlet track dictionary {track: {ds:[], environ:{prod:[], beta:[], qc:[]}}}
                        "getSecrets"                : False,                        # toggle on/off the secret store SKMS getSecrets method()
                        "getSecretsDict"            : {},                           # dictionary to store the printData
                        "getSecretsHost"            : "test_host",                  # current host to getSecrets for
                        "getSecretsStore"           : '',                           # secret store name to query
                        "groupData"                 : {'add':[], 'del':[]},         # list of groups being added or deleted
                        "groupList"                 : [],                           # the list of groups to search for
                        "historyCount"              : 0,                            # number of devices found
                        "historyFields"             : "long",                       # defaults to show all fields (change to "short" to show less)
                        "historyList"               : False,                        # toggle switch for device history
                        "historyListLength"         : 15,                           # default number of items to show in the history
                        "historySQLQuery"           : "",                           # data to perform the history sql query
                        "hostCommands"              : {'active':False},             # whether a host list will contain commands assigned to each host as well
                        "hostNameCheck"             : {},                           # temporary hostname storage for checking
                        "importModules"             : {},                           # data from modules imported
                        "interactive"               : False,                        # whether or an interactive function will be called
                        "jira_closed"               : False,                        # whether or not to show closed JIRA tickets (MRASEREQ-40937)
                        "jsonPageOutput"            : False,                        # if json output should be shown for each page, or just at the end
                        "jsonResponseDict"          : {},                           # saved/combined json response dictionary (over multiple SKMS pages)
                        "limitCount"                : 0,                            # if --limit is used, then this will be set to non-zero
                        "limitData"                 : {},                           # data storage for limit (MRASEREQ-41219)
                        "listToggle"                : False,                        # if true, display output via a list (false is for the default display)
                        "logPath"                   : '',                           # if set, directory path to create logs in.
                        "maxConnTimeout"            : 600,                          # the maximum timeout (in seconds) -- 600 == 10 minutes
                        "maxProcesses"              : 500,                          # the maximum number of processes to create for scp, ping, etc., '-c' commands
                        "maxSKMSRowReturn"          : 5000,                         # the maximum number of rows that SKMS will return for any given search before paging
                        "method"                    : "search",                     # typically 'search'
                        "methodData"                : '',                           # method != "search" :: store method data here
                        "mfa_auto_push"             : False,                        # if an automatic push is done when needed (or an interface is shown)
                        "multiHostHeader"           : False,                        # for history searches, do not print extra headers by default
                        "monitoring"                : False,                        # whether or not this is a monitoring request
                        "monitoring_auth"           : False,                        # whether or not SKMS authentication is required
                        "monitoring_cat"            : {},                           # monitoring alert service categorization
                        "monitoring_color"          : None,                         # stored color for printing wrapped lines of text
                        "monitoring_columns"        : {},                           # monitoring column assignments
                        "monitoring_debug"          : False,                        # monitoring debugging flag
                        "monitoring_default"        : 'simple',                     # default action when just "--mon" is given
                        "monitoring_list"           : {},                           # list of entities for a specific location
                        "monitoring_summary"        : {},                           # monitoring summary dictionary for host data
                        "monitorResponseValidate"   : False,                        # whether the monitoring validation code is enabled or not
                        "mon_e_cache_dir"           : '',                           # directory where entity cache files are stored, default: /$HOME/.denali/entity_cache
                        "mon_to_retry"              : True,                         # monitoring TimeOut retry (true=yes, false=no)
                        "mon_details"               : False,                        # if showing more details was requested
                        "mon_ok"                    : 'lightgreen',                 # the default 'ok' color
                        "mon_critical"              : 'red',                        # the default 'critical' color
                        "mon_warning"               : 'yellow',                     # the default 'warning' color
                        "mon_unknown"               : 'darkgrey',                   # the default 'unknown' color
                        "mon_notfound"              : 'blue',                       # the default 'not found' color
                        "mon_output"                : 'comma',                      # default host separation type
                        "nmapOptions"               : [],                           # options passed to nmap
                        "nocolors"                  : False,                        # for --list.  false (default): show colors, true: no colors
                        "nofork"                    : False,                        # should commands (-c) create multiple processes to execute
                        "noLogging"                 : False,                        # If True, the logging is disabled for pdsh and ssh work-flows
                        "noProfile"                 : False,                        # whether to use profiles or not
                        "noSearchNeeded"            : False,                        # if -c is used, and a full list of hosts is given, no login or search required
                        "non_interact"              : False,                        # whether to use non-interactive mode
                        "non_interact_data"         : {},                           # non-interactive data
                        "nostdin"                   : False,                        # do not check stdin upon loading
                        "noSummary"                 : False,                        # do not show the default summary with command output (-c | --command)
                        "num_procs"                 : -1,                           # number of processes created for command execution (-1 = default)
                        "orchFilename"              : '',                           # orchestration filename
                        "outputTarget"              : [denali_types.OutputTarget(   # where the output will be put (screen,file, etc.)
                                                        type="txt_screen",
                                                        filename='',
                                                        append=False)],
                        "pdshAppCount"              : -1,                           # number of pdsh commands that provide a return code (i.e., 0, 1, etc.)
                        "pdshCommand"               : '',                           # pdsh command to run
                        "pdsh_dshbak"               : [True, True],                 # PDSH and DSHBAK utilities are available (/usr/bin/*)
                        "pdshCanceled"              : False,                        # set to true if the user canceled a pdsh command
                        "pdshCanceledHosts"         : [],                           # hosts where pdsh was canceled and they were abruptly stopped
                        "pdshCombinedCmds"          : False,                        # whether or not to allow multiple PDSH commands to combine (for 'hostCommands' only use)
                        "pdshDshbakLog"             : True,                         # if true, dshbak analyzes the log output from pdsh / if false, it analyzes the host return codes
                        "pdshEntertainment"         : 0,                            # entertainment counter for a spinner
                        "pdshEnvironment"           : {},                           # Current PDSH environment
                        "pdshExecuting"             : False,                        # whether or not a current pdsh command is executing
                        "pdshFailedHosts"           : [],                           # hosts where pdsh failed to execute a command on
                        "pdshFailSucceedHosts"      : False,                        # some hosts give returns that are a mixture of success and failure -- show this?
                        "pdshVariableFanout"        : False,                        # if the user requested a variable fanout value (based on a percentage in the segment category)
                        "pdsh_log_file"             : 'denali-pdsh_log',            # pdsh log file name
                        "pdshOffset"                : -1,                           # pdsh number of hosts to process in a group (1, 100, 1000, etc.)
                        "pdshOptions"               : '',                           # pdsh specific command options
                        "pdshScreen"                : False,                        # pdsh screen option (False = don't use)
                        "pdshScreenDM"              : False,                        # pdsh screen -dm option (False = don't use)
                        "pdshSeparate"              : False,                        # pdsh separate
                        "pdshSeparateData"          : {},                           # pdsh separate data storage
                        "performMFA"                : False,                        # whether or not to engage the MFA authentication code paths
                        "polarisExecution"          : False,                        # whether or not polaris is executing
                        "processTimeout"            : -1,                           # number of seconds after which to kill a spawned process (-1 = default)
                        "profile"                   : 'default',                    # search profile to use ('default' is the default if it exists)
                        "profileAdded"              : False,                        # set to true if a profile is used to alter the query parameters
                        "rbDaysToKeep"              : 30,                           # number of day to keep update rollback logs (by default)
                        "rbLocation"                : '',                           # update rollback log location (default is launching user's .denali/rollback directory)
                        "refresh"                   : False,                        # to refresh monitoring cached data
                        "relogin"                   : False,                        # whether or not to automatically clear out the user's session file and re-login again
                        "responseDictionary"        : {},                           # storage for the response dictionary to be used outside of the typical retrieval code path
                        "retryCommand"              : '',                           # command to execute during the retry logic
                        "retryFunctions"            : ['pdsh', 'ssh'],              # which functions are allowed to retry
                        "retryStartTime"            : {'start_time':0},             # original time of the process starting
                        "rollbackWritten"           : False,                        # whether or not the rollback log has been written (avoid multiple writes)
                        "scpDestination"            : "",                           # scp command file destination path
                        "scpMultiFile"              : False,                        # scp multi-file code enabled or not
                        "scpMultiFileList"          : {},                           # scp multi-file list
                        "scpOptions"                : "",                           # scp specific command options
                        "scpPullOperation"          : False,                        # whether the source is local (push) or remote (pull)
                        "scpRenameDestFile"         : True,                         # whether the destination file should automatically be renamed after copying (hostname in front)
                        "scpSource"                 : "",                           # scp command file source path
                        "scpStartTime"              : 0.00,                         # scp start time
                        "searchCategory"            : "DeviceDao",                  # for simple searches, the dao to query
                        "searchCriteria"            : '',                           # for filtering the searches
                        "serverList"                : [],                           # the list of servers/hosts to search for
                        "serverListOrig"            : [],                           # the original host list
                        "sessionPath"               : '',                           # path for SKMS session file
                        "showHeaders"               : True,                         # if the headers (column titles) should be shown
                        "showInfoMessages"          : True,                         # show informational messages
                        "showsql"                   : False,                        # status of the showsql option
                        "simpleSearch"              : True,                         # is this a simple search, or complex sql query?
                        "singleUpdate"              : False,                        # option for doing all updates at once or not
                        "sis_debug"                 : False,                        # for debugging the SIS module
                        "sis_ColumnData"            : [],                           # SIS column data
                        "sis_command"               : '',                           # SIS command passed to omnitool
                        "sis_Fields"                : '',                           # SIS field data
                        "sis_HostsByDC"             : {},                           # SIS hosts arranged by Data Center
                        "sis_OriginalData"          : {},                           # Storage for CMDB and SIS column/fields (original data before it was picked clean)
                        "sis_SQLParameters"         : [],                           # SIS database sql search parameter modification
                        "skms_monapi_auth"          : False,                        # Use SKMS username/password for MonAPI authentication (default is False) - MRASEREQ-41495
                        "slack"                     : False,                        # if this is a query in slack (special use case)
                        "slackUser"                 : '',                           # the slack user making the query
                        "sorDefault"                : 1,                            # default setting for source of record updates (1 = CMDB)
                        "sorUpdateTo"               : '',                           # what the change SOR destination will be
                        "sortColumnsFirst"          : False,                        # for special queries; i.e., --switch
                        "sqlParameters"             : [],                           # sql cli parameters entered
                        "sqlParmsOriginal"          : [],                           # original sql parameters
                        "sqlSort"                   : '',                           # sort information on retrieved data
                        "spotsGrep"                 : False,                        # if spots data is asked for with a grep -- print hostname on each line
                        "spotsTitle"                : False,                        # if the title for individual spots data has been printed
                        "sshCommand"                : '',                           # ssh command to execute
                        "sshDshbakLog"              : True,                         # if true, dshbak analyzes the log output from ssh / if false, it analyzes the host return codes
                        "sshFallThrough"            : False,                        # if pdsh fails, move to ssh for failed hosts
                        "sshOptions"                : '',                           # ssh options
                        "ssh_log_file"              : 'denali-ssh_log',             # ssh log file name
                        "stdinData"                 : '',                           # the stdin field data if "--stdin" is used
                        "stream"                    : {},                           # the stream to use for import text (login, etc.)
                        "sudoUser"                  : '',                           # User to run commands as (with -c/--command, specifically pdsh and/or ssh)
                        "summary"                   : False,                        # summary status information of the DB query/results
                        "testAuth"                  : False,                        # whether to fail (return 1) on initial authentication
                        "testHost"                  : 'dn15.or1',                   # host used to test the availability of the database and if authentication succeeded
                        "textTruncate"              : False,                        # for txt_screen output, truncate columns?
                        "textWrap"                  : True,                         # should text wrap for on-screen txt display?
                        "time"                      : {},                           # time storage dictionary
                        "time_display"              : False,                        # whether to display internal time keeping
                        "time_unaccounted"          : 0.0,                          # unaccounted time
                        "tmpFilesCreated"           : [],                           # list of temp files created during execution
                        "updateColorYes"            : "red",                        # default color for updates happening -- red
                        "updateColorNo"             : "lightcyan",                  # default color for updates not happening -- light cyan
                        "updateDefault"             : "add",                        # default setting -- add new entries during an update
                        "updateHostsYes"            : [],                           # list of hosts that will be updated
                        "updateHostsNo"             : [],                           # list of hosts that will _not_ be updated
                        "updateDebug"               : False,                        # enable this to see error messages for update from SKMS
                        "updateDevice"              : '',                           # device about to be updated
                        "updateKey"                 : 'name',                       # The key for which the update will happen (default is hostname)
                        "updateLogWrite"            : False,                        # if the updatelog has been written to
                        "updateMethod"              : '',                           # either 'file' or 'console' for the method of update being done
                        "updateParameters"          : {},                           # dictionary/list of items to be updated for a host or list of hosts (key = hostname)
                        "updateCategories"          : [],                           # update categories (columns as defined by the update)
                        "updateMenuShow"            : True,                         # whether or not to show the update menu
                        "updatePreviewData"         : {},                           # the preview data in dictionary format (for easy retrieval)
                        "updatePrintData"           : '',                           # update print data save location
                        "updateSISAccepted"         : False,                        # if the first SIS update was accepted
                        "updateSISData"             : [],                           # update payload of SIS changes
                        "updateSOR"                 : {},                           # update Source of Record: SIS or CMDB
                        "updateViewCount"           : -1,                           # the number of hosts to show in the preview view (-1 == all hosts)
                        "updateSummary"             : {},                           # summary of updates (total, changed, non-changed)
                        "userAliases"               : {},                           # user aliases found in .denali/aliases file
                        "userConfig"                : False,                        # if a user specified config file was submitted
                        "userName"                  : '',                           # SKMS user name
                        "userNameSupplied"          : False,                        # Is True if the user is supplied; --user / .config file.
                        "utilityPath"               : '/usr/local/bin:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin',
                        "validateData"              : False,                        # If True, validate all hosts and include missing hosts in the output
                        "version"                   : __version__                   # Denali version information
                  }
