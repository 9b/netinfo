"""."""
import geoip2.database
import json
import logging
import os
import pyasn
import socket
import sys

from celery import Celery
from celery.schedules import crontab
from flask import Flask, redirect, url_for, render_template, request
from flask_pymongo import PyMongo
from functools import wraps
from flask import current_app as app
from app.utils.helpers import now_time, load_time
from werkzeug.contrib.cache import MemcachedCache

APP_NAME = 'netinfo'
APP_BASE = os.path.dirname(os.path.realpath(__file__))
REFRESH_TIME = 1800

mongo = PyMongo()
cache = MemcachedCache(['127.0.0.1:11211'])
celery = Celery(APP_NAME)
logger = logging.getLogger(APP_NAME)
logger.setLevel(logging.DEBUG)
shandler = logging.StreamHandler(sys.stdout)
fmt = '\033[1;32m%(levelname)-5s %(module)s:%(funcName)s():'
fmt += '%(lineno)d %(asctime)s\033[0m| %(message)s'
shandler.setFormatter(logging.Formatter(fmt))
logger.addHandler(shandler)


def server_error(e):
    """500 handler."""
    logger.error("500 triggered: %s" % (str(e)))
    return "500"


def page_not_found(e):
    """404 handler."""
    logger.info("404 triggered: Path %s" % (request.path))
    return "404"


def check_asndb(f):
    """Check if the ASN database should be updated.

    This wraps any call to the API to ensure the version of the database is
    always the most current. The PyASN database remains in a global variable
    exposed by Flask. Celery will update the configuration file after a new
    RIB has been downloaded and processed. That serves as the trigger data in
    order to reload the database or not.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        config = json.load(open('%s/resources/config.json' % APP_BASE))
        delta = (now_time() - load_time(config['asn']['last_update'])).seconds
        if delta > REFRESH_TIME or not app.config['ASNDB']:
            try:
                app.config['ASNDB'] = pyasn.pyasn('%s/resources/asn/current' % APP_BASE,
                                                  as_names_file='%s/resources/asn/as_names.json' % APP_BASE)
                app.config['ASNDB'].loaded = config['asn']['last_rib_file']
            except Exception as e:
                raise Exception("Database has not been initialized.")
        return f(*args, **kwargs)
    return decorated_function


def check_geoip(f):
    """Check if the GeoIP database should be updated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        config = json.load(open('%s/resources/config.json' % APP_BASE))
        delta = (now_time() - load_time(config['geoip']['last_update'])).seconds
        if delta > REFRESH_TIME or not app.config['GEOIPDB']:
            try:
                app.config['GEOIPDB'] = geoip2.database.Reader('%s/resources/geoip/current' % APP_BASE)
            except Exception as e:
                print(e)
                raise Exception("Database has not been initialized.")
        return f(*args, **kwargs)
    return decorated_function


def housekeeping():
    """Check if the services we need are running."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('0.0.0.0', 6379))
        raise Exception("[!] Redis does not appear to be running")
        return False
    except Exception as e:
        pass

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('0.0.0.0', 5672))
        raise Exception("[!] RabbitMQ does not appear to be running")
        return False
    except Exception as e:
        pass

    return True


def create_app(debug=False):
    """Create an application context with blueprints."""
    state = housekeeping()
    if not state:
        sys.exit(1)
    app = Flask(__name__, static_folder='./resources')
    app.config['SECRET_KEY'] = 'tRSn3mh2bY3@1$W2T9aQ'
    app.config['MONGO_DBNAME'] = 'netinfo'
    app.config['MONGO_HOST'] = 'localhost'
    app.config['ASNDB'] = None
    app.config['GEOIPDB'] = None
    app.config['DEBUG'] = debug
    muri = "mongodb://%s:27017/%s" % (app.config['MONGO_HOST'],
                                      app.config['MONGO_DBNAME'])
    app.config['MONGO_URI'] = muri
    mongo.init_app(app)
    app.config.update(
        CELERY_BROKER_URL='redis://localhost:6379',
        CELERY_RESULT_BACKEND='redis://localhost:6379',
        CELERYBEAT_SCHEDULE={
            'fetch-rib': {
                'task': 'fetch-rib',
                'schedule': crontab(minute='*/5')
            },
            'fetch-as-name': {
                'task': 'fetch-as-names',
                'schedule': crontab(hour="*/12")
            },
            'fetch-geo': {
                'task': 'fetch_geoip',
                'schedule': crontab(hour=7, minute=30, day_of_week=1)
            }
        }
    )
    celery.conf.update(app.config)

    config_file = '%s/resources/config.json' % APP_BASE
    if not os.path.exists(config_file):
        config = {'asn': {'last_rib_file': None, 'last_update': None},
                  'geoip': {'last_update': None}}
        json.dump(config, open(config_file, 'w'), indent=4)

    from .core import core as core_blueprint
    app.register_blueprint(core_blueprint)
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, server_error)

    return app
