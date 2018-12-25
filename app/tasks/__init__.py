"""Tasks related to celery."""
from .. import mongo, logger
import celery
import datetime
import json
import os
import re
import requests
from pyasn import mrtx
import codecs
from urllib.request import urlopen

from ..utils.helpers import str_now_time


app_base = os.path.dirname(os.path.realpath(__file__)).replace('/tasks', '')


ASNAMES_URL = 'http://www.cidr-report.org/as2.0/autnums.html'
HTML_FILENAME = "autnums.html"
EXTRACT_ASNAME_C = re.compile(r"<a .+>AS(?P<code>.+?)\s*</a>\s*(?P<name>.*)", re.U)


def __parse_asname_line(line):
    match = EXTRACT_ASNAME_C.match(line)
    return match.groups()


def _html_to_dict(data):
    """
    Translates an HTML string available at `ASNAMES_URL` into a dict
    :param data:
    :type data: str
    :return:
    :rtype: dict
    """
    split = data.split("\n")
    split = filter(lambda line: line.startswith("<a"), split)
    fn = __parse_asname_line
    return dict(map(fn, split))


def download_asnames():
    """
    Downloads and parses to utf-8 asnames html file
    """
    http = urlopen(ASNAMES_URL)
    data = http.read()
    http.close()

    raw_data = data.decode('latin-1')
    raw_data = raw_data.encode('utf-8')
    return raw_data.decode("utf-8")


@celery.task(name="fetch-as-names")
def fetch_as_names():
    """Process the AS names"""
    data = download_asnames()
    data_dict = _html_to_dict(data)
    data_json = json.dumps(data_dict)
    output = '%s/resources/as_names.json' % app_base
    with codecs.open(output, 'w', encoding="utf-8") as fs:
        fs.write(data_json)


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


@celery.task(name="fetch-rib")
def fetch_rib(force=False):
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
