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
            'is_on_call' : o.is_on_call,
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
        
        o.go_on_call()
        
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

class OAnswerPage(BaseHandler):
    def get(self):
        o = self.get_operator()      
        if not o:
            self.error(405)
            return
            
        try:
            call_id = long(self.request.get('call_id'))
            call, room, channel_token = o.answer_call(call_id)
        except Exception as e:
            logging.info(e)
            call = None
            
        if not call:
            self.redirect(ChatURL.OCALLANSWERED)
            return
        
        ChatOperator.announce_call(call, answered=True)
        
        vals = {
            'room_name' : room.key.id(),            
            'channel_token' : channel_token,
        }           
        return self.template_response('templates/chat_room.html', vals)

class OCheckLoginPage(BaseHandler):
    def get(self):
        o = self.get_operator()
        if not o:
            self.error(412)
            return
            
        self.response.write("you are indeed logged in")

class OCallAnsweredPage(BaseHandler):
    def get(self):
        self.response.write("Sorry, the call's been answered already! You can close this window")

class ORefreshCallsPage(BaseHandler):
    def post(self):
        o = self.get_operator()
        if not o:
            self.error(405)
            return
        
        # TODO: let operator know all the calls they missed       
     
        
app = webapp2.WSGIApplication(
    [
        (ChatURL.OHOME, OHomePage),
        (ChatURL.OMODIFY, OModifyPage),
        (ChatURL.OONCALL, OOnCallPage),
        (ChatURL.OOFFCALL, OOffCallPage),
        (ChatURL.OANSWER, OAnswerPage),
        (ChatURL.OREFRESHCALLS, ORefreshCallsPage),
        (ChatURL.OCALLANSWERED, OCallAnsweredPage),
        (ChatURL.OCHECK_LOGIN, OCheckLoginPage),
    ],
    debug=True, config=CONFIG)

def main():
    run_wsgi_app(app)

if __name__ == "__main__":
    main()
