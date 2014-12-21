from google.appengine.api import users
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import memcache

import logging
import webapp2
from webapp2_extras import sessions

import string
import random
import os
import unicodedata

import jinja2

from chat_utils import *
from chat_objs import *

_URL_CHAT = '/chat'

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
        vals = {
            'call_url' : _URL_CHAT,
            'rooms' : ChatRoom.get_rooms(),
        }
        t = get_template('templates/index.html')
        self.response.write(t.render(vals))

        
        
class ChatPage(BaseHandler):
    def get(self):
        del self.session['user_id']
        cuser = None
        user_id = self.session.get('user_id')
        if user_id:
            cuser = ChatCaller.get_by_id(user_id)

        screen_name = self.request.get('screen_name')               
        if cuser:
            if screen_name and not (screen_name == cuser.screen_name):
                cuser.screen_name = screen_name
                cuser.put()
        else:
            if not screen_name:
                screen_name = ''
                
            cuser = ChatCaller.factory(self.request.remote_addr, screen_name)
            if cuser:
                self.session['user_id'] = cuser.key.id()
        
        if not cuser:
            self.error(404)
            return
            
        vals = {
            'room_name' : ChatRoom.room_name_from_key(cuser.room_key),            
            'channel_token' : cuser.channel_token,
        }        
        t = get_template('templates/chat_room.html')
        self.response.write(t.render(vals))
               
application = webapp2.WSGIApplication(
    [
        ('/', MainPage),
        ('/dup', MainPage),
        (_URL_CHAT, ChatPage),
    ],
    debug=True, config=CONFIG)

def main():
    run_wsgi_app(application)


if __name__ == "__main__":
    main()
