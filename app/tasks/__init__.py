"""Tasks related to celery."""
from .. import mongo, logger
import celery
import datetime
import json
import os
import requests
from pyasn import mrtx

from ..utils.helpers import str_now_time


app_base = os.path.dirname(os.path.realpath(__file__)).replace('/tasks', '')


@celery.task(name="heartbeat")
def heartbeat():
    """Look alive."""
    logger.debug("I am the beat.")


def gen_request():
    """Build the routeview URL to download."""
    base = "http://archive.routeviews.org//bgpdata/"
    now = datetime.datetime.utcnow()
    slug = now.strftime('%Y.%m')
    fname = now.strftime('rib.%Y%m%d.%H00.bz2')
    hour = int(now.strftime('%H'))
    if not hour % 2 == 0:
        fname = now.strftime('rib.%Y%m%d.')
        fname = fname + str(hour - 1) + '00.bz2'
    url = "%s/%s/RIBS/%s" % (base, slug, fname)
    return {'url': url, 'filename': fname}


def to_download():
    """Check to see if we need to download."""
    now = datetime.datetime.utcnow()
    fname = now.strftime('rib.%Y%m%d.%H00.bz2')
    hour = int(now.strftime('%H'))
    if not hour % 2 == 0:
        fname = now.strftime('rib.%Y%m%d.')
        fname = fname + str(hour - 1) + '00.bz2'
    config = json.load(open('%s/resources/config.json' % app_base))
    if fname == config['file']:
        return False
    return True


@celery.task(name="fetch")
def fetch(force=False):
    """Process the routeview data."""
    if not to_download() or not force:
        return
    logger.debug("Downloading the latest RIB")
    meta = gen_request()
    response = requests.get(meta['url'])
    path = '%s/resources/ribs/%s' % (app_base, meta['filename'])
    open(path, 'wb').write(response.content)
    logger.debug("RIB file saved")
    current = '%s/resources/current' % (app_base)
    logger.debug("Converting RIB to database format")
    prefixes = mrtx.parse_mrt_file(path, print_progress=False,
                                   skip_record_on_error=True)
    mrtx.dump_prefixes_to_file(prefixes, current, path)
    logger.debug("Updated the database")
    config = {'file': meta['filename'], 'last_update': str_now_time()}
    json.dump(config, open('%s/resources/config.json' % app_base, 'w'),
              indent=4)
