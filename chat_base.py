from google.appengine.api import users
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import urlfetch

import logging
import webapp2
from webapp2_extras import sessions

import string
import random
import os

import base64
import json
import unicodedata
import urllib

from chat_utils import *
from chat_objs import *
from chat_settings import ChatSettings

def base64_pad(s):
    return s + ('=' * (4 - (len(s) % 4)))

def jwt_decode(input_jwt):
    # https://github.com/googlewallet/jwt-decoder-python
    try:
        # TODO: figure out what normal form is all about
        input_jwt = unicodedata.normalize('NFKD', input_jwt).encode(
            'ascii', 'ignore')
        
        items = input_jwt.split('.')
        jwt_header = json.loads(base64.urlsafe_b64decode(base64_pad(items[0])))
        jwt_claims = json.loads(base64.urlsafe_b64decode(base64_pad(items[1])))
        jwt_sig = items[2]
    except Exception as e:
        logging.info("JWT {0} gave error {1}".format(input_jwt, e))
        return None, None, None
    else:
        return jwt_header, jwt_claims, jwt_sig

def jwt_verify_id_token(id_token):
    # TODO: google suggests downloading the google certs periodically and verifying it locally
    verify_url = ChatSettings.GAUTH_TOKEN_VERIFY + "?id_token={0}".format(id_token)
    try:
        res = urlfetch.fetch(verify_url)
    except Exception as e:
        self.error(504)
        return False
    
    if res.status_code != 200:
        return False
   
    return True
 
def jwt_verify_claims(claims):
    try:
        return (('sub' in claims) and
                (claims['aud'] == ChatSettings.GAUTH_CLIENT_ID) and
                (claims['iss'] == ChatSettings.GAUTH_ISS))
    except:
        return False
        
class MainPage(BaseHandler):
    def get(self):        
        vals = {        
            'call_url' : ChatURL.CALL,
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

        screenname = self.request.get('screenname')
        if screenname:
            screenname = sanitize_screenname(screenname)
            
        if cuser:
            if screenname and (screenname != cuser.screenname):
                cuser.screenname = screenname
                cuser.put()
        else:
            if not screenname:
                screenname = ''
                
            cuser = ChatCaller.factory(self.request.remote_addr, screenname)
            if cuser:
                self.session['user_id'] = cuser.key.id()
        
        if not cuser:
            self.error(504)
            return
        
        call = ChatCall.factory(cuser.key)
        if not call:
            self.error(505)
            return
            
        ChatOperator.call_operators(call)

        self.redirect(call.get_url())

class LoginPage(BaseHandler):
    def post(self):
        data = self.get_post_data_default()
        if not data:
            self.error(501)
            return
            
        try:
            id_token = data['id_token']
        except KeyError:
            self.error(502)
            return
            
        if not jwt_verify_id_token(id_token):
            logging.info("bad jwt id_token {0}".format(id_token))
            return
            
        jwt_header, jwt_claims, jwt_sig = jwt_decode(id_token)
        if not jwt_header:
            self.error(503)
            return

        if not jwt_verify_claims(jwt_claims):
            logging.info("bad jwt claims {0}".format(jwt_claims))
            self.error(504)
            return        
        
        user_id = ChatOperator.gauth_user_id(jwt_claims['sub'])        
        if not ChatOperator.gauth_get_or_insert(user_id):
            self.error(505)
            return
        
        self.login_operator(user_id)
        self.redirect(ChatURL.OHOME)
        
class LogoutPage(BaseHandler):
    def post(self):
        self.logout_operator()            
        self.redirect('/')
 
application = webapp2.WSGIApplication(
    [
        ('/', MainPage),
        ('/dup', MainPage),     
        (ChatURL.CALL, CallPage),
        (ChatURL.OLOGIN, LoginPage),
        (ChatURL.OLOGOUT, LogoutPage),
    ],
    debug=True, config=CONFIG)

def main():
    run_wsgi_app(application)


if __name__ == "__main__":
    main()
