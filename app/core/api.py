"""Generic calls within the application."""
import os
import pyasn

from . import core
from .. import mongo, logger, celery, check_asndb
from flask import (jsonify, request)
from flask import current_app as app
from netaddr import IPAddress, IPNetwork


@core.route('/lookup', methods=['GET'])
@check_asndb
def lookup():
    """Enrich IP address."""
    ip_addr = request.args.get('ip')
    data = app.config['ASNDB'].lookup(ip_addr)
    __ip_addr = IPAddress(ip_addr)
    __network = IPNetwork(data[1])
    record = {'as_num': int(data[0]), 'network': data[1],
              'as_name': str(app.config['ASNDB'].get_as_name(data[0])),
              'ip': ip_addr, 'ip_version': int(__ip_addr.version),
              'ip_hex': hex(__ip_addr),
              'network_broadcast': str(__network.broadcast),
              'network_netmask': str(__network.netmask),
              'network_hostmask': str(__network.hostmask),
              'network_size': int(__network.size)}
    if app.config['DEBUG']:
        mongo.db.queries.insert(record)
        _ = record.pop('_id', None)
    return jsonify(record)


@core.route('/network-addresses', methods=['GET'])
def network_addresses():
    """Enrich IP address."""
    cidr = request.args.get('cidr')
    __network = IPNetwork(cidr)
    addresses = [str(x) for x in list(__network)]
    record = {'cidr': cidr, 'network_addresses': addresses,
              'network_size': int(__network.size)}
    if app.config['DEBUG']:
        mongo.db.queries.insert(record)
        _ = record.pop('_id', None)
    return jsonify(record)


@core.route('/prefixes', methods=['GET'])
@check_asndb
def prefixes():
    """Enrich IP address."""
    asn = request.args.get('asn')
    data = app.config['ASNDB'].get_as_prefixes(asn)
    record = {'as_num': int(asn), 'prefixes': list(data), 'count': len(data)}
    if app.config['DEBUG']:
        mongo.db.queries.insert(record)
        _ = record.pop('_id', None)
    return jsonify(record)


@core.route('/as-name', methods=['GET'])
@check_asndb
def as_name():
    """Enrich IP address."""
    asn = request.args.get('asn')
    record = {'as_name': str(app.config['ASNDB'].get_as_name(int(asn))),
              'as_num': asn}
    if app.config['DEBUG']:
        mongo.db.queries.insert(record)
        _ = record.pop('_id', None)
    return jsonify(record)
