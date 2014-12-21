from google.appengine.api import channel
from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext.webapp.util import run_wsgi_app

import json
import logging
import webapp2
from webapp2_extras import sessions

from chat_utils import *
from chat_objs import *

def get_channel_post(handler):
    user_id = handler.session.get('user_id')
    if not user_id:
        return None, None, None
    
    data = handler.request.get('data')
    if not data:
        return None, None, None
        
    data = json.loads(data)
    if not 'room_name' in data:
        return None, None, None

    room_name = data['room_name']    
    room = memcache.get(room_name)
    if not room:
        return None, None, None
    
    return user_id, data, room
    
class ChannelOpenPage(BaseHandler):
    def post(self):
        user_id, data, room = get_channel_post(self)
        if not user_id:
            self.error(404)
            return
            
        room.connected(user_id)
        memcache.add(room.room_name, room)
        
        msg = { 
            'is_server' : True,
            'line' : user_id + " just connected",
        }

        tok = get_channel_token(user_id, room.room_name)
        channel.send_message(tok, json.dumps(msg))

class ChannelMsgPage(BaseHandler):
    def post(self):
        user_id, data, room = get_channel_post(self)
        if not user_id:
            self.error(407)
            return 
            
        if not 'line' in data:
            self.error(408)
            return
            
        msg = { 
            'from' : user_id,
            'line' : data['line'],
        }
        
        tok = get_channel_token(user_id, room.room_name)
        channel.send_message(tok, json.dumps(msg))
        for user_id in room.users:                        
            tok = get_channel_token(user_id, room.room_name)
            logging.info(tok)
            logging.info(msg)
            channel.send_message(tok, json.dumps(msg))
        
class TestPage(BaseHandler):
    def get(self):
        self.response.write('test')
        
app = webapp2.WSGIApplication(
    [
        ('/channel/opened', ChannelOpenPage),
        ('/channel/msg', ChannelMsgPage),
        ('/channel/test', TestPage),
    ],
    debug=True, config=CONFIG)
run_wsgi_app(app)    
    