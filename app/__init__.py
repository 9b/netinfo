"""."""
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

APP_NAME = 'netinfo'

app_base = os.path.dirname(os.path.realpath(__file__))

mongo = PyMongo()
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
    """Check if the ASN database should be updated."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        config = json.load(open('%s/resources/config.json' % app_base))
        delta = (now_time() - load_time(config['last_update'])).seconds
        if delta > 1800:
            app.config['ASNDB'] = pyasn.pyasn('%s/resources/current' % app_base,
                                              as_names_file='%s/resources/as_names.json' % app_base)
            app.config['ASNDB'].loaded = config['file']
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
    return True


def create_app(debug=False):
    """Create an application context with blueprints."""
    state = housekeeping()
    if not state:
        sys.exit(1)
    app = Flask(__name__, static_folder='./resources')
    app.config['SECRET_KEY'] = 'RYVl4Fg3n1JLDaxWyr1m'
    app.config['MONGO_DBNAME'] = 'netinfo'
    app.config['MONGO_HOST'] = 'localhost'
    app.config['ASNDB'] = pyasn.pyasn('%s/resources/current' % app_base,
                                      as_names_file='%s/resources/as_names.json' % app_base)
    app.config['ASNDB'].loaded = None
    muri = "mongodb://%s:27017/%s" % (app.config['MONGO_HOST'],
                                      app.config['MONGO_DBNAME'])
    app.config['MONGO_URI'] = muri
    mongo.init_app(app)
    app.config.update(
        CELERY_BROKER_URL='redis://localhost:6379',
        CELERY_RESULT_BACKEND='redis://localhost:6379',
        CELERYBEAT_SCHEDULE={
            # 'heartbeat': {
            #     'task': 'heartbeat',
            #     'schedule': crontab(minute='*')
            # },
            'fetch': {
                'task': 'fetch',
                'schedule': crontab(minute='*/5')
            }
        }
    )
    celery.conf.update(app.config)

    config_file = '%s/resources/config.json' % app_base
    if not os.path.exists(config_file):
        config = {'file': None, 'last_update': None}
        json.dump(config, open(config_file, 'w'), indent=4)

    from .core import core as core_blueprint
    app.register_blueprint(core_blueprint)
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, server_error)

    return app
