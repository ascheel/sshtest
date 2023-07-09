#! /usr/bin/env python


#############################################
#
# denali_sis_integration.py
#
#############################################
#
#   This module contains the code to allow Denali to communicate with
#   the SIS database(s) for authentication and queries through the
#   omnitool utility.
#
#   This is just a quick and dirty module that takes complete advantage
#   of the fact that omnitool is a mature utility and will report back
#   any problems.
#
#   Data is passed straight through to it, and handled entirely by that
#   utility.  Denali servers only as a messenger between the two.
#

import os
import sys
import denali_groups
import subprocess


OMNITOOL_LOCATION = "/opt/netops/omnitool"


##############################################################################
#
# entryPoint(denaliVariables)
#

def entryPoint(denaliVariables):

    # Verify omnitool is available.  if not, fail out
    if os.path.isfile(OMNITOOL_LOCATION) == False:
        print "Denali Error:  SIS Integration not available without omnitool being available."
        return False

    ccode = returnDeviceList(denaliVariables)
    if ccode == False:
        return False

    ccode = callOmnitool(denaliVariables)
    if ccode == False:
        return False

    return True



##############################################################################
#
# returnDeviceList(denaliVariables)
#

def returnDeviceList(denaliVariables):

    ccode = denali_groups.createServerListFromArbitraryQuery(denaliVariables, 'DeviceDao')
    return ccode



##############################################################################
#
# callOmnitool(denaliVariables)
#

def callOmnitool(denaliVariables):

    no_errors = True

    # generate the omnitool parameters
    omnitool_parms = [OMNITOOL_LOCATION]
    omnitool_parms.extend(['-h'])
    omnitool_parms.extend([denaliVariables['serverList']])
    omnitool_parms.extend(denaliVariables['sis_command'].split())

    proc = subprocess.Popen(omnitool_parms, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1, shell=False)

    for output_line in iter(proc.stdout.readline, ""):
        if output_line.find('was not found in the sis database') != -1:
            no_errors = False
        print output_line.strip()

    return no_errors