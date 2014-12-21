from google.appengine.api import users
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import channel
from google.appengine.api import memcache

import string
import random
import os
import unicodedata

import jinja2
import webapp2
from webapp2_extras import sessions

from chat_utils import *
from chat_objs import *

_URL_CHAT = '/chat'
JS_VERSION_HACK = '206'

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)    
def get_template(path):
    return JINJA_ENVIRONMENT.get_template(path)

RAND_CHARSET = string.ascii_lowercase + string.digits
def get_rand_string(length):
    return unicode(
        ''.join( 
            (random.choice(RAND_CHARSET) for x in range(length))
        ) 
    )
    
class MainPage(BaseHandler):
    def get(self):        
        room_name = get_rand_string(10)
        room = ChatRoom(room_name)
        room_url = '{0}?room={1}'.format(_URL_CHAT, room_name)

        memcache.add(room_name, room)
        
        user_id = self.session.get('user_id')
        if not user_id:
            self.session['user_id'] = get_rand_string(10)
        
        vals = {
            'room_url' : room_url,
            'rooms' : ChatRoom.get_rooms(),
        }        
        t = get_template('templates/index.html')
        self.response.write(t.render(vals))

class ChatPage(BaseHandler):
    def get(self):
        user_id = self.session.get('user_id')        
        room_name = self.request.get('room')
        
        if (not user_id) or (not room_name):
            self.error(404)
            return
            
        token = channel.create_channel(get_channel_token(user_id, room_name))
        if not token:
            self.error(404)
            return
            
        vals = {
            'channel_token' : token,
            'room_name' : room_name,
            'version_hack' : JS_VERSION_HACK,
        }        
        t = get_template('templates/chat_room.html')
        self.response.write(t.render(vals))
        
class NopPage(BaseHandler):
    def get(self):
        self.response.write('nop')
        
    def post(self):
        return
        
application = webapp2.WSGIApplication(
    [
        ('/', MainPage),
        ('/dup', MainPage),
        (_URL_CHAT, ChatPage),        
        ('/_ah/channel/connected/', NopPage),
        ('/_ah/channel/disconnected/', NopPage),
    ],
    debug=True, config=CONFIG)

def main():
    run_wsgi_app(application)


if __name__ == "__main__":
    main()
