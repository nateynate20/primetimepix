"""Signed, login-free unsubscribe links for marketing emails.

Recipients click these from their inbox while logged out, so we can't rely on
the session to identify them. Instead we embed a tamper-proof signed token
(Django's `signing`, keyed off `SECRET_KEY`) that resolves back to the user.

Tokens intentionally have no expiry — an unsubscribe link must keep working for
the life of the email, which is the CAN-SPAM expectation.
"""
from django.conf import settings
from django.core import signing
from django.urls import reverse

# Namespacing salt so these tokens can't be replayed against another signer.
SALT = 'primetimepix.email.unsubscribe'


def make_token(user):
    """Return a signed, URL-safe token that resolves back to `user`."""
    return signing.dumps(user.pk, salt=SALT)


def read_token(token, max_age=None):
    """Return the user PK encoded in `token`.

    Raises `signing.BadSignature` (or `SignatureExpired` when `max_age` is set)
    if the token was tampered with. Callers should catch `signing.BadSignature`.
    """
    return signing.loads(token, salt=SALT, max_age=max_age)


def unsubscribe_url(user):
    """Absolute one-click unsubscribe URL for this user's marketing emails."""
    return f"{settings.SITE_URL}{reverse('unsubscribe', args=[make_token(user)])}"
