
import datetime

from hidden_settings import HiddenSettings

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
    CALL_PREP = '/call_prep'
    ROOM = '/room'
    ROOM_CONNECTED = '/room/connected'
    ROOM_MSG = '/room/msg'    
    
class ChatSettings(object):
    GAUTH_URI = 'https://accounts.google.com/o/oauth2/auth'
    GAUTH_TOKEN_URI = 'https://accounts.google.com/o/oauth2/token'
    GAUTH_SCOPE = 'https://www.googleapis.com/auth/profile'
    GAUTH_PROFILE_URI = 'https://www.googleapis.com/oauth2/v1/userinfo'
    GAUTH_TOKEN_VERIFY = 'https://www.googleapis.com/oauth2/v1/tokeninfo'
    GAUTH_RECAPTCHA_URI = 'https://www.google.com/recaptcha/api/siteverify'
    GAUTH_ISS = 'accounts.google.com'
    CHAT_CHANNEL_MINUTES = 4*60
    OPERATOR_CHANNEL_MINUTES = 2*60
    OPERATOR_CHANNEL_DURATION = datetime.timedelta(minutes=2*60 - 2)
    CHAT_MSG_INTERVAL = datetime.timedelta(seconds=10)
    CHAT_MSG_PER_INTERVAL = 10
    GAUTH_CLIENT_ID = HiddenSettings.GAUTH_CLIENT_ID
    GAUTH_CLIENT_SECRET = HiddenSettings.GAUTH_CLIENT_SECRET
    GAUTH_RECAPTCHA_SECRET = HiddenSettings.GAUTH_RECAPTCHA_SECRET
    GAUTH_RECAPTCHA_SITE_KEY = HiddenSettings.GAUTH_RECAPTCHA_SITE_KEY
    LOG_CHAT_MSGS=True
    # debug goes here    
    DEBUG_SKIP_CAPTCHA = False
