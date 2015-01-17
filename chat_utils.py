import os
import string

import json
import jinja2

import webapp2
from webapp2_extras import sessions

from chat_objs import *

CONFIG = {
    'webapp2_extras.sessions' : {
        'secret_key': 'my-super-secret-key',
    }
}

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)    
def get_template(path):
    return JINJA_ENVIRONMENT.get_template(path)

SCREENNAME_CHARS = {
    
}

def sanitize_screenname(sn):
    if not sn:
        return None
    end = len(sn)
    if end > 200:
        end = 200
    return unicode(jinja2.escape(sn[:end]))


BAD_CHARS = {
    '"'     : "&#34;", 
    '\''    : "&#39;",
    '<'     : "&lt;",
    '>'     : "&gt;",
    '&'     : "&amp;",
    '/'     : "&#47;", 
    '\\'    : "&#92;",
}
def replace_char(c):
    try:
        return BAD_CHARS[c]
    except KeyError:
        return c
     
def sanitize_chat_msg(msg):
    # TODO: use some official library
    end = len(msg)
    if end > 200:
        end = 200
    return unicode(jinja2.escape(msg[:end]))
    
class BaseHandler(webapp2.RequestHandler):
    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)
        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)

    def template_response(self, template_path, vals):
        if not vals:
            vals = dict()
        vals['gauth_scope'] = ChatSettings.GAUTH_SCOPE
        vals['gauth_client_id'] = ChatSettings.GAUTH_CLIENT_ID
        vals['logout_url'] = ChatURL.OLOGOUT
        vals['login_url'] = ChatURL.OLOGIN
        vals['check_login_url'] = ChatURL.OCHECK_LOGIN
        vals['room_connected_url'] = ChatURL.ROOM_CONNECTED
        vals['room_msg_url'] = ChatURL.ROOM_MSG
        t = get_template(template_path)
        self.response.write(t.render(vals))

    def get_chat_user(self):
        user_id = self.session.get('user_id')
        if not user_id:
            return None
        
        return ChatUser.get_by_id(user_id)
        
    def get_operator(self):
        operator_id = self.session.get('user_id')        
        if not operator_id:
            return None
            
        return ChatOperator.get_by_id(operator_id)

    def get_operator_data(self):
        o = self.get_operator()
        if not o:
            return None, None
            
        data = self.get_post_data_default()
        if not data:        
            return None, None
            
        return o, data

    def get_post_data_default(self):
        raw_data = self.request.get('data')
        if not raw_data:
            logging.info("beep1")
            return None
            
        try:
            data = json.loads(raw_data)
        except Exception as e:        
            logging.info("beep2 {0} {1}".format(e, raw_data))
            return None
            
        return data

    def login_operator(self, user_id):
        self.session['user_id'] = user_id        
        
    def logout_operator(self):
        operator_id = self.session.get('user_id')
        if operator_id:
            del self.session['user_id']
 
    @webapp2.cached_property
    def session(self):
        # Returns a session using the default cookie key.
        return self.session_store.get_session()
 
RAND_CHARSET = string.ascii_lowercase + string.digits
def get_rand_string(length):
    return unicode(
        ''.join( 
            (random.choice(RAND_CHARSET) for x in range(length))
        ) 
    )
 
class NopPage(BaseHandler):
    def get(self):
        self.response.write('nop')
        
    def post(self):
        return
        
