from google.appengine.api import channel
from google.appengine.ext import ndb
from google.appengine.ext.webapp.util import run_wsgi_app

import json
import logging
import webapp2
from webapp2_extras import sessions

from chat_utils import *
from chat_objs import *
        
def get_room_info(handler, page=""):
    user = handler.get_chat_user()
    if not user:
        logging.info("page {0} could not find user".format(page))
        return None, None, None
    
    data = handler.request.get('data')
    if not data:
        logging.info("page {0} user {1} did not have data".format(page, user))
        return None, None, None
        
    try:
        data = json.loads(data)
    except Exception as e:
        logging.info("page {0} user {1} malformed data {2} {3}".format(page, user, e, data))
        return None, None, None
    
    try:
        room_name = data['room_name']
        room = ChatRoom.get_by_id(long(room_name))
    except Exception as e:
        logging.info("page {0} user {1} data doesn't have room_name {2}".format(page, user_id, data))
        return None, None, None
    
    if not room:
        logging.info("page {0} user {1} couldn't find room {2} {3}".format(page, user_id, room_name, type(room_name)))
        return None, None, None
    
    return user, room, data

class RoomPage(BaseHandler):
    def get(self):
        user = self.get_chat_user()
        if not user:
            self.error(501)
            return

        try:
            room_id = long(self.request.get('room'))
            call_id = long(self.request.get('call'))
        except Exception as e:
            logging.info("error {0} getting room and call ids".format(e))
            room_id = None
            call_id = None
            
        if (not room_id) or (not call_id):
            self.error(502)
            return                       
        
        call = ChatCall.get_by_id(call_id)
        if not call or not (call.caller_channel.user_key == user.key):
            logging.info("call and user mismatch {0} {1}".format(call, user))
            self.error(503)
            return
            
        if not (call.caller_channel.room_key.id() == room_id):
            logging.info("call and room mismatch {0} {1}".format(call, room_key))
            self.error(504)
            return
            
        vals = {
            'room_name' : call.caller_channel.room_key.id(),
            'channel_token' : call.caller_channel.channel_token,
        }
        self.template_response('templates/chat_room.html', vals)
    
class RoomConnectedPage(BaseHandler):
    def post(self):
        user, room, data = get_room_info(self, "connected")
        if not user:
            self.error(405)
            return    

        # this is the connected for the channel
        # the clients should have already added themselves to the room
        # operator through /home/chat
        # caller through /call
        if not room.has_user_key(user.key):            
            self.error(406)
            return
        
        room.announce_user(user)
        room.refresh_screennames()
        
class RoomMsgPage(BaseHandler):
    def post(self):
        cuser, room, data = get_room_info(self, "msg")
        if not cuser:
            self.error(405)
            return
            
        if not 'line' in data:
            self.error(406)
            return

        if not cuser.chat_msg_rate_limit_check():
            logging.info('chat msg rate limit exceeded {0}'.format(cuser))
            return
                          
        line = sanitize_chat_msg(data['line'])  
        if not line:
            return
        
        msg = json.dumps({
            'content' : 'user_msg',
            'from' : cuser.screenname,
            'line' : line,
        })
  
        for c in room.chat_channels:
            channel.send_message(c.channel_token, msg)
                  
app = webapp2.WSGIApplication(
    [
        (ChatURL.ROOM, RoomPage),
        (ChatURL.ROOM_CONNECTED, RoomConnectedPage), 
        (ChatURL.ROOM_MSG, RoomMsgPage),
    ],
    debug=True, config=CONFIG)

def main():
    run_wsgi_app(app)

if __name__ == "__main__":
    main()
    
