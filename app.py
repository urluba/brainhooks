import os
import logging

from flask import Flask
from flask_restplus import Api, Resource, Namespace
from waitress import serve

from endpoints.plex import api as plex_api

logger = logging.getLogger('waitress')
logger.setLevel(logging.INFO)

app = Flask(__name__)
app.config['PHUE_BRIDGE_IP'] = os.environ.get('PHUE_BRIDGE_IP')

api = Api(app)
api.add_namespace(plex_api)
logger.info('plex namespace added')
lgtv_api = Namespace('tv', 'TV')
api.add_namespace(lgtv_api)
logger.info('tv namespace added')

if __name__ == '__main__':
    serve(app, listen='*:20000')
    # app.run(host='0.0.0.0', port=20000)

