from google.appengine.ext import ndb

class ChatRoom(ndb.Model):
    room_name = None
    users = None
    def __init__(self, room_name):
        self.users = set()
        self.room_name = room_name
        
    def connected(self, user_id):
        self.users.add(user_id)

    @staticmethod
    def get_rooms():
        return [ ('t1', '/t1'), ('t2', '/asdfads') ] 
        