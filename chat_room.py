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
    user_id = handler.session.get('user_id')
    if not user_id:
        logging.info("page {0} session does not have user_id".format(page))
        return None, None, None
    
    user = ChatUser.get_by_id(user_id)
    if not user:
        logging.info("page {0} could not find user for {1}".format(page, user_id))
        return None, None, None
    
    data = handler.request.get('data')
    if not data:
        logging.info("page {0} user {1} did not have data".format(page, user_id))
        return None, None, None
        
    try:
        data = json.loads(data)
    except Exception as e:
        logging.info("page {0} user {1} malformed data {2} {3}".format(page, user_id, e, data))
        return None, None, None
    
    try:
        room_name = data['room_name']
        room = ChatRoom.room_from_name(room_name)
    except Exception as e:
        logging.info("page {0} user {1} data doesn't have room_name {2}".format(page, user_id, data))
        return None, None, None
    
    if not room:
        logging.info("page {0} user {1} couldn't find room {2} {3}".format(page, user_id, room_name, type(room_name)))
        return None, None, None
    
    return user, room, data

class RoomConnectedPage(BaseHandler):
    def post(self):
        user, room, data = get_room_info(self, "connected")
        if not user:
            self.error(405)
            return    

        c = room.get_channel_for_user(user.key)
        if not c:
            self.error(406)
            return
            
        msg = json.dumps({
            'content' : 'user_list',
            'users' : room.get_screen_names(),
        })
        channel.send_message(c.channel_token, msg)

BAD_CHARS = frozenset([
    '"', '"', '<', '>', '&', '/', '\\'
])
        
def lol_sanitize(line):
    end = len(line)
    if end > 200:
        end = 200
    return unicode(''.join( (c for c in line[:end] if not c in BAD_CHARS) ))
        

        
class RoomMsgPage(BaseHandler):
    def post(self):
        user, room, data = get_room_info(self, "msg")
        if not user:
            self.error(405)
            return
            
        if not 'line' in data:
            self.error(406)
            return

        logging.info(user)
        logging.info(room)
            
        # TODO: real sanitize and rate-limit msgs
        line = lol_sanitize(data['line'])
        
        msg = json.dumps({
            'content' : 'user_msg',
            'from' : user.screen_name,
            'line' : line,
        })               
        for c in room.chat_channels:
            channel.send_message(c.channel_token, msg)
                        
class NopPage(BaseHandler):
    def get(self):
        self.response.write('nop')
        
    def post(self):
        return
        
app = webapp2.WSGIApplication(
    [
        ('/room/connected', RoomConnectedPage), 
        ('/room/msg', RoomMsgPage),
        ('/_ah/channel/connected/', NopPage),
        ('/_ah/channel/disconnected/', NopPage),
    ],
    debug=True, config=CONFIG)

def main():
    run_wsgi_app(app)

if __name__ == "__main__":
    main()
    