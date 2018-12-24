"""Generic calls within the application."""
from . import core
from .. import mongo, logger, celery, check_asndb
from flask import (jsonify, request)
from flask import current_app as app

import pyasn
import os


@core.route('/lookup', methods=['GET'])
@check_asndb
def lookup():
    """Enrich IP address."""
    ip_addr = request.args.get('ip')
    data = app.config['ASNDB'].lookup(ip_addr)
    record = {'as_num': data[0], 'netblock': data[1],
              'as_name': app.config['ASNDB'].get_as_name(data[0]),
              'ip': ip_addr}
    return jsonify(record)
