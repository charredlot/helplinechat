
from google.appengine.api import channel
from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel

import datetime

import json
import logging

from chat_settings import ChatSettings

class ChatURL(object):
    OHOME = '/home'
    OMODIFY = '/home/modify'
    OONCALL = '/home/oncall'
    OOFFCALL = '/home/offcall'
    OANSWER = '/home/answer'
    OCALLANSWERED = '/home/call_answered'
    OREFRESHCALLS = '/home/refresh_calls'
    OCHECK_LOGIN = '/home/check_login'
    OLOGIN = '/login'
    OLOGIN_FINISH = '/login_finish'
    OLOGOUT = '/logout'    
    CALL = '/call'
    ROOM = '/room'
    ROOM_CONNECTED = '/room/connected'
    ROOM_MSG = '/room/msg'    
    
class ChatUser(polymodel.PolyModel):    
    screenname = ndb.StringProperty()
    next_chat_msg_credit = ndb.DateTimeProperty(auto_now_add=True)
    chat_msg_credit = ndb.IntegerProperty(default=0)
     
    @ndb.transactional
    def chat_msg_rate_limit_check(self):
        if self.chat_msg_credit == 0:
            t = datetime.datetime.utcnow()
            if t < self.next_chat_msg_credit:
                return False
            else:
                self.next_chat_msg_credit = t + ChatSettings.CHAT_MSG_INTERVAL
                self.chat_msg_credit = ChatSettings.CHAT_MSG_PER_INTERVAL - 1
                self.put()
                return True
        self.chat_msg_credit -= 1
        self.put()
        return True
        
    def is_operator(self):
        return False
        
class ChatOperator(ChatUser):
    is_on_call = ndb.BooleanProperty(default=False)
    on_call_channel_token = ndb.StringProperty()
    on_call_channel_token_expiration = ndb.DateTimeProperty(auto_now_add=True)
 
    def is_operator(self):
        return True

    def answer_call(self, call_id):
        call = ChatCall.get_by_id(call_id)
        if not call:
            return None, None, None
        
        room, tok = call.answer(self)
        if not room:
            return None, None, None
            
        return call, room, tok
        
    @staticmethod
    def call_url(call):            
        return "{0}?call_id={1}".format(ChatURL.OANSWER, call.key.id())
        
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
    def announce_call(call, answered='false'):
        msg = json.dumps({
            'call_id' : call.key.id(),
            'call_url' : ChatOperator.call_url(call),
            'call_answered' : answered,
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
    
    @ndb.transactional 
    def go_on_call(self):
        # TODO save the date and do date compare
        # also this is bad but meh        
        t = datetime.datetime.utcnow()
        if self.on_call_channel_token and (t < self.on_call_channel_token_expiration):
            return
        self.on_call_channel_token = channel.create_channel(self.key.id(),
                ChatSettings.OPERATOR_CHANNEL_MINUTES)
        self.on_call_channel_token_expiration = t + \
            ChatSettings.OPERATOR_CHANNEL_DURATION
        self.is_on_call = True
        self.put()
        
        
class ChatCaller(ChatUser):
    def remote_addr(self):
        return self.key.id()
        
    @staticmethod
    def caller_get_or_insert(remote_addr, screenname):
        # TODO: need to make this multiple for people behind proxies/NATs (though unlikely for now)
        if not screenname:
            screenname = ''
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
        
        tok = channel.create_channel(self.get_channel_id(user_key), ChatSettings.CHAT_CHANNEL_MINUTES)        
        if not tok:            
            return None, None
            
        self.chat_channels.append(ChatChannel(
            user_key = user_key,
            room_key = self.key,
            channel_token = tok)
        )
        self.put()
        
        return tok, True
    
    @ndb.transactional(xg=True)
    def add_operator(self, operator, channel_token):
        for c in self.chat_channels:
            if c.user_key == operator.key:
                c.channel_token = channel_token
                self.put()
                return True
            else:
                cuser = c.user_key.get()
                if cuser and cuser.is_operator():
                    return False                    
                
        self.chat_channels.append(ChatChannel(
            user_key = operator.key,
            room_key = self.key,
            channel_token = channel_token)
        )       
        self.put()
        return True
                         
    def get_channel_id(self, user_key):
        return str(user_key.id()) + str(self.key.id())        
    
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
            'line' : u'{0} has joined the room'.format(user.screenname),
        })
        for chan in self.chat_channels:
            if chan.user_key != user.key:
                channel.send_message(chan.channel_token, msg)  
            
class ChatCall(ndb.Model):
    caller_channel = ndb.StructuredProperty(ChatChannel)
    
    def get_url(self):
        return '/room?room={0}&call={1}'.format(self.caller_channel.room_key.id(), self.key.id())

    def answer(self, operator):        
        room = self.caller_channel.room_key.get()
        if not room:
            logging.info('no room')
            return None, None
            
        tok = channel.create_channel(room.get_channel_id(operator.key), ChatSettings.OPERATOR_CHANNEL_MINUTES)
        if not tok:            
            # TODO: remove from room
            logging.info('no channel')
            return None, None       
        
        try:
            added = room.add_operator(operator, tok)
        except Exception as e:
            # could be transaction failure
            logging.info('{0}: room {1} operator {2}'.format(e, room, operator))
            added = False
        
        if not added:
            # TODO: invalidate token?
            return None, None      
            
        return room, tok
        
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
