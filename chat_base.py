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

from chat_utils import *
from chat_objs import *

_URL_LOGIN = '/login'
_URL_LOGOUT = '/logout'
_URL_DASHBOARD = '/home'
_URL_MODIFY = _URL_DASHBOARD + '/modify'
_URL_CALL = '/call'

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
            'call_url' : _URL_CALL,
            'rooms' : ChatRoom.get_rooms(),
        }
        self.template_response('templates/index.html', vals)
        
class CallPage(BaseHandler):
    def get(self):        
        cuser = None
        user_id = self.session.get('user_id')
        if user_id:
            # TODO: reset user id just for ease of testing
            del self.session['user_id']
            #cuser = ChatCaller.get_by_id(user_id)

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
        
        call = ChatCall.factory(cuser.key)
        
        vals = {
            'room_name' : ChatRoom.room_name_from_key(call.chat_channel.room_key),
            'channel_token' : call.chat_channel.channel_token,
        }
        self.template_response('templates/chat_room.html', vals)
        
class LoginPage(BaseHandler):
    def get(self):
        # TODO: actually do the login
        o = self.get_operator()
        if not o:
            o = ChatOperator.get_or_insert('smooth_operator')
            if not o:
                self.error(404)
                return
            self.session['user_id'] = o.key.id()
        self.redirect(_URL_DASHBOARD)

class LogoutPage(BaseHandler):
    def get(self):
        o = self.get_operator()
        if o:
            self.logout_operator()
        
class DashPage(BaseHandler):    
    def get(self):
        o = self.get_operator()
        if not o:
            # TODO: some kind of error?
            self.redirect('/')
            return

        vals = {
            'operator_name' : o.key.id(),
            'screen_name' : o.screen_name,
        }
        self.template_response('templates/dashboard.html', vals)

class ModifyPage(BaseHandler):
    def post(self):
        o = self.get_operator()
        if not o:
            self.redirect('/')
            return
        
        screen_name = self.request.get('screen_name')
        if screen_name:
            o.screen_name = screen_name
            o.put()

        self.redirect(_URL_DASHBOARD)
 
application = webapp2.WSGIApplication(
    [
        ('/', MainPage),
        ('/dup', MainPage),
        (_URL_LOGIN, LoginPage),
        (_URL_LOGOUT, LogoutPage),
        (_URL_DASHBOARD, DashPage),
        (_URL_CALL, CallPage),
        (_URL_MODIFY, ModifyPage),
    ],
    debug=True, config=CONFIG)

def main():
    run_wsgi_app(application)


if __name__ == "__main__":
    main()
