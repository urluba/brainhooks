import logging
import os
import time
from flask_restplus import Namespace, Resource, fields, reqparse
from flask import request, json
from qhue import Bridge

api = Namespace('plex', 'Plex')

try:
    logger
except NameError:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(name)s - %(levelname)s - %(message)s',
    )
    logger = logging.getLogger(__name__)

class Webhook(object):
    '''Actions handler'''
    # Player(s) allowed to interact
    uuid_whitelist = []
    # Light to switch on/off
    phue_lights = []
    # Philips Hue Bridge settings
    phue_bridge = os.environ.get('PHUE_BRIDGE_IP')
    phue_user = os.environ.get('PHUE_BRIDGE_USER')

    # Swagger doc
    post = reqparse.RequestParser()
    post.add_argument('payload', location='form')       # WTF !!

    @classmethod
    def is_valid_player(cls, player):
        ''' Verify we want to interact with calling player'''
        logger.debug('Player: {}'.format(player))
        player_uuid = player.get('uuid')
        player_local = player.get('local', False)
        player_ip = player.get('publicAddress', '')

        # Player must be known and declared
        if not player_uuid in cls.uuid_whitelist:
            logger.info('Player "{}" is not whitelisted.'.format(player_uuid))
            return False

        # If playback is not local, do nothing
        if not (
                player_local
                or
                player_ip == '127.0.0.1'    # Loopback is not seen as local...
            ):
            logger.info('Remote playback ({local}, {ip}), doing nothing'.format(
                local=player_local,
                ip=player_ip
            ))
            return False

        return True

    @classmethod
    def is_hue_time(cls):
        # Dirty one :)
        null, null, null, hour, null, null, null, null, null = time.localtime()
        logger.debug('Local hour {}'.format(hour))

        # We want to play with lights at night -between 20H and 06H-
        if hour > 19:
            return True

        if hour < 6:
            return True

        logger.info('Not the time to play with the light')
        return False

    @classmethod
    def media_played(cls):
        logger.debug('Start hook')
        if cls.is_hue_time():
            logger.debug('Launching Hue action')
            my_hue = Bridge(cls.phue_bridge, cls.phue_user)
            my_lights = my_hue.lights

            for index in cls.phue_lights:
                my_lights[index].state(on=False)

        return {
            'status': 200,
            'message': 'Unfinished event'
        }

    @classmethod
    def media_stopped(cls):
        logger.debug('stop hook')
        if cls.is_hue_time():
            logger.debug('Launching Hue action')
            my_hue = Bridge(cls.phue_bridge, cls.phue_user)
            my_lights = my_hue.lights

            for index in cls.phue_lights:
                my_lights[index].state(on=True, bri=80)

        return {
            'status': 200,
            'message': 'Unfinished event'
        }

    @classmethod
    def media_resumed(cls):
        logger.debug('resume hook')

    @classmethod
    def media_paused(cls):
        logger.debug('pause hook')

    @classmethod
    def media_pass(cls):
        logger.debug('pass hook')

        return {
            'status': 400,
            'message': 'Unmanaged event'
        }

@api.route('/webhook')
class WebhookView(Resource):
    # @api.expect(Webhook.model, validate=False)
    @api.expect(Webhook.post)
    def post(self):
        '''called by Plex Webhook'''
        # It's indeed a JSON in a form...
        # args = request.get_json()
        args = json.loads(request.form.get('payload', '{}'))

        if not args:
            logger.error('No payload received')

            return {
                'status': 400,
                'message': 'no payload'
            }

        # logger.debug('Received payload: {}'.format(args))

        # Extract some infos from payload
        event = args.get('event')
        mediatitle = args.get('Metadata', {}).get('title', 'Unknown')
        mediatype = args.get('Metadata', {}).get('type', '')

        # Check player authorization
        if not Webhook.is_valid_player(args.get('Player', {})):
            return {
                'status': 200,
                'message': 'nothing to do'
            }

        # Act only form movies/tv shows
        if (mediatype != "movie") and (mediatype != "episode"):
            logger.info('{} is neither movie or tvshow'.format(mediatitle))
            return {
                'status': 200,
                'message': 'nothing to do'
            }

        logger.info('Launching actions "{action}" for "{title}"'.format(
            action=event,
            title=mediatitle
        ))

        # Call action from Webhook class
        try:
            response = {
                'media.play': Webhook.media_played,
                'media.resume': Webhook.media_played,
                'media.stop': Webhook.media_stopped,
                'media.pause': Webhook.media_stopped,
                # 'media.pause': Webhook.media_paused,
                # 'media.resume': Webhook.media_resumed,
            }.get(event, Webhook.media_pass)()
        except Exception as e:
            logger.exception(e)
            return {
                'status': 500,
                'message': 'shit happens'
            }

        return response
