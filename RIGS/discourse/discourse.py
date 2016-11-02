from __future__ import unicode_literals
from social.backends.base import BaseAuth
from django.conf import settings

from .sso import DiscourseSSO


class DiscourseAssociation(object):
    """ Use Association model to save the nonce by force. """

    def __init__(self, handle, secret='', issued=0, lifetime=0, assoc_type=''):
        self.handle = handle  # as nonce
        self.secret = secret.encode()  # not use
        self.issued = issued  # not use
        self.lifetime = lifetime  # not use
        self.assoc_type = assoc_type  # as state


class DiscourseAuth(BaseAuth):
    """Discourse authentication backend"""
    name = 'discourse'
    secret = settings.DISCOURSE_SSO_SECRET
    host = settings.DISCOURSE_HOST

    EXTRA_DATA = [
        ('username', 'username'),
        ('email', 'email'),
        ('external_id', 'external_id')
    ]

    sso = DiscourseSSO(secret)

    def get_and_store_nonce(self, url):
        # Create a nonce
        nonce = self.strategy.random_string(64)
        # Store the nonce
        association = DiscourseAssociation(nonce)
        self.strategy.storage.association.store(url, association)
        return nonce

    def get_nonce(self, nonce):
        try:
            return self.strategy.storage.association.get(
                server_url=self.host,
                handle=nonce
            )[0]
        except IndexError:
            pass

    def remove_nonce(self, nonce_id):
        self.strategy.storage.association.remove([nonce_id])

    def get_user_id(self, details, response):
        """Return current user id."""

        return int(response['external_id'])

    def get_user_details(self, response):
        """Return user basic information (id and email only)."""

        return {'username': response['username'],
                'email': response['email'],
                'fullname': response['name'].replace('+', ' ') if 'name' in response else '',
                'first_name': '',
                'last_name': ''}

    def auth_url(self):
        """Build and return complete URL."""
        nonce = self.get_and_store_nonce(self.host)

        return self.host + self.sso.build_login_URL(nonce, self.redirect_uri)

    def auth_complete(self, *args, **kwargs):
        """Completes login process, must return user instance."""

        if not self.sso.validate(self.data['sso'], self.data['sig']):
            raise Exception("Someone wants to hack us!")

        nonce = self.sso.get_nonce(self.data['sso'])
        nonce_obj = self.get_nonce(nonce)
        if nonce_obj:
            self.remove_nonce(nonce_obj.id)
        else:
            raise Exception("Nonce does not match!")

        kwargs.update({'response': self.sso.get_data(
            self.data['sso']), 'backend': self})
        return self.strategy.authenticate(*args, **kwargs)
