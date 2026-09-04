import json
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.games.models import Game
from apps.users.models import PushSubscription
import apps.users.push as push


def _make_sub(user, endpoint='https://push.example/abc'):
    return PushSubscription.objects.create(
        user=user, endpoint=endpoint, p256dh='p256dh-key', auth='auth-key',
    )


@pytest.mark.django_db
class TestPushSubscribeEndpoints:
    def _payload(self, endpoint='https://push.example/xyz'):
        return {'endpoint': endpoint, 'keys': {'p256dh': 'PK', 'auth': 'AK'}}

    def test_subscribe_requires_login(self):
        response = Client().post(
            reverse('push_subscribe'), data=json.dumps(self._payload()),
            content_type='application/json',
        )
        assert response.status_code in (302, 401, 403)

    def test_subscribe_stores_subscription(self, user):
        client = Client()
        client.force_login(user)
        response = client.post(
            reverse('push_subscribe'), data=json.dumps(self._payload()),
            content_type='application/json',
        )
        assert response.status_code == 200
        assert PushSubscription.objects.filter(user=user, endpoint='https://push.example/xyz').exists()

    def test_subscribe_is_idempotent_on_endpoint(self, user):
        client = Client()
        client.force_login(user)
        for _ in range(2):
            client.post(
                reverse('push_subscribe'), data=json.dumps(self._payload()),
                content_type='application/json',
            )
        assert PushSubscription.objects.filter(endpoint='https://push.example/xyz').count() == 1

    def test_subscribe_rejects_missing_fields(self, user):
        client = Client()
        client.force_login(user)
        response = client.post(
            reverse('push_subscribe'), data=json.dumps({'endpoint': 'x'}),
            content_type='application/json',
        )
        assert response.status_code == 400

    def test_unsubscribe_deletes(self, user):
        _make_sub(user, 'https://push.example/del')
        client = Client()
        client.force_login(user)
        response = client.post(
            reverse('push_unsubscribe'),
            data=json.dumps({'endpoint': 'https://push.example/del'}),
            content_type='application/json',
        )
        assert response.status_code == 200
        assert not PushSubscription.objects.filter(endpoint='https://push.example/del').exists()


@pytest.mark.django_db
class TestPushOptInPlacement:
    """The opt-in has a permanent home on the profile page, gated on VAPID."""

    def test_profile_shows_optin_when_configured(self, user, settings):
        settings.VAPID_PUBLIC_KEY = 'pub-key'
        client = Client()
        client.force_login(user)
        body = client.get(reverse('edit_profile')).content.decode()
        assert 'push-optin' in body
        assert 'push-enable-btn' in body

    def test_profile_hides_optin_when_unconfigured(self, user, settings):
        settings.VAPID_PUBLIC_KEY = ''
        client = Client()
        client.force_login(user)
        body = client.get(reverse('edit_profile')).content.decode()
        assert 'push-optin' not in body

    def test_optin_buttons_are_type_button(self, user, settings):
        # Inside the profile <form>, the toggle buttons must not submit it.
        settings.VAPID_PUBLIC_KEY = 'pub-key'
        client = Client()
        client.force_login(user)
        body = client.get(reverse('edit_profile')).content.decode()
        assert 'type="button" id="push-enable-btn"' in body
        assert 'type="button" id="push-disable-btn"' in body


@pytest.mark.django_db
class TestSendWebPush:
    def test_noop_when_push_disabled(self, user, settings):
        settings.VAPID_PUBLIC_KEY = ''
        settings.VAPID_PRIVATE_KEY = ''
        _make_sub(user)
        assert push.send_web_push(user, 'Hi', 'Body') == 0

    def test_sends_to_each_subscription(self, user, settings, monkeypatch):
        settings.VAPID_PUBLIC_KEY = 'pub'
        settings.VAPID_PRIVATE_KEY = 'priv'
        _make_sub(user, 'https://push.example/1')
        _make_sub(user, 'https://push.example/2')
        calls = []
        monkeypatch.setattr(push, '_deliver', lambda info, payload, pk, claims: calls.append(payload))
        sent = push.send_web_push(user, 'Title', 'Body', url='/dashboard/')
        assert sent == 2
        assert len(calls) == 2
        # Payload carries the notification content the SW will render.
        assert json.loads(calls[0])['title'] == 'Title'

    def test_prunes_expired_subscription(self, user, settings, monkeypatch):
        settings.VAPID_PUBLIC_KEY = 'pub'
        settings.VAPID_PRIVATE_KEY = 'priv'
        _make_sub(user, 'https://push.example/gone')

        class _Resp:
            status_code = 410

        class _Gone(Exception):
            response = _Resp()

        def raise_gone(*a, **k):
            raise _Gone()

        monkeypatch.setattr(push, '_deliver', raise_gone)
        sent = push.send_web_push(user, 'T', 'B')
        assert sent == 0
        # 410 Gone → subscription pruned.
        assert not PushSubscription.objects.filter(endpoint='https://push.example/gone').exists()

    def test_other_errors_keep_subscription(self, user, settings, monkeypatch):
        settings.VAPID_PUBLIC_KEY = 'pub'
        settings.VAPID_PRIVATE_KEY = 'priv'
        _make_sub(user, 'https://push.example/keep')

        def boom(*a, **k):
            raise RuntimeError('temporary')

        monkeypatch.setattr(push, '_deliver', boom)
        assert push.send_web_push(user, 'T', 'B') == 0
        # A transient error must NOT delete the subscription.
        assert PushSubscription.objects.filter(endpoint='https://push.example/keep').exists()


@pytest.mark.django_db
class TestReminderPushIntegration:
    @pytest.fixture(autouse=True)
    def _always_primetime(self, monkeypatch):
        monkeypatch.setattr(Game, 'is_primetime', property(lambda self: True))

    def test_weekly_reminder_also_pushes(self, user, settings, monkeypatch):
        settings.VAPID_PUBLIC_KEY = 'pub'
        settings.VAPID_PRIVATE_KEY = 'priv'
        Game.objects.create(
            game_id='wk_push', season=2026, week=1, game_type='regular',
            start_time=timezone.now() + timedelta(hours=48),
            home_team='Kansas City Chiefs', away_team='Buffalo Bills',
            status='scheduled',
        )
        _make_sub(user)
        calls = []
        monkeypatch.setattr(push, '_deliver', lambda *a, **k: calls.append(1))
        call_command('send_weekly_reminder', '--week', '1', stdout=StringIO())
        assert len(calls) == 1  # email + one web push to the subscribed device
