from google.appengine.api import channel
from google.appengine.ext import ndb
from google.appengine.api import users
from google.appengine.ext.webapp.util import run_wsgi_app

import json
import logging
import webapp2
from webapp2_extras import sessions

from chat_utils import *
from chat_objs import *

def get_post_data(handler):
    o = handler.get_operator()
    if not o:
        logging.info("beep0")
        return None, None
        
    data = handler.get_post_data_default()
    if not data:        
        return None, None
        
    return o, data
        
class OHomePage(BaseHandler):    
    def get(self): 
        o = self.get_operator()
        if not o:
            self.logout_operator()
            self.redirect('/')
            return

        vals = {            
            'operator_name' : o.key.id(),
            'on_call_channel_token' : o.on_call_channel_token,
            'screenname' : o.screenname,
        }
        self.template_response('templates/operator.html', vals)

class OModifyPage(BaseHandler):
    def post(self):
        o = self.get_operator()
        if not o:
            self.redirect('/')
            return
        
        screenname = self.request.get('screenname')
        if screenname:
            o.screenname = sanitize_screenname(screenname)
            o.put()            
            o.update_rooms()

        self.redirect(ChatURL.OHOME)

class OOnCallPage(BaseHandler):
    def post(self): 
        o = self.get_operator()
        if not o:
            self.error(406)
            return
        
        o.refresh_channel()
        o.is_on_call = True
        o.put()
        
        self.response.write(json.dumps(o.on_call_channel_token))

class OOffCallPage(BaseHandler):
    def post(self):
        o = self.get_operator()
        if not o:
            self.error(404)
            return
            
        o.is_on_call = False
        o.put()
        
        self.response.write("off call")

class OChatPage(BaseHandler):
    def get(self):
        o = self.get_operator()      
        if not o:
            self.error(405)
            return
            
        try:
            room_name = long(self.request.get('room_name'))
        except Exception as e:
            room_name = None
            
        if not room_name:
            self.error(406)
            return

        room = ChatRoom.get_by_id(room_name)
        if not room:
            self.error(407)
            return

        tok, newly_added = room.add_user_key(o.key)
        if not tok:
            self.error(408)
            return
            
        vals = {
            'room_name' : room_name,
            'channel_token' : tok,
        }           
        return self.template_response('templates/chat_room.html', vals)

class OCheckLoginPage(BaseHandler):
    def get(self):
        o = self.get_operator()
        if not o:
            self.error(412)
            return
            
        self.response.write("you are indeed logged in")
        
app = webapp2.WSGIApplication(
    [
        (ChatURL.OHOME, OHomePage),
        (ChatURL.OMODIFY, OModifyPage),
        (ChatURL.OONCALL, OOnCallPage),
        (ChatURL.OOFFCALL, OOffCallPage),
        (ChatURL.OCHAT, OChatPage),
        (ChatURL.OCHECK_LOGIN, OCheckLoginPage),
    ],
    debug=True, config=CONFIG)

def main():
    run_wsgi_app(app)

if __name__ == "__main__":
    main()