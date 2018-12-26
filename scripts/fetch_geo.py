import tarfile
import requests
import shutil

from pyasn import mrtx, __version__

APP_BASE = "/tmp"

if __name__ == '__main__':
    url = "https://geolite.maxmind.com/download/geoip/database/GeoLite2-City.tar.gz"
    response = requests.get(url)
    path = '%s/GeoLite2-City.tar.gz' % (APP_BASE)
    open(path, 'wb').write(response.content)
    tar = tarfile.open(path)
    files = tar.getmembers()
    tar.extractall(path='/tmp/')
    tar.close()

    for file in files:
        if not file.name.endswith('.mmdb'):
            continue
        shutil.move('/tmp/%s' % file.name, '/tmp/GeoLite2-City.mmdb')