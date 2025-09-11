# apps/games/models.py
from django.db import models
from django.utils import timezone
import pytz
from datetime import time, date, timedelta


class Game(models.Model):
    """NFL Game model with improved primetime detection, team logos, and helper methods."""

    # Choices
    SPORT_CHOICES = [('NFL', 'National Football League')]
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('final', 'Final'),
        ('cancelled', 'Cancelled'),
    ]
    GAME_TYPE_CHOICES = [
        ('regular', 'Regular Season'),
        ('playoff', 'Playoff'),
        ('superbowl', 'Super Bowl'),
        ('wildcard', 'Wild Card'),
        ('divisional', 'Divisional'),
        ('conference', 'Conference Championship'),
    ]

    TEAM_LOGOS = {
        'Cardinals': 'https://a.espncdn.com/i/teamlogos/nfl/500/ari.png',
        'Falcons': 'https://a.espncdn.com/i/teamlogos/nfl/500/atl.png',
        'Ravens': 'https://a.espncdn.com/i/teamlogos/nfl/500/bal.png',
        'Bills': 'https://a.espncdn.com/i/teamlogos/nfl/500/buf.png',
        'Panthers': 'https://a.espncdn.com/i/teamlogos/nfl/500/car.png',
        'Bears': 'https://a.espncdn.com/i/teamlogos/nfl/500/chi.png',
        'Bengals': 'https://a.espncdn.com/i/teamlogos/nfl/500/cin.png',
        'Browns': 'https://a.espncdn.com/i/teamlogos/nfl/500/cle.png',
        'Cowboys': 'https://a.espncdn.com/i/teamlogos/nfl/500/dal.png',
        'Broncos': 'https://a.espncdn.com/i/teamlogos/nfl/500/den.png',
        'Lions': 'https://a.espncdn.com/i/teamlogos/nfl/500/det.png',
        'Packers': 'https://a.espncdn.com/i/teamlogos/nfl/500/gb.png',
        'Texans': 'https://a.espncdn.com/i/teamlogos/nfl/500/hou.png',
        'Colts': 'https://a.espncdn.com/i/teamlogos/nfl/500/ind.png',
        'Jaguars': 'https://a.espncdn.com/i/teamlogos/nfl/500/jax.png',
        'Chiefs': 'https://a.espncdn.com/i/teamlogos/nfl/500/kc.png',
        'Raiders': 'https://a.espncdn.com/i/teamlogos/nfl/500/lv.png',
        'Chargers': 'https://a.espncdn.com/i/teamlogos/nfl/500/lac.png',
        'Rams': 'https://a.espncdn.com/i/teamlogos/nfl/500/lar.png',
        'Dolphins': 'https://a.espncdn.com/i/teamlogos/nfl/500/mia.png',
        'Vikings': 'https://a.espncdn.com/i/teamlogos/nfl/500/min.png',
        'Patriots': 'https://a.espncdn.com/i/teamlogos/nfl/500/ne.png',
        'Saints': 'https://a.espncdn.com/i/teamlogos/nfl/500/no.png',
        'Giants': 'https://a.espncdn.com/i/teamlogos/nfl/500/nyg.png',
        'Jets': 'https://a.espncdn.com/i/teamlogos/nfl/500/nyj.png',
        'Eagles': 'https://a.espncdn.com/i/teamlogos/nfl/500/phi.png',
        'Steelers': 'https://a.espncdn.com/i/teamlogos/nfl/500/pit.png',
        '49ers': 'https://a.espncdn.com/i/teamlogos/nfl/500/sf.png',
        'Seahawks': 'https://a.espncdn.com/i/teamlogos/nfl/500/sea.png',
        'Buccaneers': 'https://a.espncdn.com/i/teamlogos/nfl/500/tb.png',
        'Titans': 'https://a.espncdn.com/i/teamlogos/nfl/500/ten.png',
        'Commanders': 'https://a.espncdn.com/i/teamlogos/nfl/500/wsh.png',
        'Washington': 'https://a.espncdn.com/i/teamlogos/nfl/500/wsh.png',
    }

    # Fields
    game_id = models.CharField(max_length=100, unique=True, default="default_game_id")
    season = models.IntegerField()
    week = models.IntegerField()
    game_type = models.CharField(max_length=20, choices=GAME_TYPE_CHOICES, default='regular')
    start_time = models.DateTimeField(db_index=True)
    home_team = models.CharField(max_length=50)
    away_team = models.CharField(max_length=50)
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.away_team} @ {self.home_team} (Week {self.week})"

    # --------------------------
    # Time / Primetime
    # --------------------------
    @property
    def display_time_et(self):
        """Return start_time converted to US/Eastern."""
        if not self.start_time:
            return None
        eastern = pytz.timezone("US/Eastern")
        dt = self.start_time
        if timezone.is_naive(dt):
            dt = pytz.UTC.localize(dt)
        return dt.astimezone(eastern)

    @property
    def is_primetime(self):
        """Determine if game is primetime with improved logic."""
        et_time = self.display_time_et
        if not et_time:
            return False

        # Playoffs & major games
        if self.game_type in ['playoff', 'wildcard', 'divisional', 'conference', 'superbowl']:
            return True

        # Holidays
        if self._is_holiday_game(et_time.date()):
            return True

        weekday = et_time.weekday()  # 0=Mon ... 6=Sun
        game_time = et_time.time()

        if weekday == 6 and game_time >= time(19, 0):  # Sunday Night
            return True
        if weekday == 0 and game_time >= time(19, 0):  # Monday Night
            return True
        if weekday == 3 and game_time >= time(19, 0):  # Thursday Night
            return True
        if weekday == 5:  # Saturday
            if self.week >= 17 or self.game_type != 'regular' or game_time >= time(19, 0):
                return True

        return False

    @property
    def primetime_type(self):
        """Return the type of primetime game."""
        if not self.is_primetime:
            return ""

        if self.game_type in ['playoff', 'wildcard', 'divisional', 'conference', 'superbowl']:
            return self.get_game_type_display()

        et_time = self.display_time_et
        if et_time:
            game_date = et_time.date()
            if self._is_holiday_game(game_date):
                if game_date.month == 11:
                    return "Thanksgiving"
                elif game_date.month == 12 and game_date.day == 25:
                    return "Christmas"
                elif game_date.month == 1 and game_date.day == 1:
                    return "New Year's"
                else:
                    return "Holiday"

            weekday = et_time.weekday()
            if weekday == 6:
                return "Sunday Night"
            elif weekday == 0:
                return "Monday Night"
            elif weekday == 3:
                return "Thursday Night"
            elif weekday == 5:
                return "Saturday Night"

        return "Primetime"

    # --------------------------
    # Logos
    # --------------------------
    @property
    def home_logo(self):
        for key, logo in self.TEAM_LOGOS.items():
            if key in self.home_team:
                return logo
        return None

    @property
    def away_logo(self):
        for key, logo in self.TEAM_LOGOS.items():
            if key in self.away_team:
                return logo
        return None

    # --------------------------
    # Status / Winner
    # --------------------------
    @property
    def has_started(self):
        dt = self.start_time
        if timezone.is_naive(dt):
            dt = pytz.UTC.localize(dt)
        return timezone.now() >= dt

    @property
    def is_finished(self):
        return self.status.lower() in ['final', 'finished', 'completed']

    @property
    def winner(self):
        if self.status != 'final' or self.home_score is None or self.away_score is None:
            return None
        if self.home_score > self.away_score:
            return self.home_team
        if self.away_score > self.home_score:
            return self.away_team
        return 'tie'

    @property
    def is_locked(self):
        return self.has_started or self.status != 'scheduled'

    @property
    def locked(self):
        return self.is_locked

    def can_make_picks(self):
        return not self.is_locked

    # --------------------------
    # Pick Results
    # --------------------------
    def update_pick_results(self):
        from apps.picks.models import Pick
        if self.status == 'final' and self.winner is not None:
            picks = Pick.objects.filter(game=self)
            updated_count = 0
            for pick in picks:
                old_correct = pick.is_correct
                pick.calculate_result()
                if old_correct != pick.is_correct:
                    updated_count += 1
            return updated_count
        return 0

    # --------------------------
    # Holiday Helpers
    # --------------------------
    def _is_holiday_game(self, game_date):
        """Check if game is on a major holiday."""
        year = game_date.year
        thanksgiving = self._get_thanksgiving_date(year)
        if game_date == thanksgiving:
            return True
        if game_date.month == 12 and game_date.day in [24, 25]:
            return True
        if (game_date.month == 12 and game_date.day == 31) or (game_date.month == 1 and game_date.day == 1):
            return True
        return False

    def _get_thanksgiving_date(self, year):
        """Fourth Thursday in November."""
        nov1 = date(year, 11, 1)
        days_until_thursday = (3 - nov1.weekday()) % 7
        first_thursday = nov1 + timedelta(days=days_until_thursday)
        return first_thursday + timedelta(weeks=3)

    # --------------------------
    # Lock & Display
    # --------------------------
    @property
    def is_locked_for_picks(self):
        """Determine if picks are locked for this game."""
        if self.status != 'scheduled':
            return True
        dt = self.start_time
        if timezone.is_naive(dt):
            dt = pytz.UTC.localize(dt)
        lock_time = dt - timezone.timedelta(minutes=5)
        return timezone.now() >= lock_time

    @property
    def display_status(self):
        """Get display-friendly status."""
        status_map = {
            'scheduled': 'Scheduled',
            'in_progress': 'LIVE',
            'final': 'Final',
            'cancelled': 'Cancelled',
        }
        return status_map.get(self.status, self.status)

    @property
    def score_display(self):
        """Get formatted score display."""
        if not self.has_started:
            if self.display_time_et:
                return self.display_time_et.strftime('%I:%M %p ET')
            return "TBD"

        if self.status == 'final':
            return f"{self.away_score or 0} - {self.home_score or 0} (Final)"
        elif self.status == 'in_progress':
            return f"{self.away_score or 0} - {self.home_score or 0} (Live)"
        else:
            return "Starting soon"
