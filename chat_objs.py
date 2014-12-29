
from google.appengine.api import channel
from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel

import logging

import json

from chat_settings import ChatSettings

class ChatURL(object):
    OHOME = '/home'
    OMODIFY = '/home/modify'
    OONCALL = '/home/oncall'
    OOFFCALL = '/home/offcall'
    OCHAT = '/home/chat'
    OCHECK_LOGIN = '/home/check_login'
    OLOGIN = '/login'
    OLOGIN_FINISH = '/login_finish'
    OLOGOUT = '/logout'    
    CALL = '/call'
    ROOM = '/room'
    ROOM_CONNECTED = '/room/connected'
    ROOM_MSG = '/room/msg'
    

def get_channel_id(user_id, room_id):
    # TODO: this needs to be secret? if so do a hash?
    return str(user_id) + str(room_id)
    
class ChatUser(polymodel.PolyModel):    
    screenname = ndb.StringProperty()
        
    def chat_msg_rate_limit_check(self):
        return True
        
    def is_operator(self):
        return False
        
class ChatOperator(ChatUser):
    is_on_call = ndb.BooleanProperty(default=False)
    on_call_channel_token = ndb.StringProperty()
    
    def is_operator(self):
        return True
        
    @staticmethod
    def room_url_from_call(call):        
        room = call.caller_channel.room_key.get()
        if not room:
            return None
            
        return "{0}?room_name={1}".format(ChatURL.OCHAT, room.key.id())
        
    @staticmethod
    def gauth_user_id(raw_user_id):    
        # in case we do non-google logins
        return "gplus{0}".format(raw_user_id)
        
    @staticmethod
    def gauth_get_or_insert(user_id):        
        o = ChatOperator.get_or_insert(user_id)
        if o:            
            o.put()
        return o

    @staticmethod
    def call_operators(call):
        # TODO: handle if room_url_from_call fails for some reason
        msg = json.dumps({
            'call_info' : call.key.id(),
            'call_url' : ChatOperator.room_url_from_call(call),
        })
        operators = ChatOperator.query(ChatOperator.is_on_call==True).fetch()
        for operator in operators:
            channel.send_message(operator.on_call_channel_token, msg)       
        
    def update_rooms(self):
        # find all rooms this user is in and refresh screen name lists
        rooms = ChatRoom.query(ChatRoom.chat_channels.user_key == self.key).fetch(20)
        if not rooms:
            return
            
        for r in rooms:
            r.refresh_screennames()            
        
    def refresh_channel(self):
        # TODO save the date and do date compare
        # also this is bad but meh        
        if not self.on_call_channel_token:
            self.on_call_channel_token = channel.create_channel(self.key.id(), 2*60)
            self.put()
        
class ChatCaller(ChatUser):
    @staticmethod
    def factory(remote_addr, screenname):
        # TODO: need to make this multiple for people behind proxies/NATs (though unlikely for now)
        caller = ChatCaller.get_or_insert(remote_addr, screenname=screenname)
        if not caller:
            return None
            
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
    
    def has_user_key(self, user_key):
        c = self.get_channel_for_user(user_key)
        if c:
            return c
        else:
            return None
            
    # better have called room.put() and user.put() at least once so key is valid
    def add_user_key(self, user_key):
        # TODO: this should be a transaction probably
        c = self.has_user_key(user_key)
        if c:
            return c.channel_token, False
        
        tok = channel.create_channel(get_channel_id(user_key.id(), self.key.id()))
        if not tok:            
            return None, None
            
        self.chat_channels.append(ChatChannel(
            user_key = user_key,
            room_key = self.key,
            channel_token = tok)
        )
        self.put()
        
        return tok, True
    
    def get_channel_for_user(self, user_key):
        for c in self.chat_channels:
            if c.user_key == user_key:
                return c
        return None
        
    def get_screennames(self):
        def user_key_to_screenname(user_key):
            u = user_key.get()
            if u:
                return u.screenname
            else:
                return ""
            
        return [ user_key_to_screenname(c.user_key) for c in self.chat_channels ]

    def refresh_screennames(self):        
        msg = json.dumps({
            'content' : 'screennames',
            'screennames' : self.get_screennames(),
        })
        for chan in self.chat_channels:
            channel.send_message(chan.channel_token, msg)  

    def announce_user(self, user):
        msg = json.dumps({
            'content' : 'announcement',
            'line' : '{0} has joined the room'.format(user.screenname),
        })
        for chan in self.chat_channels:
            if chan.user_key != user.key:
                channel.send_message(chan.channel_token, msg)  
            
class ChatCall(ndb.Model):
    caller_channel = ndb.StructuredProperty(ChatChannel)

    def get_url(self):
        return '/room?room={0}&call={1}'.format(self.caller_channel.room_key.id(), self.key.id())
    
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
        tok, newly_added = room.add_user_key(caller_key)
        if not tok:
            # call isn't put, should not need delete
            room.key.delete()
            return
        
        call.caller_channel = ChatChannel(user_key = caller_key,
                                   room_key = room.key,
                                   channel_token = tok)
        call.put()
        return call