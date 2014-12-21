
from google.appengine.api import channel
from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel

import logging

from chat_utils import *

def get_channel_id(user_id, room_id):
    # TODO: this needs to be secret? if so do a hash?
    return str(user_id) + str(room_id)
    
class ChatUser(polymodel.PolyModel):
    screen_name = ndb.StringProperty()

    @staticmethod
    def factory(cls, screen_name, do_put=True):               
        user = cls(screen_name = screen_name)
        if do_put:
            user.put()
        return user

    def clean_up(self):
        self.room.key.delete()

class ChatCaller(ChatUser):
    remote_addr = ndb.StringProperty()
    # every caller gets exactly one room, also use quotes for annoying circular ref issue
    channel_token = ndb.StringProperty()
    room_key = ndb.KeyProperty(kind='ChatRoom')
    
    @staticmethod
    def factory(remote_addr, screen_name):
        room = ChatRoom()
        if not room:
            return None
            
        caller = ChatUser.factory(ChatCaller, screen_name, do_put=False)
        if not caller:
            # TODO: invalidate channel somehow
            room.key.delete()
            return None
        
        # need to put so room.key is there
        room.put()                
        caller.remote_addr = remote_addr
        caller.room_key = room.key
        caller.put()
        
        channel_token = room.user_join(caller)        
        if not channel_token:
            caller.clean_up()
            return None
            
        caller.channel_token = channel_token
        caller.put()        
        return caller
        
class ChatRoom(ndb.Model):
    user_list = ndb.KeyProperty(kind=ChatUser, repeated=True)
    
    # better have called room.put() and user.put() at least once so key is valid
    def user_join(self, user):
        tok = channel.create_channel(get_channel_id(user.key.id(), self.key.id()))
        if not tok:            
            return None
        logging.info('3332sadfds')
        self.user_list.append(user.key)
        self.put()
        
        return tok
        
    @staticmethod
    def room_name_from_key(room_key):
        return room_key.id()
        
    @staticmethod
    def get_rooms():
        return [ ('t1', '/t1'), ('t2', '/asdfads') ] 

        