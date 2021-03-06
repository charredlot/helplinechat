
from google.appengine.api import channel
from google.appengine.ext import ndb
from google.appengine.ext.ndb import polymodel

import datetime

import json
import logging

from chat_settings import ChatSettings, ChatURL
from site_settings import SiteSettings

def to_iso_format_hack(dt):    
    # python datetime is bullshit and doesn't add the Z for iso
    # so isoformat does not actually return isoformat
    # this causes problems in firefox, which interprets it as a local date
    s = dt.isoformat()
    if (not s.endswith('Z')) and \
        (not s.endswith('+00:00')) and \
        (not s.endswith('-00:00')):
        return s + 'Z'
    else:
        return s

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
    
    @classmethod
    def channel_connected(cls, channel_user_id):
        args = channel_user_id.split('_')
        u = ChatUser.get_by_id(args[0])
        if u:
            u.handle_channel_connected(args)

    @classmethod
    def channel_disconnected(cls, channel_user_id):
        args = channel_user_id.split('_')
        u = ChatUser.get_by_id(args[0])
        if u:
            u.handle_channel_disconnected(args)

    def handle_channel_connected(self, vals):
        logging.info("connect not implemented?")

    def handle_channel_disconnected(self, vals):
        logging.info("disconnect not implemented?")
    
class ChatOperator(ChatUser):
    is_on_call = ndb.BooleanProperty(default=False)
    on_call_channel_token = ndb.StringProperty()
    on_call_channel_token_expiration = ndb.DateTimeProperty(auto_now_add=True)
    calls_answered = ndb.IntegerProperty(default=0)

    def is_operator(self):
        return True

    @ndb.transactional
    def answered_call(self):
        self.calls_answered += 1
        self.put()

    def answer_call(self, call_id):
        call = ChatCall.get_by_id(call_id)
        if not call:
            return None, None, None
        
        room, tok = call.answer(self)
        if not room:
            return None, None, None
    
        self.answered_call()

        return call, room, tok

    def refresh_calls(self, last_call_datetime):
        for c in ChatCall.calls_since(last_call_datetime):
            msg = c.to_operator_json(is_historic=True)
            channel.send_message(self.on_call_channel_token, msg) 
        
    @classmethod
    def gauth_user_id(cls, raw_user_id):    
        # in case we do non-google logins
        return "gplus{0}".format(raw_user_id)
        
    @classmethod
    def gauth_get_or_insert(cls, user_id):        
        o = ChatOperator.get_or_insert(user_id)
        if o:            
            o.put()
        return o

    @classmethod
    def announce_call(cls, call):
        msg = call.to_operator_json()
        operators = cls.query(cls.is_on_call==True).fetch()
        for operator in operators:
            channel.send_message(operator.on_call_channel_token, msg) 

    @classmethod
    def verify_email(cls, email):
        return SiteSettings.verify_email(email)

    def to_on_call_channel_user_id(self):
        return str(self.key.id()) + '_oncall' 

    def update_rooms(self):
        # find all rooms this user is in and refresh screen name lists
        rooms = ChatRoom.query(ChatRoom.chat_channels.user_key == self.key).fetch(20)
        if not rooms:
            return
            
        for r in rooms:
            r.refresh_screennames()            
    
    @ndb.transactional
    def go_on_call(self, check_channel=True):
        # TODO save the date and do date compare
        # also this is bad but meh
        if check_channel:
            t = datetime.datetime.utcnow()
            if (not self.on_call_channel_token) or (t >= self.on_call_channel_token_expiration):
                self.on_call_channel_token = channel.create_channel(self.to_on_call_channel_user_id(),
                        ChatSettings.OPERATOR_CHANNEL_MINUTES)
                self.on_call_channel_token_expiration = t + \
                    ChatSettings.OPERATOR_CHANNEL_DURATION
        self.is_on_call = True
        self.put()

    @ndb.transactional
    def go_off_call(self):
        self.is_on_call = False
        self.put()
        
    def handle_channel_connected(self, vals):
        if vals[1] == 'oncall':
            # sometimes channel disconnects in dev server
            # TODO: not sure if it's dev server nonsense or local bug
            self.is_on_call = True
            self.put()
        return

    def handle_channel_disconnected(self, vals):
        if vals[1] == 'oncall':
            self.go_off_call()
        else:
            room = ChatRoom.get_by_id(long(vals[1]))
            if room:
                room.remove_user(self)

class ChatCaller(ChatUser):
    def remote_addr(self):
        s = str(self.key.id())
        return s[len('caller'):]
        
    @classmethod
    def form_user_id(cls, remote_addr):
        return 'caller{0}'.format(remote_addr)

    @classmethod
    def caller_get_or_insert(cls, remote_addr, screenname):
        # TODO: need to make this multiple for people behind proxies/NATs (though unlikely for now)
        if not screenname:
            screenname = ''
        caller = cls.get_or_insert(ChatCaller.form_user_id(remote_addr), screenname=screenname)
        if not caller:
            return None
            
        caller.put()
   
        return caller
        
    def handle_channel_connected(self, vals):
        pass

    def handle_channel_disconnected(self, vals):
        room = ChatRoom.get_by_id(long(vals[1]))
        if room:
            room.remove_user(self)

class ChatChannel(ndb.Model):
    user_key = ndb.KeyProperty(kind=ChatUser)
    room_key = ndb.KeyProperty(kind='ChatRoom')
    channel_token = ndb.StringProperty()
        
class ChatRoom(polymodel.PolyModel):    
    chat_channels = ndb.StructuredProperty(ChatChannel, repeated=True)
    parent_call = ndb.KeyProperty(kind='ChatCall', default=None)
 
    def has_user_key(self, user_key):
        c = self.get_channel_for_user(user_key)
        if c:
            return c
        else:
            return None

    @ndb.transactional
    def remove_user_key_t(self, user_key):
        remove_index = None
        for i, c in enumerate(self.chat_channels):
            if c.user_key == user_key:
                remove_index = i
                break
        if remove_index is not None:
            del self.chat_channels[remove_index]
            self.put()

    def remove_user(self, user):
        self.remove_user_key_t(user.key)
        self.announce_user_leave(user)
            
    # better have called room.put() and user.put() at least once so key is valid
    @ndb.transactional
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
    
    def get_channel_id(self, user_key):
        return '{0}_{1}'.format(user_key.id(), self.key.id()) 

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

    def announce_user_join(self, user):
        msg = json.dumps({
            'content' : 'announcement',
            'line' : u'{0} has joined the room'.format(user.screenname),
        })
        for chan in self.chat_channels:
            if chan.user_key != user.key:
                channel.send_message(chan.channel_token, msg)  

    def announce_user_leave(self, user):
        msg = json.dumps({
            'content' : 'announcement',
            'line' : u'{0} has left the room'.format(user.screenname),
        })
        for chan in self.chat_channels:
            if chan.user_key != user.key:
                channel.send_message(chan.channel_token, msg)  
            
class ChatCall(ndb.Model):
    caller_channel = ndb.StructuredProperty(ChatChannel)
    call_datetime = ndb.DateTimeProperty(auto_now_add=True)    
    answered_datetime = ndb.DateTimeProperty(default=None)
    answered_by = ndb.KeyProperty(kind=ChatOperator, default=None)

    def caller_url(self):
        return '/room?room={0}&call={1}'.format(self.caller_channel.room_key.id(), self.key.id())

    def operator_url(self):
        return "{0}?call_id={1}".format(ChatURL.OANSWER, self.key.id())
    
    def to_operator_json(self, is_historic = False): 
        msg = {
            'call_id' : self.key.id(),
            'call_url' : self.operator_url(),
            'call_date' : to_iso_format_hack(self.call_datetime),
        }
        if is_historic:
            msg['is_historic'] = 1
        if not self.answered_datetime is None:
            msg['call_answered'] = str(self.answered_datetime)

        return json.dumps(msg)

    @ndb.transactional
    def mark_answered(self, operator):
        if self.answered_by is None:
            self.answered_by = operator.key
            self.put()
            return True
        elif self.answered_by == operator.key:
            return True
        else:
            return False
        
    def answer(self, operator):
        try:
            won = self.mark_answered(operator)
        except:
            logging.info('{0}: operator {1} call {2}'.format(e, operator, call))
            won = False

        if not won:
            return None, None
            
        room = self.caller_channel.room_key.get()
        if not room:
            logging.info('no room')
            return None, None

        try:
            tok, added = room.add_user_key(operator.key)
        except Exception as e:
            # could be transaction failure
            logging.info('{0}: room {1} operator {2}'.format(e, room, operator))
            tok = None
        
        if not tok:
            return None, None      
        
        self.answered_datetime = datetime.datetime.utcnow()
        self.put()    
        return room, tok

    @classmethod
    def calls_since(cls, last_call_datetime):
        # get 20 most recent, but sort from earliest time
        return sorted(
            cls.query(cls.call_datetime > last_call_datetime).order(-cls.call_datetime).fetch(20),
            key=lambda c: c.call_datetime)
        
    @classmethod
    def factory(cls, caller_key):
        call = ChatCall()
        if not call:
            return None
            
        room = ChatRoom()
        if not room:
            # call isn't put, so should be okay?
            return None

        call.put() # so call.key is valid
        room.parent_call = call.key
        room.put() # so room.key is valid

        tok, newly_added = room.add_user_key(caller_key)
        if not tok:
            call.key.delete()
            room.key.delete()
            return
        
        call.caller_channel = ChatChannel(user_key = caller_key,
                                   room_key = room.key,
                                   channel_token = tok)
        call.put()
        return call

class ChatMsg(ndb.Model):
    user_key = ndb.KeyProperty(kind=ChatUser) 
    room_key = ndb.KeyProperty(kind=ChatRoom)
    msg = ndb.StringProperty()
    sent_datetime = ndb.DateTimeProperty(auto_now_add=True) 
