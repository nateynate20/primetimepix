"""Web push delivery (VAPID).

Sends notifications to a user's browser Push subscriptions as a *second channel*
alongside email. Everything here is a no-op unless VAPID keys are configured, so
dev/tests and unconfigured deploys stay quiet.

`_deliver` is the single network seam (imports pywebpush lazily), which keeps
this module importable without the package installed and gives tests one place
to monkeypatch.
"""
import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def push_enabled():
    """True only when both VAPID keys are configured."""
    return bool(getattr(settings, 'VAPID_PUBLIC_KEY', '') and getattr(settings, 'VAPID_PRIVATE_KEY', ''))


def _deliver(subscription_info, payload, vapid_private_key, vapid_claims):
    """Actually hand the message to the push service. Isolated so tests can
    monkeypatch it without needing pywebpush installed or the network."""
    from pywebpush import webpush  # lazy import
    return webpush(
        subscription_info=subscription_info,
        data=payload,
        vapid_private_key=vapid_private_key,
        vapid_claims=vapid_claims,
    )


def send_web_push(user, title, body, url='/dashboard/', tag=None):
    """Push a notification to all of `user`'s subscriptions.

    Returns the number of successful sends. Expired subscriptions (404/410) are
    pruned; other failures are logged and skipped so one bad device can't block
    the rest.
    """
    if not push_enabled():
        return 0

    from apps.users.models import PushSubscription

    subs = list(PushSubscription.objects.filter(user=user))
    if not subs:
        return 0

    payload = json.dumps({'title': title, 'body': body, 'url': url, 'tag': tag})
    claims = {'sub': f"mailto:{getattr(settings, 'VAPID_ADMIN_EMAIL', '')}"}

    sent = 0
    for sub in subs:
        try:
            _deliver(sub.subscription_info(), payload, settings.VAPID_PRIVATE_KEY, dict(claims))
            sent += 1
        except Exception as exc:  # noqa: BLE001 - never let one device break the loop
            status = getattr(getattr(exc, 'response', None), 'status_code', None)
            if status in (404, 410):
                sub.delete()  # subscription is gone — stop trying it
            else:
                logger.warning("Web push failed for %s: %s", user.username, exc)
    return sent
