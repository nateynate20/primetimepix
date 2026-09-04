from datetime import timedelta
from io import StringIO

import pytest
from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from apps.games.models import Game
from apps.picks.models import Pick
from apps.users.models import Notification, ReminderLog


def _primetime_game(gid, hours_from_now, week=1, status='scheduled'):
    return Game.objects.create(
        game_id=gid, season=2026, week=week, game_type='regular',
        start_time=timezone.now() + timedelta(hours=hours_from_now),
        home_team='Kansas City Chiefs', away_team='Buffalo Bills',
        status=status,
    )


@pytest.mark.django_db
class TestSendPickRemindersTestSend:
    """The --user / --force options let us safely send a real reminder to a
    single account in production without spamming everyone or disturbing the
    genuine scheduled reminders."""

    def _run(self, week, **kwargs):
        out, err = StringIO(), StringIO()
        call_command(
            'send_pick_reminders',
            '--type', 'day_before',
            '--week', str(week),
            stdout=out, stderr=err,
            **kwargs,
        )
        return out.getvalue(), err.getvalue()

    def test_force_user_send_delivers_one_email(self, user, thursday_night_game):
        self._run(thursday_night_game.week, user='testplayer', force=True)
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [user.email]

    def test_force_send_does_not_log_or_notify(self, user, thursday_night_game):
        # A forced test send must leave real scheduling untouched: no
        # ReminderLog (which would suppress the genuine reminder) and no
        # in-app notification.
        self._run(thursday_night_game.week, user='testplayer', force=True)
        assert not ReminderLog.objects.filter(user=user).exists()
        assert not Notification.objects.filter(user=user).exists()

    def test_force_send_repeatable(self, user, thursday_night_game):
        self._run(thursday_night_game.week, user='testplayer', force=True)
        self._run(thursday_night_game.week, user='testplayer', force=True)
        assert len(mail.outbox) == 2  # dedupe bypassed each time

    def test_targeted_user_ignores_disabled_preference(self, user, thursday_night_game):
        user.profile.email_reminders_enabled = False
        user.profile.save()
        self._run(thursday_night_game.week, user='testplayer', force=True)
        assert len(mail.outbox) == 1

    def test_unknown_user_errors_and_sends_nothing(self, thursday_night_game):
        _, err = self._run(thursday_night_game.week, user='ghost', force=True)
        assert 'No active user matches' in err
        assert len(mail.outbox) == 0

    def test_targeting_one_user_does_not_email_others(self, user, second_user, thursday_night_game):
        self._run(thursday_night_game.week, user='testplayer', force=True)
        recipients = [addr for m in mail.outbox for addr in m.to]
        assert recipients == [user.email]
        assert second_user.email not in recipients


@pytest.mark.django_db
class TestPerGameReminders:
    """The scheduled (non-forced) path fires a reminder per specific game whose
    kickoff falls in a day-before / morning-of / hours-before window."""

    @pytest.fixture(autouse=True)
    def _always_primetime(self, monkeypatch):
        # Decouple the tests from the wall-clock primetime slot logic.
        monkeypatch.setattr(Game, 'is_primetime', property(lambda self: True))

    def test_day_before_window_sends_game_specific_reminder(self, user):
        game = _primetime_game('pg_daybefore', hours_from_now=20)
        call_command('send_pick_reminders', '--week', '1', stdout=StringIO())
        assert len(mail.outbox) == 1
        # Subject names the specific matchup, not a week total.
        assert 'Bills' in mail.outbox[0].subject and 'Chiefs' in mail.outbox[0].subject
        assert ReminderLog.objects.filter(
            user=user, game=game, reminder_type='day_before'
        ).exists()

    def test_game_far_out_gets_no_reminder(self, user):
        _primetime_game('pg_far', hours_from_now=24 * 5)
        call_command('send_pick_reminders', '--week', '1', stdout=StringIO())
        assert len(mail.outbox) == 0

    def test_reminder_deduped_per_game(self, user):
        _primetime_game('pg_dedupe', hours_from_now=20)
        call_command('send_pick_reminders', '--week', '1', stdout=StringIO())
        call_command('send_pick_reminders', '--week', '1', stdout=StringIO())
        assert len(mail.outbox) == 1  # second run is deduped

    def test_already_picked_game_is_skipped(self, user, league):
        game = _primetime_game('pg_picked', hours_from_now=20)
        Pick.objects.create(user=user, game=game, league=league, picked_team=game.home_team)
        call_command('send_pick_reminders', '--week', '1', stdout=StringIO())
        assert len(mail.outbox) == 0

    def test_each_upcoming_game_gets_its_own_reminder(self, user):
        _primetime_game('pg_a', hours_from_now=20)   # day_before window
        _primetime_game('pg_b', hours_from_now=2)    # hours_before window
        call_command('send_pick_reminders', '--week', '1', stdout=StringIO())
        assert len(mail.outbox) == 2
        assert ReminderLog.objects.filter(user=user, reminder_type='day_before').exists()
        assert ReminderLog.objects.filter(user=user, reminder_type='hours_before').exists()


@pytest.mark.django_db
class TestWeeklyReminder:
    @pytest.fixture(autouse=True)
    def _always_primetime(self, monkeypatch):
        monkeypatch.setattr(Game, 'is_primetime', property(lambda self: True))

    def test_weekly_sends_overview_and_logs(self, user):
        _primetime_game('wk_a', hours_from_now=48)
        call_command('send_weekly_reminder', '--week', '1', stdout=StringIO())
        assert len(mail.outbox) == 1
        assert 'Week 1' in mail.outbox[0].subject
        assert ReminderLog.objects.filter(
            user=user, reminder_type='weekly', game__isnull=True
        ).exists()

    def test_weekly_deduped_per_week(self, user):
        _primetime_game('wk_b', hours_from_now=48)
        call_command('send_weekly_reminder', '--week', '1', stdout=StringIO())
        call_command('send_weekly_reminder', '--week', '1', stdout=StringIO())
        assert len(mail.outbox) == 1

    def test_weekly_force_send_repeatable_without_log(self, user):
        _primetime_game('wk_c', hours_from_now=48)
        call_command('send_weekly_reminder', '--user', 'testplayer', '--force', '--week', '1', stdout=StringIO())
        call_command('send_weekly_reminder', '--user', 'testplayer', '--force', '--week', '1', stdout=StringIO())
        assert len(mail.outbox) == 2
        assert not ReminderLog.objects.filter(user=user, reminder_type='weekly').exists()


@pytest.mark.django_db
class TestFrequencyCap:
    """At most one 'awareness' email (weekly or day-before) per user per day;
    game-day urgency reminders are exempt."""

    @pytest.fixture(autouse=True)
    def _always_primetime(self, monkeypatch):
        monkeypatch.setattr(Game, 'is_primetime', property(lambda self: True))

    def test_weekly_suppresses_same_day_day_before(self, user):
        # Weekly (fires first in prod) covers the game, so the same-day
        # day-before nudge is held.
        _primetime_game('cap_daybefore', hours_from_now=20)
        call_command('send_weekly_reminder', '--week', '1', stdout=StringIO())
        mail.outbox.clear()
        call_command('send_pick_reminders', '--week', '1', stdout=StringIO())
        assert len(mail.outbox) == 0
        assert not ReminderLog.objects.filter(
            user=user, reminder_type='day_before'
        ).exists()

    def test_urgency_is_never_capped(self, user):
        # An hours-before (game-day last call) still sends even after the weekly.
        _primetime_game('cap_urgent', hours_from_now=2)
        call_command('send_weekly_reminder', '--week', '1', stdout=StringIO())
        mail.outbox.clear()
        call_command('send_pick_reminders', '--week', '1', stdout=StringIO())
        assert len(mail.outbox) == 1
        assert ReminderLog.objects.filter(
            user=user, reminder_type='hours_before'
        ).exists()

    def test_only_one_day_before_awareness_per_day(self, user):
        # Two games both in the day-before window on the same day -> one email.
        _primetime_game('cap_a', hours_from_now=20)
        _primetime_game('cap_b', hours_from_now=30)
        call_command('send_pick_reminders', '--week', '1', stdout=StringIO())
        assert len(mail.outbox) == 1

    def test_force_bypasses_the_cap(self, user):
        _primetime_game('cap_force', hours_from_now=20)
        call_command('send_weekly_reminder', '--week', '1', stdout=StringIO())
        mail.outbox.clear()
        call_command('send_pick_reminders', '--user', 'testplayer', '--force', '--week', '1', stdout=StringIO())
        assert len(mail.outbox) == 1

    def test_weekly_and_urgency_can_coexist_same_day(self, user):
        # Sanity: weekly + a game-day last call = two emails is allowed
        # (different jobs), the cap only limits stacked awareness emails.
        _primetime_game('coexist', hours_from_now=2)
        call_command('send_weekly_reminder', '--week', '1', stdout=StringIO())
        call_command('send_pick_reminders', '--week', '1', stdout=StringIO())
        assert len(mail.outbox) == 2
