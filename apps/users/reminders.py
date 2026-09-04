"""Shared helpers for the email reminder system.

Frequency capping (marketing best practice): a user should get at most one
"awareness" reminder — the weekly slate digest or a game's day-before nudge —
per calendar day. Game-day urgency reminders (morning-of, hours-before) are the
highest-value conversion emails and are never capped.
"""
from datetime import datetime, timedelta

import pytz
from django.utils import timezone

EASTERN = pytz.timezone('US/Eastern')

# Digest-style nudges that count toward the one-per-day cap.
AWARENESS_TYPES = ('weekly', 'day_before')


def awareness_email_sent_today(user, now=None):
    """Return True if the user already got a weekly/day-before reminder today (ET).

    Days are bucketed in US/Eastern so the cap lines up with when people
    actually read email, regardless of the server timezone.
    """
    now = now or timezone.now()
    now_et = now.astimezone(EASTERN)
    start_et = EASTERN.localize(datetime(now_et.year, now_et.month, now_et.day))
    end_et = start_et + timedelta(days=1)

    # ReminderLog.sent_at is stored in UTC; compare against the ET day window.
    from apps.users.models import ReminderLog
    return ReminderLog.objects.filter(
        user=user,
        reminder_type__in=AWARENESS_TYPES,
        sent_at__gte=start_et.astimezone(pytz.UTC),
        sent_at__lt=end_et.astimezone(pytz.UTC),
    ).exists()


def _rank_of(user, ordered_members):
    for i, member in enumerate(ordered_members, start=1):
        if member == user:
            return i
    return None


def weekly_recap_for_user(user, week, season):
    """Build a 'how you did last week' recap payload, or None if there's nothing
    worth sending.

    Returns None when the user isn't in any league or has no graded picks for
    the given week — a recap with an empty record is just noise, so we skip it.

    The recap is scoped to the user's *primary* league (the one they've graded
    the most picks in) to keep the email punchy. Rank movement compares the
    cumulative standings through `week` vs through `week - 1`.
    """
    from django.db.models import Sum, Count
    from apps.picks.models import Pick
    from apps.leagues.models import League

    leagues = list(League.objects.filter(members=user, is_approved=True))
    if not leagues:
        return None

    def graded_count(lg):
        return Pick.objects.filter(
            user=user, league=lg, is_correct__isnull=False
        ).count()

    league = max(leagues, key=graded_count)

    week_picks = Pick.objects.filter(
        user=user, league=league,
        game__week=week, game__season=season,
        is_correct__isnull=False,
    )
    wins = week_picks.filter(is_correct=True).count()
    losses = week_picks.filter(is_correct=False).count()
    if wins + losses == 0:
        return None

    week_points = week_picks.filter(is_correct=True).aggregate(
        t=Sum('points')
    )['t'] or 0

    members = list(league.members.all())

    def cumulative_key(member, upto_week):
        agg = Pick.objects.filter(
            user=member, league=league, game__season=season,
            game__week__lte=upto_week, is_correct=True,
        ).aggregate(pts=Sum('points'), w=Count('id'))
        return (agg['pts'] or 0, agg['w'] or 0)

    now_ranked = sorted(members, key=lambda m: cumulative_key(m, week), reverse=True)
    prev_ranked = sorted(members, key=lambda m: cumulative_key(m, week - 1), reverse=True)
    rank_now = _rank_of(user, now_ranked)
    rank_prev = _rank_of(user, prev_ranked)
    movement = (rank_prev - rank_now) if (rank_prev and rank_now) else 0

    return {
        'league': league,
        'week': week,
        'wins': wins,
        'losses': losses,
        'record': f"{wins}-{losses}",
        'week_points': week_points,
        'rank': rank_now,
        'total_members': len(members),
        'movement': movement,  # +N climbed, -N dropped, 0 held
        'movement_abs': abs(movement),
    }
