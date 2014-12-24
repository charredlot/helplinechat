
from google.appengine.api import channel
from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel

import logging

class ChatURL(object):
    LOGIN = '/login'
    LOGOUT = '/logout'
    OHOME = '/home'
    OMODIFY = '/home/modify'
    OONCALL = '/home/oncall'
    OOFFCALL = '/home/offcall'
    OCHAT = '/home/chat'
    CALL = '/call'

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

    def is_operator(self):
        return False
        
class ChatOperator(ChatUser):
    is_on_call = ndb.BooleanProperty()
    on_call_channel_token = ndb.StringProperty()
    def is_operator(self):
        return True
        
    @staticmethod
    def room_url_from_call(call):        
        room = call.caller_channel.room_key.get()
        if not room:
            return None
            
        return "{0}?room_name={1}".format(ChatURL.OCHAT, room.key.id())
    
    def refresh_channel(self):
        # TODO save the date and do date compare
        # also this is bad but meh        
        if not self.on_call_channel_token:
            self.on_call_channel_token = channel.create_channel(self.key.id(), 24*60)
            self.put()
        
class ChatCaller(ChatUser):
    remote_addr = ndb.StringProperty()   
    
    @staticmethod
    def factory(remote_addr, screen_name):
        caller = ChatUser.factory(ChatCaller, screen_name, do_put=False)
        if not caller:
            return None
            
        caller.remote_addr = remote_addr
        caller.put()
   
        return caller
        
    def clean_up(self):
        self.room.key.delete()

class ChatChannel(ndb.Model):
    user_key = ndb.KeyProperty(kind=ChatUser)
    room_key = ndb.KeyProperty(kind='ChatRoom')
    channel_token = ndb.StringProperty()
        
class ChatRoom(polymodel.PolyModel):    
    chat_channels = ndb.StructuredProperty(ChatChannel, repeated=True)
    
    # better have called room.put() and user.put() at least once so key is valid
    def add_user(self, user_key):
        tok = channel.create_channel(get_channel_id(user_key.id(), self.key.id()))
        if not tok:            
            return None
            
        self.chat_channels.append(ChatChannel(
            user_key = user_key,
            room_key = self.key,
            channel_token = tok)
        )
        self.put()
        
        return tok
    
    def get_channel_for_user(self, user_key):
        for c in self.chat_channels:
            if c.user_key == user_key:
                return c
        return None
        
    def get_screen_names(self):
        def user_key_to_screen_name(user_key):
            u = user_key.get()
            if u:
                return u.screen_name
            else:
                return ""
            
        return [ user_key_to_screen_name(c.user_key) for c in self.chat_channels ]
    
    @staticmethod
    def room_name_from_key(room_key):
        return room_key.id()

    @staticmethod
    def room_from_name(room_name):
        try:
            return ChatRoom.get_by_id(long(room_name))
        except ValueError:
            return None
        
    @staticmethod
    def get_rooms():
        return [ ('t1', '/t1'), ('t2', '/asdfads') ] 

class ChatCall(ndb.Model):
    caller_key = ndb.KeyProperty(kind='ChatCaller')
    caller_channel = ndb.StructuredProperty(ChatChannel)

    def get_url(self):
        return '/room?r=' + self.room_key.id()
    
    @staticmethod
    def factory(caller_key):
        call = ChatCall()
        if not call:
            return None
            
        room = ChatRoom()
        if not room:
            # call isn't put, so should be okay?
            return None
        
        room.put() # so room key is valid
        tok = room.add_user(caller_key)
        if not tok:
            # call isn't put, should not need delete
            room.key.delete()
            return
        
        call.caller_channel = ChatChannel(user_key = caller_key,
                                   room_key = room.key,
                                   channel_token = tok)
        call.put()
        return call