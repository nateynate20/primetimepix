# Remove the test_email function, keep only:
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from apps.games.models import Game
from django.contrib.auth.models import User

def landing_page(request):
    context = {
        'total_games': Game.objects.count(),
        'primetime_games': sum(1 for g in Game.objects.all() if g.is_primetime),
        'active_users': User.objects.filter(is_active=True).count(),
    }
    return render(request, 'nflpix/landing_page.html', context)


@staff_member_required
def sentry_debug(request):
    """Deliberately raise an error so we can verify Sentry captures 500s.

    Staff-only (non-staff are redirected to the admin login), so random
    visitors and bots can't trigger it. Safe to leave in place or remove
    once Sentry delivery is confirmed.
    """
    raise RuntimeError("Sentry debug test error from /debug/sentry-test/")