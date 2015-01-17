from google.appengine.ext import ndb
from google.appengine.ext.webapp.util import run_wsgi_app

import json
import logging
import webapp2

from chat_utils import *
from chat_objs import *
        
class ChannelConnectedPage(BaseHandler):
    def post(self):
        channel_user_id = self.request.get("from")
        if not channel_user_id:
            return

        logging.info("{0} connected".format(channel_user_id))
        ChatOperator.channel_connected(channel_user_id)

class ChannelDisconnectedPage(BaseHandler):
    def post(self):
        channel_user_id = self.request.get("from")
        if not channel_user_id:
            return

        logging.info("{0} disconnected".format(channel_user_id))
        ChatOperator.channel_disconnected(channel_user_id)

app = webapp2.WSGIApplication(
    [
        ('/_ah/channel/connected/', ChannelConnectedPage),
        ('/_ah/channel/disconnected/', ChannelDisconnectedPage),
    ],
    debug=True, config=CONFIG)

def main():
    run_wsgi_app(app)

if __name__ == "__main__":
    main()
    
