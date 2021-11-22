import os
import logging
import requests
import json
import configparser
import sys


DEV = False
VER = '1.0.1'

########################################################################################################################
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")

fileHandler = logging.FileHandler("./Output.txt")
fileHandler.setFormatter(logFormatter)
logger.addHandler(fileHandler)

consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(logFormatter)
logger.addHandler(consoleHandler)
########################################################################################################################


def ConfigSectionMap(section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                logger.debug("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1

logger.debug('SonarrSync Version {}'.format(VER))
Config = configparser.ConfigParser()

# Loads an alternate config file so that I can work on my servers without uploading config to github
if DEV:
    settingsFilename = os.path.join(os.getcwd(), 'Dev'
                                                 'Config.txt')
else:
    settingsFilename = os.path.join(os.getcwd(), 'Config.txt')
Config.read(settingsFilename)

sonarr_url = ConfigSectionMap("Sonarr")['url']
sonarr_key = ConfigSectionMap("Sonarr")['key']
sonarrSession = requests.Session()
sonarrSession.trust_env = False
sonarrSeries = sonarrSession.get('{0}/api/series?apikey={1}'.format(sonarr_url, sonarr_key))
if sonarrSeries.status_code != 200:
    logger.error('Sonarr server error - response {}'.format(sonarrSeries.status_code))
    sys.exit(0)

for server in Config.sections():

    if server == 'Default' or server == "Sonarr":
        continue  # Default section handled previously as it always needed

    else:
        logger.debug('syncing to {0}'.format(server))

        session = requests.Session()
        session.trust_env = False
        SyncServer_url = ConfigSectionMap(server)['url']
        SyncServer_key = ConfigSectionMap(server)['key']
        SyncServer_target_profile = ConfigSectionMap(server)['target_profile']
        SyncServerSeries = session.get('{0}/api/series?apikey={1}'.format(SyncServer_url, SyncServer_key))
        if SyncServerSeries.status_code != 200:
            logger.error('4K Sonarr server error - response {}'.format(SyncServerSeries.status_code))
            sys.exit(0)

    # build a list of series IDs already in the sync server, this is used later to prevent reading a series that already
    # exists.
    # TODO refactor variable names to make it clear this builds list of existing not list of series to add
    # TODO #11 add reconcilliation to remove series that have been deleted from source server
    seriesIds_to_syncserver = []
    for series_to_sync in SyncServerSeries.json():
        seriesIds_to_syncserver.append(series_to_sync['tvdbId'])
        #logger.debug('found series to be added')

    newSeries = 0
    searchid = []
    for series in sonarrSeries.json():
        if series['profileId'] == int(ConfigSectionMap(server)['profile']):
            if series['tvdbId'] not in seriesIds_to_syncserver:
                logging.debug('title: {0}'.format(series['title']))
                logging.debug('qualityProfileId: {0}'.format(series['qualityProfileId']))
                logging.debug('titleSlug: {0}'.format(series['titleSlug']))
                images = series['images']
                for image in images:
                    image['url'] = '{0}{1}'.format(sonarr_url, image['url'])
                    logging.debug(image['url'])
                logging.debug('tvdbId: {0}'.format(series['tvdbId']))
                logging.debug('path: {0}'.format(series['path']))
                logging.debug('monitored: {0}'.format(series['monitored']))

                # Update the path based on "path_from" and "path_to" passed to us in Config.txt
                path = series['path']
                path = path.replace(ConfigSectionMap(server)['path_from'], ConfigSectionMap(server)['path_to'])

                payload = {'title': series['title'],
                           'qualityProfileId': series['qualityProfileId'],
                           'titleSlug': series['titleSlug'],
                           'tvdbId': series['tvdbId'],
                           'path': path,
                           'monitored': series['monitored'],
                           'images': images,
                           'profileId': SyncServer_target_profile, 
                           'minimumAvailability': 'released'
                           }

                r = session.post('{0}/api/series?apikey={1}'.format(SyncServer_url, SyncServer_key), data=json.dumps(payload))
                if r.status_code in (200, 201):
                     searchid.append(int(r.json()['id']))
                     logger.info('adding {0} to {1} server'.format(series['title'], server))
                else:
                     logger.debug('Failed with error: {0}'.format(r.json()))
            else:
                logging.debug('{0} already in {1} library'.format(series['title'], server))
        else:
            logging.debug('Skipping {0}, wanted profile: {1} found profile: {2}'.format(series['title'],
                                                                                        series['profileId'],
                                                                                        int(ConfigSectionMap(server)['profile'])
                                                                                        ))



    if len(searchid):
        payload = {'name' : 'SeriesSearch', 'seriesIds' : searchid}
        session.post('{0}/api/command?apikey={1}'.format(SyncServer_url, SyncServer_key), data=json.dumps(payload))

