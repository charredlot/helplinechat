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
        return None, None
    
    user = ChatCaller.get_by_id(user_id)
    if not user:
        return None, None
    
    data = handler.request.get('data')
    if not data:
        return None, None
        
    try:
        data = json.loads(data)
    except Exception as e:
        return None, None
    
    return user, data
    
class ChannelOpenPage(BaseHandler):
    def post(self):
        user, data = get_channel_post(self)
        if not user:
            self.error(404)
            return           

        msg = { 
            'is_server' : True,
            'line' : user.screen_name + " just connected",
        }

        tok = user.channel_token
        if tok:        
            channel.send_message(tok, json.dumps(msg))
        else:
            self.error(404) 

class ChannelMsgPage(BaseHandler):
    def post(self):
        user, data = get_channel_post(self)
        if not user:
            self.error(405)
            return
            
        if not 'line' in data:
            self.error(408)
            return
            
        msg = json.dumps({ 
            'from' : user.screen_name,
            'line' : data['line'],
        })
                
        room = user.room_key.get()
        if room:
            logging.info(room.user_list)
            for user_key in room.user_list:            
                recipient = user_key.get()
                if recipient:
                    tok = recipient.channel_token
                    if tok:
                        channel.send_message(tok, msg)
                        
class NopPage(BaseHandler):
    def get(self):
        self.response.write('nop')
        
    def post(self):
        return


        
app = webapp2.WSGIApplication(
    [
        ('/channel/opened', ChannelOpenPage),
        ('/channel/msg', ChannelMsgPage),
        ('/channel/test', NopPage),
        ('/_ah/channel/connected/', NopPage),
        ('/_ah/channel/disconnected/', NopPage),
    ],
    debug=True, config=CONFIG)
run_wsgi_app(app)    
    