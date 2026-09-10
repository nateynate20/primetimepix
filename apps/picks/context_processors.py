#apps/picks/context_processors.py
from apps.leagues.models import League


def user_leagues(request):
    """Leagues for the navbar switcher, each annotated with how many primetime
    picks are still due this week so the dropdown can flag which leagues need
    attention (mirrors how ESPN/Sleeper badge a league that needs action).

    Kept deliberately cheap — it runs on every authenticated page: one small
    games query for the week plus one picks query, then in-memory bucketing.
    """
    if not request.user.is_authenticated:
        return {'user_leagues': [], 'leagues_needing_picks': 0}

    leagues = list(League.objects.filter(is_approved=True, members=request.user))
    for lg in leagues:
        lg.picks_due = 0
    leagues_needing = 0

    try:
        from django.utils import timezone
        from apps.games.models import Game
        from apps.games.utils import get_current_nfl_week
        from apps.picks.models import Pick

        week = get_current_nfl_week()
        now = timezone.now()
        # Still-pickable primetime games this week (not yet kicked off).
        open_games = [
            g for g in Game.objects.filter(
                game_type='regular', week=week, status='scheduled'
            )
            if g.is_primetime and g.start_time > now
        ]
        if open_games and leagues:
            open_ids = [g.id for g in open_games]
            made = set(
                Pick.objects.filter(
                    user=request.user,
                    league__in=leagues,
                    game_id__in=open_ids,
                ).values_list('league_id', 'game_id')
            )
            for lg in leagues:
                due = sum(1 for gid in open_ids if (lg.id, gid) not in made)
                lg.picks_due = due
                if due:
                    leagues_needing += 1
    except Exception:
        # Never let a navbar annotation break page rendering.
        pass

    return {'user_leagues': leagues, 'leagues_needing_picks': leagues_needing}
