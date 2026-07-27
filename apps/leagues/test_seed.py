"""Smoke tests for the seed_season management command."""
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.games.models import Game
from apps.leagues.models import League
from apps.picks.models import Pick

User = get_user_model()


@pytest.mark.django_db
def test_seed_season_builds_coherent_dataset():
    out = StringIO()
    call_command('seed_season', '--users', '12', '--seed', '1', stdout=out)

    assert User.objects.filter(username__startswith='demo_user_').count() == 12
    assert League.objects.exists()
    assert Game.objects.filter(game_id__startswith='demo_game_').count() == 3
    assert Pick.objects.exists()

    # Standings must be computable and internally consistent.
    league = League.objects.first()
    standings = league.get_standings()
    assert len(standings) == league.members.count()
    for row in standings:
        assert row['correct_predictions'] <= row['total_predictions']


@pytest.mark.django_db
def test_seed_season_is_idempotent_and_fresh_resets():
    call_command('seed_season', '--users', '8', '--seed', '2', stdout=StringIO())
    first_users = User.objects.filter(username__startswith='demo_user_').count()

    # Re-running without --fresh should not duplicate namespaced users.
    call_command('seed_season', '--users', '8', '--seed', '2', stdout=StringIO())
    assert User.objects.filter(username__startswith='demo_user_').count() == first_users

    # --fresh clears demo data before rebuilding.
    call_command('seed_season', '--users', '5', '--seed', '2', '--fresh', stdout=StringIO())
    assert User.objects.filter(username__startswith='demo_user_').count() == 5
