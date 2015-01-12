
import datetime

class ChatSettings(object):
    GAUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
    GAUTH_TOKEN_URI = 'https://accounts.google.com/o/oauth2/token'
    GAUTH_SCOPE = 'https://www.googleapis.com/auth/profile'
    GAUTH_PROFILE_URI = 'https://www.googleapis.com/oauth2/v1/userinfo'
    GAUTH_CLIENT_ID = '959104160060-5bnte4j2416us7pu91qua26gf8j9c3b4.apps.googleusercontent.com'
    GAUTH_CLIENT_SECRET = 'anmrc4JrRPdNtqtkWVcY6izm'
    GAUTH_TOKEN_VERIFY = 'https://www.googleapis.com/oauth2/v1/tokeninfo'
    GAUTH_ISS = 'accounts.google.com'
    GAUTH_REDIRECT_URI_PREFIX = 'http://localhost:8080'
    CHAT_CHANNEL_MINUTES = 4*60
    OPERATOR_CHANNEL_MINUTES = 2*60
    OPERATOR_CHANNEL_DURATION = datetime.timedelta(minutes=2*60 - 2)
    CHAT_MSG_INTERVAL = datetime.timedelta(seconds=10)
    CHAT_MSG_PER_INTERVAL = 10
