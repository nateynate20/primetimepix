# Remove the test_email function, keep only:
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.core import signing
from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
from apps.games.models import Game
from django.contrib.auth.models import User

def landing_page(request):
    context = {
        'total_games': Game.objects.count(),
        'primetime_games': sum(1 for g in Game.objects.all() if g.is_primetime),
        'active_users': User.objects.filter(is_active=True).count(),
    }
    return render(request, 'nflpix/landing_page.html', context)


def _site_base(request):
    """Absolute site root for SEO files — prefers SITE_URL, falls back to the
    request host so it's correct in every environment."""
    base = (getattr(settings, 'SITE_URL', '') or '').rstrip('/')
    return base or f"{request.scheme}://{request.get_host()}"


def manifest_webmanifest(request):
    """Web App Manifest — makes the site installable (Add to Home Screen) and
    controls the standalone, full-screen app experience. Rendered as a template
    so icon URLs go through {% static %} (hashed in production)."""
    return render(
        request, 'pwa/manifest.webmanifest',
        content_type='application/manifest+json',
    )


def service_worker(request):
    """Service worker script served from the site root so its scope covers the
    whole origin (a /static/ path would only control /static/). Rendered as a
    template so precached asset URLs resolve to the real (hashed) static files."""
    response = render(
        request, 'pwa/sw.js',
        content_type='application/javascript',
    )
    # Allow root scope even though the file lives behind a view.
    response['Service-Worker-Allowed'] = '/'
    # The SW itself must never be staled by a CDN/browser cache.
    response['Cache-Control'] = 'no-cache'
    return response


def pwa_offline(request):
    """Standalone offline fallback shown by the service worker when a navigation
    fails with no network. Intentionally self-contained (inline styles) so it
    renders without any cached CSS/CDN assets."""
    return render(request, 'pwa/offline.html')


def robots_txt(request):
    """robots.txt — allow crawling of public pages, keep app/admin private, and
    point crawlers at the sitemap."""
    base = _site_base(request)
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /unsubscribe/",
        "Disallow: /users/",
        "Disallow: /picks/",
        "",
        f"Sitemap: {base}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def sitemap_xml(request):
    """Minimal sitemap of the public, indexable pages."""
    base = _site_base(request)
    paths = ['/']
    for name in ('signup', 'login', 'privacy', 'terms'):
        try:
            paths.append(reverse(name))
        except Exception:
            pass
    # De-dupe while preserving order.
    seen, urls = set(), []
    for p in paths:
        if p not in seen:
            seen.add(p)
            urls.append(f"<url><loc>{base}{p}</loc></url>")
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(urls)
        + '</urlset>'
    )
    return HttpResponse(xml, content_type="application/xml")


def privacy_policy(request):
    """Static Privacy Policy page (linked from footer, signup, and emails)."""
    return render(request, 'legal/privacy.html')


def terms_of_service(request):
    """Static Terms of Service page (linked from footer and signup)."""
    return render(request, 'legal/terms.html')


def unsubscribe(request, token=None):
    """One-click unsubscribe from marketing/reminder emails.

    Resolves the recipient from the signed token in the email link (no login
    required); falls back to the logged-in user if the link is untokenized.
    A GET performs the opt-out immediately (standard email UX); passing
    ``?resubscribe=1`` re-enables reminders from the same confirmation page.
    """
    from apps.users.models import Profile
    from apps.users.unsubscribe import read_token

    target_user = None
    if token:
        try:
            target_user = User.objects.filter(pk=read_token(token)).first()
        except signing.BadSignature:
            target_user = None
    elif request.user.is_authenticated:
        target_user = request.user

    resubscribed = False
    if target_user is not None:
        profile = getattr(target_user, 'profile', None)
        if profile is None:
            profile, _ = Profile.objects.get_or_create(
                user=target_user,
                defaults={'team_name': f'{target_user.username}-{target_user.pk}'},
            )
        if request.GET.get('resubscribe'):
            profile.email_reminders_enabled = True
            resubscribed = True
        else:
            profile.email_reminders_enabled = False
        profile.save(update_fields=['email_reminders_enabled'])

    return render(request, 'legal/unsubscribe.html', {
        'target_user': target_user,
        'token': token,
        'resubscribed': resubscribed,
        'success': target_user is not None,
    })


@staff_member_required
def sentry_debug(request):
    """Deliberately raise an error so we can verify Sentry captures 500s.

    Staff-only (non-staff are redirected to the admin login), so random
    visitors and bots can't trigger it. Safe to leave in place or remove
    once Sentry delivery is confirmed.
    """
    raise RuntimeError("Sentry debug test error from /debug/sentry-test/")