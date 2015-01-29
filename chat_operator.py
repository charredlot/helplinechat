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
from chat_settings import ChatSettings, ChatURL
        
class OHomePage(BaseHandler):    
    def get(self): 
        o = self.get_operator()
        if not o:
            self.logout_operator()
            self.redirect('/')
            return

        csrf_token = self.set_csrf_token()
        vals = {            
            'operator_name' : o.key.id(),
            'on_call_channel_token' : o.on_call_channel_token,
            'screenname' : o.screenname,
            'is_on_call' : o.is_on_call,
            'csrf_token' : csrf_token,
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
        logging.info(self.request.get('data'))
        o, data = self.get_operator_data()
        if not o:
            self.error(406)
            return
        
        if not self.verify_csrf_token(data):
            return

        o.go_on_call()
        
        self.response.write(json.dumps(o.on_call_channel_token))

class OOffCallPage(BaseHandler):
    def post(self):
        o = self.get_operator()
        if not o:
            self.error(404)
            return
        
        o.go_off_call()    
        
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
        
        ChatOperator.announce_call(call)
        
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
        # TODO: allow shadowing
        self.response.write("Sorry, the call's been answered already! You can close this window")

class ORefreshCallsPage(BaseHandler):
    def post(self):
        o, data = self.get_operator_data();
        if not o:
            self.error(405)
            return

        if not self.verify_csrf_token(data):
            return

        # Expecting javascript Date toISOString, but who knows if we can rely on it
        last_call_datetime = datetime.datetime.strptime(data['last_call_datetime'],
            '%Y-%m-%dT%H:%M:%S.%fZ')
        o.refresh_calls(last_call_datetime)
        
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
