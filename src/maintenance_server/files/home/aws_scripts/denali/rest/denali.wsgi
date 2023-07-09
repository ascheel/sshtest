############################################################################
#
# denali.wsgi
#
#   Author      :  Mike Hasleton
#   Version     :  0.5 (BETA)
#   Last Update :  April 7, 2016
#   Company     :  Adobe Systems, Inc.
#
#   This file is the launching point for the mod_wsgi module in Apache.
#   Internally the denali_ss file will be imported along with the bottle
#   code to allow web server "directories" to have different reactions
#   and returned results.
#
#   This code is called via the Apache mod_wsgi module when the denali
#   application POSTs data to the web at:
#
#       http://zenith.dmz.ut1.omniture.com/denali/denali
#
#   The "denali/denali" path was chosen because Zenith looks at everything
#   coming in on the root directory path "/".  This should hopefully
#   avoid Zenith getting involved in this.
#
#   The /denali path is registered in the Apache configuration file for
#   Zenith (virtual server:80), and then the additional /denali path
#   is looked for in the denali_ss.py file (@route /denali).
#

import sys
sys.path.insert(0, "/var/www/html/wsgi-scripts")

import bottle
import denali_ss
application = bottle.default_app()
