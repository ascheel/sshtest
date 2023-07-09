#! /usr/bin/env python


#############################################
#
# denali_sis.py
#
#############################################
#
#   This module contains the code to allow Denali to communicate with
#   the SIS database(s) for authentication and queries.
#

import MySQLdb


# This is a basic mapping of SIS to CMDB (and vice-versa).  The user can enter the field in
# either SIS-format or CMDB-format and the code will translate it appropriately to talk with
# the SIS database

sis_services_fields =   [
                              # ALIAS                       # SIS Name                                  # Print Header Title               # Width
                            [ "service_id",                 "service_id",                               "Service ID",                       12],
                            [ "name",                       "name",                                     "Service Name",                     50],
                            [ "device_service",             "name",                                     "Device Service",                   50],
                            [ "short",                      "short",                                    "Short Name",                       25],
                            [ "path",                       "path",                                     "Path",                             20],
                            [ "mirror_dbs",                 "mirror_dbs",                               "Mirror DBs",                       12],
                            [ "real_service",               "real_service",                             "Real Service",                     14],
                            [ "vrsn",                       "vrsn",                                     "VRSN",                             10],
                            [ "ebay",                       "ebay",                                     "eBay",                             10],
                            [ "sj2",                        "sj2",                                      "SJ2",                              10],
                            [ "hk1",                        "hk1",                                      "HK1",                              10],
                            [ "oak1",                       "oak1",                                     "OAK1",                             10],
                            [ "locationid",                 "locationid",                               "Location ID",                      13],
                            [ "service_description",        "service_description",                      "Service Description",              30],
                            [ "mrtg_server_id",             "mrtg_server_id",                           "MRTG Server ID",                   14],
                        ]

sis_servers_fields =    [
                              # ALIAS                       # SIS Name                                  # Print Header Title               # Width
                            [ "apc_unit",                   "apc_unit",                                 "APC Unit",                         10],
                            [ "archive_backup_status",      "archive_backup_status",                    "Archive Backup Status",            23],
                            [ "asset_id",                   "asset_id",                                 "Asset ID",                         10],
                            [ "back_interface",             "back_interface",                           "Back Interface",                   18],
                            [ "backup_priority",            "backup_priority",                          "Backup Priority",                  17],
                            [ "backup_status",              "backup_status",                            "Backup Status",                    15],
                            [ "backup_type",                "backup_type",                              "Backup Type",                      13],
                            [ "blackout_end",               "blackout_end",                             "Blackout End",                     14],
                            [ "blackout_starts",            "blackout_starts",                          "Blackout Starts",                  17],
                            [ "blackout_type",              "blackout_type",                            "Blackout Type",                    15],
                            [ "cage",                       "cage",                                     "Cage",                             10],
                            [ "cas_host",                   "cas_host",                                 "CAS Host",                         20],
                            [ "class",                      "classification",                           "Classification",                   35],
                            [ "console",                    "console",                                  "Console",                          10],
                            [ "cpu",                        "cpu",                                      "CPU",                              10],
                            [ "cpu_cores",                  "cpu_cores",                                "CPU Cores",                        11],
                            [ "customer",                   "customer",                                 "Customer",                         10],
                            [ "description",                "description",                              "Description",                      20],
                            [ "disks",                      "disks",                                    "Disks",                            10],
                            [ "full_backup",                "full_backup",                              "Full Backup",                      13],
                            [ "has_remote_mgt",             "has_remote_mgt",                           "Has Remote Mgt?",                  17],
                            [ "info_backup",                "info_backup",                              "Info Backup",                      13],
                            [ "install_date",               "install_date",                             "Install Date",                     14],
                            [ "invoice",                    "invoice",                                  "Invoice",                           9],
                            [ "label",                      "label",                                    "Label",                            15],
                            [ "last_audit_date",            "last_audit_date",                          "Last Audit Date",                  17],
                            [ "lease",                      "lease",                                    "Lease",                            10],
                            [ "location",                   "location",                                 "Location",                         10],
                            [ "lun_mod",                    "lun_mod",                                  "LUN Mod",                           9],
                            [ "mac",                        "mac_address",                              "MAC Address",                      19],
                            [ "manufacturer",               "manufacturer",                             "Manufacturer",                     14],
                            [ "memory",                     "memory",                                   "Memory",                            8],
                            [ "model",                      "model",                                    "Model",                            33],
                            [ "mrtg_group",                 "mrtg_group",                               "MRTG Group",                       12],
                            [ "nagios_host",                "nagios_hostname",                          "Nagios Hostname",                  20],
                            [ "name",                       "name",                                     "Host Name",                        20],
                            [ "order_data",                 "order_data",                               "Order Data",                       10],
                            [ "primary_ip",                 "primary_ip",                               "IP Address (P)",                   16],
                            [ "price",                      "price",                                    "Price",                            10],
                            [ "po",                         "purchase_order",                           "Purchase Order",                   16],
                            [ "rack_location",              "rack_location",                            "Rack Location",                    15],
                            [ "rack_port",                  "rack_port",                                "Rack Port",                        11],
                            [ "ramdisk_size",               "ramdisk_size",                             "Ramdisk Size",                     14],
                            [ "serial",                     "serial",                                   "Serial #",                         15],
                            [ "server_id",                  "server_id",                                "Server ID",                        11],
                            [ "device_id",                  "server_id",                                "Server ID",                        11],
                            [ "snaps_to",                   "snaps_to",                                 "Snaps To",                         10],
                            [ "status",                     "status",                                   "Status",                           35],
                            [ "device_state",               "status",                                   "Status",                           35],
                            [ "sw_os_version",              "sw_os_version",                            "Operating System",                 30],
                            [ "os_name",                    "sw_os_version",                            "Operating System",                 30],
                            [ "sw_apache",                  "sw_apache",                                "Apache Version",                   20],
                            [ "apache",                     "sw_apache",                                "Apache Version",                   20],
                            [ "sw_kernel",                  "sw_kernel",                                "Kernel Version",                   22],
                            [ "kernel",                     "sw_kernel",                                "Kernel Version",                   22],
                            [ "sw_mysql",                   "sw_mysql",                                 "MySQL Version",                    20],
                            [ "mysql",                      "sw_mysql",                                 "MySQL Version",                    20],
                            [ "sw_php",                     "sw_php",                                   "PHP Version",                      20],
                            [ "php",                        "sw_php",                                   "PHP Version",                      20],
                            [ "switch",                     "switch",                                   "Switch",                           25],
                            [ "switch_port",                "switch_port",                              "Switch Port",                      13],
                            [ "today",                      "today",                                    "Today",                            10],
                            [ "unit_size",                  "unit_size",                                "Unit Size",                        11],
                            [ "vendor",                     "vendor",                                   "Vendor",                           10],
                            [ "write_cache_size",           "write_cache_size",                         "Write Cache Size",                 18],
                        ]


sis_server_to_services = [
                            [ "service_id",                 "service_id",                               "Service ID",                       12],
                            [ "server_id",                  "server_id",                                "Server ID",                        11],
                         ]


# SIS database servers are geo-location specific.  This list helps translate where to
# lookup a server depending upon the datacenter location of the device

'''
#                0       1       2       3       4       5       6       7       8       9
dc_location = ["",     "SJ1",  "SJ2",  "OAK1", "DAL",  "DA2",  "DA3",  "LON1", "LON3", "ORM1",      #   0-9
               "VA1",  "VA2",  "VA3",  "LON2", "LON4", "SJ3",  "",     "",     "SD1",  "CPH1",      #  10-19
               "",     "VA5",  "BOS1", "LOF1", "LOF2", "ORM2", "SYD1", "HOU1", "EGM1", "CPH2",      #  20-29
               "LA1",  "NY1",  "NY2",  "NY3",  "PHX1", "SD2",  "SJ4",  "SJ0",  "WIS1", "SF1",       #  30-39
               "SYD2", "SF2",  "SF3",  "SF4",  "SF5",  "LA2",  "SB1",  "DA4",  "SJ6",  "BJG1",      #  40-49
               "PAR1", "STK1", "MUN1", "TYO1", "PTN1", "CNU1", "HLA1", "TYO2", "LON5", "ML1",       #  50-59
               "SF6",  "DA5",  "NJ1",  "DUB1", "LON6", "SIN1", "NJ2",  "LA3",  "NY6",  "SIN2",      #  60-69
               "SIN3", "VA6",  "",     "MAI1", "SAO1", "SF7",  "SJ5",  "VA4",  "LON7", "SV2",       #  70-79
               "OAK2", "IND1", "HK1",  "HK2",  "HQ1",  "UT1",  "AMS1", "OR1",  "OH1",  "TX4",       #  80-89
               "SAO2", "SYD3", "CA1",  "IRL1", "TYO3", "NY7",  "SD3",  "OR2",  "SJO",  "SEA1",      #  90-99
               "PNW",  "BOS2", "PAR2", "PAR3", "MON1", "MON2", "SYD4", "BRS1", "BOS3", "PAR4",      # 100-109
               "PAR5", "GER1", "LON"]                                                               # 110-112
'''


rdc_locations        =  ["ams1", "bos1", "bos2", "bos3", "brs1", "dub1", "hk2",  "hq1",  "mai1", "ml1",
                         "mon1", "nj1",  "oak1", "oh1",  "par2", "par3", "par4", "par5", "sao1", "sf4",
                         "sf6",  "sj1",  "sj5",  "sv2",  "syd2", "tx4",  "tyo2", "ut1",  "va5"]

sis_datacenter_hosts =  [
                            # All RDCs redirect to SJO
                            [ rdc_locations,    "servers.db.sjo"    ],

                            # All other DCs are directed to their geographic location
                            [ ["dal","da2"],    "servers.db.dal"    ],
                            [ ["lon5"],         "servers.db.lon"    ],
                            [ ["or1"],          "servers.db.pnw"    ],
                            [ ["sin2"],         "servers.db.sin"    ],
                        ]





##############################################################################
#
# determineSISDatabaseLocation(denaliVariables, datacenter)
#

def determineSISDatabaseLocation(denaliVariables, datacenter):

    for location in sis_datacenter_hosts:
        if datacenter in location[0]:
            sisHost = location[1]
            break
    else:
        # It wasn't found?  Assume San Jose SIS Host
        sisHost = "servers.db.sjo"

    return sisHost



##############################################################################
#
# sis_unaliasFields(denaliVariables)
#

def sis_unaliasFields(denaliVariables):
    return True



##############################################################################
#
# sis_determineColumnOrder(denaliVariables)
#

def sis_determineColumnOrder(denaliVariables):

    # STEP #1:  For the field variable (denaliVariables["sis_Fields"]), replace
                # all aliased names with their SIS counterpart.
    ccode = sis_unaliasFields(denaliVariables)

    # STEP #2:  Review the columnData variable (denaliVariables["sis_ColumnData"])
                # for correctness.

    #   do step 2 here in the function   #


    print "dvsf   = %s" % denaliVariables["sis_Fields"]
    print "dvsql  = %s" % denaliVariables["sis_SQLParameters"]
    print "dvorig = %s" % denaliVariables["sis_OriginalData"]

    return True



##############################################################################
#
# constructSISQuery(denaliVariables, cmdb_printData)
#

def constructSISHostQuery(denaliVariables, cmdb_printData):

    # STEP #1:  Massage the field names to be correct for a SIS sql request
                # this includes if an alias is used for a SIS column -- replace it with
                # the correct SIS database field
    ccode = sis_determineColumnOrder(denaliVariables)

    # STEP #2:  Massage SQL parameters to meet SQL syntax requirements
                # this should be pretty straight-forward -- essentially a copy of the
                # CMDB version of this function (but make it more efficient/better)
    #ccode = sis_processSQLParameters(denaliVariables)

    # STEP #3:  Separate the host list into SIS datacenter specific locations (sin, sjo, etc.)
                # Store the result in denaliVariables["sis_HostsByDC"]
                # { "pnw" : [<list of hosts>], "sin" : [<list of hosts>], ... }
                # Something to think about --- get the location ID via CMDB and store it so
                # SIS can access it?
                #
                # Current method is to take the extension and put it in the proper category;
                # hosts that cannot be categorized will be put in SJO.
    #ccode = sis_separateHostsByLocation(denaliVariables)

    #
    # Loop start
    #

    # Using data from #3 (above), loop through each defined SIS data center, and take the
    # list of hosts from there.
    #for location in denaliVariables["sis_HostsByDC"]:
    #    hostList = location[0]

        # STEP #4:  Put the SQL Query together -- "SELECT / FROM / WHERE", etc.
                    # hopefully this is straight-forward like the CMDB version.
                    # don't forget the "FROM" statement -- SIS requires it.
    #    sqlQuery = sis_buildSQLQuery(denaliVariables)

        # STEP #5:  For each set of geo-specific data, query the local SIS database for results
    #    sis_responseData = sis_doSISQuery(denaliVariables, sqlQuery)

        # STEP #6:  Append this data to previous runs (if applicable)
                    # Store/update the SIS data in a host-keyed dictionary
                    # { hostname1 : [ column1, column2, column3 ], hostname2 : [...] }
    #    sis_dictionaryData = appendToExistingData(denaliVariables, sis_responseData)

    #
    # Loop end
    #

    # STEP #7:  Combine SIS and CMDB data
    # data collection is finished -- now combine it with the already-gathered CMDB data
    # use the original saved data (denaliVariables["sis_OriginalData"]) to determine the correct
    # column order.
    #
    # insert columns as required -- keyed by host name -- into the CMDB data.
    #ccode = sis_CombineSISWithCMDBData(denaliVariables, sis_dictionaryData, cmdb_printData)

    # STEP #8:  # What's left?
    #     (1) Wrap the data columns (if required)
    #     (2) Send it off to be printed

    return True


##############################################################################
#
# Main execution starting point
#

if __name__ == "__main__":

    # just a quick proof of concept to get connectivity to a sis database
    # host and look at the return data
    db = MySQLdb.connect(host="servers.db.sjo",
                         user="ouser",
                         passwd="<password>",
                         db="servers")

    cur = db.cursor()

    cur.execute("SELECT name FROM servers WHERE name LIKE ('db225%.oak1')")

    for row in cur.fetchall():
        print row[0]