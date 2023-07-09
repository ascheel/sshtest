#! /usr/bin/env python

import os

##############################################################################
#
# denaliHelpDisplay(denaliVariables, cli_parameters)
#

def denaliHelpDisplay(denaliVariables, cli_parameters):

    subsection         = []
    available_sections = [
                           'all',

                           'auth',
                           'authenticate',
                           'authentication',

                           'basic',
                           'example',
                           'examples',
                           'extra',
                           'extras',
                           'host',
                           'out',
                           'output',
                           'search',
                           'sis',
                           'stdin',
                           'toggle',
                           'track',

                           'history',
                           'group',
                           'groups',

                           'command',
                           'info',
                           'pdsh',
                           'ping',
                           'scp',
                           'spots',
                           'ssh',

                           'mon',
                           'monitor',
                           'monitoring',

                           'quick',

                           'update',
                         ]

    for parameter in cli_parameters:
        parameter = parameter.split(',')
        for parm in parameter:
            if parm in available_sections:
                subsection.append(parm)

    version = denaliVariables['version']
    date    = denaliVariables['date']
    command = os.path.basename(denaliVariables['argumentList'].split(' ')[0])

    # assign some basic sub-sections based on what was requested
    if 'scp' in subsection or 'pdsh' in subsection or 'ping' in subsection or 'spots' in subsection or 'ssh' in subsection:
        subsection.append('individual_command')

    if 'basic' in subsection:
        subsection.extend(['auth', 'host', 'out', 'stdin', 'toggle'])


    # if nothing was requested, show the 'short' help
    if len(subsection) == 0:
        print
        print "{0} (v{1}) Help Overview:".format(command, version)
        print
        print "Syntax:"
        print "     {0} --help [sub-section(s) to show detailed help]".format(command)
        print
        print "Examples:"
        print "     {0} --help           |  Show this help documentation".format(command)
        print "     {0} --help all       |  Show help for all sub-sections".format(command)
        print "     {0} --help ping scp  |  Show help for PING and SCP command sub-sections".format(command)
        print
        print "Available help sub-sections are:"
        print "         all  |  Show help for all sections"
        print "        auth  |  Show help for authentication switches"
        print "       basic  |  Show help for basic functionality"
        print "     command  |  Show help for all available command switches"
        print "    examples  |  Show help for denali examples"
        print "       extra  |  Show help for extra switches"
        print "      groups  |  Show help for group switches"
        print "     history  |  Show help for history switches"
        print "        host  |  Show help for host-base switches"
        print "        info  |  Show help for host information switch"
        print "         mon  |  Show help for monitoring command switches"
        print "         out  |  Show help for output configuration"
        print "        pdsh  |  Show help for the PDSH command switches"
        print "        ping  |  Show help for the ping command switches"
        print "       quick  |  Show help for the quick search term switches"
        print "         scp  |  Show help for the SCP command switches"
        print "         sis  |  Show help for the sis integration switch"
        print "      search  |  Show help for search options"
        print "       spots  |  Show help for the spots command switches"
        print "         ssh  |  Show help for the SSH command switches"
        print "       stdin  |  Show help for stdin functionality"
        print "      toggle  |  Show help for generic toggle switches"
        print "       track  |  Show help for the Gauntlet track targeting feature"
        print "      update  |  Show help for the CMDB update functionality"
        return

    print "{0} - A CLI interface to the SKMS/CMDB API.".format(command)
    print "  Version: %s" % version
    print "  Date   : %s" % date
    print

    if 'all' in subsection or 'basic' in subsection:
        print "Command-Line Switch Order:"
        print "  The order of command-line switches with denali is arbitrary with the exception of the monitoring"
        print "  switch data (switches for that should immediately follow the --mon switch as shown in that section's"
        print "  help documentation).  For example, the following command lines for denali are identical:"
        print
        print "    {0} --hosts=dn1?.or1 --fields=name,device_state --summary --showsql".format(command)
        print "    {0} --summary --fields=name,device_state --showsql --hosts=dn1?.or1".format(command)

    if 'toggle' in subsection or 'all' in subsection:
        print
        print "Functionality Toggle switches:"
        print
        print "  Functionality switches are optional and only modify default behavior.  With the noted exception of the"
        print "  \'--help\' and \'--aliases\' switches (for which additional layered functionality is accessed with optional"
        print "  parameters), toggle switches require no additional parameter(s) to function correctly."
        print
        print "  --help\t\tShow the generic help screen or targeted sub-section(s).  See \'{0} --help\' for usage information.".format(command)
        print
        print "  --aliases\t\tShow a list of built-in aliases and CMDB-specific parameter names for column and data display."
        print "           \t\tThis switch supports searching by DAO, individual alias or a combination of both."
        print "           \t\tAll DAO names and alias search terms entered can be case-insensitive.  Alias search terms may be"
        print "           \t\tincomplete and represent a partial match of the column name, aliased name, or CMDB reference.  If"
        print "           \t\tthe search term matches any piece of text in those three fields, it will be a positive match to be"
        print "           \t\tdisplayed.  Multiple search DAOs and alias search terms are allowed in the same command line request."
        print
        print "           \t\tAliases Examples:"
        print "           \t\t  {0} --aliases dao                  : Display a list of DAOs for which denali has built-in aliases".format(command)
        print "           \t\t  {0} --aliases userdao teamdao      : Display all UserDao and TeamDao aliases (case insensitive)".format(command)
        print "           \t\t  {0} --aliases devicedao full_name  : For the DeviceDao, show all aliases that have \'full_name\'".format(command)
        print "           \t\t  {0} --aliases device_id address    : For all DAOs, show all aliases with \'device_id\' or \'address\'".format(command)
        print
        print "  --aliasheaders\t\tDisplay the alias names for the column headers"
        print "  --attrcolumns\t\t\tDisplay attributes by column, instead of by row (one column per attribute)"
        print "  --auth\t\t\tCreate a valid session with username/password"
        print "  --autoresize\t\t\tAutomatically shrink default column width to match the largest text length (shortcut: --ar)"
        print "  --check_forwarding_schedule\tEnable the oncall DAO to look at the forwarding schedule"
        print "  --clearoverrides\t\tAll host-level attributes that are overridden will be reset to their inherited value"
        print "  --combine\t\t\tCombine command output from ping with CDMB search data (<-c | --command> ping --combine)"
        print "  --debug\t\t\tEnable debugging messages"
        print "  --jira_closed\t\t\tEnable the showing of CLOSED Jira tickets; default is not to show them -- used with JIRA_INFO field alias"
        print "  --mheaders\t\t\tFor data with multiple hosts (with multiple lines), separate each host with a new set of headers (e.g., --history)"
        print "  --mondetails\t\t\tDisplay additional monitoring information (see monitoring help)"
        print "  --monitoringdebug\t\tEnable debugging messages specific to monitoring"
        print "  --nocolors\t\t\tDo not display colors in the output"
        print "  --nolog\t\t\tDo not create PDSH/SSH log files during command execution"
        print "  --noheaders\t\t\tDo not include column headers in output"
        print "  --noprofile\t\t\tDo not allow a search profile to be added to the query"
        print "  --nosummary\t\t\tDo not show the default summary for command output (-c | --command)"
        print "  --nowrap\t\t\tDo not wrap or truncate columns in output"
        print "  --quiet\t\t\tDo not show informational messages (ex. failed queries)"
        print "  --relogin\t\t\tClear all local session information to force a re-login"
        print "  --showdecomm\t\t\tAllow decommissioned servers to be queried and shown in the output"
        print "  --showinherit\t\t\tWhen displaying ATTRIBUTES, show an additional column indicating whether an attribute was inherited or not"
        print "  --showoverrides\t\tWhen displaying ATTRIBUTES, show an additional column indicating whether an attribute has been overridden or not"
        print "  --showsql\t\t\tShow the SQL query sent to CMDB from Denali"
        print "  --spots_grep\t\t\tUsed with spots command to show a hostname by each category line"
        print "  --summary\t\t\tShow a summary count of devices/servers requested and/or displayed"
        print "  --testAuth\t\t\tTest the authentication for the current user (return 1 if not authenticated)"
        print "  --truncate\t\t\tTruncate column output so it does not wrap"
        print "  --updatedebug\t\t\tEnable debugging messages specific to updating"
        print "  --version\t\t\tShow Denali version, availability, and application dependency information"
        print
        print "              \t\tExamples:"
        print "              \t\t  {0} --hosts=dn1?.or1 --noheaders --summary --showsql".format(command)
        print "              \t\t  {0} --hosts=dn1?.or1 --fields=name,ATTRIBUTES --attrcolumns --summary".format(command)
        print "              \t\t  {0} --hosts=dn1?.or1 --hist=s --mheaders".format(command)
        print "              \t\t  {0} --version".format(command)

    if 'authentication' in subsection or 'auth' in subsection or 'authenticate' in subsection or 'all' in subsection:
        print
        print "Authentication Switches:"
        print
        print "  If none of the below are specified, denali will test the current session for correct authentication, and request"
        print "  SKMS authentication if necessary.  An SKMS session lasts 12 hours (where an additional login isn't required)."
        print
        print "       --creds\t\tSpecify a file that contains an SKMS API username and password (API passkey) for authentication."
        print "              \t\tYou can create an API passkey at https://skms.adobe.com/tools.web_api/index/"
        print "              \t\tFile format is the following:"
        print "              \t\t    username:<username>"
        print "              \t\t    password:<API passkey>"
        print "        \t\tThis switch is typically for automated processes that execute denali commands within a cron job"
        print "        \t\tor some other on-demand schedule.  With this switch, authentication credentials are automatically"
        print "        \t\tpassed to denali."
        print
        print "        \t\tExample:"
        print "        \t\t  {0} --creds='/home/<user>/sksm_api_creds.txt' --hosts=dn1?.or1".format(command)
        print
        print "  -u | --user\t\tSpecify a username for authentication to SKMS.  If this switch isn't used, the currently"
        print "        \t\tlogged in user is assumed (via an environment variable)."
        print
        print "        \t\tExample:"
        print "        \t\t  {0} --user=<user_name> --hosts=dn1?.or1".format(command)
        print
        print "       --relogin\tForce a reauthentication to SKMS by removing all records of the current user session."
        print "        \t\tThe current user is assumed to be the logged in user according to an environment variable."
        print
        print "        \t\tExamples:"
        print "        \t\t  {0} --relogin".format(command)
        print "        \t\t  {0} -h dn1?.or1 --relogin".format(command)
        print
        print "       --testAuth\tTest if the current SKMS session is valid (return 0 if the session if valid, 1 if not)"
        print
        print "        \t\tExample:"
        print "        \t\t  {0} --testAuth".format(command)
        print
        print "       --config\t\tAllow the specification of a user-defined config file location.  By default the location is"
        print "               \t\tin the user's home directory:  ~/.denali/config"
        print
        print "       --mon_creds\tSpecify a file that contains an LDAP username and password to be used for authentication"
        print "                  \twith MonApi.  File format is the following:"
        print "                  \t    username:<username>"
        print "                  \t    password:<password>"
        print "         \t\tThis switch is typically used for automated processes that require access to monitoring data to accomplish"
        print "         \t\tthe goals of the process."
        print
        print "         \t\tExample:"
        print "         \t\t  {0} --mon_creds='/home/<user>/mon_creds_file.txt' --hosts=dn1?.or1".format(command)
        print

    if 'stdin' in subsection or 'all' in subsection:
        print
        print "Server Pre-Load Switches:"
        print
        print "  The following switches are used when a group of hosts/devices is known beforehand, with the data likely stored"
        print "  in a file (each line representing a single host or device)."
        print
        print "  --   \t\t\tUse submitted list of hosts from STDIN"
        print
        print "       \t\t\tExamples:"
        print "       \t\t\t  cat my_file_of_hosts.txt | {0} --".format(command)
        print "       \t\t\t  echo \"dn1.or1 dn2.or1\" | {0} -- --fields=name device_state device_service".format(command)
        print "       \t\t\t  echo \"10.54.144.210 dn1.or1\" | {0} --".format(command)
        print
        print "  --stdin=<field>\tUse stdin for a non-hostname pre-load; if ommitted, hostname is assumed."
        print "       \t\t\tThe fields allowed for this switch are device specific and unique"
        print "       \t\t\t  (1) serial, (2) device_id, or (3) asset_id"
        print
        print "       \t\t\tTypically a file containing a list of unique device identifiers is given to"
        print "       \t\t\tdenali.  Each line in the file represents a single device."
        print
        print "       \t\t\tExample:"
        print "       \t\t\t  cat host_serial_numbers.txt | {0} -- --stdin=serial --fields=name device_service".format(command)
        print
        print "  -l | --load\t\tGather list of hosts from specified file (space, comma, or newline"
        print "             \t\tdelimited list).  Host names are typically DNS in nature, but can also"
        print "             \t\tinclude an IPv4 address (x.x.x.x)"
        print
        print "       \t\t\tExample:"
        print "       \t\t\t  {0} -l or1-cookie-monster.txt -f name,device_state,environment".format(command)

    if 'host' in subsection or 'search' in subsection or 'all' in subsection:
        print
        print "Host/Column Search and Sorting Switches:"
        print
        print "Workhorse switches in denali.  The host (device list) and fields (columns to show) are the most"
        print "widely used searching switches."
        print
        print "  --dao\t\t\tSpecify the DAO to search (DeviceDao is default)"
        print
        print "              \t\tExample:"
        print "              \t\t  {0} --dao=DeviceServiceDao --full_name=\"*\" --fields=full_name --sort=full_name --active=1".format(command)
        print
        print "  -h | --hosts\t\tList of hosts to use for searching in the DAO."
        print "              \t\tCan be a comma separated list of hosts, a range of hosts, an inclusive list"
        print "              \t\tor a bash glob.  If the range syntax is used, the devices specified must"
        print "              \t\tbe from the same data center.  The inclusive list substitutes each single"
        print "              \t\tnumber given in the list; i.e., dn[123].or1 is dn1.or1, dn2.or1, and dn3.or1."
        print "              \t\tIPv4 addresses are also accepted as a hostname."
        print
        print "              \t\tRange syntax     : <device1>..<device2> [, <device3>..<device4>]"
        print "              \t\tInclusion syntax : <device>[single digit numbers].<site>"
        print
        print "              \t\tGlobbing:"
        print "              \t\t  Bash globbing syntax with curly braces is supported."
        print "              \t\t  Bash globbing syntax with square brackets is not supported."
        print "              \t\t  Wildcard characters can be used with globbing ('*' and '?')"
        print
        print "              \t\tExamples:"
        print "              \t\t  Inclusive list : {0} -h dn[123456].or1".format(command)
        print "              \t\t  Range          : {0} -h dn1.or1..dn6.or1".format(command)
        print "              \t\t  Comma list     : {0} -h dn1.or1,dn2.or1,dn3.or1".format(command)
        print "              \t\t  Space list     : {0} -h dn1.or1 dn2.or1 dn3.or1".format(command)
        print "              \t\t  Globbing list  : {0} -h dn{{111..120}}.or1".format(command)
        print "              \t\t                   {0} -h dn{{1..2}}{{0..9}}.or1".format(command)
        print "              \t\t                   {0} -h dn{{11,13,15,7}}.or1".format(command)
        print "              \t\t                   {0} -h dn{{11,13}}*.or1".format(command)
        print "              \t\t                   {0} -h dn?{{1..3}}{{1,2,3,4}}.or1".format(command)
        print
        print "  -f | --fields\t\tComma separated list of columns to display. Fields can also"
        print "               \t\treference aliases. For the current list of available built-in"
        print "               \t\taliases, execute '{0} --aliases'. See EXAMPLES".format(command)
        print
        print "  +f | ++fields\t\tComma separated list of additional columns to display.  This switch"
        print "               \t\tis used when the default columns are wanted, plus an additional column"
        print "               \t\tor more.  For example, if the default columns are:"
        print "               \t\t    name,device_state,device_service,environment"
        print "               \t\tand if \"+f model,os_name\" is used, then the resulting columns shown"
        print "               \t\twill be \"name,device_state,device_service,environment,model,os_name\""
        print
        print "               \t\tUse only a \"-f|--fields\" or \"+f|++fields\", not both together on the"
        print "               \t\tsame command line."
        print
        print "  --sort=<column(s)>\tDefine the sort criteria (by column) for the display"
        print "        \t\tUsing a display column, sort the data in either an ASCENDING (default)"
        print "        \t\tor DESCENDING fashion, with individual column sort direction specified."
        print
        print "        \t\tExamples:"
        print "        \t\t      --sort=name:DESC"
        print "        \t\t      --sort=name,device_state:DESC,device_service:DESC"
        print
        print "        \t\t'DESC' is required for a descending sort; if not specified, ascending is assumed."
        print
        print "        \t\t  {0} -h dn1?.or1 -f name device_state device_service --sort=name,device_state".format(command)
        print
        print
        print "  --sort=dc\t\tData Center specific sorting"
        print "        \t\t  Using this criteria will sort all hosts first by data center (i.e., da2,"
        print "        \t\t  or1, etc.), and then by the host or device name."
        print "        \t\t  If used, no other sorting directives are recognized; i.e., it is stand-alone."
        print "        \t\t  This sort feature only functions correctly with a device total of less than %d." % denaliVariables['maxSKMSRowReturn']
        print
        print "        \t\tExample:"
        print "        \t\t  {0} --device_service=\"*mongo*generic*\" -f name device_state device_service --sort=dc".format(command)
        print
        print
        print "  AND, OR, and NOT Boolean Operator Use:"
        print
        print "         \t\t  The use of wildcard characters ('*' and '?') is allowed and even encouraged."
        print
        print "    [AND]\t\t  By default each separate field request is AND'd together by Denali to create the SQL query"
        print "        \t\t  sent to the SKMS API."
        print
        print "        \t\t  Example:"
        print "        \t\t     {0} --device_service=\"Analytics - DB - Mongo Generic\" --device_state=\"On Duty - In Service\"".format(command)
        print "        \t\t                                                              ^"
        print "        \t\t                                                              ^"
        print "        \t\t                                 Implied 'AND' between \"device_service\" and \"device_state\" fields"
        print
        print "        \t\t  The above example says if the device service is \"Analytics - DB - Mongo Generic\" AND if the device"
        print "        \t\t  state is \"On Duty - In Service\", then show the device(s) found for that query.  The AND is, by"
        print "        \t\t  default, automatically implied when using multiple \"--\" queries in the same command.  The same"
        print "        \t\t  holds true if a 3rd or 4th field was requested; they would all be AND'd together to create the SQL"
        print "        \t\t  query submitted."
        print
        print "    [OR]\t\t  To use more than one criteria within a distinct field request, use the OR operator."
        print
        print "        \t\t  Example:"
        print "        \t\t     {0} --device_service=\"Analytics - DB - Mongo Generic OR SiteCatalyst - Cache - Production\"".format(command)
        print "        \t\t                                                             ^"
        print "        \t\t                                                             ^"
        print "        \t\t                                                   Explicit 'OR' (capitalized)"
        print
        print "        \t\t  The above example states that if the device service is either *Mongo OR *Cache, then show the"
        print "        \t\t  device(s).  Note that the \"OR\" is fully capitalized - this is a requirement or it will be"
        print "        \t\t  missed by the code."
        print
        print "        \t\t  Use of an OR between field requests is allowed, and this will modify the query sent to CMDB."
        print
        print "        \t\t  Example:"
        print "        \t\t     {0} --device_service=\"Analytics - DB - Mongo Generic\" --device_state=OR:\"On Duty - In Service\"".format(command)
        print "        \t\t                                                                             ^"
        print "        \t\t                                                                             ^"
        print "        \t\t                                                                   Explicit 'OR' (capitalized)"
        print
        print "        \t\t  The above example states if that any devices are found that have a device service of \"Analytics - DB -"
        print "        \t\t  Mongo Generic\" or if there are any devices (from any device service, anywhere) that have a state of"
        print "        \t\t  \"On Duty - In Service\", then show them all.  The use of the 'OR' in this case must be followed by"
        print "        \t\t  a colon, then an open quotation mark; which then contains the requested query data."
        print
        print "    [NOT]\t\t  The NOT boolean operator is used in the same way as the previous example with the OR - it precedes"
        print "        \t\t  the data query."
        print
        print "        \t\t  Example:"
        print "        \t\t     {0} --device_service=NOT:\"Analytics - DB - Mongo Generic\"".format(command)
        print "        \t\t                              ^"
        print "        \t\t                              ^"
        print "        \t\t                   Explicit 'NOT' (capitalized)"
        print
        print "        \t\t  The above example will print all devices with a devices service that it NOT \"Analytics - DB - "
        print "        \t\t  Mongo Generic\".  Multiple items in the 'NOT' sequence should be separated with an 'AND', not with"
        print "        \t\t  an 'OR' operator; i.e., \"Analytics - DB - Mongo Generic AND SiteCatalyst - Cache - Production\""
        print
        print "        \t\t  NOT examples:"
        print "        \t\t     {0} --location=NOT:ut1".format(command)
        print "        \t\t     {0} --location=NOT:ut1 --environment=NOT:\"*sbx1*\"".format(command)
        print "        \t\t     {0} --location=NOT:\"lon5 AND lon7 AND va*\"".format(command)


    if 'out' in subsection or 'output' in subsection or 'all' in subsection:
        print
        print "Output Switches:"
        print
        print "Switches used to define the output destination(s) for the queried data."
        print
        print "  -o | --out\t\tDefine terminal and file data outputs."
        print
        print "            \t\tThe following format outputters are available:"
        print "            \t\t  (1) txt     : column-based text output (default)"
        print "            \t\t  (2) csv     : comma separated values (one line per device record)"
        print "            \t\t  (3) comma   : comma separated values (single line output)"
        print "            \t\t  (4) space   : space separated values (single line output)"
        print "            \t\t  (5) newline : newline separated values (one line per data item)"
        print "            \t\t  (6) yaml    : yaml-like organized key-value pairs (grouped by host name)"
        print "            \t\t  (7) json    : json formatted output (single line string)"
        print
        print "            \t\tMultiple output formats (the screen/stdout or file formats) can be combined"
        print "            \t\tfor the same query -- use the exact output format name defined above:"
        print "            \t\t  -o txt,csv            : Write txt (columns) and CSV formats to the"
        print "            \t\t                          screen."
        print "            \t\t  -o txt,file.csv       : Write txt output to the screen, and then"
        print "            \t\t                          write to file.csv (in CSV format)."
        print "            \t\t  -o oak1.txt,oak1.json : Output to files in txt and JSON formats."
        print
        print "            \t\tExamples:"
        print "            \t\t  {0} -l host_list.txt -o txt.csv".format(command)
        print "            \t\t  {0} -l host_list.txt -o sin2.txt".format(command)
        print "            \t\t  {0} --location=sin2 --device_service=\"*mongo*generic*\" -f name -o newline".format(command)
        print
        print "            \tNotes:"
        print "            \t    (1) Denali assumes a file if a file-like structure is used and the format output"
        print "            \t        is specified; i.e., -o myhosts.yaml assumes yaml output for a file.  If a file"
        print "            \t        like structure is not used, then screen output is assumed."
        print
        print "            \t    (2) For comma, space, and newline formatted output, using the \"--noheaders\" switch"
        print "            \t        may be appropriate to suppress column header information (e.g., generation of"
        print "            \t        a host list only where only a single field is displayed)."

    if 'extra' in subsection or 'extras' in subsection or 'all' in subsection:
        print
        print "Extra Switches:"
        print
        print " Each 'id' switch below (powerid, rackid, switchid) supports a range modifier (the '..') and a"
        print " comma separated list; e.g., rackid=1094..1096,1099."
        print " Each 'non-id' switch supports only a comma separated list; e.g., rack=OAK1:102,DA2:102."
        print
        print "  --power\t\tSearch for a specific power appliance by name (e.g., rpc203.oak1)."
        print "  --powerid\t\tSearch for a specific power appliance by device ID (e.g., 22674)."
        print "  --rack\t\tSearch for a specific rack configuration by name (e.g., OAK1:102)."
        print "        \t\tThe data center location must preceed the rack name with a colon separator."
        print "  --rackid\t\tSearch for a specific rack configuration by ID (e.g., 1096)."
        print "  --switch\t\tSearch for a specific switch configuration by name (e.g., sw-a-42.da2)."
        print "  --switchid\t\tSearch for a specific switch configuration by device ID (e.g., 35642)."
        print
        print "       \t\t\tPower/Rack/Switch Examples:"
        print "       \t\t\t  {0} --power=rpc203.oak".format(command)
        print "       \t\t\t  {0} --rack=OAK1:102,OAK1:103,DA2:102".format(command)
        print "       \t\t\t  {0} --switchid=35642..35644".format(command)
        print
        print "       \t\t\tUse of any of the above 6 switches should exclude --hosts, --load, --fields,"
        print "       \t\t\tand --sort.  No other switches are required."
        print
        print "       \t\t\tExample:"
        print "       \t\t\t  {0} --switch=sw-a-41.da2,sw-a-42.da2".format(command)
        print
        print
        print "  --sql\t\t\tEnter an SQL statement directly into denali to pass to SKMS"
        print
        print "       \t\t\tExample:"
        print "       \t\t\t  {0} --sql=\"DeviceDao:SELECT name,device_state \\".format(command)
        print "       \t\t\t      WHERE name IN ('dn1.or1','dn2.or1') ORDER BY name\""
        print
        print "       \t\t\tThe above SQL statement is equivalent to:"
        print "       \t\t\t  {0} -h dn1.or1 dn2.or1 -f name device_state --sort=name".format(command)
        print
        print "       \t\t\tNote:"
        print "       \t\t\tThe above SQL parameter switch in Denali does NOT support updating, just searching."
        print
        print
        print "  --ext\t\t\tDynamically load and use an external module"
        print
        print "       \t\t\tCurrently available modules:"
        print "       \t\t\t  (1)  chassis   : Show information about a chassis (devices, slots, etc.)"
        print "       \t\t\t                 : Example:  {0} --hosts=bc1.or1 --ext=chassis".format(command)
        print "       \t\t\t  (2)  netrollup : Show network hierarchy from device up [this module still needs work]"
        print "       \t\t\t                 : Syntax :  {0} --hosts=<hosts> --ext=netrollup.listing".format(command)
        print "       \t\t\t                 :           {0} --hosts=<hosts> --ext=netrollup.table".format(command)
        print "       \t\t\t  (3)  oncall    : Show the on-call information for teams [this module still needs work]"
        print "       \t\t\t                 : Syntax :  {0} --ext=oncall".format(command)
        print "       \t\t\t                 :           {0} --ext=oncall:list".format(command)
        print "       \t\t\t                 :           {0} --ext=oncall:table".format(command)
        print "       \t\t\t                 :           {0} --ext=oncall:[queue name or IDs]".format(command)
        print "       \t\t\t                 :           {0} --ext=oncall:table,[queue name or IDs]".format(command)
        print "       \t\t\t                 : Example:  {0} --ext=oncall:table,1,13,SC-ARK".format(command)
        print "       \t\t\t  (4)  owner     : Show owners of specified host(s)"
        print "       \t\t\t                 : Example:  {0} --hosts=dn1.or1 --fields=name --ext=owner".format(command)
        print "       \t\t\t                 : Show all device services with associated owners"
        print "       \t\t\t                 : Example:  {0} --ext=owner.masterList".format(command)
        print "       \t\t\t  (5)  sisgroups : Show sisgroup(s) of specified host(s)"
        print "       \t\t\t                 : Example:  {0} --hosts=dn1.or1 --fields=name --ext=sisgroups".format(command)
        print "       \t\t\t  (6)  software  : Show software registered in CMDB for specified host(s)"
        print "       \t\t\t                 : Example:  {0} --hosts=dn1.or1 --fields=name --ext=software".format(command)
        print
        print "       \t\t\t  Only one external module can be called per command line.  You cannot call the"
        print "       \t\t\t  owner and software module on the same command line (i.e., --ext=owner --ext=software)"
        print
        print
        print "  --count\t\tHave the SQL server count and categorize for Denali."
        print "       \t\t\tSyntax:"
        print "       \t\t\t  --count=[column name to count]:[group by column name, ...]"
        print "       \t\t\tExample:"
        print "       \t\t\t  {0} --hosts=www*.da2 --count=name:device_service".format(command)
        print
        print
        print "  --limit\t\tStop printing after [x] devices are shown."
        print "       \t\t\tExample:"
        print "       \t\t\t  {0} --hosts=\"*.da2\" --limit=100".format(command)
        print
        print "  --profile\t\tAllow the addition of a search profile to commands submitted."
        print
        print "       \t\t\tBy default no profiles are active for Denali.  They are found in the ~/.denali/config"
        print "       \t\t\tfile.  The title of the line will be \"profile:<profile_name>\" followed by an indented"
        print "       \t\t\tset of configurations to be used for that specific profile.  Using the --profile switch"
        print "       \t\t\twith the profile name will activate it.  If there is a 'default' profile, it will always"
        print "       \t\t\tbe used (unless the --noprofile switch is put on the command line or the name of the"
        print "       \t\t\tprofile is changed from 'default' in the file)."
        print
        print "       \t\t\tExample:"
        print "       \t\t\t  {0} --device_service=\"*puck*\" --profile=or1".format(command)
        print
        print "       \t\t\tThe above example loads in the 'or1' profile and then looks for all devices with the"
        print "       \t\t\tdevice service of *puck*.  The profile could have a location specified, or a device state"
        print "       \t\t\tspecified, or any number of things."
        print
        print "       \t\t\tUse of the --showsql switch will identify the profile used if any configuration parameters"
        print "       \t\t\twere added to the current search from that profile.  If no parameters were added, the"
        print "       \t\t\t'Profile Used' line will not appear."
        print

    if 'sis' in subsection or 'all' in subsection:
        print "SIS Database Integration Feature:"
        print
        print "  Denali has the ability to interact with the SIS database (precursor to SKMS/CMDB) by passing commands"
        print "  directly to the Omnitool utility.  Omnitool was written to interact with SIS, and rather than rewrite"
        print "  Denali to handle SIS, the decision was made to just call Omnitool with the submitted command(s).  By"
        print "  default Omnitool is installed on the server in the /opt/netops/ directory.  Most of the commands available"
        print "  in Omnitool are now available in Denali with the pass-through functionality feature of this switch."
        print
        print "  If the Omnitool utility is not available, Denali will error out stating as much.  To verify Omnitool's"
        print "  availability, type \"denali --version\" and look at the last set of lines displayed from that output."
        print
        print "  The use of this switch requires knowledge of Omnitool and its command syntax and structure.  The command(s)"
        print "  submitted to the --sis switch, are passed directly to Omnitool for processing and execution, with the output"
        print "  shown as received back from Omnitool."
        print
        print "  Syntax:"
        print "   --sis=\"<omnitool command(s) to execute>\""
        print
        print "  Examples:"
        print "    denali -h db279.lon5 --sis=\"-c get hostgroups\""
        print "    denali -h db277.lon5 db279.lon5 --sis=\"-c get classification\""
        print "    denali -h db277.lon5 db279.lon5 --sis=\"-c delgroup install addgroup lon5-sick\""
        print
        print "  Help for omnitool:"
        print "    denali -h db277.lon5 --sis=\"-h\""
        print

    if 'track' in subsection or 'all' in subsection:
        print "Gauntlet Track Targeting Feature:"
        print
        print "  Denali has the ability to target devices based upon data found in Gauntlet.  The user will submit both"
        print "  the name of the track (or tracks), and the promotion-level of the code (environment).  With that, Denali"
        print "  will query for the devices and allow normal operations (command, monitoring, etc.) against them."
        print
        print "  --track\t\tThis is the name of the Gauntlet track."
        print "         \t\tThe track switch can contain multiple track names ('OR' separated) and also supports wildcard"
        print "         \t\tsearching with either '?' or '*'."
        print "         \t\tTo list all available tracks, use a track name of \"all\" or \"list\"."
        print
        print "  --promotion-level\tThis is the name of the code promotion-level."
        print "                   \tIf the promotion-level is not found, Denali will show the available levels for the"
        print "                   \tspecified track."
        print
        print "  Example:"
        print "    {0} --track=amps --promotion-level=beta".format(command)
        print
        print "         \tNote:"
        print "         \t\tBoth the \'track' and \'promotion-level\' switch allow for multiple values to be assigned to them."
        print "         \t\tThis will enable a search for multiple tracks with multiple promotion-level environments if desired."
        print "         \t\tThe syntax usage is to place multiple items in quotation marks and separate them with a capitalized"
        print "         \t\t\'OR\' between them."
        print
        print "  Examples:"
        print "    {0} --track=\"ia_201804 OR rts_201803\" --promotion-level=prod".format(command)
        print "    {0} --track=ia_201804 --promotion-level=\"beta OR prod\"".format(command)
        print "    {0} --track=\"ia_201804 OR rts_201803\" --promotion-level=\"beta OR prod\"".format(command)
        print

    if 'individual_command' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "Command Execution Switches:"
        print
        print "  -c | --command\tCommand to be run against list of servers (limit: one command per query)"
        print "       \t\t\tAvailable commands:"

    if 'ping' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t  ping [--combine]  :  Ping each host found or submmited and return the results"
        print "       \t\t\t                    :  \"--combine\" integrates the ping output with normal denali output"
        print "       \t\t\t  ping ilo          :  If 'ilo' is placed after the 'ping' command, then each host DNS name is"
        print "       \t\t\t                       modified to include '.ilo' so as to ping the ilo address instead of the"
        print "       \t\t\t                       primary ip address.  Syntax:  denali -h <hosts> -c ping ilo"

    if 'info' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t  info              :  Gather and display information about a host or device.  The information"
        print "       \t\t\t                       collected is (1) 'simple' monitoring status, (2) spots complete output,"
        print "       \t\t\t                       and (3) last 15 entries of history as stored in CMDB."
        print

    if 'scp' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t  scp               :  SCP (secure copy - remote file copy program) a file or files/directories"
        print "       \t\t\t                       from the current host where denali is being executed, to a targeted set of"
        print "       \t\t\t                       hosts either searched for or specified.  The source path/file(s) must be"
        print "       \t\t\t                       specified along with the destination path.  Optionally, SCP options can also"
        print "       \t\t\t                       be included."
        print
        print "       \t\t\t                       Default behavior is a parallel copy with a pool of up 150 processes to use;"
        print "       \t\t\t                       one process per host."
        print
        print "       \t\t\t                     Required SCP Options:"
        print "       \t\t\t                       (1) --src              : Source file(s) to copy to designated target hosts."
        print "       \t\t\t                           --source"
        print "       \t\t\t                       (2) --dest             : Destination directory path on target hosts."
        print "       \t\t\t                           --destination"
        print
        print "       \t\t\t                     Optional:"
        print "       \t\t\t                       (1) --scp_opts         : Any scp specific options that are wanted."
        print "       \t\t\t                           --scp_options        See \"man 5 ssh_config\" for an itemized list of"
        print "       \t\t\t                           --so                 scp options with descriptions."
        print "       \t\t\t                       (2) --ni               : Enable non-interactive mode.  A prompt will request"
        print "       \t\t\t                           --non-interactive    a username/password for SCP host authentication.  See"
        print "       \t\t\t                                                below for detailed usage information."
        print "       \t\t\t                       (3) --no-fork          : Run the scp copy in serial-mode instead of in"
        print "       \t\t\t                                                parallel (a single process proceeding host by host)."
        print "       \t\t\t                       (4) --num_procs        : Override the default number of parallel processes in the"
        print "       \t\t\t                                                pool to use for the copy process (default is 150)."
        print "       \t\t\t                       (5) --conn_timeout     : Amount of time (in seconds) to wait for the initial"
        print "       \t\t\t                                                ssh connection to succeed (connect).  This option will"
        print "       \t\t\t                                                include the SCP option \"-o ConnectTimeout=<#>\" to the"
        print "       \t\t\t                                                SCP arguments submitted.  The default value for the timeout"
        print "       \t\t\t                                                is based on the host\'s resolver.conf  configuration"
        print "       \t\t\t                                                (maximum of 30 seconds -- see \"man 5 resolv.conf\")."
        print "       \t\t\t                       (6) --logoutput=[value]: This switch determines the type of output to show with"
        print "       \t\t\t                                                SCP.  Accepted values are [failure,success,normal]."
        print
        print "       \t\t\t                                                  failure : Show only failure log lines."
        print "       \t\t\t                                                  success : Show only success log lines."
        print "       \t\t\t                                                  normal  : Show normal log output lines."
        print
        print "       \t\t\t  scp-pull          :  SCP pull feature.  The same feature that exists where files are pushed out to"
        print "       \t\t\t                       devices is available for files to be pulled from those devices.  By default"
        print "       \t\t\t                       all files copied will be renamed:  <device_name>-<file_name>.  This rename will"
        print "       \t\t\t                       prevent file overwrites (multiple devices all having the same file copying to the"
        print "       \t\t\t                       same location).  The source file location (on a remote device), can be specified"
        print "       \t\t\t                       with wildcard characters; i.e., --source=\"/var/log/tomcat8/catalina*.log\""
        print
        print "       \t\t\t                       The pull feature has a source of a remote device with a destination of the local"
        print "       \t\t\t                       host where Denali is executing.  It is recommended that a directory be created for"
        print "       \t\t\t                       the storage of these files to avoid confusion."
        print
        print "       \t\t\t                     Required SCP Options:"
        print "       \t\t\t                       (1) --src              : Source file(s) to copy from designated target hosts."
        print "       \t\t\t                           --source"
        print "       \t\t\t                       (2) --dest             : Destination directory path on the local host."
        print "       \t\t\t                           --destination"
        print
        print "       \t\t\t                     Optional: (only differences from 'scp' are shown; otherwise all switches are identical)."
        print "       \t\t\t                       (1) --scp_norename        : Disable the default file rename with the scp pull"
        print "       \t\t\t                                                   feature."
        print
        print "       \t\t\t                    Note:"
        print "       \t\t\t                       If multiple files are requested with a wildcard character, logic will be engaged to"
        print "       \t\t\t                       first contact all of the targeted hosts to get a list of files that match the given"
        print "       \t\t\t                       source requested, and second to give that discovered file list to SCP for download."
        print "       \t\t\t                       Depending upon the number of targeted hosts, this contact may take a few minutes."
        print "       \t\t\t                       During the wait time, a character spinner is active and each spin indicates a new line"
        print "       \t\t\t                       of data received from this request."
        print
        print "       \t\t\t                       A work-around suggestion to using this would be to send a command to the targeted hosts"
        print "       \t\t\t                       to zip up (compress) all files with a specific name -- create a tarball.  That single"
        print "       \t\t\t                       file can then be brought down using SCP to the local host."
        print
        print "       \t\t\t  scp-push          :  SCP push feature.  This is the exact same as if the user entered 'scp'.  It is"
        print "       \t\t\t                       included to be complete and has no functional difference from the use of 'scp'."

    if 'pdsh' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t  pdsh              :  PDSH is used to execute a remote command (or commands) on hosts returned by"
        print "       \t\t\t                       CDMB query, or submitted via a command line argument.  Required with this"
        print "       \t\t\t                       command is \"--pdsh_command='<pdsh_command>'\".  Any specific PDSH options are"
        print "       \t\t\t                       accepted via \"--pdsh_options='<pdsh_options>'; i.e., the \"-f\" switch, etc."
        print
        print "       \t\t\t                       Default PDSH utility behavior is a process pool of up to 32 processes for use; one"
        print "       \t\t\t                       process per host.  If a larger pool is needed, use the following syntax to increase"
        print "       \t\t\t                       the process pool size (testing has shown < 150-200 give the best performance)."
        print
        print "       \t\t\t                           --pdsh_options=\"-f <number of processes>\""
        print
        print "       \t\t\t                       If the PDSH utility is not installed locally, the command will not function and"
        print "       \t\t\t                       Denali will stop when it determines this."
        print
        print
        print "       \t\t\t                     Required PDSH Options:"
        print "       \t\t\t                       (1) --pdsh_command      : Command(s) to execute on targeted hosts."
        print "       \t\t\t                           --pc"
        print
        print "       \t\t\t                     Optional:"
        print "       \t\t\t                       (1)  --pdsh_options     : Any PDSH specific options that are wanted."
        print "       \t\t\t                            --po                 See \"man pdsh\" for a detailed list and description."
        print "       \t\t\t                       (2)  --pdsh_apps        : Count of the number of apps/commands that will return"
        print "       \t\t\t                                                 a success or failure code.  See below for detailed usage"
        print "       \t\t\t                                                 usage information."
        print "       \t\t\t                       (3)  --pdsh_separate    : Designate a separator value to divide the running of PDSH"
        print "       \t\t\t                            --ps                 in parallel across more than one segment of devices.  This"
        print "       \t\t\t                                                 instructs Denali to create \"swim-lanes\" for each segment"
        print "       \t\t\t                                                 that then operate independent of each other.  Each segment"
        print "       \t\t\t                                                 will report separately -- including log files."
        print "       \t\t\t                                                 Values accepted: Any single CMDB value like device_service"
        print "       \t\t\t                                                                  or location, etc.  'dpc' is accepted to"
        print "       \t\t\t                                                                  separate by DPC (hostname value based)."
        print "       \t\t\t                                                 See below for a usage example, and a bonus feature with a"
        print "       \t\t\t                                                 variable fanout based on a percentage.  To see the segment"
        print "       \t\t\t                                                 fanout value, select \"s\" from the PDSH check menu."
        print "       \t\t\t                       (4)  --pdsh_offset      : Command(s) will be executed in serial batches of 'offset'"
        print "       \t\t\t                            --offset             size."
        print "       \t\t\t                       (5)  --proc_timeout     : Amount of time (in seconds) for a process to execute"
        print "       \t\t\t                                                 before being terminated.  See below for detailed usage"
        print "       \t\t\t                                                 information."
        print "       \t\t\t                       (6)  --conn_timeout     : Amount of time (in seconds) to allow for an SSH connection"
        print "       \t\t\t                                                 to be established before terminating the attempt.  This is"
        print "       \t\t\t                                                 only used when the server is slow in allowing a connection,"
        print "       \t\t\t                                                 not when it refuses."
        print "       \t\t\t                       (7)  --num_procs        : Override the default number of parallel PDSH processes to"
        print "       \t\t\t                                                 use (default is 32).  The --pdsh_options switch can also"
        print "       \t\t\t                                                 be used to set this value; e.g., --po=\"-f 15\""
        print "       \t\t\t                       (8)  --screen           : Command will be executed in a detached screen session."
        print "       \t\t\t                                                 See below for detailed usage information."
        print "       \t\t\t                       (9)  --non-interactive  : Enable non-interactive mode.  A prompt will request"
        print "       \t\t\t                            --ni                 a username/password for PDSH/SCP host authentication."
        print "       \t\t\t                                                 See below for detailed usage information."
        print "       \t\t\t                       (10) --sudo             : Auto fill in standard syntax to execute a command as a"
        print "       \t\t\t                                                 specific user.  Text pre-pended to the command:"
        print "       \t\t\t                                                    sudo -H -u <user> -i bash -c \"<command>\""
        print "       \t\t\t                       (11) --host_commands    : Allow different command variations to execute against a"
        print "       \t\t\t                            --hc                 set of devices as defined in a submitted device list."
        print "       \t\t\t                                                 See below for detailed usage information."
        print "       \t\t\t                       (12) --logoutput=[value]: This switch determines the type of output to show with"
        print "       \t\t\t                                                 PDSH.  Accepted values are [failure,success,normal]."
        print
        print "       \t\t\t                                                   failure : Show only failure log lines."
        print "       \t\t\t                                                   success : Show only success log lines."
        print "       \t\t\t                                                   normal  : Show normal log output lines."
        print "       \t\t\t                       (13) --rcode            : Process all returns codes through dshbak instead of the"
        print "       \t\t\t                                                 default log lines."
        print "       \t\t\t                       (14) --retry=<#>        : Enable retry logic to run # number of loops (retries) on"
        print "       \t\t\t                                                 devices that fail the command initially.  If no number is"
        print "       \t\t\t                                                 specified after \"--retry\", then a single retry is assumed."
        print "       \t\t\t                       (15) --retry_command    : If \"--retry\" is specified, this switch allows a different"
        print "       \t\t\t                            --rc                 command to be executed on the failed devices."
        print "       \t\t\t                       (16) --verify=[command] : Run the submitted command against a verification host, and"
        print "       \t\t\t                            -v [command]         if successful, allow the remainder of the hosts to execute"
        print "       \t\t\t                                                 the same command.  By default, this is the first host from"
        print "       \t\t\t                                                 the submission."
        print "       \t\t\t                                                 If a [command] is included, that will be the verification"
        print "       \t\t\t                                                 command to run.  If one is not included, the default"
        print "       \t\t\t                                                 command in the code (if it exists) will be executed."
        print "       \t\t\t                       (17) --verify_hosts=[#] : Change the default number of verification hosts to the"
        print "       \t\t\t                            --vh [#]             integer value given here (e.g., 2)."

    if 'ssh' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t ssh                :  SSH is used to execute a command (or commands on hosts returned by query, or"
        print "       \t\t\t                       submitted via command line argument.  Required with this command is:"
        print "       \t\t\t                         \"--ssh_command='<ssh_command>'\"."
        print
        print "       \t\t\t                       Any specific SSH options are accepted via \"--ssh_options='<ssh_options>'; i.e.,"
        print "       \t\t\t                       the \"-p\" switch for connecting via a specific port, etc."
        print
        print "       \t\t\t                    Required SSH Options:"
        print "       \t\t\t                       (1) --ssh_command : Command to execute on targeted hosts."
        print "       \t\t\t                           --sc"
        print "       \t\t\t                       (2) --retry=<#>        : Enable retry logic to run # number of loops (retries) on"
        print "       \t\t\t                                                devices that fail the command initially.  If no number is"
        print "       \t\t\t                                                specified after \"--retry\", then a single retry is assumed."
        print "       \t\t\t                       (3) --retry_command    : If \"--retry\" is specified, this switch allows a different"
        print "       \t\t\t                           --rc                 command to be executed on the failed devices."
        print
        print "       \t\t\t                    Optional:"
        print "       \t\t\t                       (1) --ssh_options : Any ssh specific options that are wanted."

    if 'spots' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t  spots             :  Talk to the spots app (tcp port 24210) and return all results from the host(s)."
        print "       \t\t\t  spots:[search]    :  With an optional \"search\" criteria, only what is asked for is displayed."
        print
        print "       \t\t\t                       Available search criteria and description:"
        print "       \t\t\t                         disk              :  Disk partition space statistics (partition, free, used, available)"
        print "       \t\t\t                         free_disk_space   :  Percentage of free disk space (unsure what this is, really)"
        print "       \t\t\t                         kernel            :  Kernel version installed"
        print "       \t\t\t                         load              :  Load average (1m, 5m, 15m)"
        print "       \t\t\t                         memory            :  Memory statistics (free, used, available)"
        print "       \t\t\t                         os                :  Operating System"
        print "       \t\t\t                         swap              :  Swap space statistics (free, used)"
        print "       \t\t\t                         time              :  Time as reported by the host"
        print "       \t\t\t                         uptime            :  Current uptime of the host"
        print "       \t\t\t                         www               :  Number of www (web server) connections"
        print
        print "       \t\t\t                       Multiple items can be displayed if they are enclosed in quotes and are space-separated;"
        print "       \t\t\t                       e.g., -c spots:\"memory disk\""

    if 'scp' in subsection or 'pdsh' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t  --non-interactive :  Used with the \"-c scp\" or \"-c pdsh\" commands; it requests a username and password"
        print "       \t\t\t  --ni                 combination to be sent to each server for the SCP copy process or the PDSH parallel"
        print "       \t\t\t                       distributed shell process.  This will allow a different user to be specified (e.g.,"
        print "       \t\t\t                       root, httpd, etc.) or for the current user's password to be used, hopefully pre-"
        print "       \t\t\t                       venting some hosts from failing due to public/private key problems.  The request for"
        print "       \t\t\t                       the username and password is made only once (at the beginning of the command process"
        print "       \t\t\t                       execution); it then automatically passes this information to each host.  For this"
        print "       \t\t\t                       functionality to work, the \"sshpass\" utility needs to be installed locally.  If"
        print "       \t\t\t                       this utility isn't present, the code path will not be executed, and Denali will"
        print "       \t\t\t                       function as if this command switch were not requested."
        print
        print "       \t\t\t                     Note:"
        print "       \t\t\t                       For PDSH, a separate username/password cannot be passed to each host (current"
        print "       \t\t\t                       limitation of the PDSH utility).  Using this switch will instead activate a \"fall-"
        print "       \t\t\t                       through\" code path from PDSH to SSH remote command execution.  How it works:  If any"
        print "       \t\t\t                       PDSH requested host or hosts fails to execute the requested command due to an"
        print "       \t\t\t                       authentication issue, that host or hosts will automatically be processed with the"
        print "       \t\t\t                       username/password combination submitted using SSH remote command execution.  This"
        print "       \t\t\t                       \"fall-through\" processing happens after the PDSH run has completed."
        print
        print "       \t\t\t  --progress=[value]:  With the pdsh and scp commands, by default a progress indicatory will be shown."
        print "       \t\t\t                       The ssh command does not have the progress indicators integrated yet, and as such"
        print "       \t\t\t                       it is not available for this command yet."
        print
        print "       \t\t\t                       The indicator is different for each command, and can be changed or disabled with"
        print "       \t\t\t                       the following values:"
        print
        print "       \t\t\t                         default : Show the default progress indicators (this switch isn't needed as the"
        print "       \t\t\t                                   default display shows this anyway."
        print "       \t\t\t                         adv     : Show an advanced progress indicator (more output)."
        print "       \t\t\t                         bar     : Show a progress bar."
        print "       \t\t\t                         none    : Disable the progress indicators."
        print
        print "       \t\t\t                         Example use (complete syntax of full command not provided):"
        print "       \t\t\t                             {0} ... -c pdsh --pc=\"uptime\" --progress=bar".format(command)
        print "       \t\t\t                             {0} ... -c scp --src=<...> --dest=<...> --progress=adv".format(command)
        print
        print "       \t\t\t                       PDSH Progress Indicators:"
        print "       \t\t\t                         default : Show the percentage of devices completed and the number remaining."
        print "       \t\t\t                                   [   1.3% | r:1162 ]"
        print "       \t\t\t                         adv     : Show the percentage of devices completed, the device number being"
        print "       \t\t\t                                   processd, and the number of devices remaining."
        print "       \t\t\t                                   [   5.9% |   82/1177 | r:1107 ]"
        print "       \t\t\t                         bar     : Show only a progress bar with NO OUTPUT or logs shown on screen."
        print "       \t\t\t                                   There is a bar spinner shown at the beginning and the end has counts"
        print "       \t\t\t                                   of the success or failures recorded."
        print "       \t\t\t                                   [ / ][ 147/294 | r:147 ]|---->[ 50.0%]    |[ Norm: 140  Fail: 7  S: 0 ]"
        print
        print "       \t\t\t                       SCP Progress Indicators:"
        print "       \t\t\t                         default : Show the remaining counts for SCP operations yet to [S]tart and for those"
        print "       \t\t\t                                   yet to [C]omplete."
        print "       \t\t\t                                   [ Sr:1101 | Cr:1171 ]"
        print "       \t\t\t                         adv     : Show both the percentage and remaining counts for SCP operations that"
        print "       \t\t\t                                   have [S]tarted and [C]ompleted.  Also show the [O]utstanding operations"
        print "       \t\t\t                                   or those that are currently in-flight.  The in-flight number can grow to"
        print "       \t\t\t                                   the maximum number of processes allows for the operation."
        print "       \t\t\t                                   [ S: 14.9% r:1002 | C:  0.4% r:1172 | O: 14.4% r:150 ]"
        print "       \t\t\t                         bar     : Same as the PDSH bar progress indicator, but with two side-by-side"
        print "       \t\t\t                                   progress bars that update at the same time.  The first bar is for the SCP"
        print "       \t\t\t                                   started and the second is for the SCP completed operations.  Success and"
        print "       \t\t\t                                   failure counts are shown at the end of both bars."

    if 'pdsh' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t  --pdsh_apps=<#>   :  Used only with the \"-c pdsh\" command; it allows the code to know how many return"
        print "       \t\t\t                       values (success or failure) there will be.  Based on this information, it can build"
        print "       \t\t\t                       a summary table for each host where a percentage of what ran (and succeeded or"
        print "       \t\t\t                       failed) for each host is detailed.  The exact syntax looked for is:"
        print "       \t\t\t                       \"return = <0/1>\"; i.e., \"return = 0\"."
        print
        print "       \t\t\t  --host_commands   :  Specific to PDSH use-cases only.  The default PDSH work-flow requires that all"
        print "       \t\t\t                       devices receive and execute the exact same command.  However, this switch allows"
        print "       \t\t\t                       different commands to be assigned to each device and then have those commands"
        print "       \t\t\t                       executed in parallel."
        print
        print "       \t\t\t                         Requirements:"
        print "       \t\t\t                           (1) Devices/hosts and associated commands must be given in a file to Denali."
        print "       \t\t\t                           (2) The commands in the file are separated from the device name by a colon ':'."
        print "       \t\t\t                           (3) The number of submitted commands must be identical across each device."
        print "       \t\t\t                               In other words, all devices get 1, 2, or 10 commands; not 1 for some, and"
        print "       \t\t\t                               5 for others."
        print "       \t\t\t                           (4) If multiple commands are to be executed on each device, they must be"
        print "       \t\t\t                               separted by a semi-colon from other commands in the file."
        print
        print "       \t\t\t                         Example file line:"
        print "       \t\t\t                         scvm1008.dev.ut1:date;cat /proc/cpuinfo"
        print "       \t\t\t                             ^           ^ ^  ^              ^"
        print "       \t\t\t                             |           | |  |              |"
        print "       \t\t\t                            host     colon c1 semi-colon     c2"
        print
        print "       \t\t\t                            host       = scvm1008.dev.ut1 -- host where the command(s) will be executed."
        print "       \t\t\t                            colon      = separates the hostname from the command(s) to follow."
        print "       \t\t\t                            c1         = First command (\"date\")"
        print "       \t\t\t                            semi-colon = Command separator - identifies a new command to follow."
        print "       \t\t\t                            c2         = Second command (\"cat /proc/cpuinfo\")"
        print
        print "       \t\t\t                         Example device file, showing 2 commands per device:"
        print
        print "       \t\t\t                         ------- (hosts.txt) cut here -------"
        print "       \t\t\t                         db43.ut1.adobe.net:uptime;cat /proc/loadavg | awk '{print $1\" \"$2\" \"$3}'"
        print "       \t\t\t                         ip-10-27-10-161.ut1.adobe.net:date; echo \"You have `cat /proc/cpuinfo | grep ^process | wc -l` CPUs\""
        print "       \t\t\t                         scvm1008.dev.ut1:date;cat /proc/cpuinfo"
        print "       \t\t\t                         ------- (hosts.txt) cut here -------"
        print
        print "       \t\t\t                         Required Syntax:"
        print "       \t\t\t                           {0} --load=<device_list> --host_commands -c pdsh --pc=\"<pdsh_commands>\"".format(command)
        print
        print "       \t\t\t                         Example Denali command to use the above file:"
        print "       \t\t\t                           {0} -l hosts.txt --hc -c pdsh --pc=\"var=\`%s\`; echo \$var | awk '{{print \$1}}'; %s\"".format(command)
        print
        print "       \t\t\t                         The command code path is activated with the \"--hc\" switch.  This instructs the"
        print "       \t\t\t                         code to parse the submitted list of devices for commands (device name [colon]"
        print "       \t\t\t                         command(s)).  The number of commands depends upon the use of semi-colons in the"
        print "       \t\t\t                         command list and the number of \"%s\" given in the PDSH command line.  They must be"
        print "       \t\t\t                         equal or an error will be thrown."
        print
        print "       \t\t\t                         The command given Denali with the \"--pc\" switch can have surrounding text or"
        print "       \t\t\t                         commands, as the above example shows.  This command says to take the first device"
        print "       \t\t\t                         command and execute it, storing the results in the \"var\" variable.  Then take the"
        print "       \t\t\t                         \"var\" variable and echo out the contents and pipe that to awk where the 1st item is"
        print "       \t\t\t                         displayed.  That is the first full command to be executed.  The second command is"
        print "       \t\t\t                         only \"%s\" -- which means that it will run whatever it is given (a command with no"
        print "       \t\t\t                         extras)."
        print
        print "       \t\t\t                         One pain-point with this will be having to manually escape any and all characters"
        print "       \t\t\t                         that the SHELL would normally assume requires a replacement.  Because of this, the"
        print "       \t\t\t                         above command escapes the backticks, and the dollar signs ($).  This must be done"
        print "       \t\t\t                         by the user, and not programmatically by denali as the shell passes denali the"
        print "       \t\t\t                         command(s)."
        print
        print "       \t\t\t                         Putting the two together (the command file and the PDSH command itself), gives the"
        print "       \t\t\t                         following final commands for each device after the command substitution is"
        print "       \t\t\t                         complete.  These are the actual set of commands that will be run against each"
        print "       \t\t\t                         device:"
        print
        print "       \t\t\t                         db43.ut1.adobe.net"
        print "       \t\t\t                            var=`uptime`;echo $var | awk '{print $1}'; cat /proc/loadavg | awk '{print $1\" \"$2\" \"$3}'"
        print "       \t\t\t                         ip-10-27-10-161.ut1.adobe.net"
        print "       \t\t\t                            var=`date`;echo $var | awk '{print $1}';  echo \"You have `cat /proc/cpuinfo | grep ^process | wc -l` CPUs\""
        print "       \t\t\t                         scvm1008.dev.ut1.omniture.com"
        print "       \t\t\t                            var=`date`;echo $var | awk '{print $1}'; cat /proc/cpuinfo"
        print
        print "       \t\t\t                         Other examples:"
        print "       \t\t\t                           (1) --pc=\"ls -alF %s\"  <--  This expects a directory name in the command"
        print "       \t\t\t                                                         file to list."
        print "       \t\t\t                           (2) --pc=\"%s\"          <--  Execute a single command."
        print "       \t\t\t                           (3) --pc=\"%s;%s;%s\"    <--  Execute 3 commands."



    if 'spots' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t  --spots_grep      :  Used only with the \"-c spots\" command; it instructs the output to have the host"
        print "       \t\t\t                       name in front each line -- this helps with grep displays."

    if 'pdsh' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t  --nofork          :  Execute the command in a serial fashion, instead of in parallel.  For PDSH, use the"
        print "       \t\t\t                       following switch: \"--pdsh_options='-f 1'\".  This ensures that only a single host"
        print "       \t\t\t                       at a time is running the command."
        print "       \t\t\t  --num_procs       :  Specify the maximum number of processes Denali will spawn to accomplish the task."
        print "       \t\t\t                       Useful with \"ping\", \"scp\", and \"ssh\" commands."
        print "       \t\t\t                         Syntax:  \"--num_procs=3\""
        print "       \t\t\t  --conn_timeout    :  For pdsh, ping, scp, and ssh connection types."
        print "       \t\t\t                       This is a connection timeout limit when first establishing the SSH session."
        print "       \t\t\t                       For SSH, this is translated to \"-o ConnectTimeout=<#>\".  For PDSH, this is"
        print "       \t\t\t                       translated to \"-t <#>\"."
        print "       \t\t\t  --proc_timeout    :  Used only with the \"-c pdsh\" command.  This is translated to \"-u <#>\".  This is"
        print "       \t\t\t                       the amount of time to allow a process to execute on a remote server (in seconds)"
        print "       \t\t\t                       before terminating the link.  See \"man pdsh\" for more information."
        print "       \t\t\t  --screen          :  Used only with the \"-c pdsh\" command.  This switch prefaces any PDSH command"
        print "       \t\t\t                       with the following commands:"
        print
        print "       \t\t\t                           screen -dm bash -c \'<command_to_execute>\'"
        print
        print "       \t\t\t                       This creates a screen session with the command executing inside of it, and"
        print "       \t\t\t                       automatically detaches from it.  See \"man screen\" for more information."
        print
        print "       \t\t\t                     Note:"
        print "       \t\t\t                       When used, no direct logging of the host(s) is returned; therefore, any command"
        print "       \t\t\t                       validation must be handled manually; i.e., check each host to determine if the"
        print "       \t\t\t                       command succeeded or failed."

    if 'individual_command' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\tCommand Examples:"

    if 'ping' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t  {0} --device_service=\"*analytics*mongo*\" --location=or1 -c ping".format(command)
        print "       \t\t\t  {0} --device_service=\"*analytics*mongo*\" --location=or1 -c ping --combine".format(command)
        print "       \t\t\t  {0} --device_service=\"*analytics*mongo*\" --location=or1 -c ping ilo".format(command)

    if 'spots' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t  {0} --device_service=\"*analytics*mongo*\" --location=or1 -c spots".format(command)
        print "       \t\t\t  {0} --hosts=db2255.oak1 -c spots:\"uptime load\"".format(command)
        print "       \t\t\t  {0} --service=\"Analytics - DB - Mongo Generic\" --state=\"On Duty - In Service\" --environment=\"*prod*\" -c spots:disk \\"
        print "       \t\t\t         --spots_grep | egrep \'/var|Partition\'".format(command)

    if 'scp' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t  {0} --device_service=\"*contribution analysis*\" --location=lon5 -c scp".format(command)
        print "       \t\t\t         --source=\"/home/<user>/*.txt,/var/log/messages*,/home/<user>/find_this.py\""
        print "       \t\t\t         --destination=/home/<user>/ --scp_options=\"-o StrictHostKeyChecking=no\""
        print
        print "       \t\t\t  {0} --device_service=\"*contribution analysis*\" --location=lon5 -c scp-pull".format(command)
        print "       \t\t\t         --source=\"/etc/yum.repos.d/*.repo\" --destination=\".\""


    if 'pdsh' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t  {0} --hosts=<list_of_hosts> -c pdsh --pdsh_command=\"ls -l\"".format(command)
        print
        print "       \t\t\t  {0} --hosts=ip-10-27-11-11.ut1.adobe.net --sudo=httpd -c pdsh --pc=\"ls -l;id;whoami\"".format(command)
        print
        print "       \t\t\t  {0} --hosts=db225*.oak1 -c scp,pdsh --scp_options=\"-o StrictHostKeyChecking=no -o ConnectTimeout=5\"".format(command)
        print "       \t\t\t         --source=fix_problems.sh --destination=/directory/to/place --pdsh_options=\"-u 20 -f 2\""
        print "       \t\t\t         --pdsh_command=\"./fix_problems.sh\""
        print
        print "       \t\t\t  {0} --service=\"SiteCatalyst - Data Collection - Stats\" --state=\"On Duty - In Service\" --location=NOT:ut1".format(command)
        print "       \t\t\t         --pdsh_separate=dpc --pdsh_options=\"-f 2\" -c pdsh --pc=\"uptime\""
        print
        print "       \t\t\t  {0} --service=\"SiteCatalyst - Data Collection - Stats\" --state=\"On Duty - In Service\" --location=NOT:ut1".format(command)
        print "       \t\t\t         --pdsh_separate=dpc --pdsh_options=\"-f 10%\" -c pdsh --pc=\"uptime\""
        print
        print "       \t\t\t  {0} --service=\"*report timing* OR *intelligent*\" --location=NOT:ut1 --state=\"On Duty - In Service\"".format(command)
        print "       \t\t\t         --ps=service -c pdsh --pc=\"date\""
        print
        print "       \t\t\t  {0} --service=\"SiteCatalyst - AxleGrid - Puck\" --pdsh_offset=25 --state=\"On Duty - In Service\"".format(command)
        print "       \t\t\t         -c pdsh --pc=\"date\""

    if 'ssh' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t  {0} --hosts=<list_of_hosts> -c ssh --ssh_command=\"ls -l\"".format(command)
        print "       \t\t\t  {0} --hosts=dn1?.or1 -c ssh --sc \"./fix_problems.sh\" --ssh_options=\"-p 2222\" --nofork".format(command)

    if 'individual_command' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t  Notes on the examples above:"

    if 'ping' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t     + The ping examples show one with and without combining CMDB data and one that shows"
        print "       \t\t\t       the pinging of ilo addresses."

    if 'scp' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t     + The scp example copies multiple files to a group of hosts.  Each scp source file is separated by"
        print "       \t\t\t       commas.  Wilcards and globbing are allowed in the specified names."
        print
        print "       \t\t\t     + The second scp example shows the 'scp-pull' feature."

    if 'pdsh' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t     + The second pdsh example shows the --sudo switch which will automatically pre-pend a set of commands"
        print "       \t\t\t       to allow the execution of the commands to happen as that specific user."
        print
        print "       \t\t\t     + The third pdsh example is a combination of both SCP and PDSH (comma separated after the \"-c\" command"
        print "       \t\t\t       option).  It will execute the SCP command first (copying the shell script) and then execute PDSH"
        print "       \t\t\t       where it runs that just copied script.  The commands are executed in the order in which they are"
        print "       \t\t\t       specified.  Only one command of each type is allowed; i.e., \"-c scp,pdsh,pdsh\" is not allowed;"
        print "       \t\t\t       however, \"-c scp,pdsh,ping\" is allowed."
        print
        print "       \t\t\t     + The next two pdsh examples show how to use the pdsh_separator feature.  The first of the two requests"
        print "       \t\t\t       that all 'stats' hosts be divided by Data Processing Center (dpc).  These hosts need to be On Duty,"
        print "       \t\t\t       and not located in UT1.  The hosts are then gone through 2 at a time showing the current uptime."
        print "       \t\t\t       The final example divides the hosts queried by device_service, and using only On Duty hosts not in"
        print "       \t\t\t       UT1, it will run through all hosts (up to the maximum allowed by PDSH because no '-f' option was"
        print "       \t\t\t       given)."
        print
        print "       \t\t\t     + The final pdsh example shows the use of the 'offset' parameter in specifying 25 puck hosts to run at"
        print "       \t\t\t       a time in a serial fashion."

    if 'ssh' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t     + The first ssh example performs a simple directory listing for servers."
        print
        print "       \t\t\t     + The second ssh example executes the 'fix_problems.sh' shell script in the user's home"
        print "       \t\t\t       directory.  It attaches to the ssh daemon on each box using port 2222 and it does the"
        print "       \t\t\t       action one host at a time (in serial) instead of in parallel."

    if 'spots' in subsection or 'command' in subsection or 'all' in subsection:
        print
        print "       \t\t\t     + The first spots command shows all available data from the searched-for hosts."
        print
        print "       \t\t\t     + The second spots command shows only the uptime and load from db2255.oak1.  Take note of the quotation"
        print "       \t\t\t       marks around the selected variables.  This is only needed if more than one is requested; otherwise,"
        print "       \t\t\t       no quotes are needed for a single item."
        print
        print "       \t\t\t     + The third spots command searches for all MongoDB hosts in Analytics that are on duty in the production"
        print "       \t\t\t       environment.  With that list, it then collects all of the spots data for the \'disk\' information"
        print "       \t\t\t       requesting that each line displayed also include the host name (the \"--spots_grep\" switch).  Then a"
        print "       \t\t\t       grep is executed against the output to show only the /var partition disk information and the header"
        print "       \t\t\t       (egrep \'/var|Partition\')."

    if 'history' in subsection or 'all' in subsection:
        print
        print "History Switches:"
        print
        print "  --history\t\tDisplay device history from the HistoryDao in CMDB."
        print
        print "           \t\tSyntax:"
        print "           \t\t  --history=[columns shown]:[lines printed]"
        print "           \t\t    \"--history\" can be abbreviated to \"--hist\""
        print "           \t\t      By default, all available history columns are displayed; however if \'s\' is used after"
        print "           \t\t      --history, i.e., --history=s, the number of columns is reduced from 8 to 5."
        print
        print "           \t\t      The history search supports internal queries.  These are the columns printed with an"
        print "           \t\t      addition \"--hist_\" attached to the front of the search criteria.  For example:"
        print "           \t\t          --hist_datetime"
        print "           \t\t          --hist_details"
        print
        print "           \t\t      A full list of available columns (potential search criteria to be used with the history command)"
        print "           \t\t      can be identified this command:"
        print "           \t\t          {0} --aliases HistoryDao".format(command)
        print
        print "           \t\t      [Use the aliased column name after \"--hist_\" to modify the search critera]"
        print
        print "           \t\t      By default, 15 rows of data per host/device will be displayed.  For additional rows,  add \"=[#]\""
        print "           \t\t      to the history switch; i.e., --hist=40.  This example will request up to 40 entries from the"
        print "           \t\t      history database about the device(s) requested."
        print
        print "           \t\tHistory Examples:"
        print "           \t\t  {0} --hosts=dn1.or1 --history"
        print "           \t\t      15 lines are printed by default/all columns displayed.".format(command)
        print
        print "           \t\t  {0} --hosts=dn1.or1 --history=s:20".format(command)
        print "           \t\t      The \'s\' after --history shortens the columns printed (from 8 to 5)."
        print "           \t\t      The \'20\' increases the history shown to 20 lines (up from the default of 15)."
        print
        print "           \t\t  {0} --hosts=dn1.or1 --history=s:200 --hist_datetime=\">2015\"".format(command)
        print "           \t\t      Shorten the displayed columns, and print up to 200 lines of history from 2015 forward for the dn1.or1 host."
        print
        print "           \t\t  {0} --hosts=dn1.or1,dn2.or1 --history=s:200 --hist_datetime=\">2013-10\" --hist_datetime=\"<2014-12\"".format(command)
        print "           \t\t      Shorten the displayed columns, and print up to 200 lines of history between Oct 2013 and Dec 2014."
        print "           \t\t      The \"--hosts\" parameter can take multiple hosts as before (or wildcards, ranges, etc.)."
        print
        print "           \t\t  {0} --hosts=dn1.or1 --history=s --hist_details=\"php*\"".format(command)
        print "           \t\t      Shorten the displayed columns, print the default 15 lines for any history details column search that"
        print "           \t\t      includes the string \"php\""
        print
        print "  --addhistory\t\tAdd a note to the history of a device (or devices)."
        print "           \t\tSyntax:"
        print "           \t\t  {0} --addhistory=\"note_to_add_to_history\"".format(command)
        print
        print "           \t\taddhistory Example:"
        print "           \t\t  {0} --hosts=dn15.or1 --addhistory=\"reboot node for dirty cow kernel upgrade\"".format(command)

    if 'group' in subsection or 'groups' in subsection or 'all' in subsection:
        print
        print "Group Operations with Hosts:"
        print
        print "   -g | --groups\tList of groups whose device name will be returned."
        print "             \t\tThe group search parameter is used in the same way as the 'host' search parameter."
        print "             \t\tWildcards ('*' and '?') are supported in the search string.  The difference between"
        print "             \t\tthe host and group searches is that the group search returns the member hosts from"
        print "             \t\tthe device group, while a host search returns the hosts."
        print
        print "             \t\t  Syntax:"
        print "             \t\t    --groups=<list of group(s)> --fields=<list of columns to display>"
        print
        print "             \t\t  Examples:"
        print "             \t\t    {0} -g da2-cm1".format(command)
        print "             \t\t    {0} -g da2-cm*".format(command)
        print "             \t\t    {0} -g va7::stats::rdc1".format(command)
        print "             \t\t    {0} -g da2-cm1 da2-cm2 -f name state service".format(command)
        print "             \t\t    {0} -g da2-cm1 -c spots:memory".format(command)
        print "             \t\t    {0} -g da2-cm1 -c pdsh --pc=\"./fix_things.sh\"".format(command)
        print
        print "             \t\t  The final example above shows a PDSH command to run a shell script on all hosts in the da2-cm1 group."
        print
        print "  -ag | --addgroup\tAdd specified hosts to one or more device groups"
        print "  -dg | --delgroup\tRemove specified hosts from one or more device groups"
        print "             \t\tThe 'addgroup' and 'delgroup' switches can be used together or separately on the same denali command line"
        print "             \t\tso that multiple groups can be added and removed with a single command if needed."
        print
        print "             \t\t  Syntax:"
        print "             \t\t    --addgroup=<list of group(s)> --delgroup=<list of group(s)>"
        print "             \t\t"
        print "             \t\tGroup addition/removal Example:"
        print "             \t\t  {0} --hosts=db1879.or1,db1897.or1 --addgroup=Test1 --delgroup=Test2".format(command)
        print "             \t\t      This command adds two servers to the Test1 group, and then removes the same two servers from the"
        print "             \t\t      Test2 group.  No matter the order of the command line, if 'add' and 'del' are included, the 'add'"
        print "             \t\t      command will be executed first.".format(command)
        print
        print "  --newgroup \t\tCreate a new device group in CMDB."
        print
        print "             \t\t  Syntax:"
        print "             \t\t    --newgroup"
        print "             \t\t    --newgroup=\"<new_group_data>\""
        print
        print "             \t\tWith the first method (--newgroup, no added parameters), Denali will enter an interactive mode to help"
        print "             \t\tthe user create a new group.  It will walk through all of the needed details and will syntax check what"
        print "             \t\tit is given.  At the end of the creation process, a line of text is displayed showing the command line"
        print "             \t\tsyntax that would create the same group without the interactive process."
        print
        print "             \t\tWith the second method, all of the information required to create a new group is assumed to be on the"
        print "             \t\tcommand line.  Syntax checking is done, but no help beyond that is offered."
        print
        print "             \t\tSuggestion:"
        print "             \t\t  For users new to group creation, it is suggested to walk through the creation first in interactive"
        print "             \t\t  mode for the group type wanted, and then use the given information to request additional groups via"
        print "             \t\t  the command line."
        print
        print "  --grphistory\t\tAdd a note to the history of a group (or groups)."
        print "             \t\tSyntax:"
        print "             \t\t  {0} --groups=<group or group(s)> --grphistory=\"note_to_add_to_history\"".format(command)
        print
        print "             \t\tgrphistory Examples:"
        print "             \t\t  {0} --groups=Test1,Test2 --grphistory=\"changed group configuration\"".format(command)
        print
        print "  --updateattr\t\tUpdate group attributes in CMDB."
        print
        print "             \t\tUpdating group attributes is keyed by the use of the -g/--groups switch on the command line.  This"
        print "             \t\tinstructs the code that the update is for a group."
        print
        print "             \t\t  Syntax:"
        print "             \t\t    {0} -g <name of group(s)> --updateattr=\"<attribute_name>=<attribute_value>\"".format(command)
        print
        print "             \t\t  Multiple attributes can be updated if they are separated by a comma, for example:"
        print "             \t\t    --updateattr=\"MONGO_VER=3.6,RAID_SETTINGS=10\""

    if 'mon' in subsection or 'monitor' in subsection or 'monitoring' in subsection or 'all' in subsection:
        print
        print "Monitoring Switches:"
        print
        print " --mon\t\tMain switch used to access the monitoring API infrastructure."
        print
        print "      \t\tAuthentication is required (Digital Marketing username/password) for monitoring data access and will"
        print "      \t\tautomatically be requested by denali.  By default the session data for monitoring is stored 12 hours."
        print
        print "      \t\tMonitoring Syntax:  {0} <device_list> --mon [command(s)] [search_parameters]".format(command)
        print
        print "      \t\t  Commands(s) can be from the following list:"
        print "      \t\t    Display commands for monitoring data (use one per query):"
        print "      \t\t       all      : A substitute for the 'details' command that shows everything the 'details' command"
        print "      \t\t                  does, and includes 3 additional monitoring check and notification interval columns."
        print "      \t\t       details  : Shows the individual checks of each device, the current status, individual check"
        print "      \t\t                  details, whether checks and notifications are enabled for that service, and the"
        print "      \t\t                  last time the check was executed."
        print "      \t\t       simple   : Default command with the \"--mon\" switch.  This command shows a simplified output"
        print "      \t\t                  of each device requested and that device's checks and individual status."
        print "      \t\t       summary  : This command shows a summary of all entities and includes a count of Critical,"
        print "      \t\t                  Warning, Unknown, and OK checks.  It also shows a count of the total number of"
        print "      \t\t                  checks and notifications that are enabled for each device."
        print
        print "      \t\t    Action commands for monitoring data:"
        print "      \t\t       ack      : To acknowledge an alert on a host/entity."
        print "      \t\t       debug    : Used with a specific alert to show monitoring details for debugging."
        print "      \t\t       downtime : Schedule a downtime (maintenance) event."
        print "      \t\t       enable   : Enable a set of services/checks, or all at the same time for specified hosts."
        print "      \t\t       disable  : Disable a set of services/checks, or all at the same time for specified hosts."
        print "      \t\t                  Additionally, the key-words of 'checks' or 'notify' can be used with enable/disable"
        print "      \t\t                  to specify if the checks or notifications (or both) are to be actioned against."
        print "      \t\t                  If neither 'checks' nor 'notify' are used, both are assumed."
        print "      \t\t                  Syntax:"
        print "      \t\t                      {0} -h <entities> --mon [enable|disable]".format(command)
        print "      \t\t                                                 [checks|notify]"
        print "      \t\t                                                 [<alert service(s)>]"
        print "      \t\t       delete   : Used with the 'ack' and downtime' commands to remove either acknowledgements or"
        print "      \t\t                  a maintenance windows."
        print "      \t\t       mismatch : This command displays devices that have a check or notification disabled.  It can be"
        print "      \t\t                  paired with the 'details' command to show the specific check in question."
        print "      \t\t       passive  : Request a passive run of checks on a device.  The phrase 'run' can be substituted"
        print "      \t\t                  for 'passive' with the same result."
        print "      \t\t       submit   : For a 'passive' run, submit the results to monitoring.  If this command is not"
        print "      \t\t                  included, the results are not submitted to the monitoring infrastructure; rather,"
        print "      \t\t                  they are returned to denali for further review."
        print
        print "      \t\t  Additional monitoring specific switches:"
        print "      \t\t     --mondetails  : This switch can be used with most of the above monitoring commands to see"
        print "      \t\t                     additional information."
        print "      \t\t                     Examples:  --mon HOST --mondetails"
        print "      \t\t                                --mon passive --mondetails"
        print "      \t\t                                --mon enable --mondetails"
        print "      \t\t     --m_separator = <separator>"
        print "      \t\t                   By default a comma is the separator between hosts/entities.  If something"
        print "      \t\t                   different is wanted, this switch allows for that.  For a space use"
        print "      \t\t                   --m_separator=space; all other characters should work as expected; e.g.,"
        print "      \t\t                   --m_separator=/, for example."
        print

        print "      \t\t  Reserved Search Parameters:"
        print "      \t\t       c, crit  : Search for all CRITICAL alert states."
        print "      \t\t       w, warn  : Search for all WARNING alert states."
        print "      \t\t       u, unk   : Search for all UNKNOWN alert states."
        print "      \t\t       o, ok    : Search for all OK alert states."
        print "      \t\t       +        : Engage the 'AND' search algorithm ('OR' is the default)."
        print "      \t\t       cw       : Search shortcut to include both CRITICAL and WARNING alert states."
        print "      \t\t       cwu      : Search shortcut to include CRITICAL, WARNING, and UNKNOWN alert states."
        print "      \t\t       cu       : Search shortcut to include CRITICAL and UNKNOWN alert states."
        print "      \t\t       wu       : Search shortcut to include WARNING and UNKNOWN alert states."
        print
        print
        print "      \t\tMonitoring Examples:"
        print
        print "      \t\tVIEWING/SEARCHING"
        print "      \t\t-----------------"
        print "      \t\t  {0} -h dn15.or1 --mon".format(command)
        print "      \t\t     Show a summary view (which is the default command) for the db15.or1 host."
        print
        print "      \t\t  {0} -h dn1?.or1 --mon --summary".format(command)
        print "      \t\t     Show a summary view of all dn?.or1 hosts with a categorization at the end (the '--summary'"
        print "      \t\t     switch)."
        print
        print "      \t\t  {0} -h dn1?.or1 --mon details".format(command)
        print "      \t\t     Show a detailed view of all dn1?.or1 hosts (all checks and individual status)."
        print
        print "      \t\t  {0} -h dn1.or1 --mon all".format(command)
        print "      \t\t     Show a detailed view of the dn1.or1 host (same as 'details' above); however, include 3"
        print "      \t\t     additional check and notification interval columns."
        print
        print "      \t\t  {0} -h dn1?.or1,arc626.da2 --mon details HOST TIME".format(command)
        print "      \t\t     Show a detailed view of the hosts specified but only display the HOST and TIME checks."
        print
        print "      \t\t  {0} -h dn10.or1 --mon details c w".format(command)
        print "      \t\t  {0} -h dn10.or1 --mon details cw".format(command)
        print "      \t\t     Show a detailed view, but only display CRITICAL and WARNING alerts (ignore all others).  The"
        print "      \t\t     'c' and 'w' are reserved search parameters that denali translates automatically to the proper"
        print "      \t\t     search terms."
        print
        print "      \t\t  {0} -h dn1?.or1 --mon mismatch".format(command)
        print "      \t\t     Show the entities/hosts from the submitted list that have one or more checks disabled or one or"
        print "      \t\t     more notifications disabled.  'details' can be used as well:  --mon details mismatch"
        print
        print "      \t\t  {0} --device_service='SiteCatalyst* OR Analytics*' --device_state='On Duty* OR Online'".format(command)
        print "      \t\t         --location=or1 --mon details 'Verify Quick' + w --summary -o txt,or1.csv"
        print "      \t\t     Search the monitor checks for all SiteCat/Analytics hosts in OR1 for the 'Verify Quick' check"
        print "      \t\t     and if that check is in a WARNING state, print out the host detail information for it.  The "
        print "      \t\t     output will print to the screen (txt) and then to a CSV file (or1.csv).  At the end of the run,"
        print "      \t\t     a summary will appear with all hosts in the query separated into categories.  Notice the '+'"
        print "      \t\t     sign so the search does a logical 'and' (not the default 'or' which would happen without the"
        print "      \t\t     plus sign); meaning, the check must be in a WARNING state _and_ it must be the 'Verify Quick'"
        print "      \t\t     check to qualify."
        print
        print "      \t\t  {0} -h db3799.or1 --mon details Check_ZooKeeper debug".format(command)
        print "      \t\t     Perform a web screen scrape of monitoring information for this specific check (authentication"
        print "      \t\t     will be requested for this functionality -- Digital Marketing password)."
        print
        print "      \t\t  Notes:"
        print "      \t\t     (1) No session information is stored for this, and as such every time it is used a username"
        print "      \t\t         and password will be requested."
        print "      \t\t     (2) Only a single entity is allowed for this query.  Any multi-entity request will be denied."
        print
        print
        print "      \t\tENABLE/DISABLE ALERTS"
        print "      \t\t---------------------"
        print "      \t\t  {0} -h dn10.or1 --mon disable".format(command)
        print "      \t\t     Disable all checks and notifications for all services on the dn10.or1 host.  Any terms that"
        print "      \t\t     follow 'disable' are interpreted as individual check(s) to disable, instead of the entire set."
        print "      \t\t     If nothing follows 'disable' or 'enable' (below), all services/checks are assumed and included."
        print "      \t\t     The Check/Notification name must be spelled correctly for this to work, including any"
        print "      \t\t     capitalization.  If a check is specified that doesn't exist, or is misspelled, it will be"
        print "      \t\t     ignored."
        print
        print "      \t\t  {0} -h dn1?.or1 --mon enable HOST".format(command)
        print "      \t\t     Enable just the HOST check/notification for all dn1?.or1 hosts."
        print
        print "      \t\t  {0} -h dn10.or1 --mon disable notify".format(command)
        print "      \t\t     Disable the notifications for each check (leave the checks running) for the host."
        print
        print "      \t\t  {0} -h db1879.or1 --mon disable HOST \"m:disabling HOST alert for testing per <user>\"".format(command)
        print "      \t\t     Add a customized message for inclusion in SKMS history for the entities listed (db1879.or1 in"
        print "      \t\t     this case).  The message needs to be enclosed in quotes and start with \"m:\" to be properly"
        print "      \t\t     detected, otherwise it will be treated as the name of an alert (to enable/disable) and"
        print "      \t\t     ignored.  Message length is required to be <= 100 characters."
        print
        print
        print "      \t\tDOWNTIME A HOST"
        print "      \t\t---------------"
        print "      \t\t  {0} -h db1897.or1 --mon downtime 'reboot to fix problems' d:30m".format(command)
        print "      \t\t     Example above shows a typical downtime syntax -- 30 minutes of downtime for a host."
        print
        print "      \t\t  {0} -h db1879.or1 --mon downtime 'reboot for dirty cow' d:60m 2017-02-03_14:30".format(command)
        print "      \t\t     Schedule a downtime event for db1879.or1 to last 60 minutes starting on Feb 3rd at 2:30pm."
        print "      \t\t       + Downtime comment is required"
        print "      \t\t       + Downtime duration time is required (syntax shown below)"
        print "      \t\t       + Downtime start time is optional (24 hour clock)"
        print
        print "      \t\t     The duration time is prefixed with 'd:' to allow the code to identify the variable.  If the"
        print "      \t\t     start time is omitted, the current time of day is assumed as the initial start time; in other"
        print "      \t\t     words, start the downtime event now."
        print
        print "      \t\t     The duration time can be specified with a combination of days (d), hours (h) and minutes (m)."
        print "      \t\t       Example duration times:"
        print "      \t\t         d:1d12h, d:45m, d:1d30m, d:4h48m, d:11d22h33m"
        print
        print "      \t\t  {0} -h db1879.or1 --mon downtime delete".format(command)
        print "      \t\t     Remove any/all downtime events assocaited with the db1879.or1 host."
        print
        print "      \t\t  Note:"
        print "      \t\t     Multiple downtime events can be placed on the same device/entity, and will be visible in the"
        print "      \t\t     default summary search view."
        print
        print
        print "      \t\tACKNOWLEDGE AN ALERT"
        print "      \t\t--------------------"
        print "      \t\t  {0} -h db1879.or1 --mon ack 'Verify Quick'".format(command)
        print "      \t\t     Acknowledge the alert for 'Verify Quick' on host db1879.or1.  If a check name isn't provided,"
        print "      \t\t     the code will attempt to acknowledge every check/alert on the specified host or entity."
        print
        print "      \t\t  {0} -h db1879.or1 --mon ack delete 'Verify Quick' HOST".format(command)
        print "      \t\t     Delete or remove the acknowledgements for the 'Verify Quick' and HOST checks/alerts on the"
        print "      \t\t     db1879.or1 host.  If a check/alert isn't specified, all will be attempted to be deleted from"
        print "      \t\t     any prior acknowledgements."
        print
        print
        print "      \t\tRUN A PASSIVE CHECK"
        print "      \t\t-------------------"
        print "      \t\t  {0} -h arc626.da2 --mon passive".format(command)
        print "      \t\t     Execute a passive run of all checks on the arc626.da2 host."
        print
        print "      \t\t  {0} -h db1879.or1 --mon passive submit".format(command)
        print "      \t\t     Execute a passive run of all checks on the db1879.or1 host and SUBMIT the results to the"
        print "      \t\t     monitoring infrastructure."
        print
        print "      \t\t  {0} -h arc626.da2 --mon passive HOST RAID --mondetails".format(command)
        print "      \t\t     Execute a passive run of the HOST and RAID checks on arc626.da2, showing the details."

    if 'all' in subsection or 'update' in subsection:
        print
        print "CMDB Updating Functionality and Feature Switches:"
        print "  Denali is able to update data in CMDB given a few command line switches and the proper data to digest."
        print
        print "  Currently the 'update' feature only supports DeviceDao updates.  With the current instantiation of code,"
        print "  denali works in concert with SIS<->CMDB two-way syncing.  Because of this, the device service, device state,"
        print "  and environment are available for modification or updating if two-way syncing is enabled for that specific"
        print "  device service."
        print
        print "  Available Switches:"
        print "  --up | --update\tCMDB updates done via the command line."
        print
        print "      \t\t\t  Syntax:"
        print "      \t\t\t    {0} -h <list of hosts> --update=\"<items to be updated>\"".format(command)
        print
        print "      \t\t\t  Examples:"
        print "      \t\t\t    {0} -h <host_name> --update=\"Device State=On Duty - In Service\"".format(command)
        print "      \t\t\t    {0} -h <host_name> --update=\"device_state=On Duty - In Service\"".format(command)
        print
        print "      \t\t\t  The above examples for updating the device state are different in syntax; however,"
        print "      \t\t\t  they accomplish the same goal.  The first uses the Column Header for the identifier,"
        print "      \t\t\t  and the second uses the CMDB alias name."
        print
        print "      \t\t\t  The functionality here can be very powerful if an entire set of hosts needs the exact"
        print "      \t\t\t  same type of upgrade.  For example:"
        print
        print "      \t\t\t    {0} --device_service=\"*mongo generic*\" --update=\"Device State=On Duty - In Service\"".format(command)
        print
        print "      \t\t\t  The example will update every host with a Device Service that includes \"mongo generic\""
        print "      \t\t\t  to have a Device State of \"On Duty - In Service\"."
        print
        print "      \t\t\t  Denali has the ability to change the hostname of multiple hosts (appending data to it)."
        print "      \t\t\t  To access this feature, use a command line similar to the following:"
        print "      \t\t\t    Syntax:"
        print "      \t\t\t      denali -h <list of hosts> --update=\"<hostname><augmented name>\""
        print
        print "      \t\t\t    Example:"
        print "      \t\t\t      denali -h scvm48[5678].dev.ut1 --update=\"name=<hostname>-cptreq-12345\""
        print
        print "      \t\t\t  The \"<hostname>\" string is identified by Denali and is used as a key to engage the code"
        print "      \t\t\t  to replace that text with the actual hostname itself as devices are iterated across."
        print
        print "      \t\t\t  In this case, scvm485.dev.ut1 through scvm488.dev.ut1 will have their hostname changed"
        print "      \t\t\t  to be scvm485.dev.ut1-cptreq-12345, through scvm488.dev.ut1-cptreq-12345"
        print "      \t\t\t  Check the output given for the update to make sure each host has the proper new"
        print "      \t\t\t  name, and then allow the update to proceed."
        print

        print
        print "  --updatefile\t\tCMDB updates submitted via a yaml-like file."
        print
        print "      \t\t\t  Syntax:"
        print "      \t\t\t    {0} --updatefile=\"/home/<user>/my_update_file.txt\"".format(command)
        print
        print "      \t\t\t  Example:"
        print "      \t\t\t    {0} --updatefile=\"~/hosts_to_update.txt\"".format(command)
        print
        print "      \t\t\t  Example update file (text should be left-justified):"
        print "      \t\t\t  -------------start cut here-------------"
        print "      \t\t\t  # hosts to do an update on"
        print
        print "      \t\t\t  host : bsg314.oak1"
        print "      \t\t\t    operating_system : CentOS Linux 6.2 64 bit"
        print "      \t\t\t    primary_ip : 1.2.3.4"
        print
        print "      \t\t\t  host : www870.oak1"
        print "      \t\t\t    operating_system : CentOS Linux 4.4 32 bit"
        print "      \t\t\t    device_state : On Duty - In Service"
        print "      \t\t\t    primary_ip : 5.6.7.8"
        print "      \t\t\t    cpu_cores : 4"
        print
        print "      \t\t\t  host : www869.oak1"
        print "      \t\t\t    cpu_cores : 4"
        print "      \t\t\t    environment : SiteCatalyst - OAK - beta"
        print "      \t\t\t  -------------end cut here-------------"
        print
        print "      \t\t\t  Above file syntax explained:"
        print "      \t\t\t    (1) Each host to be updated starts with the key name of \"host\", followed by a colon,"
        print "      \t\t\t        and then the name of the host itself."
        print "      \t\t\t        I typically put a set of spaces around the colon for readability, but it isn't"
        print "      \t\t\t        required."
        print "      \t\t\t    (2) Each attribute of the host to be updated is indented under the host name (yes,"
        print "      \t\t\t        the indent is required).  For the first host shown above, both the operating system"
        print "      \t\t\t        and primary ip address values in CMDB will be updated."
        print "      \t\t\t    (3) Each attribute to be updated has the name of the attribute, then a colon, and then"
        print "      \t\t\t        the new value it will be set or updated to."
        print "      \t\t\t    (4) The file supports comments (lines that start with the hash symbol '#').  Empty"
        print "      \t\t\t        lines are also supported and ignored."
        print "      \t\t\t    (5) Each additional host operates in the same manner as described and shown here."
        print
        print "      \t\t\t  For the file above, 3 hosts are going to be updated with a different set of attributes being"
        print "      \t\t\t  changed for each one."
        print

        print "  --updateattr\t\tCMDB attribute update for a host or hosts."
        print
        print "      \t\t\t  Syntax:"
        print "      \t\t\t    {0} -h <list_of_hosts> --updateattr=\"<attribute_name>=<attribute_value>, ...\"".format(command)
        print
        print "      \t\t\t  Example:"
        print "      \t\t\t    {0} -h dn1.or1 --updateattr=\"MONGO_VER=3.4\"".format(command)
        print

        print "  --updatesor\t\tUpdate the Source of Record to CMDB for the device list submitted."
        print
        print "      \t\t\t  !! Be careful with this parameter as it is dangerous and will delete SIS data records !!"
        print
        print "      \t\t\t  Syntax:"
        print "      \t\t\t    {0} -h <list_of_hosts> --updatesor".format(command)
        print
        print "      \t\t\t  To execute this option successfully, the correct SKMS permissions are required."

    if 'quick' in subsection or 'all' in subsection:
        print
        print "Quick search terms for CMDB"
        print
        print "The quick search switches are designed to reduce the number of keystrokes needed to quickly get at"
        print "information in the DAO in an expected manner.  Because of this, assumptions are made as to what will"
        print "be displayed and required when using these switches.  If a more full-featured search is required,"
        print "use the --dao=<dao_name> search feature with --fields=<field_names> and any search criteria as"
        print "desired."
        print
        print
        print "  --dao_environment\tAllow quick searching of the EnvironmentDao"
        print "  --dao_env"
        print
        print "               \t\tInput    :  Environment name (CMDB key = full_name)"
        print "               \t\tOutput   :  Environment name"
        print "               \t\tSort     :  Environment name (ascending)"
        print
        print "               \t\tExamples :  {0} --dao_env=\"SiteCatalyst - PNW*\"".format(command)
        print "               \t\t            {0} --dao_env=\"SiteCatalyst - PNW*\" -f name ATTRIBUTES".format(command)
        print
        print "  --dao_service\t\tAllow quick searching of the DeviceServiceDao"
        print
        print "               \t\tInput    :  Device Service name (CMDB key = full_name)"
        print "               \t\tOutput   :  Device Service name"
        print "               \t\tSort     :  full_name (ascending)"
        print
        print "               \t\tExamples :  {0} --dao_service=\"Analytics - Reporting*\"".format(command)
        print "               \t\t            {0} --dao_service=\"*contribution analysis*\"".format(command)
        print "               \t\t            {0} --dao_service=\"Analytics - DB - Mongo Generic\" -f name ATTRIBUTES".format(command)
        print
        print "  --dao_state  \t\tAllow quick searching of the DeviceStateDao"
        print
        print "               \t\tInput    :  Device State name (CMDB key = full_name)"
        print "               \t\tOutput   :  Device State name"
        print "               \t\tSort     :  full_name (ascending)"
        print
        print "               \t\tExamples :  {0} --dao_state=\"*provisioning*\"".format(command)
        print "               \t\t            {0} --dao_state=\"*reclamation*\"".format(command)
        print
        print "  --dao_group  \t\tAllow quick searching of the DeviceGroupDao for group names and data"
        print
        print "               \t\tInput    :  Device Group name (CMDB key = name)"
        print "               \t\tOutput   :  Device Group name"
        print "               \t\tSort     :  name (ascending)"
        print
        print "               \t\tExamples :  {0} --dao_group=\"*::stats::*\"".format(command)
        print "               \t\t         :  {0} --dao_group=va7::stats:rdc1 -f name ATTRIBUTES".format(command)
        print
        print "  --dao_cmr    \t\tAllow quick searching of the CmrDao"
        print
        print "               \t\tInput    :  Delta search term for the date range (CMDB key = start_date)"
        print "               \t\tOutput   :  id, start_date, duration, priority, risk, impact, summary"
        print "               \t\tSort     :  start_date, ascending"
        print "               \t\tOther    :  --id=\"*\""
        print "               \t\t         :  --cmr_service=\"Adobe Marketing Cloud - Adobe Analytics* OR "
        print "               \t\t                           Adobe Mobile Services - Mobile Analytics*\""
        print
        print "               \t\tExamples :  {0} --dao_cmr=\"+1 week\"".format(command)
        print "               \t\t            {0} --dao_cmr=\"-2 weeks\"".format(command)
        print "               \t\t            {0} --dao_cmr=\"4 days\"".format(command)
        print
        print "               \t\tDelta search terms accepted: day, days, week, weeks, month, months, year, years"
        print "               \t\tUse a minus sign (-) to indicate a time previous.  Examples #4 and #5 in the"
        print "               \t\t\"{0} --help examples\" section show a full-featured search of the CmrDao.".format(command)


    if 'all' in subsection or 'basic' in subsection or 'example' in subsection or 'examples' in subsection:
        print
        print "EXAMPLES:"
        print
        print "Example #1 -- Loading servers from STDIN:"
        print "  cat servers.txt | {0} -- --user=demouser --fields=name,device_state,device_service".format(command)
        print
        print "       The above example takes input from a servers.txt (which presumably is a list of server host"
        print "       names) and queries the CMDB for the name, device state, and device_service of each of those"
        print "       hosts.  The output is not specifically defined, so the default is to output to the console"
        print "       in columns."
        print
        print "Example #2 -- Mixed ranges, aliases, and sorting with csv output to terminal:"
        print "  {0} --user=demouser --hosts=db2240.oak1,db2255.or1..db2288.or1,db22[123]0.da2".format(command)
        print "            --fields=name,LOCATION,POWER --sort=cage_name,rack_name -o csv --showsql"
        print
        print "       This command has a list of hosts to query for (including a range, and an inclusive set:"
        print "       db2210.da2,db2220.da2,db2230.da2).  For these hosts, the name, LOCATION and POWER information"
        print "       are gathered, sorted by cage and then rack name, and output in csv format to the console.  When"
        print "       this is finished, the SQL query sent to CMDB is shown.  The -o csv directive instructs the code"
        print "       to output the data in csv format to the terminal.  To save the output to a file, use -o <filename>.csv"
        print
        print "Example #3 -- Listing devices assigned to a specific DeviceGroup:"
        print "  {0} --user=demouser --dao=DeviceGroupDao --fields=name,device.name,device.device_state.full_name".format(command)
        print "            --device_group_type=5 --name='%vcache%'"
        print
        print "       This command requests all vcache hosts in the DeviceGroupDao to be shown.  The output will then"
        print "       separate each host in the different vCache groups onto separate lines."
        print
        print "Example #4 -- CMR searching:"
        print "  {0} --dao=CmrDao --id=\"*\" --fields=CMR --start_date=\">2017-08-08\" --start_date=\"<2017-08-14\"\\".format(command)
        print "            --truncate --sort=start_date --summary \\"
        print "            --cmr_service=\"Adobe Marketing Cloud - Adobe Analytics* OR Adobe Mobile Services - Mobile Analytics*\""
        print
        print "Example #5 -- CMR searching (simplified date):"
        print "  {0} --dao=CmrDao --id=\"*\" -f id,start_date,priority,risk,impact,summary --start_date=\"+1 week\" \\".format(command)
        print "            --sort=start_date --truncate --summary \\"
        print "            --cmr_service=\"Adobe Marketing Cloud - Adobe Analytics* OR Adobe Mobile Services - Mobile Analytics*\""
        print
        print "       This command searches for all CMRs that will start between August 8th and August 14th.  These CMRs"
        print "       are sorted by their start date and must be in the Analytics service tree.  There are two available"
        print "       aliases for CMR searching: (1) CMR and (2) CMR_URL, which shows the SKMS URL to the CMR in addition"
        print "       to the other columns (see '{0} --aliases | grep CMR' for more information).".format(command)
        print
