"""Project-wide template context.

Exposes site metadata and opt-in analytics IDs so the base template can render
the analytics snippet and canonical/OG tags without every view passing them in.
"""
import json

from django.conf import settings

from primetimepix.analytics import pop_events


def site_context(request):
    # Pop any server-queued analytics events so the partial can replay them.
    events = pop_events(request)
    return {
        'SITE_NAME': settings.SITE_NAME,
        'SITE_URL': settings.SITE_URL,
        'GA_MEASUREMENT_ID': getattr(settings, 'GA_MEASUREMENT_ID', ''),
        'PLAUSIBLE_DOMAIN': getattr(settings, 'PLAUSIBLE_DOMAIN', ''),
        # Public key is safe to expose; the client needs it to subscribe. Empty
        # string means push is off, and the opt-in UI stays hidden.
        'VAPID_PUBLIC_KEY': getattr(settings, 'VAPID_PUBLIC_KEY', ''),
        # JSON list of {name, props} for the analytics partial to fire on load.
        'ANALYTICS_EVENTS_JSON': json.dumps(events) if events else '',
    }
