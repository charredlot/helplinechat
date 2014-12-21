
import webapp2
from webapp2_extras import sessions

CONFIG = {
    'webapp2_extras.sessions' : {
        'secret_key': 'my-super-secret-key',
    }
}

def get_channel_token(user_id, room_name):
    # TODO: this needs to be secret?
    return str(user_id) + str(room_name)

class BaseHandler(webapp2.RequestHandler):
    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)
        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        # Returns a session using the default cookie key.
        return self.session_store.get_session()
        