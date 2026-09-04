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
