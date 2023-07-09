#############################################
#
# denali_gauntlet.py
#
#############################################
#
#   This module contains the code to allow the user to query a specific set
#   of devices/hosts based on gauntlet tracks, environments, and promotion
#   levels.
#

import os
import fnmatch
import json
import shutil
import subprocess
import denali_search
import denali_utility



##############################################################################
#
# findAndDisplayAllTracks(denaliVariables, track_name, location, destination, print_list)
#

def findAndDisplayAllTracks(denaliVariables, track_name, location, destination, print_list):

    all_tracks_list = []

    all_tracks = fileRetrieval(denaliVariables, location, destination, directory=False, full_list=True)

    # get the track names into a List
    for (index, filename) in enumerate(all_tracks['filenames']):
        if filename.endswith('.json') and all_tracks['results'][index] == "200 OK":
            filename_track = filename.split('/')[-1]
            filename_track = filename_track[:-5]
            all_tracks_list.append(filename_track)

    # print the track list
    all_tracks_list.sort()

    if print_list == True:
        print
        print "Available Gauntlet Tracks:"
        for track in all_tracks_list:
            print "  %s" % track

    return all_tracks_list



##############################################################################
#
# findMatchingTracks(denaliVariables, all_tracks, track_name)
#

def findMatchingTracks(denaliVariables, all_tracks, track_name):

    matching_tracks  = []
    submitted_tracks = track_name.split(',')

    for pattern in submitted_tracks:
        pattern = pattern.strip()
        matches = fnmatch.filter(all_tracks, pattern)
        if len(matches):
            matching_tracks.extend(matches)

    return matching_tracks



##############################################################################
#
# retrieveDeviceServiceAndEnvironmentList(denaliVariables, track_name)
#

def retrieveDeviceServiceAndEnvironmentList(denaliVariables, track_name):

    # original/decommissioned locations (kept for reference purposes)
    #devService_location   = "http://yumorigin1.dmz.ut1.omniture.com/gauntlet-export/track-device-services/"
    #environments_location = "http://yumorigin1.dmz.ut1.omniture.com/gauntlet-export/track-environments/"

    # new locations
    devService_location   = "http://yumorigin.or1.omniture.com/gauntlet-export/track-device-services/"
    environments_location = "http://yumorigin.or1.omniture.com/gauntlet-export/track-environments/"
    promotion_level       = denaliVariables['gauntletPromotion']
    service_strings       = set()
    environment_strings   = set()

    if track_name == "Waiting":
        # no name specified -- issue an error and exit out
        return False

    destination = determineDestination(denaliVariables)

    # Display all of the available gauntlet tracks
    if track_name in ['all', 'list'] or '?' in track_name or '*' in track_name:
        if '?' in track_name or '*' in track_name:
            print_list = False
        else:
            print_list = True

        all_tracks = findAndDisplayAllTracks(denaliVariables, track_name, devService_location, destination, print_list)

        # if the tracks are displayed/printed, then just return/exit
        if print_list == True:
            return True

    # separate the promotion level into different values, if needed
    if promotion_level.find(' OR ') != -1:
        promotion_level = promotion_level.split(' OR ')
    elif promotion_level.find(',') != -1:
        promotion_level = promotion_level.split(',')
    else:
        promotion_level = [promotion_level]

    # Did the user submit more than one track to work with?
    # The following are accepted syntax variations:
    #   (1) "<track_name1> OR <track_name2> OR <track_name3>"
    #   (2)  <track_name1>,<track_name2>,<track_name3>
    #   (3) "<track_name1>, <track_name2>, <track_name3>"
    if track_name.find(' OR ') != -1:
        track_name = track_name.split(' OR ')
    elif track_name.find(',') != -1:
        track_name = track_name.split(',')
    else:
        track_name = [track_name]

    track_name_list = []

    for track in track_name:
        # Handle wildcard searching of the available gauntlet tracks
        if '?' in track or '*' in track:
            # find any matching tracks from the submitted list
            track_name_temp = findMatchingTracks(denaliVariables, all_tracks, track)
            if len(track_name_list) == 0:
                track_name_list = track_name_temp
            else:
                track_name_list.extend(track_name_temp)
        else:
            # put the track name in a List for going through
            track_name_temp = track.split(',')
            if len(track_name_list) == 0:
                track_name_list = track_name_temp
            else:
                track_name_list.extend(track_name_temp)

    # loop through the found tracks one at a time, retrieving data
    for track in track_name_list:
        # make sure the track name is clear of extraneous characters
        track = track.strip()

        # Retrieve the data about the track
        ds_location = devService_location + track + '.json'
        track_data  = fileRetrieval(denaliVariables, ds_location, destination)

        if len(track_data['results']) == len(track_data['filenames']) and len(track_data['results']):
            track_file = track_data['filenames'][0]
        else:
            # no data returned
            print "Denali Error: No device targeting data returned from remote server."
            return False

        if track_data['results'][0] != "200 OK":
            # file could not be downloaded
            print track_data['results'][0] + ": " + track_data['filenames'][0]
            return False

        # go get the device services from the file downloaded
        device_services = extractKeyFromJSONFile(denaliVariables, track_file, 'device-services')
        denaliVariables['gauntletTrackData'].update({track:{'device_services':device_services}})

        # using the submitted track as the basis for the directory structure, retrieve all environments
        # that are currently associated with this track
        env_location = environments_location + track + '/'
        environ_data = fileRetrieval(denaliVariables, env_location, destination, directory=True)

        for (index, filename) in enumerate(environ_data['filenames']):
            if filename.endswith('.json') and environ_data['results'][index] == "200 OK":
                environment_data = extractKeyFromJSONFile(denaliVariables, filename, 'environments')
                environment_name = filename.split('/')[-1]
                environment_name = environment_name[:-5]        # removes ".json" on the end

                if 'environments' not in denaliVariables['gauntletTrackData'][track]:
                    denaliVariables['gauntletTrackData'][track].update({'environments':{environment_name:environment_data}})
                else:
                    denaliVariables['gauntletTrackData'][track]['environments'].update({environment_name:environment_data})

        # get a list of the current environments for this specific track
        environment_keys = denaliVariables['gauntletTrackData'][track]['environments'].keys()
        environment_keys.sort()

        # handle multiple promotion level (beta,prod) if requested
        for promotion in promotion_level:
            if promotion in environment_keys:
                targeted_environment = denaliVariables['gauntletTrackData'][track]['environments'][promotion]
                returnString = generateDenaliCLIForSearching(denaliVariables, targeted_environment)
                for environment in returnString:
                    environment_strings.add(environment)
            else:
                print "Denali Error: Specified promotion level [%s] was not found for the track [%s]" % (promotion, track)
                print "              Available promotion levels:  %s" % environment_keys
                return False

            returnString = generateDenaliCLIForSearching(denaliVariables, device_services)
            for service in returnString:
                service_strings.add(service)

    service_strings     = ' OR '.join(service_strings)
    environment_strings = ' OR '.join(environment_strings)

    # This call integrates the track data into mimicking a cli parameter.
    # It allows the code to search for the hosts, and then operate on them (-c/--command)
    # just like any other search operation.
    ccode = integrateTrackSearchParameters(denaliVariables, [service_strings], [environment_strings])
    if ccode == False:
        return False

    return True



##############################################################################
#
# combineLists(denaliVariables, cli_list, target_list)
#

def combineLists(denaliVariables, cli_list, target_list):

    non_existant_target = False

    cli_set_lo = set(cli_list.lower().split(' or '))
    target_set = set(target_list.split(' OR '))

    for element in target_set:
        if element.lower() not in cli_set_lo:
            non_existant_target = True
            print "Denali Error:  \"%s\" is not a member of %s" % (element, list(cli_list.split(' OR ')))

    if non_existant_target == True:
        return False

    combined_list = ' OR '.join(list(cli_set_lo & target_set))

    return combined_list



##############################################################################
#
# searchDao(denaliVariables, search_parameter, dao)
#

def searchDao(denaliVariables, search_parameter, dao):

    parameter_string = ''
    new_return_data  = ''

    for parameter in search_parameter.split(' OR '):
        if len(parameter_string):
            parameter_string += " OR full_name LIKE '%s'" % parameter
        else:
            parameter_string = "full_name LIKE '%s'" % parameter

    queryData = "SELECT full_name WHERE (%s) ORDER BY full_name PAGE 1, 5000" % parameter_string
    queryData = queryData.replace('*', '%')
    queryData = queryData.replace('?', '_')

    saveDao    = denaliVariables["searchCategory"]
    saveSQLMod = denaliVariables["sqlParameters"]

    denaliVariables['searchCategory'] = dao

    if denaliVariables['api'] is None:
        denali_utility.retrieveAPIAccess(denaliVariables)

    respDict = denali_search.executeWebAPIQuery(denaliVariables, queryData)
    respDict = respDict['data']['results']

    for element in respDict:
        if len(new_return_data):
            new_return_data += ' OR ' + element['full_name'].strip()
        else:
            new_return_data = element['full_name'].strip()

    denaliVariables["searchCategory"] = 'DeviceDao'
    denaliVariables["sqlParameters"]  = saveSQLMod

    # reset API to None or the search will fail
    denaliVariables["api"]            = None

    return new_return_data



##############################################################################
#
# integrateTrackSearchParameters(denaliVariables, device_service, environment_list)
#

def integrateTrackSearchParameters(denaliVariables, device_service, environment_list):

    device_service_cli = ''
    environment_cli    = ''

    #print "(B) dvsql = %s" % denaliVariables['sqlParameters']

    # build the device service cli string
    for service in device_service:
        if len(device_service_cli) == 0:
            device_service_cli = service
        else:
            device_service_cli += " OR %s" % service

    # build the environment cli string
    for environment in environment_list:
        if len(environment_cli) == 0:
            environment_cli = environment
        else:
            environment_cli += "OR %s" % environment

    # integrate the strings into the existing data (or create them if they don't exist)
    device_service_updated = False
    environment_updated    = False

    # look for existing data and append to it
    for (index, parameter) in enumerate(denaliVariables['sqlParameters']):
        if parameter[0] == "--device_service":
            device_service_updated = True
            if (denaliVariables['sqlParameters'][index][1].find('*') != -1 or
                denaliVariables['sqlParameters'][index][1].find('?') != -1 or
                denaliVariables['sqlParameters'][index][1].find('%') != -1 or
                denaliVariables['sqlParameters'][index][1].find('_') != -1):
                denaliVariables['sqlParameters'][index][1] = searchDao(denaliVariables, denaliVariables['sqlParameters'][index][1], 'DeviceServiceDao')
            device_service_cli = combineLists(denaliVariables, device_service_cli, denaliVariables['sqlParameters'][index][1])
            if device_service_cli == False:
                return False
            if len(device_service_cli) and denaliVariables['sqlParameters'][index][1] != device_service_cli:
                denaliVariables['sqlParameters'][index][1] += " OR %s" % device_service_cli
        elif parameter[0] == "--environment":
            environment_updated = True
            if (denaliVariables['sqlParameters'][index][1].find('*') != -1 or
                denaliVariables['sqlParameters'][index][1].find('?') != -1 or
                denaliVariables['sqlParameters'][index][1].find('%') != -1 or
                denaliVariables['sqlParameters'][index][1].find('_') != -1):
                denaliVariables['sqlParameters'][index][1] = searchDao(denaliVariables, denaliVariables['sqlParameters'][index][1], 'EnvironmentDao')
            environment_cli = combineLists(denaliVariables, environment_cli, denaliVariables['sqlParameters'][index][1])
            if environment_cli == False:
                return False
            if len(environment_cli) and denaliVariables['sqlParameters'][index][1] != environment_cli:
                denaliVariables['sqlParameters'][index][1] += " OR %s" % environment_cli

    # see if an update is needed (existing data not found, but the cli string is populated)
    if device_service_updated == False and len(device_service_cli) > 0:
        denaliVariables['sqlParameters'].append(['--device_service', device_service_cli])

    if environment_updated == False and len(environment_cli) > 0:
        denaliVariables['sqlParameters'].append(['--environment', environment_cli])

    #print "(A) dvsql = %s" % denaliVariables['sqlParameters']

    return True



##############################################################################
#
# generateDenaliCLIForSearching(denaliVariables, data_element)
#

def generateDenaliCLIForSearching(denaliVariables, data_element):

    string_to_use = ''

    for element in data_element:
        if len(string_to_use) == 0:
            string_to_use = element
        else:
            string_to_use += ",%s" % element

    return string_to_use.split(',')



##############################################################################
#
# determineDestination(denaliVariables)
#

def determineDestination(denaliVariables):

    destination = denali_utility.returnHomeDirectory(denaliVariables)

    # make sure the "gauntlet" directory exists under the destination directory
    if destination[-1] != '/':
        destination += "/.denali/gaunlet/"
    else:
        destination += ".denali/gauntlet/"

    # make sure the directory path exists before putting files in it.
    if os.path.exists(destination):
        # Delete (rm -rf) this directory path.  wget will put new files in it and will not
        # remove the old ones, so there is a possibility of mixing old with new, and that
        # could definitely cause an issue with this code as it investigates all files.
        # Just delete the directory structure, and avoid any potential problems.
        shutil.rmtree(destination)

    # make the directory path now
    os.makedirs(destination)

    return destination



##############################################################################
#
# fileRetrieval(denaliVariables, location, destination, directory=False, full_list=False)
#

def fileRetrieval(denaliVariables, location, destination, directory=False, full_list=False):

    if full_list == True:
        # gather a full list of all available track
        wget_parms = ['wget', '-r', '-np', '--cut-dirs=1', '-P', destination, location]
    else:
        if directory == False:
            wget_parms = ['wget', '-P', destination, location]
        else:
            # -r       = recursive
            # -np      = no parents
            # -A .json = only download files with the .json extension
            # -P       = where to write the downloaded file
            wget_parms = ['wget', '-r', '-np', '-A', '.json', '-P', destination, location]

    proc = subprocess.Popen(wget_parms, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.wait()

    # overall success/failure of this process
    process_result = proc.returncode

    # get stdout/stderr ready for parsing (wget outputs to stderr, but look at stdout anyway)
    std_out = proc.stdout.read().splitlines()
    std_err = proc.stderr.read().splitlines()

    if len(std_out):
        results = parseWGETResult(std_out)

    if len(std_err):
        results = parseWGETResult(std_err)

    if process_result != 0:
        print
        print "WGET Error code: %s" % process_result

    return results



##############################################################################
#
# parseWGETResult(wget_output)
#

def parseWGETResult(wget_output):

    output = {'filenames': [], 'results': []}

    # determine if the file retrieval was successful (or not), and the name
    # of the file downloaded
    for line in wget_output:
        result   = ''
        filename = ''

        if line.startswith('--'):
            output['filenames'].append(line.split('--')[-1].strip())
        elif line.startswith('HTTP request sent'):
            result   = line.split('... ')[1].strip()
        elif line.startswith('Saving to:'):
            filename = line.split(':',1)[1].strip()

            # strip off any unicode characters (wget puts them on sometimes)
            filename = ''.join(i for i in filename if ord(i) < 128)

        if len(result):
            output['results'].append(result)
        if len(filename):
            if len(output['results']) == len(output['filenames']):
                # overwrite the last one becaues it currently has the really
                # long filename that was downloaded -- line that starts with "--"
                output['filenames'][-1] = filename
            else:
                output['filenames'].append(filename)

    return output



##############################################################################
#
# extractKeyFromJSONFile(denaliVariables, filename, key)
#

def extractKeyFromJSONFile(denaliVariables, filename, key):

    # read the entire file into memory
    with open(filename, 'r') as filename:
        file_content = filename.read()

    # transform the file data to json
    file_content = json.loads(file_content)

    # pull out and return just the key element
    return file_content[key]
