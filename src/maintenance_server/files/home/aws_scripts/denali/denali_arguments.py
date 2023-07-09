#! /usr/bin/env python

####################
#                  #
# Arguments Module #
#                  #
####################

import denali_location
import denali_search



##############################################################################
#
# clswitches:  command-line switch
#
#   Dictionary of available command line switches (if it isn't in here, the code won't accept it)
#   This also has information (true/false) whether the switch is stand-alone or not.
#       True  == combined switch    (i.e., --load=/home/user/useme.txt  )
#                                   (       -l /home/user/useme.txt     )
#
#       False == stand-alone toggle switch (e.g., whether debugging is enabled or not)
#
#  A "simple search" has a basic query.
#  An "extended search" has multiple "and"/"or"/"not" binary qualifiers in it
#    to help reduce the amount of data being searched and narrow the scope of
#    what is expected to be returned by the database.
#

clswitches = {
              '--help'                      : True,         # show help
              '--version'                   : False,        # show denali version information
              '--aliases'                   : False,        # show cmdb column aliases
              '--aliasheaders'              : False,        # show alias column headers
              '--debug'                     : False,        # debugging flag
              '--monitoringdebug'           : False,        # monitoring debugging flag
              '--mondetails'                : False,        # monitoring details flag (show more than normal -- verbosity)
              '--monvalidate'               : False,        # monitoring validate flag (check after submission)
              '--updatedebug'               : False,        # update debugging flag
              '--sisdebug'                  : False,        # sis module debugging flag
              '--showsql'                   : False,        # show the constructed sql statement
              '--summary'                   : False,        # show a summary of the data printed
              '--nosummary'                 : False,        # do not show a default summary in the command output
              '--truncate'                  : False,        # truncate data lines to the width of the column
              '--nowrap'                    : False,        # do not truncate -- just write as much data as there
              '--yes'                       : False,        # Automatic agreement (used for update)
              '--yes_sis'                   : False,        # Automatic agreement (used for SIS updates)
              '--nostdin'                   : False,        # disable stdin checking
              '--attrcolumns'               : False,        # toggle the attribute display method (stacked or column-ized)
              '--clearoverrides'            : False,        # clear any/all attributes that have been overridden
              '--showoverrides'             : False,        # toggle the attribute override display (show whether an attribute is overridden or not)
              '--showinherit'               : False,        # toggle the attribute inherit diplay (show whether an attribute is inherited or not)
              '--ar'                        : False,        # whether or not columns automatically resize
              '--autoresize'                : False,        #
              '--verify'                    : True,         # whether or not to verify/validate a group of hosts during ssh/pdsh execution
              '-v'                          : True,         #
              '--verify_hosts'              : True,         # number of verify hosts to use
              '--vh'                        : True,         #
              '--nocolors'                  : False,        # whether or not colors are displayed with --list
              '--screen'                    : False,        # whether or not to use a screen directive with pdsh
              '--screendm'                  : False,        # whether or not to use "screen -dm" directive with pdsh
              '--refresh'                   : False,        # to refresh monitoring cached data file(s)
              '--auth'                      : False,        # tell denali to authenticate (session create) only
              '--relogin'                   : False,        # whether to clear out existing session file for user (False = no)
              '--testAuth'                  : False,        # test authentication (fail out if not successful)
              '--time'                      : False,        # whether to display internal time keeping
              '--m_separator'               : True,         # the monitoring separator to use (comma ',' is the default)
              '--jira_closed'               : False,        # whether or not to show closed JIRA tickets (MRASEREQ-40937)
              '--check_forwarding_schedule' : False,        # whether or not to check the forwarding on-call schedule in the oncall extension
              '--config'                    : True,         # allow the user to specify a config file directory/file location
              '--host_commands'             : False,        # whether or not a host list contains commands as well (MRASEREQ-42003)
              '--hc'                        : False,        #
              '--logoutput'                 : True,         # what type of output to show for commands
              '--profile'                   : True,         # designated profile
              '--noprofile'                 : False,        # whether to use a profile or not
              '--dest'                      : True,         # the scp destination path
              '--destination'               : True,         #
              '-i'                          : False,        # toggle switch for interactive mode
              '--interactive'               : False,        #
              '--orch'                      : True,         # orchestration filename
              '--orchestration'             : True,         #
              '--sudo'                      : True,         # sudo user to execute commands as
              '--rcode'                     : False,        # whether to analyze the log (True) or return code (False) output
              '--retry'                     : True,         # whether to retry any command failures, and how many times (optional)
              '--rc'                        : True,         #
              '--retry_command'             : True,         # if a retry is issued, use this command instead of the original one
              '--pdsh_apps'                 : True,         # number of command where a return value is expected
              '--pdsh_command'              : True,         # command to be executed (used by pdsh)
              '--pc'                        : True,         #
              '--pci'                       : False,        #
              '--pdsh_opts'                 : True,         # command options (used by pdsh)
              '--pdsh_options'              : True,         #
              '--po'                        : True,         #
              '--pdsh_offset'               : True,         # host offset count (used by pdsh)
              '--offset'                    : True,         # host offset count (used by pdsh)
              '--pdsh_separator'            : True,         # request host separation for parallel work
              '--pdsh_separate'             : True,         #
              '--ps'                        : True,         #
              '--scp_opts'                  : True,         # command options (used by scp)
              '--scp_options'               : True,         #
              '--scp_norename'              : False,        # rename the copied destination files to include the hostname
              '--so'                        : True,         #
              '--ssh_command'               : True,         # command to be executed (used by ssh)
              '--sc'                        : True,         #
              '--ssh_opts'                  : True,         # command options (used by ssh)
              '--ssh_options'               : True,         #
              '--src'                       : True,         # the scp source path
              '--source'                    : True,         #
              '--num_procs'                 : True,         # number of processes to spawn (for -c use)
              '--proc_timeout'              : True,         # number of seconds for a process to be allowed to run (for -c use)
              '--conn_timeout'              : True,         # number of seconds to wait for an SSH connection (for -c use)
              '--ni'                        : False,        # use non-interactive mode scp transfers
              '--non-interactive'           : False,        # ditto
              '--nolog'                     : False,        # if used, all logging to a file (pdsh/ssh) is disabled
              '--quiet'                     : False,        # if used, informational messages are disabled
              '--slack'                     : False,        # if this is a query in slack (default is false, or no)
              '--singleupdate'              : False,        # do an update in one request or serially
              '--spots_grep'                : False,        # if spots data is requested and a grep is done at the same time
              '--update_key'                : True,         # the key to base an update off of (hostname is default)
              '--list'                      : False,        # toggle a table vs. list display
              '--creds'                     : True,         # user credentials (username/password)
              '--mon_creds'                 : True,         # monitoring user credentials (username/password)
              '-u'                          : True,         # user name
              '--user'                      : True,         #
              '--stdin'                     : True,         # stdin directed pointerd
              '-'                           : False,        # stdin on/off switch
              '--'                          : False,        #
              '--updatesor'                 : True,         # change Source of Record to ... CMDB/SIS
              '--defupdate'                 : True,         # default behavior for updates (add)
              '--updatefile'                : True,         # update CMDB data with file
              '--up'                        : True,         # update CMDB data
              '--update'                    : True,         #
              '--updateattr'                : True,         # update host attribute(s)
              '--addhistory'                : True,         # add history entry for host(s)
              '--grphistory'                : True,         # add group history entry
              '--ag'                        : True,         # group list to add to devices
              '--addgroup'                  : True,         #
              '--dg'                        : True,         # group list to delete from devices
              '--delgroup'                  : True,         #
              '--newgroup'                  : True,         # create a new group
              '--track'                     : True,         # gauntlet track to use for the query-basis
              '--promotion-level'           : True,         # gauntlet track promotion level (required w/ --track)
              '--noheaders'                 : False,        # Whether or not to show the headers (set to False)
              '--headers'                   : False,        # show the headers (set to True -- default setting)
              '--mheaders'                  : False,        # show multi-host headers (set to False by default)
              '-o'                          : True,         # type of output file to create
              '--out'                       : True,         #
              '--symlink'                   : True,         # for command execution, create a symlink to the stdout data
              '--progress'                  : True,         # what type of progress to show for command execution
              '--separator'                 : True,         # switch to modify the separator for CSV output (default is comma)
              '--power'                     : True,         # switch to show an RPC and associated hosts (by RPC name)
              '--powerid'                   : True,         # switch to show an RPC and associated hosts (by RPC id)
              '--rack'                      : True,         # switch to show a rack and assocaited hosts (by rack name)
              '--rackid'                    : True,         # switch to show a rack and assocaited hosts (by rack id)
              '--switch'                    : True,         # switch to show a network switch and associated hosts (by switch name)
              '--switchid'                  : True,         # switch to show a network switch and assocaited hosts (by switch id)
              '--count'                     : True,         # toggle the "count" method on
              '--sql'                       : True,         # sql entered query
              '-l'                          : True,         # hosts listed in a file
              '--load'                      : True,         #
              '-h'                          : True,         # hosts comma separated (or space) at the cli
              '--hosts'                     : True,         #
              '--sis'                       : True,         # use omnitool integration to access SIS database
              '--omnitool'                  : True,         #
              '--ot'                        : True,         #
              '-g'                          : True,         # groups comma separated (or space) at the cli
              '--groups'                    : True,         #
              '--getsecrets'                : True,         # toggle the SKMS getSecrets method on
              '--dc'                        : True,         # Data Center location of hosts
              '--dao'                       : True,         # DAO to search under
              '--dao_role'                  : True,         # shortcut for name searching in the DeviceRoleDao
              '--dao_service'               : True,         # shortcut for name searching in the DeviceServiceDao
              '--dao_state'                 : True,         # shortcut for name searching in the DeviceStateDao
              '--dao_cmr'                   : True,         # shortcut for CMR searching in the CmrDao
              '--dao_environment'           : True,         # shortcut for name searching in the EnvironmentDao
              '--dao_env'                   : True,         #
              '--dao_group'                 : True,         # shortcut for group name searching in the DeviceGroupDao
              '--obj'                       : True,         # name type - devices, etc. (DAO)
              '--object'                    : True,         #
              '--showdecomm'                : False,        # default search settings (don't show decommissioned, etc.)
              '-s'                          : True,         # simple search
              '--search'                    : True,         #
              '--history'                   : True,         # toggle the history search code on
              '-f'                          : True,         # fields to display
              '--fields'                    : True,         #
              '--sort'                      : True,         # sort the displayed fields
              '--limit'                     : True,         # limit the number of items displayed
              '-e'                          : True,         # custom add-on modules to denali
              '-m'                          : True,         #
              '--ext'                       : True,         #
              '-c'                          : True,         # Command to execute on servers found
              '--command'                   : True,         #
              '--mon'                       : True,         # Monitoring switch
              '--pol'                       : True,         # Polaris functionality switch
              '--polaris'                   : True,         #
              '--noanalytics'               : False,        # Switch to disable denali analytics
              '--validate'                  : False,        # Switch to toggle host (input data) validation
              '--combine'                   : False,        # Switch to toggle display of command data with CMDB data
              '--nofork'                    : False,        # whether or not to create multiple processes for command execution (-c)
             }





##############################################################################
#
# cliPrioritySort(cliArguments)
#
#  Sort the List into a new List based on the order in which a switch/date
#  should be processed.
#

def cliPrioritySort(cliArguments):

    argumentReturn = []

    # Function to modify iterables (in-place) -- this is expected -- so there
    # is no return value

    def findArgument(cliArgs, switches, rList):
        for (count, index) in enumerate(cliArgs):
            for switch in switches:
                if switch in index:
                    rList.append(index)
                    cliArgs.pop(count)
                    return

    # The order here (below) is the order in which the parameters are
    # put into a List to be processed

    findArgument(cliArguments, ['--help'                        ], argumentReturn)
    findArgument(cliArguments, ['--version'                     ], argumentReturn)
    findArgument(cliArguments, ['--aliases'                     ], argumentReturn)
    findArgument(cliArguments, ['--aliasheaders'                ], argumentReturn)
    findArgument(cliArguments, ['--debug'                       ], argumentReturn)
    findArgument(cliArguments, ['--monitoringdebug'             ], argumentReturn)
    findArgument(cliArguments, ['--mondetails'                  ], argumentReturn)
    findArgument(cliArguments, ['--monvalidate'                 ], argumentReturn)
    findArgument(cliArguments, ['--updatedebug'                 ], argumentReturn)
    findArgument(cliArguments, ['--update_key'                  ], argumentReturn)
    findArgument(cliArguments, ['--sisdebug'                    ], argumentReturn)
    findArgument(cliArguments, ['--showsql'                     ], argumentReturn)
    findArgument(cliArguments, ['--summary'                     ], argumentReturn)
    findArgument(cliArguments, ['--nosummary'                   ], argumentReturn)
    findArgument(cliArguments, ['--truncate'                    ], argumentReturn)
    findArgument(cliArguments, ['--nowrap'                      ], argumentReturn)
    findArgument(cliArguments, ['--attrcolumns'                 ], argumentReturn)
    findArgument(cliArguments, ['--showoverrides'               ], argumentReturn)
    findArgument(cliArguments, ['--showinherit'                 ], argumentReturn)
    findArgument(cliArguments, ['--ar', '--autoresize'          ], argumentReturn)
    findArgument(cliArguments, ['--verify', '-v'                ], argumentReturn)
    findArgument(cliArguments, ['--verify_hosts', '--vh'        ], argumentReturn)
    findArgument(cliArguments, ['--yes'                         ], argumentReturn)
    findArgument(cliArguments, ['--yes_sis'                     ], argumentReturn)
    findArgument(cliArguments, ['--refresh'                     ], argumentReturn)
    findArgument(cliArguments, ['--relogin'                     ], argumentReturn)
    findArgument(cliArguments, ['--auth'                        ], argumentReturn)
    findArgument(cliArguments, ['--testAuth'                    ], argumentReturn)
    findArgument(cliArguments, ['--time'                        ], argumentReturn)
    findArgument(cliArguments, ['--m_separator'                 ], argumentReturn)
    findArgument(cliArguments, ['--check_forwarding_schedule'   ], argumentReturn)
    findArgument(cliArguments, ['--jira_closed'                 ], argumentReturn)      # MRASEREQ-40937
    findArgument(cliArguments, ['--host_commands', '--hc'       ], argumentReturn)      # MRASEREQ-42003
    findArgument(cliArguments, ['--logoutput'                   ], argumentReturn)
    findArgument(cliArguments, ['--profile'                     ], argumentReturn)
    findArgument(cliArguments, ['--noprofile'                   ], argumentReturn)
    findArgument(cliArguments, ['--nocolors'                    ], argumentReturn)
    findArgument(cliArguments, ['--config'                      ], argumentReturn)
    findArgument(cliArguments, ['--screen'                      ], argumentReturn)
    findArgument(cliArguments, ['--screendm'                    ], argumentReturn)
    findArgument(cliArguments, ['--dc'                          ], argumentReturn)
    findArgument(cliArguments, ['--list'                        ], argumentReturn)
    findArgument(cliArguments, ['--noanalytics'                 ], argumentReturn)
    findArgument(cliArguments, ['--quiet'                       ], argumentReturn)
    findArgument(cliArguments, ['--singleupdate'                ], argumentReturn)
    findArgument(cliArguments, ['--slack'                       ], argumentReturn)
    findArgument(cliArguments, ['--promotion-level'             ], argumentReturn)      # process the promotion-level before the track
    findArgument(cliArguments, ['--track'                       ], argumentReturn)
    findArgument(cliArguments, ['--dest', '--destination'       ], argumentReturn)
    findArgument(cliArguments, ['-i', '--interactive'           ], argumentReturn)
    findArgument(cliArguments, ['--orch', '--orchestration'     ], argumentReturn)
    findArgument(cliArguments, ['--sudo',                       ], argumentReturn)
    findArgument(cliArguments, ['--progress'                    ], argumentReturn)
    findArgument(cliArguments, ['--rcode'                       ], argumentReturn)
    findArgument(cliArguments, ['--rc', '--retry_command'       ], argumentReturn)
    findArgument(cliArguments, ['--retry'                       ], argumentReturn)
    findArgument(cliArguments, ['--pdsh_apps'                   ], argumentReturn)
    findArgument(cliArguments, ['--pdsh_opts', '--pdsh_options' ], argumentReturn)
    findArgument(cliArguments, ['--po'                          ], argumentReturn)
    findArgument(cliArguments, ['--pdsh_offset', '--offset'     ], argumentReturn)
    findArgument(cliArguments, ['--pdsh_separator'              ], argumentReturn)
    findArgument(cliArguments, ['--pdsh_separate', '--ps'       ], argumentReturn)
    findArgument(cliArguments, ['--pdsh_command', '--pc'        ], argumentReturn)
    findArgument(cliArguments, ['--pci'                         ], argumentReturn)
    findArgument(cliArguments, ['--scp_opts', '--scp_options'   ], argumentReturn)
    findArgument(cliArguments, ['--scp_norename'                ], argumentReturn)
    findArgument(cliArguments, ['--ssh_opts', '--ssh_options'   ], argumentReturn)
    findArgument(cliArguments, ['--ssh_command', '--sc'         ], argumentReturn)
    findArgument(cliArguments, ['--so'                          ], argumentReturn)
    findArgument(cliArguments, ['--src', '--source'             ], argumentReturn)
    findArgument(cliArguments, ['--num_procs'                   ], argumentReturn)
    findArgument(cliArguments, ['--conn_timeout'                ], argumentReturn)
    findArgument(cliArguments, ['--proc_timeout'                ], argumentReturn)
    findArgument(cliArguments, ['--ni'                          ], argumentReturn)
    findArgument(cliArguments, ['--non-interactive'             ], argumentReturn)
    findArgument(cliArguments, ['--nolog'                       ], argumentReturn)
    findArgument(cliArguments, ['--spots_grep'                  ], argumentReturn)
    findArgument(cliArguments, ['--stdin'                       ], argumentReturn)      # stdin before -, --, and --load
    findArgument(cliArguments, ['-l', '--load'                  ], argumentReturn)
    findArgument(cliArguments, ['-g', '--groups'                ], argumentReturn)      # groups before hosts (groups make the host list)
    findArgument(cliArguments, ['-h', '--hosts'                 ], argumentReturn)
    findArgument(cliArguments, ['-', '--'                       ], argumentReturn)
    findArgument(cliArguments, ['--creds'                       ], argumentReturn)
    findArgument(cliArguments, ['--mon_creds'                   ], argumentReturn)
    findArgument(cliArguments, ['-u', '--user'                  ], argumentReturn)
    findArgument(cliArguments, ['--noheaders'                   ], argumentReturn)
    findArgument(cliArguments, ['--headers'                     ], argumentReturn)
    findArgument(cliArguments, ['--mheaders'                    ], argumentReturn)
    findArgument(cliArguments, ['--validate'                    ], argumentReturn)
    findArgument(cliArguments, ['-o', '--out'                   ], argumentReturn)
    findArgument(cliArguments, ['--symlink'                     ], argumentReturn)
    findArgument(cliArguments, ['--pol', '--polaris'            ], argumentReturn)      # polaris functionality
    findArgument(cliArguments, ['--sis', '--omnitool', '--ot'   ], argumentReturn)      # omnitool (sis) integration
    findArgument(cliArguments, ['--defupdate'                   ], argumentReturn)
    findArgument(cliArguments, ['--updatesor'                   ], argumentReturn)
    findArgument(cliArguments, ['--separator'                   ], argumentReturn)
    findArgument(cliArguments, ['--power'                       ], argumentReturn)
    findArgument(cliArguments, ['--powerid'                     ], argumentReturn)
    findArgument(cliArguments, ['--rack'                        ], argumentReturn)
    findArgument(cliArguments, ['--rackid'                      ], argumentReturn)
    findArgument(cliArguments, ['--switch'                      ], argumentReturn)
    findArgument(cliArguments, ['--switchid'                    ], argumentReturn)
    findArgument(cliArguments, ['--dao_role'                    ], argumentReturn)
    findArgument(cliArguments, ['--dao_service'                 ], argumentReturn)
    findArgument(cliArguments, ['--dao_state'                   ], argumentReturn)
    findArgument(cliArguments, ['--dao_group'                   ], argumentReturn)
    findArgument(cliArguments, ['--dao_cmr'                     ], argumentReturn)
    findArgument(cliArguments, ['--dao_environment'             ], argumentReturn)
    findArgument(cliArguments, ['--dao_env'                     ], argumentReturn)
    findArgument(cliArguments, ['--limit'                       ], argumentReturn)
    findArgument(cliArguments, ['--count'                       ], argumentReturn)
    findArgument(cliArguments, ['--sql'                         ], argumentReturn)
    findArgument(cliArguments, ['--getsecrets'                  ], argumentReturn)
    findArgument(cliArguments, ['--updatefile'                  ], argumentReturn)
    findArgument(cliArguments, ['--up', '--update'              ], argumentReturn)
    findArgument(cliArguments, ['--updateattr'                  ], argumentReturn)
    findArgument(cliArguments, ['--clearoverrides'              ], argumentReturn)
    findArgument(cliArguments, ['--ag', '--addgroup'            ], argumentReturn)
    findArgument(cliArguments, ['--dg', '--delgroup'            ], argumentReturn)
    findArgument(cliArguments, ['--newgroup'                    ], argumentReturn)
    findArgument(cliArguments, ['--addhistory'                  ], argumentReturn)
    findArgument(cliArguments, ['--grphistory'                  ], argumentReturn)
    findArgument(cliArguments, ['--dao'                         ], argumentReturn)
    findArgument(cliArguments, ['--obj', '--object'             ], argumentReturn)
    findArgument(cliArguments, ['--showdecomm'                  ], argumentReturn)
    findArgument(cliArguments, ['-s', '--search'                ], argumentReturn)
    findArgument(cliArguments, ['--history'                     ], argumentReturn)
    findArgument(cliArguments, ['--sort'                        ], argumentReturn)
    findArgument(cliArguments, ['--combine'                     ], argumentReturn)
    findArgument(cliArguments, ['--nofork'                      ], argumentReturn)
    findArgument(cliArguments, ['-f', '--fields'                ], argumentReturn)
    findArgument(cliArguments, ['-e', '--ext', '-m'             ], argumentReturn)
    findArgument(cliArguments, ['-c', '--command'               ], argumentReturn)
    findArgument(cliArguments, ['--mon'                         ], argumentReturn)  # keep after -f, or sql parm queries fail

    return argumentReturn



##############################################################################
#
# validate_switch(switch, switch_type)
#
#   The purpose of this function is to validate a single argument passed in
#   to it.  There are two parameters passed in:
#       (1) switch          - the argument itself (--user, -l, etc.)
#       (2) switch_type     - the type of argument (if known)
#
#   The code then determines if the passed in switch is valid (checking it
#   against the dictionary of items hard-coded command-line switch.  It also
#   helps determine if this is a combined switch (switch with a value), or a
#   stand-alone switch (to toggle an action on/off, or enable a feature).
#

def validate_switch(switch, switch_type):

    retMessage = ''

    #print "switch = %s  :  type = %s" % (switch, switch_type)

    # see if there are dashes in the argument (specifying a new switch)
    dash = switch.find('-')
    if dash == 0:   # dash(es) at the beginning of the argument
        #count = switch.count('-')
        if switch_type == 'value':
            #print "Validate: change switch_type"
            switch_type = 'unsure'
    else:
        if switch_type == 'value':
            return True
        #print "no dashes found"
        return 'argument-value'

    if switch_type == 'combined':
        if switch in clswitches:
            if clswitches[switch] == True:
                retMessage = "Valid combined switch"
                retValue = True
            else:
                retMessage = "Syntax Error:  Improper use of a stand-alone switch as a combined switch"
                retValue = False
        else:
            retMessage = "Syntax Error:  Invalid combined switch"
            retValue = False
    elif switch_type == 'unsure':       # maybe 'stand-alone', maybe 'combined' -- test it.
        if switch in clswitches:
            if clswitches[switch] == True:   # combined switch
                retMessage = "Valid first element for combined switch"
                retValue = 'valid-combined'
            else:
                retMessage = "Valid stand-alone switch"
                retValue = 'stand-alone'
        else:
            retMessage = "Syntax Error:  Invalid switch"
            retValue = False

    #print "  %s" % retMessage
    return retValue



##############################################################################
#
# checkForCommonMisspellings(denaliVariables, argumentList)
#
#   This function checks for common (mis)uses of command-line switches in
#   denali.  If it finds one, it replaces it with the correct switch name
#   so that the query can still execute as desired.
#

def checkForCommonMisspellings(denaliVariables, argumentList):

    newArguments   = []
    ddnewArguments = []
    misspelled     = {  "--host"          : "--hosts",         "-host"          : "--hosts" ,     "-hosts"      : "--hosts",
                        "--users"         : "--user" ,         "-user"          : "--user"  ,     "-users"      : "--user",
                        "--field"         : "--fields",        "-field"         : "--fields",     "-fields"     : "--fields",
                        "--cred"          : "--creds",         "-cred"          : "--creds" ,     "-creds"      : "--creds",
                        "--h"             : "--hosts",         "--f"            : "--fields",
                        "--g"             : "--groups",        "--group"        : "--groups",     "-group"      : "--groups",
                        "--hist"          : "--history",       "--getsecret"    : "--getsecrets",
                        "-getsecret"      : "--getsecrets",    "-getsecrets"    : "--getsecrets",
                        "--attrcolumn"    : "--attrcolumns",   "--addgroups"    : "--addgroup",   "--delgroups" : "--delgroup",
                        "-ag"             : "--ag",            "-dg"            : "--dg",         "-ar"         : "--ar",
                        "--authTest"      : "--testAuth",      "--authtest"     : "--testAuth",   "--testauth"  : "--testAuth",
                        "--test"          : "--testAuth",      "--nocolor"      : "--nocolors",
                        "--sum"           : "--summary",
                        "--nh"            : "--noheaders",
                        "--tracks"        : "--track",
                        "--showoverride"  : "--showoverrides", "--showinherits" : "--showinherit",
                        "--clearoverride" : "--clearoverrides",
                        "--cfs"           : "--check_forwarding_schedule",
                        "--pol"           : "--polaris",
                        #"--groups"       : "--hosts",
                     }

    device_dao_aliases = {
                            "--service"  : "--device_service",
                            "--state"    : "--device_state",
                            "--env"      : "--environment",
                            "--env_name" : "--environment_name",
                            "--loc"      : "--location",
                            "--ip"       : "--ip_address",
                            "--vendor"   : "--vendor_supplier",
                            "--role"     : "--device_role",
                         }

    if denaliVariables['searchCategory'] == 'DeviceDao':
        for arg in argumentList:
            if '=' in arg:
                fullArg = []
                equalSign = True
                loc = arg.find('=')
                fullArg.append(arg[:loc])
                fullArg.append(arg[(loc + 1):])
                arg = fullArg[0]
            else:
                equalSign = False

            if arg in device_dao_aliases:
                if equalSign == True:
                    front = device_dao_aliases[arg]
                    arg = front + '=' + fullArg[1]
                else:
                    arg = device_dao_aliases[arg]
                ddnewArguments.append(arg)

            else:
                if equalSign == True:
                    arg = fullArg[0] + '=' + fullArg[1]
                ddnewArguments.append(arg)
    else:
        # If a different dao than DeviceDao comes in, without this return
        # an empty argument list is sent back and all kinds of assumptions
        # are then made (probably most of them incorrect).
        return argumentList

    for arg in ddnewArguments:
        if '=' in arg:
            fullArg = []
            equalSign = True
            loc = arg.find('=')
            fullArg.append(arg[:loc])
            fullArg.append(arg[(loc + 1):])
            arg = fullArg[0]
        else:
            equalSign = False

        if arg in misspelled:
            if equalSign == True:
                front = misspelled[arg]
                arg = front + '=' + fullArg[1]
            else:
                arg = misspelled[arg]
            newArguments.append(arg)

        else:
            if equalSign == True:
                arg = fullArg[0] + '=' + fullArg[1]
            newArguments.append(arg)

    return newArguments



##############################################################################
#
# filter_non_printable(input_string)
#

def filter_non_printable(input_string):

    #for (index, character) in enumerate(input_string):
    #    print "charac[index=%d] = %s :: %s" % (index, character, ord(character))

    # Right now this filter seems very limiting.  It essentially says that if
    # any character _sent_ through Denali's command line switch input is not
    # normal, it will be ejected.  There are upper ascii characters that are
    # potentially used in names this will reject.  Need to revisit this later.


    return ''.join([c for c in input_string if (ord(c) > 31 and ord(c) < 128) or ord(c) == 9])



##############################################################################
#
# combineArguments(argList)
#
#   This function allows values (like a list of hosts) to be separated by a
#   space; i.e., host1 host2 host3; or separated by a comma-space delimiter;
#   i.e., host1, host2, host3.  Without this function, a comma is required
#   to list hosts behind the "--hosts" switch, and extra spaces cannot be
#   included; i.e., host1,host2,host3.
#
#   Currently only the hosts and fields switches are allowed to have a space
#   separator.
#
#   The implementation of this function also means that bash globbing for
#   host names is now supported; i.e., --hosts db22{22..55}.oak1 --fields ...
#

def combineArguments(argList):

    originalArgumentList = argList[:]
    newArgumentList      = []
    combinedArguments    = ""

    for argument in argList:

        # remove any commas at the beginning or end of the argument
        # if they exist
        argument = argument.strip()
        if len(argument) > 0:
            while len(argument) > 0 and argument[0] == ',':
                argument = argument[1:]
            while len(argument) > 0 and argument[-1] == ',' :
                argument = argument[:-1]
        else:
            continue

        if argument.startswith("-h"):
            argument = argument.replace("-h", "--hosts")
        if argument.startswith("-f"):
            argument = argument.replace("-f", "--fields")
        if argument.startswith("+f"):
            argument = argument.replace("+f", "++fields")
        if argument.startswith("-g"):
            argument = argument.replace("-g", "--groups")
        if argument == "--pol":
            argument = argument.replace("--pol", "--polaris")

        if (argument.startswith("--hosts")  or
            argument.startswith("--fields") or
            argument.startswith("++fields") or
            argument.startswith("--groups") or
            argument.startswith("--mon")    or
            argument.startswith("--polaris")):

            if argument.find('=') != -1:
                argument = argument.replace('=', ' ', 1)
                argument = argument.split(' ')

                if len(combinedArguments) > 0:
                    newArgumentList.append(combinedArguments)

                newArgumentList.append(argument[0])
                combinedArguments = argument[1]

            elif len(combinedArguments) > 0:
                newArgumentList.append(combinedArguments)
                combinedArguments = ""
                newArgumentList.append(argument)
            else:
                newArgumentList.append(argument)

        elif (argument.startswith('--ip') or
              argument.startswith('--primary_ip') or
              argument.startswith('--secondary_ip') or
              argument.startswith('--ilo_ip') or
              argument.startswith('--subnet')):
            argument = argument.replace(',', ' OR ')
            newArgumentList.append(argument)

        elif argument.startswith('-') or argument.startswith('+'):
            if len(combinedArguments) > 0:
                newArgumentList.append(combinedArguments)
                combinedArguments = ""
            newArgumentList.append(argument)

        else:
            if len(combinedArguments) > 0:
                combinedArguments += ',' + argument
            else:
                combinedArguments = argument

    # catch the last one -- don't leave it dangling
    if len(combinedArguments) > 0:
        newArgumentList.append(combinedArguments)

    # go through the list once more, stripping out any duplicate commas
    searchNow = False
    for (index, argument) in enumerate(newArgumentList):
        if (argument == "--hosts"  or
            argument == "--fields" or
            argument == "++fields" or
            argument == "--groups" or
            argument == "--mon"    or
            argument == "--polaris"):
            searchNow = True
            continue

        if searchNow == True:
            searchNow = False
            while argument.find(",,") != -1:
                argument = argument.replace(",,",',')

            newArgumentList[index] = argument

    return newArgumentList



##############################################################################
#
# determineArgumentValue(arg, arg_values, sqlSearch)
#
#   MRASEREQ-41043:  Found a problem where some switches didn't work without
#   an equal sign.  Because all of these specific switches need the exact same
#   type of manipulation, this function was created to do that.
#

def determineArgumentValue(arg, arg_values, sqlSearch):

    if arg.find('=') != -1:
        # remove the first equal sign and have everything behind it become the
        # value for the argument
        return ([arg.split('=')[0], arg[(arg.find('=') + 1):]], sqlSearch)

    # see if there is a previous value in the arg_value List that is now stranded
    if arg_values[1] == "Waiting":
        # clear it out -- because it is useless now, the parameter will be ignored
        arg_values = ["None", "None"]

    retValue = validate_switch(arg, "unsure")

    if retValue == False or retValue == "invalid-combined":   # modified sql search?
        # add the argument if it is a list with 2 items in it
        # otherwise, ignore the switch completely.
        if len(arg) == 2:
            sqlSearch.append(arg)

    elif retValue == "valid-combined":
        arg_values = [arg, "Waiting"]

    elif retValue == "stand-alone":
        # mark the remaining value as "Empty" -- never to be filled
        arg_values = [arg, "Empty"]

    return (arg_values, sqlSearch)



##############################################################################
#
# checkForEqualSigns(denaliVariables, argumentList)
#
#   MRASEREQ-41586: Fix command line parameters that should have an equal
#                   sign included, but do not.
#

def checkForEqualSigns(denaliVariables, argumentList):

    special_handling = [ '--pdsh_options', '--po',
                         '--scp_options' , '--so', 'ssh_options',
                         '--pdsh_command', '--pc',
                         '--sudo',
                         '--pol',          '--polaris',
                       ]

    # zero-based
    al_length = len(argumentList)

    for (index, argument) in enumerate(argumentList):
        # See if we have a condition where one of the special_handling types is
        # without an equal sign -- if the argument matches, that means an equal
        # sign doesn't exist.
        if argument in special_handling:
            if (index + 1) >= al_length:
                # Houston, we have a problem.  Do not assign this, let it go
                # through and it will be caught in the huge if-else statement
                pass
            else:
                # Check and make sure the argument we're bolting on to the switch
                # is valid.  The current check is just to make sure that the text
                # doesn't start with '--'; if it doesn't use it.
                if argumentList[index + 1].startswith('--') == False:
                    argumentList[index] = argument + '=' + argumentList[index + 1]
                else:
                    pass

    new_argumentList = []

    for (index, argument) in enumerate(argumentList):
        # Search for any switch that is NOT part of the defined list
        if argument not in clswitches and argument.startswith('--') == True:
            # This means it is likely a qualifier (specific column/field search criteria)
            # Give it an equal sign if it doesn't have one.  Then, put the value with the
            # equal sign in the same argument.  Finally, delete the stand-alone argument.
            # This is done by only adding correct arguments to a new list, which is returned.
            if argument.find('=') == -1 and index != (len(argument) - 1):
                if argumentList[index + 1].startswith('--') == False:
                    argumentList[index] = argument + '=' + argumentList[index + 1]
                    new_argumentList.append(argumentList[index])
            else:
                new_argumentList.append(argument)
        else:
            if index > 0:
                if argumentList[index - 1].find('=') != -1:
                    arg_split = argumentList[index - 1].split('=')
                    if argument != arg_split[-1]:
                        new_argumentList.append(argument)
                else:
                    new_argumentList.append(argument)
            else:
                new_argumentList.append(argument)

    return new_argumentList



##############################################################################
#
# parseArgumentList(argumentList, denaliVariables)
#

def parseArgumentList(argumentList, denaliVariables):

    cliParameters = []
    sqlSearch     = []
    simpleSearch  = True
    arg_values    = ["None", "None"]
    oStream       = denaliVariables['stream']['output']

    special_handling = ['--pdsh_options', '--po', '--scp_options', '--so', 'ssh_options']

    # switches that can be empty (for default handling) or have values
    exception_switches = ['--mon', '--help', '--pol', '--polaris', '--verify']
    exception_found    = []

    fields_to_display  = ''

    # remove the script name (first List item)
    argumentList.pop(0)

    if denaliVariables['debug'] == True:
        print "Original argument list = %s" % argumentList

    # More than one user has had a problem here (including me)
    #   e.g., --host, instead of the correct --hosts
    #
    # It would be nice if denali could "catch" these simple mistakes where
    # the intent was correct, but the typing suffered (misspelled, missed
    # a letter, etc.).  Correct the known issues instead of erroring out
    # with minimal reasoning/explanation.
    argumentList = checkForCommonMisspellings(denaliVariables, argumentList)

    # allow spaces between hosts/fields
    argumentList = combineArguments(argumentList)

    # MRASEREQ-41586
    # Reorganize the parameters -- if needed because of some equal-sign non-compatibility
    # in the code
    argumentList = checkForEqualSigns(denaliVariables, argumentList)

    for (count, arg) in enumerate(argumentList):
        #print "argument = %s" % arg
        # strip off all white space (in case there are funny characters)
        arg = arg.strip()

        # remove any hidden characters (hopefully accepting all unicode variants)
        arg = filter_non_printable(arg)

        # search/replace ">=" with ">-" and "<=" with "<-"
        arg = arg.replace(">=",">-")
        arg = arg.replace("<=","<-")

        # special case, handle ++fields (addition to the default)
        if arg.startswith('++fields'):
            arg = arg.replace('++','--')

            # find the default alias information
            if "_DEFAULT" in denaliVariables["userAliases"].keys():
                fields_to_display = denaliVariables["userAliases"]["_DEFAULT"]
            elif "DEFAULT" in denaliVariables["userAliases"].keys():
                fields_to_display = denaliVariables["userAliases"]["DEFAULT"]

        # handle any switches that aren't sql parameters (MRASEREQ-41043)
        if arg in clswitches or arg.split('=')[0] in clswitches or arg.startswith('--up'):
            (arg_values, sqlSearch) = determineArgumentValue(arg, arg_values, sqlSearch)

        elif arg_values[1] == "Waiting" and arg_values[0] in special_handling:
            arg_values[1] = arg

        # if there is an equal sign, split the result and check it.
        elif '=' in arg:
            if arg_values[1] != "Waiting":
                # handle the default case with the equal sign (should be only one)
                arg_values = split_parameters(arg)

                if validate_switch(arg_values[0], "combined") != True:
                    # switch is not in the main list -- modified sql search?
                    if denaliVariables['polarisExecution'] == True and arg_values[0].startswith('--') == False:
                        # ensure that only properly formatted sql sequences are added
                        # for correct query syntax ... otherwise reject it because it
                        # is likely destined for handling by polaris
                        continue

                    sqlSearch.append(arg_values)
                    continue
            elif arg_values[0].startswith('--up') or arg_values[0] == '--polaris':
                # for updates, they arrive with multiple equal signs, which this
                # 'else' is designed to handle
                arg_values[1] = arg

            else:
                sqlSearch.append(arg.split('='))
                continue

        # if the argument is "waiting" for data, and there are no dashes in the
        # argument, then validate the switch as a 'value' only.
        elif arg_values[1] == "Waiting" and arg.startswith('-') == False:
            if validate_switch(arg, "value") == True:
                arg_values[1] = arg
                #if arg_values[0] in exception_switches:
                #    exception_found.remove(arg_values[0])
            else:
                # switch is not in the main list -- modified sql search?
                sqlSearch.append(arg_values)
                continue

        # no equal sign in the argument
        else:
            # It is possible that the user incorrectly entered parameters, and that
            # accidentally set in motion an entire scan of the CMDB host list.
            # Check for that and modify the host list if needed, or kill it if it
            # cannot be determined what was wanted.
            if len(sqlSearch) == 0 and len(argumentList) == 1:
                # If there are no sql search terms/qualifiers, and if there is only
                # one argument specified, verify whether it is a host or not.
                hostname = arg.split('.')
                for host_piece in hostname:
                    if host_piece.upper() in denali_location.dc_location:
                        arg_values = ['--hosts', arg]
                        break
                else:
                    oStream.write("Denali: Parameter syntax incorrect, stopping search execution.\n")
                    oStream.flush()
                    return (False, False, False)

            # see if there is a previous value in the arg_value List that is now stranded
            if arg_values[1] == "Waiting":
                # clear it out -- because it is useless now, the parameter will be ignored
                arg_values = ["None", "None"]

            retValue = validate_switch(arg, "unsure")

            if retValue == False or retValue == "invalid-combined":   # modified sql search?
                # add the argument if it is a list with 2 items in it
                # otherwise, ignore the switch completely.
                if len(arg) == 2:
                    sqlSearch.append(arg)
                continue

            elif retValue == "valid-combined":
                arg_values = [arg, "Waiting"]
                if arg_values[0] in exception_switches:
                    exception_found.append(arg_values[0])
                continue

            elif retValue == "stand-alone":
                # mark the remaining value as "Empty" -- never to be filled
                arg_values = [arg, "Empty"]

        #print "cli switch value(s) = %s" % arg_values
        # store the reformed (corrected) List of passed in parameters ... !IF! it isn't
        # already in the list of parameters
        if (arg_values[0] == "--hosts" or arg_values[0] == '--fields'):
            if arg_values[1] == 'Waiting':
                cliParameters.append(arg_values)
            else:
                if cliParameters[-1] != arg_values:
                    cliParameters.append(arg_values)
        else:
            cliParameters.append(arg_values)

    # monitoring exception -- if monitoring is still waiting
    if len(exception_found) > 0:
        #print "found an exception switch still waiting for data"
        #print "exception found = %s" % exception_found
        for exception in exception_found:
            if exception == "--mon":
                cliParameters.append(["--mon", denaliVariables["monitoring_default"]])
            if exception == "--help":
                cliParameters.append(["--help", ''])

    # check if the user gave a credential file to read
    #  -- if yes, then have the argument parser handle it.
    #  -- if no, then they need to login manually.  Add an argument to the list
    #            to alert the code to this fact.

    # parameterCheck
    parameterCheck = {
                        "command"       :   False,
                        "credentials"   :   False,
                        "dao"           :   False,
                        "dao_"          :   False,
                        "external"      :   False,
                        "fields"        :   False,
                        "help"          :   False,
                        "history"       :   False,
                        "hosts"         :   False,
                        "load"          :   False,
                        "monitor"       :   False,
                        "output"        :   False,
                        "pdsh"          :   False,
                        "polaris"       :   False,
                        "power"         :   False,
                        "powerid"       :   False,
                        "rack"          :   False,
                        "rackid"        :   False,
                        "scp_dest"      :   False,
                        "scp_source"    :   False,
                        "showoverrides" :   False,
                        "sql"           :   False,
                        "stdin"         :   False,
                        "stdinData"     :   False,
                        "switch"        :   False,
                        "switchid"      :   False,
                        "update"        :   False,
                        "username"      :   False,
                        "verify"        :   False,
                     }

    for parameter_pair in cliParameters:
        # was a credentials file submitted?
        if "--creds" in parameter_pair[0]:
            parameterCheck["credentials"] = True

            # with "--creds" entered a --user parameter is unnecessary
            for (index, parameter_pair) in enumerate(cliParameters):
                if "--user" in parameter_pair[0] or parameter_pair[0].startswith("-u"):
                    if denaliVariables["slack"] == True:
                        denaliVariables["slackUser"] = parameter_pair[1]
                    cliParameters.pop(index)
                    break
            continue

        if "--user" in parameter_pair[0] or parameter_pair[0].startswith("-u"):
            parameterCheck["username"] = True
            continue

        if "--count" in parameter_pair[0]:
            denaliVariables["method"] = "count"
            denaliVariables["methodData"] = parameter_pair[1]
            continue

        # were column fields submitted?
        if parameter_pair[0].startswith("-f") or "--fields" in parameter_pair[0]:
            parameterCheck["fields"] = True
            continue

        if "--mon" in parameter_pair[0]:
            parameterCheck["monitor"] = True
            continue

        if "--help" in parameter_pair[0]:
            parameterCheck["help"] = True
            continue

        if "--verify" in parameter_pair[0] or "-v" in parameter_pair[0]:
            parameterCheck["verify"] = True
            continue

        if (parameter_pair[0] == "--up"         or parameter_pair[0] == "--update"     or
            parameter_pair[0] == "--updatefile" or parameter_pair[0] == "--updateattr" or
            parameter_pair[0] == "--addhistory" or parameter_pair[0] == "--grphistory" or
            parameter_pair[0] == "--addgroup"   or parameter_pair[0] == "--delgroup"   or
            parameter_pair[0] == "--ag"         or parameter_pair[0] == "--dg"         or
            parameter_pair[0] == "--newgroup"   or parameter_pair[0] == "--clearoverrides"):
            parameterCheck["update"] = True
            continue

        if parameter_pair[0] == "--dao":
            parameterCheck["dao"] = True
            continue

        if parameter_pair[0].startswith('--dao_'):
            parameterCheck['dao_'] = True
            continue

        if parameter_pair[0] == "-c" or parameter_pair[0] == "--command":
            parameterCheck["command"] = True
            continue

        pdsh_commands = ['--pdsh_command', '--pc', '--pci']
        if parameter_pair[0] in pdsh_commands:
            parameterCheck["pdsh"] = True

        scp_source      = ['--src',  '--source']
        scp_destination = ['--dest', '--destination']
        if parameter_pair[0] in scp_source:
            parameterCheck["scp_source"] = True
            continue

        if parameter_pair[0] in scp_destination:
            parameterCheck["scp_dest"] = True
            continue

        if "--polaris" in parameter_pair[0]:
            parameterCheck["polaris"] = True
            continue

        if parameter_pair[0].startswith("--power"):
            parameterCheck["power"] = True
            # MRASETEAM-40434
            for (index, parameter_pair) in enumerate(cliParameters):
                if parameter_pair[0].startswith("-f") or "--fields" in parameter_pair[0]:
                    cliParameters.pop(index)
                    break
            continue

        if parameter_pair[0].startswith("--powerid"):
            parameterCheck["powerid"] = True
            # MRASETEAM-40434
            for (index, parameter_pair) in enumerate(cliParameters):
                if parameter_pair[0].startswith("-f") or "--fields" in parameter_pair[0]:
                    cliParameters.pop(index)
                    break
            continue

        if parameter_pair[0] == "--rack":
            parameterCheck["rack"] = True
            # MRASETEAM-40434
            for (index, parameter_pair) in enumerate(cliParameters):
                if parameter_pair[0].startswith("-f") or "--fields" in parameter_pair[0]:
                    cliParameters.pop(index)
                    break
            continue

        if parameter_pair[0].startswith("--rackid"):
            parameterCheck["rackid"] = True
            # MRASETEAM-40434
            for (index, parameter_pair) in enumerate(cliParameters):
                if parameter_pair[0].startswith("-f") or "--fields" in parameter_pair[0]:
                    cliParameters.pop(index)
                    break
            continue

        if parameter_pair[0] == "--switch":
            parameterCheck["switch"] = True
            # MRASETEAM-40434
            for (index, parameter_pair) in enumerate(cliParameters):
                if parameter_pair[0].startswith("-f") or "--fields" in parameter_pair[0]:
                    cliParameters.pop(index)
                    break
            continue

        if parameter_pair[0] == "--switchid":
            parameterCheck["switchid"] = True
            # MRASETEAM-40434
            for (index, parameter_pair) in enumerate(cliParameters):
                if parameter_pair[0].startswith("-f") or "--fields" in parameter_pair[0]:
                    cliParameters.pop(index)
                    break
            continue

        if parameter_pair[0] == "--" or parameter_pair[0] == "--stdin":
            parameterCheck["stdin"] = True
            continue

        if parameter_pair[0] == "--stdin":
            parameterCheck["stdinData"] = True
            continue

        if parameter_pair[0] == "--history":
            parameterCheck["history"] = True
            continue

        if "--load" in parameter_pair[0] or parameter_pair[0].startswith("-l"):
            parameterCheck["load"]  = True
            parameterCheck["hosts"] = True
            simpleSearch = True
            continue

        # were a list of servers submitted (simple search?)
        if (
            parameter_pair[0].startswith("-h") or "--hosts" in parameter_pair[0] or
            parameter_pair[0] == "--" or parameter_pair[0] == "-"
           ):
            parameterCheck["hosts"] = True
            simpleSearch = True
            continue

        # was an output target submitted?
        if parameter_pair[0].startswith("-o") or "--out" in parameter_pair[0]:
            parameterCheck["output"] = True
            continue

        if parameter_pair[0].startswith("--sql"):
            parameterCheck["sql"] = True
            continue

        if parameter_pair[0] == "-e" or parameter_pair[0] == "-m"  or parameter_pair[0].startswith("--ext"):
            parameterCheck["external"] = True
            continue

        if parameter_pair[0] == "--showoverrides":
            parameterCheck["showoverrides"] = True
            continue

    # All of the initial parameters checks have been made.
    # Using this information, make sure the denali state is proper for what
    # is being asked for.

    if parameterCheck["credentials"] == False and parameterCheck["username"] == False:
        # last check -- see if there was a username specified in the config file
        if denaliVariables["userName"] == '':
            cliParameters.append(["--user", "Waiting"])
        else:
            cliParameters.append(["--user", denaliVariables["userName"]])

    if parameterCheck["update"] == True:
        # remove the fields switch (if applicable)
        for (index, parameter_pair) in enumerate(cliParameters):
            if parameter_pair[0].startswith("-f") or "--fields" in parameter_pair[0]:
                cliParameters.pop(index)
                break

    if (parameterCheck["fields"] == False and parameterCheck["command"]  == False and
        parameterCheck["rack"]   == False and parameterCheck["rackid"]   == False and
        parameterCheck["power"]  == False and parameterCheck["powerid"]  == False and
        parameterCheck["switch"] == False and parameterCheck["switchid"] == False and
        parameterCheck["update"] == False):

        cliParameters.append(["--fields", "Empty"])

    if parameterCheck["output"] == False:
        cliParameters.append(["--out", "txt"])

    # if load with a stdin switch is used, flag it appropriately (or it won't display)
    if parameterCheck["load"] == True and parameterCheck["stdin"] == True:
        # "hosts" is off to include a full search - added just below
        parameterCheck["hosts"]     = False
        parameterCheck["stdinData"] = True

    # if --stdin is used without using "--", set it correctly for the user
    if parameterCheck["stdinData"] == True and parameterCheck["stdin"] == False:
        parameterCheck["stdin"] == True
        if parameterCheck['load'] == False:
            cliParameters.append(["--", "Empty"])

    if parameterCheck["hosts"] == False and parameterCheck["dao"] == False and parameterCheck["dao_"] == False:
        if parameterCheck["stdin"] == False or (parameterCheck["stdin"] == True and
                                                parameterCheck["stdinData"] == True):

            for (index, parameter_pair) in enumerate(cliParameters):
                if parameter_pair[0] == "-h" or parameter_pair[0] == "--hosts":
                    break
            else:
                # Block this query?  Make the user request at least a field or host.
                # This means the user is requesting a flat-scan of the entire database
                # to include all hosts -- although this is possible, it is required
                # that the user request this, instead of Denali putting it in for them.
                if ["--fields", "Empty"] in cliParameters:
                    denaliVariables['db_flatscan'] = True
                # no host parameter found -- add in the generic "find everything"
                cliParameters.append(["--hosts", "*"])

        simpleSearch = True
    elif parameterCheck["hosts"] == False:
        simpleSearch = False

    if parameterCheck["sql"] == True:
        simpleSearch = False
        sqlSearch    = []

        # with "--sql" entered a --fields parameter set is unnecessary
        for (index, parameter_pair) in enumerate(cliParameters):
            if parameter_pair[0].startswith("-f") or "--fields" in parameter_pair[0]:
                cliParameters.pop(index)
                break

    if parameterCheck["showoverrides"] == True:
        for (index, parameter_pair) in enumerate(cliParameters):
            if parameter_pair[0].startswith("-f") or parameter_pair[0].startswith("--fields"):
                # remove 'Empty' from the field list
                if 'Empty' in parameter_pair[1].split(','):
                    parameter_pair[1] = parameter_pair[1].split(',')
                    parameter_pair[1].remove('Empty')
                    parameter_pair[1] = ','.join(parameter_pair[1])

                # add in 'name' if needed
                if 'name' not in parameter_pair[1].split(','):
                    add_name = parameter_pair[1] + ",name"
                    cliParameters[index] = ['--fields',add_name]
                    parameter_pair[1]    = add_name

                # add in 'ATTRIBUTES' if needed
                if 'ATTRIBUTES' not in parameter_pair[1].split(','):
                    add_attr = parameter_pair[1] + ",ATTRIBUTES"
                    cliParameters[index] = ['--fields',add_attr]
                break
        else:
            cliParameters.append(["--fields", "name,ATTRIBUTES"])

    # if the command switch is entered, make sure there is an associated fields command.
    # if not, then mark it empty so the default(s) will be used.
    if parameterCheck["command"] == True:
        denaliVariables['commandExecuting'] = True
        for (index, parameter_pair) in enumerate(cliParameters):
            if parameter_pair[0].startswith("-f") or parameter_pair[0].startswith("--fields"):
                # The FIELDS parameter must contain 'name' as an entry because it
                # will be used in denali_utility.extractHostList()
                if 'name' not in parameter_pair[1].split(',') and len(fields_to_display) == 0:
                    add_name = parameter_pair[1] + ",name"
                    cliParameters[index] = ['--fields',add_name]
                break
        else:
            cliParameters.append(["--fields", "Empty"])
    else:
        # Command is set to False -- see if the user requested a command without using -c/--command
        # This is just trying to have the code be user-friendly (filling in the blanks, so to speak)
        command = ''

        if parameterCheck["pdsh"] == True:
            command = "pdsh"
        elif parameterCheck["scp_source"] == True and parameterCheck["scp_dest"] == True:
            command = "scp"

        if len(command) > 0:
            denaliVariables['commandExecuting'] = True
            # Automatically set the command for the user
            # !!DO NOT!! put an else on this, or all "--help" command(s) will fail
            cliParameters.append(["--command", command])

    if parameterCheck["external"] == True:
        if (parameterCheck["rack"]    == True or parameterCheck["rackid"]   == True or
            parameterCheck["power"]   == True or parameterCheck["powerid"]  == True or
            parameterCheck["switch"]  == True or parameterCheck["switchid"] == True or
            parameterCheck["command"] == True or parameterCheck["update"]   == True):

            oStream.write("Improper syntax for command-line switches.\n")
            oStream.write("The -e/--ext switch was used and also one of the\n")
            oStream.write("following:  --power/--powerid, --rack/--rackid,\n")
            oStream.write("            --switch/--switchid, -c/--command\n")
            oStream.write("The external switch cannot be used in combination with any\n")
            oStream.write("of those.  Remove the offending switch and submit the\n")
            oStream.write("command again.\n\n")
            oStream.flush()
            return (False, False, False)

    if parameterCheck["history"] == True:
        # with "--history" entered the --fields parameter will be set programmetically by denali
        for (index, parameter_pair) in enumerate(cliParameters):
            if parameter_pair[0].startswith("-f") or "--fields" in parameter_pair[0]:
                cliParameters.pop(index)
                break
        cliParameters.append(["--fields", "name,device_id"])

    if parameterCheck["fields"] == False and parameterCheck["dao"] == True:
        oStream.write("Denali syntax error:  Fields to search for are missing from the Dao query.  The SQL query will fail.\n")
        oStream.write("                      Add \"--fields=<field/s to search for>\" to the denali run statement.\n")
        return (False, False, False)

    if parameterCheck["monitor"] == True:
        # remove external and command parameters if they exist, because these are the
        # 2 command line parameters that could possibly be included
        for (index, parameter_pair) in enumerate(cliParameters):
            if (parameter_pair[0] == "-e" or parameter_pair[0] == "--ext" or parameter_pair[0] == "-m" or
                parameter_pair[0] == "-c" or parameter_pair[0] == "--command"):
                cliParameters.pop(index)

    # no --fields parameter with polaris
    if parameterCheck["polaris"] == True:
        for (index, parameter_pair) in enumerate(cliParameters):
            if parameter_pair[0].startswith("-f") or "--fields" in parameter_pair[0]:
                cliParameters.pop(index)
                break

    # For rundeck specific support, replace all double underscores in either the
    # Device State or the Device Service with a single space.
    (sqlSearch, cliParameters) = replaceDoubleUnderscores(denaliVariables, sqlSearch, cliParameters)

    # If the daoDictionary is non-empty, then see if any items need to be added
    # (by default) to the sqlSearch list
    (sqlSearch, cliParameters) = addDefaultSearchItems(denaliVariables, sqlSearch, cliParameters)
    if sqlSearch == False and cliParameters == False:
        # Error case when a bogus profile is requested
        return (False, False, False)

    # Check to see if pdsh_separate additions are required
    separator_reserved = [ 'dpc', '_single_' ]

    if denaliVariables['pdshSeparate'] != False:
        # don't add 'dpc' as a query object for SQL -- that will cause a search failure
        if denaliVariables['pdshSeparate']['separator'] not in separator_reserved:
            temp_cliParameters = []
            for (index, field_key) in enumerate(cliParameters):
                if field_key[0] != "--fields":
                    temp_cliParameters.append(cliParameters[index])
            cliParameters = temp_cliParameters[:]
            fields_to_use = "name,%s" % denaliVariables['pdshSeparate']['separator']
            cliParameters.append(['--fields',fields_to_use])

    # Check to see if attribute_value (or attribute_name) were used alone as a column field
    # to show.  If so, add the other one.
    for (index,field_key) in enumerate(cliParameters):
        if field_key[0] == "--fields":
            field_values = field_key[1].split(',')
            attr_name  = False
            attr_value = False
            for value in field_values:
                if value == 'attribute_name':
                    attr_name = True
                elif value == 'attribute_value':
                    attr_value = True
            if attr_name == False and attr_value == False:
                break
            else:
                if attr_name == False:
                    field_key[1] += ',attribute_name'
                elif attr_value == False:
                    field_key[1] += ',attribute_value'
                cliParameters[index] = field_key
                denaliVariables["attributesStacked"] = False

    if parameterCheck["verify"] == True:
        # Ensure that device_state, device_service, and environment are included
        # in the fields command so the verify code can properly function
        for (index, field_key) in enumerate(cliParameters):
            if field_key[0] == "--fields":
                cliParameters[index][1] = "name,device_state.full_name,device_service.full_name,environment.full_name"
                break
            else:
                cliParameters.append(["--fields","name,device_state.full_name,device_service.full_name,environment.full_name"])

    # if +f is used, add the given field list to the default aliases
    # fields_to_display is only used with +f/++fields
    if len(fields_to_display):
        for (index, field_key) in enumerate(cliParameters):
            if field_key[0] == "--fields":
                cliParameters[index][1] = fields_to_display + ',' + cliParameters[index][1]
                break

    # The parameters have been gathered, added to (profile items), and validated.
    # Sort the completed list by priority.
    cliParameters = cliPrioritySort(cliParameters)

    if denaliVariables['debug'] == True:
        print "Modified argument list:"
        print "  cliParameters = %s" % cliParameters
        print "  sqlSearch     = %s" % sqlSearch
        print "  simpleSearch  = %s" % simpleSearch

    return (cliParameters, sqlSearch, simpleSearch)



##############################################################################
#
# addDefaultSearchItems(denaliVariables, sqlSearch, cliParameters)
#
#   This function adds default options declared in the .denali/config file.
#   They are added by a specified profile (--profile) and only if no other
#   sql search term matches (alias or cmdb).
#

def addDefaultSearchItems(denaliVariables, sqlSearch, cliParameters):

    debug = False

    if debug == True:
        print "sqlSearch     (b) = %s" % sqlSearch
        print "cliParameters (b) = %s" % cliParameters

    if denaliVariables['external'] == True:
        # Determine the module called -- potentially setting the dao
        # The oncall external module is the only one written (so far) that uses
        # a different dao than the other external modules.  This causes problems
        # because the profile code will add in (by default) DeviceDao settings if
        # there is a 'default' profile configuration -- which causes the oncall
        # code to fail.  By setting the dao properly, it fixes this issue.
        for argument in cliParameters:
            if argument[0] == '-e' or argument[0] == '--ext' or argument[0] == '-m':
                external_module = argument[1]
                if external_module.startswith('oncall'):
                    dao = 'OnCallDao'
    else:
        dao = denaliVariables['searchCategory']

    profile = denaliVariables['profile']

    if debug == True:
        print "dao               = %s" % dao
        print "profile           = %s" % profile

    # Make sure there is data in the dictionary, the specified profile exists,
    # and that the search dao is in the specified profile before continuing.
    if denaliVariables['noProfile'] == True or len(denaliVariables['daoDictionary']) == 0:
        return (sqlSearch, cliParameters)
    if profile not in denaliVariables['daoDictionary']:
        for argument in cliParameters:
            # check if the user specifically requested a profile
            if argument[0] == '--profile':
                break
        else:
            # no profile requested -- just 'default' assumed, and currently
            # there is no 'default' defined in the config file.  Just return
            # the current parameters and continue.
            return (sqlSearch, cliParameters)
        # if the user requests a profile that doesn't exist - error out
        print "Denali: Requested profile [%s] does not exist." % profile
        return (False, False)
    if dao not in denaliVariables['daoDictionary'][profile]:
        return (sqlSearch, cliParameters)

    # Other than sql search criteria, these are the switches that a profile will
    # successfully accept and use.
    accepted_keys = [
                     # keys with values
                     'sort', 'count', 'fields', 'limit', 'out', 'load', 'hosts',

                     # keys with no values (toggle switches)
                     'aliasheaders', 'attrcolumns', 'jira_closed', 'mheaders', 'mondetails',
                     'nocolors'    , 'noheaders'  , 'nosummary'  , 'nowrap'  , 'showdecomm',
                     'showsql'     , 'spots_grep' , 'summary'    , 'truncate'
                    ]

    field_key_list = denaliVariables['daoDictionary'][profile][dao].keys()
    for field_key in field_key_list:
        # Depending upon what is in the config file, one of two Lists could
        # be operated on (cliParameters or sqlSearch).  Use python's ability
        # to redirect to allow those Lists to be changed by changing a single
        # variable for both (sneaky, but nice).
        if field_key in accepted_keys:
            search_list = cliParameters

            # Count needs to be handled differently -- so input the data here
            # because this step typically takes place in the parseArgumentList
            # function above.
            if field_key == "count":
                denaliVariables["method"]     = "count"
                denaliVariables["methodData"] = denaliVariables['daoDictionary'][profile][dao][field_key][1]
        else:
            search_list = sqlSearch

        # make sure the requested update was not already requested -- if is was, skip it
        for search_term in search_list:
            search_field_key = search_term[0][2:]       # [2:] this eliminates the "--"
            if field_key == search_field_key == "out" and search_term[1] == 'txt':
                continue
            if field_key == search_field_key == "hosts" and search_term[1] == '*':
                continue
            if field_key == search_field_key and search_term[1] != 'Empty':
                break
            if denaliVariables['daoDictionary'][profile][dao][field_key][0] == search_field_key and search_term[1] != 'Empty':
                break
        else:
            # There are some switches that are defaulted into the cliParameters, so if
            # a profile uses them, they should be overwritten by removing the original
            # key/value pair
            if field_key == "fields":
                search_list.remove(['--fields', 'Empty'])
            elif field_key == "out":
                search_list.remove(['--out', 'txt'])
            elif (field_key == "hosts" or field_key == "load") and ['--hosts', '*'] in search_list:
                # If either 'hosts' or 'load' is used in a profile and the default search
                # criteria of "all of CMDB" is used, just remove it
                search_list.remove(['--hosts', '*'])

            # add the profile value to the designated list
            addKey_Value = ['--' + field_key, denaliVariables['daoDictionary'][profile][dao][field_key][1]]
            search_list.append(addKey_Value)
            denaliVariables['profileAdded'] = True

    if debug == True:
        print "profile added     = %s" % denaliVariables['profileAdded']
        print "sqlSearch     (a) = %s" % sqlSearch
        print "cliParameters (a) = %s" % cliParameters

    return (sqlSearch, cliParameters)



##############################################################################
#
# replaceDoubleUnderscores(denaliVariables, sqlSearchParameters, cliSearchParameters)
#
#   This function replaces a global replace-all double underscores.  That statement
#   caused problems because of a file search with the -c/--command issued via
#   PDSH to a group of servers.  The legitimate double underscore was replaced
#   with a space, which caused the file search to completely fail.  This function
#   will only replace double underscores in the Device State and Device Service
#   parameters -- if they are used.  If more categories are needed, they can
#   easily be added below.
#

def replaceDoubleUnderscores(denaliVariables, sqlSearchParameters, cliSearchParameters):

    sql_possible_matches = [
                             '--device_role'   , '--device_role.full_name'   , '--device.device_role.full_name'   , '--role'   ,
                             '--device_service', '--device_service.full_name', '--device.device_service.full_name', '--service',
                             '--device_state'  , '--device_state.full_name'  , '--device.device_state.full_name'  , '--state'  ,
                           ]

    cli_possible_matches = [
                             '--update',
                           ]

    # look in the sql parameters first
    for (index, argument) in enumerate(sqlSearchParameters):
        if argument[0] in sql_possible_matches:
            sqlSearchParameters[index][1] = argument[1].replace("__", " ")

    # look in the cli parameters
    for (index, argument) in enumerate(cliSearchParameters):
        if argument[0] in cli_possible_matches:
            if argument[0] == '--update':
                argument_split = argument[1].split(',')
                for (aIndex, aSplit) in enumerate(argument_split):
                    if ('--' + aSplit.split('=')[0]) in sql_possible_matches:
                        argument_split[aIndex] = argument_split[aIndex].replace("__", " ")

                # put them back together now (changed values back in original variable)
                argument[1] = ','.join(argument_split)

            else:
                cliSearchParameters[index][1] = argument[1].replace("__", " ")

    return sqlSearchParameters, cliSearchParameters



##############################################################################
#
# split_parameters(argument)
#
#   argument is a single item from the argument List (sys.argv)
#
#   Assume a given input as such:  "--file=/home/user/servers.txt"
#   Split this into two parts:
#       (1)  --file
#       (2)  /home/user/servers.txt
#
#   I also account for the case where the user put multiple equal signs back
#   to back (--file===/home/user/servers.txt).  The code removes all equal
#   signs (in case someone got keyboard "happy"
#

def split_parameters(argument):

    while argument.count('=') > 1:
        argument = argument.replace("=", "", 1)

    return argument.strip().split('=', 1)



##############################################################################
#
# showDefaultAliases(denaliVariables)
#

def showDefaultAliases(denaliVariables):

    print
    print "Default hard-coded aliases:"
    print
    print " Alias Name        |  Fields Represented"
    print '=' * 120

    aliasKeys = fieldSubstitutions.keys()
    aliasKeys.sort()

    for key in aliasKeys:
        print " %-13s     |  %s" % (key, fieldSubstitutions[key])

    if len(denaliVariables['userAliases'].keys()):
        print
        print
        print "User-defined aliases:"
        print
        print " Alias Name        |  Fields Represented"
        print '=' * 120

        aliasKeys = denaliVariables['userAliases'].keys()
        aliasKeys.sort()

        # remove any duplicates (i.e., 'DEFAULT' if '_DEFAULT' exists)
        possibleDuplicates = ['DEFAULT', 'POWER', 'SWITCH', 'RACK']
        for dup in possibleDuplicates:
            if dup in aliasKeys:
                aliasKeys.remove(dup)

        for key in aliasKeys:
            print " %-13s     |  %s" % (key, denaliVariables['userAliases'][key])

    print
    print
    print "Alias names shown above (the capitalized names) can be put directly in the \"--fields\" switch and will"
    print "programmatically be expanded to the represented fields to be displayed."
    print
    print "Example:"
    print "   denali.py --hosts=dn1?.or1 --fields=name,HARDWARE"
    print
    print "   The above example is transferred to CMDB as the following set of fields:"
    print "     --fields=name,model,serial,asset_id,model_category,memory,cpu"
    print



##############################################################################
#
# fieldSubstitutionCheck(denaliVariables, fieldString)
#

fieldSubstitutions = {
                        "ALERTS"        : "alert_state,alert_update,alert_details",#,alert_time",
                        "ATTRIBUTE"     : "attribute_name,attribute_value", #attribute_inheritance",
                        "ATTRIBUTES"    : "attribute_name,attribute_value", #attribute_inheritance",
                        "ARCHIVE"       : "master_slave,related_device",
                        "BASE"          : "device_state,device_service,environment",
                        "CMR"           : "id,start_date,end_date,priority,risk,impact,summary",
                        "CMR_URL"       : "id_url,start_date,end_date,priority,risk,impact,summary",
                        "DATES"         : "date_received,actual_arrival_date,install_date,initial_kick_date,last_imaged_date,last_update_datetime",
                        "DEFAULT"       : "name,device_state,device_service,environment,model,cage_name,rack_name",
                        "HARDWARE"      : "model,serial,asset_id,model_category,memory,cpu",
                        "JIRA"          : "jira_ticket,jira_status",
                        "JIRA_INFO"     : "jira_ticket,jira_status,jira_subject,jira_assignee,jira_creator,jira_created_on,jira_updated_on",
                        "JIRA_URL"      : "jira_url,jira_status",
                        "LAN"           : "primary_ip_address,mac,ip_block_prefix,default_gateway,switch_name,vlan_number,vlan,int_dns_name,ilo_ip_address",
                        "LOCATION"      : "cage_location,cage_name,rack_name,rack_unit,rack_position,rack_id",
                        "MASTER_SLAVE"  : "master_slave,related_device",
                        "OS"            : "os_name,kernel,cpu_cores,memory,cpu",
                        "POWER"         : "host_power_supply,dc_power_supply_connection,dc_power_supply_connection_id",
                        "SECRET"        : "name",
                        "SWITCH"        : "device_interfaces,switch_name,switch_port_name"
                     }

def fieldSubstitutionCheck(denaliVariables, fieldString):

    adjustedFields = ''

    # add any user aliases to the fieldSubstitutions dictionary
    fieldSubstitutions.update(denaliVariables["userAliases"])

    keyList = fieldSubstitutions.keys()
    fieldList = fieldString.split(',')

    for key in keyList:
        for (index, field) in enumerate(fieldList):
            if key == field:
                # add the extra field in the aliased names if requested
                if field.startswith('ATTRIBUTE') and denaliVariables['attributeOverride'] == True:
                    fieldList[index] = 'attribute_name,attribute_value,attribute_overrides_id'
                elif field.startswith('ATTRIBUTE') and denaliVariables['attributeInherit'] == True:
                    fieldList[index] = 'attribute_name,attribute_value,attribute_inherited_id'
                else:
                    fieldList[index] = fieldSubstitutions[key]
                continue

    for field in fieldList:
        if adjustedFields == '':
            adjustedFields = field
        else:
            adjustedFields += ',' + field

    return adjustedFields



##############################################################################
#
# checkForAttributeField(fields)
#

def checkForAttributeField(fields):

    # turn the string into a List
    fieldList = fields.split(',')

    for field in fieldList:
        if (field == "ATTRIBUTES" or field == "attribute_name" or
            field == "attribute_value" or field == "attribute_inheritance"):

            return True

    return False



##############################################################################
#
# getAttributeFields(argumentFields, denaliVariables)
#
#   This is a function that finds the attribute columns and records their
#   column numbers in a denaliVariables field.  The column with the '*' by
#   it represents the column that the other two (if included) will be sorted
#   by.  By default this is attribute_name.
#

def getAttributeFields(argumentFields, denaliVariables):

    attributeFields = ''
    attr_name_included        = -1
    attr_value_included       = -1
    attr_inheritance_included = -1

    argFields = argumentFields.split(',')

    for (index, field) in enumerate(argFields):
        if field == "ATTRIBUTES":
            attributeFields = '*' + str(index) + ',' + str(index + 1) + ',' + str(index + 2)
            break

        if field == "attribute_name":
            attr_name_included = '*' + str(index)

        elif field.startswith("attribute_"):
            if "value" in field:
                attr_value_included = str(index)
            else:
                attr_inheritance_included = str(index)
    else:
        # see if "attribute_name" was included
        if attr_name_included == -1:
            if attr_value_included == -1:
                attr_inheritance_included = '*' + str(attr_inheritance_included)
            else:
                attr_value_included = '*' + str(attr_value_included)

        attributeFields = str(attr_name_included) + ' ' + str(attr_value_included) + ' ' + str(attr_inheritance_included)

        attributeFields = attributeFields.replace("-1", '')
        attributeFields = attributeFields.strip()
        attributeFields = attributeFields.replace(' ', ',')
        attributeFields = attributeFields.replace(",,", ',')

    denaliVariables["attributeColumns"] = attributeFields

    return True



##############################################################################
#
# validateDataCenter(argumentList)
#

def validateDataCenter(argumentList):

    dcList = []

    if ',' in argumentList:
        tempList = argumentList.split(',')
    else:
        tempList = [argumentList]

    for dc in tempList:
        if dc.upper() in denali_location.dc_location:
            dcList.append(dc)

    return dcList



##############################################################################
#
# expandSQLShortCutParameters(denaliVariables)
#

def expandSQLShortCutParameters(denaliVariables):

    replace_dictionary = {
                            'device_state': {
                                                'odis' : 'On Duty - In Service',
                                                'ods'  : 'On Duty - Standby',
                                                'poh'  : 'On Duty - Poweroff Hold',

                                                'odr'  : 'Off Duty - Reserved',
                                                'spare': 'Off Duty - Spare',

                                                'ppc'  : 'Provisioning - Pending Config',
                                                'pxe'  : 'Provisioning - Ready for PXE',
                                                'pis'  : 'Provisioning - Image Started',
                                                'pds'  : 'Provisioning - Deploying Software',
                                                'pic'  : 'Provisioning - Image Complete',
                                            }
                         }

    for (a_index, argument) in enumerate(denaliVariables['sqlParameters']):
        argument_type = argument[0][2:]
        if argument_type in replace_dictionary:
            argument_values = argument[1].split()
            replace_keys    = replace_dictionary[argument_type].keys()
            for (v_index, value) in enumerate(argument_values):
                if value in replace_keys:
                    argument_values[v_index] = replace_dictionary[argument_type][value]

            denaliVariables['sqlParameters'][a_index][1] = ' '.join(argument_values)

    return True



##############################################################################
#
# validateSQLParameters(denaliVariables)
#

def validateSQLParameters(denaliVariables):

    #
    # This routine should ?only? be run when doing the "simple" query format
    # and construction.
    #
    # All "sql parameters" must come in one of the two following formats:
    #   (1) --<object_name>="condition1 <qualifier> condition2 ..."
    #   (2) --<object_name>=condition1
    #
    # Qualifiers supported:  AND, OR, NOT
    #
    # The equal sign isn't required; however, if there is a space in the
    # conditional statement following the object, the entire statement must
    # be surrounded by double-quotation marks.
    #
    # This doesn't doesn't touch the conditional statement -- it just validates
    # the object name portion; it will remove "--" for each object.
    #
    # It compares the "field" value(s) from the cli parameters with all of the
    # sql parameters.  Every sql parameter must have a matching cli field
    # parameter, or the parameter is invalid and will be dropped from the
    # resultant comination.
    #
    #   Updated:  sql parameters are not removed if they don't have a
    #             matching cli field -- they are added anyway.
    #
    # At the end of this function, the sql parameters are validated against
    # potential alias names in cmdb, and their full (un-aliased) name is
    # stored in the final sql parameter set.
    #
    # The function returns the completed/modified sql parameter set.
    #

    sqlModifiedList = ''
    sqlTempList     = []
    cliParameters   = denaliVariables["cliParameters"]
    sqlParameters   = denaliVariables["sqlParameters"]

    # get the field value(s) from the cliParameter (List of Lists)
    for argument in cliParameters:
        if argument[0] == '-f' or argument[0] == '--fields':
            fields = argument[1]
            break
    else:
        # no fields argument given -- invalid cli entered?
        # this function can be used during a "--update/file" command
        # assign the name to the fields argument
        fields = "name"
        #return False

    for (index, sqlObject) in enumerate(sqlParameters):
        # remove all of the dashes from the switch
        while '-' in sqlObject:
            sqlObject = sqlObject.replace('-', '')

        # separate by commas
        cliParms = fields.split(',')

        for cliObject in cliParms:
            if sqlObject == cliObject:
                sqlModifiedList += sqlObject + ','
                sqlTempList.append(sqlObject)
                break
        else:
            # the sql object wasn't found in the cli parm list -- add it anyway
            sqlModifiedList += sqlObject + ','
            sqlTempList.append(sqlObject)

    denaliVariables["sqlParameters"] = sqlModifiedList[:-1]

    # create a temporary list to be used to validate against the cmdb defs
    aliasReturn = denali_search.replaceAliasedNames(denaliVariables, 'sqlParameters')

    return aliasReturn



##############################################################################
#
# returnLoginCLIParameter(denaliVariables)
#

def returnLoginCLIParameter(denaliVariables):

    cliParameters = denaliVariables["cliParameters"]

    for parm in cliParameters:
        if "--user" in parm[0]:
            return parm

        if "--creds" in parm[0]:
            return parm

    return False



##############################################################################
#
# generateHistoryQuery(denaliVariables)
#
#   The purpose of this function is to take a command line query for the
#   --history switch and use it to determine the number of lines to print,
#   and if a short or long output is wanted.
#

def generateHistoryQuery(denaliVariables):

    # HistoryDao query example:
    #   denali --dao=HistoryDao --fields=subject_id,datetime,user_id,action,details,field_label,old_value,new_value
    #          --subject_type_label.value="Device" --subject_id=6692 --limit=30 --sort=datetime:d

    # assume default value(s) unless specifically requested
    denaliVariables["limitCount"] = denaliVariables["historyListLength"]

    if len(denaliVariables["historyQuery"]) > 0:
        location = denaliVariables["historyQuery"].find(':')
        if location != -1:
            queryParameters = denaliVariables["historyQuery"].split(':')

            # drop all items past the 2nd in the list
            queryParameters = queryParameters[:2]

            # the given parameters can be in any order (digit:word, or word:digit); handle both cases
            if queryParameters[0].isdigit() == True:
                denaliVariables["limitCount"] = int(queryParameters[0])
                queryParameters[1] = queryParameters[1].lower()
                if queryParameters[1] == 's' or queryParameters[1] == "short" or queryParameters[1] == "small":
                    # ignore any other characters -- no setting changes
                    denaliVariables["historyFields"] = "short"

            else:
                if queryParameters[1].isdigit() == True:
                    denaliVariables["limitCount"] = int(queryParameters[1])
                    queryParameters[0] = queryParameters[0].lower()
                    if queryParameters[0] == 's' or queryParameters[0] == "short" or queryParameters[0] == "small":
                        # ignore any other characters -- no setting changes
                        denaliVariables["historyFields"] = "short"
                else:
                    # two strings? -- that's incorrect syntax.  Look at the first, ignore the second
                    if queryParameters[0] == 's' or queryParameters[0] == "short" or queryParameters[0] == "small":
                        # ignore any other characters -- no setting changes
                        denaliVariables["historyFields"] = "short"

        else:
            # no colon found -- this means a single entry, either a number of word/letter
            queryParameters = denaliVariables["historyQuery"]
            if queryParameters.isdigit() == True:
                denaliVariables["limitCount"] = int(queryParameters)
            else:
                queryParameters = queryParameters.lower()
                if queryParameters == 's' or queryParameters == "short" or queryParameters == "small":
                    # ignore any other characters -- no setting changes
                    denaliVariables["historyFields"] = "short"

    # clear out the variable -- make it a dictionary
    denaliVariables["historyQuery"] = {}

    # assume passed in value is number of history items to be shown
    denaliVariables["historyQuery"].update({"number":denaliVariables["limitCount"]})

    return True



##############################################################################
##############################################################################
##############################################################################

if __name__ == '__main__':

    pass
