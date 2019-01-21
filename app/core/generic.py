"""Generic calls within the application."""
import json
import os

from . import core
from .. import mongo, logger, celery
from flask import (
    render_template, redirect, url_for, jsonify, request, Response
)
from flask import current_app as app


APP_BASE = os.path.dirname(os.path.realpath(__file__)).replace('/core', '')


@core.route('/')
def root():
    """Render the index page."""
    config = json.load(open('%s/resources/config.json' % APP_BASE))
    return render_template('index.html', config=config)


@core.route('/force-geo')
def force_geo():
    """Force a fetching of the latest database."""
    logger.debug("Fetch the latest copy of the database")
    celery.send_task('fetch-geoip')
    return jsonify({'success': True,
                    'message': 'This will take a few minutes to complete'})


@core.route('/force-db')
def force_db():
    """Force a fetching of the latest database."""
    logger.debug("Fetch the latest copy of the database")
    celery.send_task('fetch-geoip')
    celery.send_task('fetch-as-names')
    celery.send_task('fetch-rib', kwargs={'force': True})
    return jsonify({'success': True,
                    'message': 'This will take a few minutes to complete'})
