from io import StringIO

import pytest
from django.core import mail
from django.core.management import call_command

from apps.users.models import Notification, ReminderLog


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
