# Remove the test_email function, keep only:
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.core import signing
from apps.games.models import Game
from django.contrib.auth.models import User

def landing_page(request):
    context = {
        'total_games': Game.objects.count(),
        'primetime_games': sum(1 for g in Game.objects.all() if g.is_primetime),
        'active_users': User.objects.filter(is_active=True).count(),
    }
    return render(request, 'nflpix/landing_page.html', context)


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