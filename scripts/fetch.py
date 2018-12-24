import datetime
import requests

from pyasn import mrtx, __version__

if __name__ == '__main__':
    base = "http://archive.routeviews.org//bgpdata/"
    now = datetime.datetime.utcnow()
    slug = now.strftime('%Y.%m')
    fname = now.strftime('rib.%Y%m%d.%H00.bz2')
    hour = int(now.strftime('%H'))
    if not hour % 2 == 0:
        fname = now.strftime('rib.%Y%m%d.')
        fname = fname + str(hour - 1) + '00.bz2'
    url = "%s/%s/RIBS/%s" % (base, slug, fname)

    response = requests.get(url)
    path = 'app/resources/ribs/%s' % (fname)
    open(path, 'wb').write(response.content)

    current = 'app/resources/current'
    prefixes = mrtx.parse_mrt_file(path,
                                   print_progress=False,
                                   skip_record_on_error=True)
    mrtx.dump_prefixes_to_file(prefixes, current, path)
