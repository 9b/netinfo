"""Generic calls within the application."""
from . import core
from .. import mongo, logger, celery
from flask import (
    render_template, redirect, url_for, jsonify, request, Response
)
from flask import current_app as app
from bson.objectid import ObjectId


@core.route('/')
def root():
    """Render the index page."""
    return "Here to serve."


@core.route('/async-test')
def heartbeat_example():
    """Run an async job in the background."""
    logger.debug("Executing the heartbeat task and returning")
    celery.send_task('heartbeat')
    return render_template('index.html', name="HEARTBEAT")


@core.route('/check-db')
def check_db():
    """Run an async job in the background."""
    logger.debug("Executing the heartbeat task and returning")
    celery.send_task('fetch')
    return


@core.route('/init')
def init():
    """Run an async job in the background."""
    logger.debug("Executing the heartbeat task and returning")
    celery.send_task('fetch')
    return
