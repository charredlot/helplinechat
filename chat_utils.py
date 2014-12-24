
import os

import jinja2
import webapp2
from webapp2_extras import sessions

from chat_objs import *

CONFIG = {
    'webapp2_extras.sessions' : {
        'secret_key': 'my-super-secret-key',
    }
}

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)    
def get_template(path):
    return JINJA_ENVIRONMENT.get_template(path)

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

    def template_response(self, template_path, vals):
        t = get_template(template_path)
        self.response.write(t.render(vals))

    def get_operator(self):
        operator_id = self.session.get('user_id')
        if not operator_id:
            return None
        
        return ChatOperator.get_by_id(operator_id)
        
    def logout_operator(self):
        operator_id = self.session.get('user_id')
        if operator_id:
            del self.session['user_id']
 
    @webapp2.cached_property
    def session(self):
        # Returns a session using the default cookie key.
        return self.session_store.get_session()
        