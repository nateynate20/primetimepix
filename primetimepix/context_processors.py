"""Project-wide template context.

Exposes site metadata and opt-in analytics IDs so the base template can render
the analytics snippet and canonical/OG tags without every view passing them in.
"""
from django.conf import settings


def site_context(request):
    return {
        'SITE_NAME': settings.SITE_NAME,
        'SITE_URL': settings.SITE_URL,
        'GA_MEASUREMENT_ID': getattr(settings, 'GA_MEASUREMENT_ID', ''),
        'PLAUSIBLE_DOMAIN': getattr(settings, 'PLAUSIBLE_DOMAIN', ''),
    }
