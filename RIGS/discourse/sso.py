import urllib
from hashlib import sha256
import hmac
from base64 import b64decode, b64encode


class DiscourseSSO:
    def __init__(self, secret_key):
        self.__secret_key = secret_key

    def validate(self, payload, sig):
        payload = urllib.unquote(payload)
        computed_sig = hmac.new(
            self.__secret_key.encode(),
            payload.encode(),
            sha256
        ).hexdigest()
        print(type(computed_sig), type(sig))
        return hmac.compare_digest(unicode(computed_sig), sig)

    def get_nonce(self, payload):
        payload = b64decode(urllib.unquote(payload)).decode()
        d = dict(nonce.split("=") for nonce in payload.split('&'))

        if 'nonce' in d and d['nonce'] != '':
            return d['nonce']
        else:
            raise Exception("Nonce could not be found in payload")

    def get_data(self, payload):
        payload = urllib.unquote(b64decode(urllib.unquote(payload)).decode())
        d = dict(data.split("=") for data in payload.split('&'))

        return d

    def build_login_URL(self, nonce, redirect_uri):
        data = {
            'nonce': nonce,
            'return_sso_url': redirect_uri
        }

        payload = urllib.urlencode(data)
        payload = b64encode(payload.encode())
        sig = hmac.new(self.__secret_key.encode(), payload, sha256).hexdigest()

        return '/session/sso_provider?' + urllib.urlencode({'sso': payload, 'sig': sig})
