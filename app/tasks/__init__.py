"""Tasks related to asynchronous processing.

For all intents and purposes, this is where the magic of the database syncing
takes place. There's some extra functions in here that should really move over
to the utils file, but it was easier to keep the logic in one spot during
testing.

Each of the celery decorated functions are tasks that can be called directly
from the Flask web application aka the API or via some scheduler. These tasks
will all run as a non-blocking call if made through the API or scheduler; they
just run and log out to the Celery handler.

If you're using the service wrappers, this is netinfod. And if it wasn't clear,
this needs to be running in order for any real processing to take place.
"""
from .. import mongo, logger
import celery
import datetime
import json
import os
import re
import requests
import tarfile
import shutil
from pyasn import mrtx
import codecs
from urllib.request import urlopen

from ..utils.helpers import str_now_time


APP_BASE = os.path.dirname(os.path.realpath(__file__)).replace('/tasks', '')
ASNAMES_URL = 'http://www.cidr-report.org/as2.0/autnums.html'
HTML_FILENAME = "autnums.html"
EXTRACT_ASNAME_C = re.compile(r"<a .+>AS(?P<code>.+?)\s*</a>\s*(?P<name>.*)", re.U)


def __parse_asname_line(line):
    match = EXTRACT_ASNAME_C.match(line)
    return match.groups()


def _html_to_dict(data):
    """Translates an HTML string available at `ASNAMES_URL` into a dict."""
    split = data.split("\n")
    split = filter(lambda line: line.startswith("<a"), split)
    fn = __parse_asname_line
    return dict(map(fn, split))


def download_asnames():
    """Downloads and parses to utf-8 asnames html file."""
    http = urlopen(ASNAMES_URL)
    data = http.read()
    http.close()

    raw_data = data.decode('latin-1')
    raw_data = raw_data.encode('utf-8')
    return raw_data.decode("utf-8")


@celery.task(name="fetch-as-names")
def fetch_as_names():
    """Process the AS names."""
    data = download_asnames()
    data_dict = _html_to_dict(data)
    data_json = json.dumps(data_dict)
    output = '%s/resources/asn/as_names.json' % APP_BASE
    with codecs.open(output, 'w', encoding="utf-8") as fs:
        fs.write(data_json)


def build_filename():
    """Build out the filename based on current UTC time."""
    now = datetime.datetime.utcnow()
    fname = now.strftime('rib.%Y%m%d.%H00.bz2')
    hour = int(now.strftime('%H'))
    if not hour % 2 == 0:
        if len(str(hour)) == 1:
            hour = "0%d" % (hour - 1)
        else:
            hour = hour - 1
        fname = now.strftime('rib.%Y%m%d.')
        fname = fname + str(hour) + '00.bz2'
    return fname


def gen_request():
    """Build the routeview URL to download."""
    base = "http://archive.routeviews.org//bgpdata/"
    now = datetime.datetime.utcnow()
    slug = now.strftime('%Y.%m')
    fname = build_filename()
    url = "%s/%s/RIBS/%s" % (base, slug, fname)
    return {'url': url, 'filename': fname}


def to_download():
    """Check to see if we need to download."""
    now = datetime.datetime.utcnow()
    fname = build_filename()
    config = json.load(open('%s/resources/config.json' % APP_BASE))
    if fname == config['asn']['last_rib_file']:
        return False
    return True


@celery.task(name="fetch-rib")
def fetch_rib(force=False):
    """Process the routeview data."""
    if not to_download() and not force:
        return
    logger.debug("Downloading the latest RIB")
    meta = gen_request()
    response = requests.get(meta['url'])
    path = '%s/resources/asn/ribs/%s' % (APP_BASE, meta['filename'])
    open(path, 'wb').write(response.content)
    logger.debug("RIB file saved")
    current = '%s/resources/asn/current' % (APP_BASE)
    logger.debug("Converting RIB to database format")
    prefixes = mrtx.parse_mrt_file(path, print_progress=False,
                                   skip_record_on_error=True)
    mrtx.dump_prefixes_to_file(prefixes, current, path)
    logger.debug("Updated the database")
    config = json.load(open('%s/resources/config.json' % APP_BASE))
    config['asn']['last_rib_file'] = meta['filename']
    config['asn']['last_update'] = str_now_time()
    json.dump(config, open('%s/resources/config.json' % APP_BASE, 'w'),
              indent=4)


@celery.task(name="fetch-geoip")
def fetch_geoip(force=False):
    """Process the maxmind geoip database."""
    url = "https://geolite.maxmind.com/download/geoip/database/GeoLite2-City.tar.gz"
    response = requests.get(url)
    path = '%s/resources/geoip/GeoLite2-City.tar.gz' % (APP_BASE)
    open(path, 'wb').write(response.content)
    tar = tarfile.open(path)
    files = tar.getmembers()
    tar.extractall(path='%s/resources/geoip/' % APP_BASE)
    tar.close()

    for file in files:
        if not file.name.endswith('.mmdb'):
            continue
        shutil.move('%s/resources/geoip/%s' % (APP_BASE, file.name),
                    '%s/resources/geoip/current' % APP_BASE)
    config = json.load(open('%s/resources/config.json' % APP_BASE))
    config['geoip']['last_update'] = str_now_time()
    json.dump(config, open('%s/resources/config.json' % APP_BASE, 'w'),
              indent=4)
    path = '%s/resources/geoip/' % APP_BASE
    for f in os.listdir('%s/resources/geoip/' % APP_BASE):
        if f in ['current', '__init__.py']:
            continue
        try:
            shutil.rmtree(path + f)
        except:
            os.remove(path + f)
