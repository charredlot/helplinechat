
class SiteSettings(object):
    @classmethod
    def verify_email(cls, email):
        return email.endswith('@translifeline.org')
