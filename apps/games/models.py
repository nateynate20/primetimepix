from django.db import models
from django.utils import timezone
import pytz
from datetime import time, date, timedelta

class Game(models.Model):
    """Enhanced Game model with better primetime detection and team logos."""

    SPORT_CHOICES = [
        ('NFL', 'National Football League'),
    ]

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

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.away_team} @ {self.home_team} (Week {self.week})"

    @property
    def start_time_et(self):
        """Return start_time converted to US Eastern time safely."""
        if not self.start_time:
            return None
        eastern = pytz.timezone('US/Eastern')
        dt = self.start_time
        if timezone.is_naive(dt):
            dt = pytz.UTC.localize(dt)
        return dt.astimezone(eastern)

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
    def home_logo(self):
        for team_key, logo_url in self.TEAM_LOGOS.items():
            if team_key in self.home_team:
                return logo_url
        return None

    @property
    def away_logo(self):
        for team_key, logo_url in self.TEAM_LOGOS.items():
            if team_key in self.away_team:
                return logo_url
        return None

    @property
    def is_primetime(self):
        """Enhanced primetime detection based on ET."""
        if not self.start_time:
            return False

        # All playoff games
        if self.game_type in ['playoff', 'wildcard', 'divisional', 'conference', 'superbowl']:
            return True

        try:
            et_time = self.start_time_et
            game_date = et_time.date()
            game_time = et_time.time()
            weekday = et_time.weekday()  # Monday=0, Sunday=6

            if self._is_holiday_game(game_date):
                return True

            # Thursday Night Football
            if weekday == 3 and game_time >= time(19, 0):
                return True
            # Sunday Night Football
            if weekday == 6 and game_time >= time(20, 0):
                return True
            # Monday Night Football
            if weekday == 0 and game_time >= time(19, 0):
                return True
            # Saturday late-season games
            if weekday == 5 and game_time >= time(16, 30):
                return True
        except:
            return False

        return False

    def _is_holiday_game(self, game_date):
        year = game_date.year
        thanksgiving = self._get_thanksgiving_date(year)
        if game_date == thanksgiving:
            return True
        if game_date.month == 12 and game_date.day in [24, 25, 31]:
            return True
        if game_date.month == 1 and game_date.day == 1:
            return True
        return False

    def _get_thanksgiving_date(self, year):
        nov1 = date(year, 11, 1)
        days_until_thursday = (3 - nov1.weekday()) % 7
        first_thursday = nov1 + timedelta(days=days_until_thursday)
        return first_thursday + timedelta(weeks=3)

    @property
    def primetime_type(self):
        if not self.is_primetime:
            return None

        if self.game_type in ['playoff', 'wildcard', 'divisional', 'conference', 'superbowl']:
            return self.get_game_type_display()

        et_time = self.start_time_et
        game_date = et_time.date()
        weekday = et_time.weekday()

        if self._is_holiday_game(game_date):
            if game_date.month == 11:
                return "Thanksgiving"
            elif game_date.month == 12 and game_date.day == 25:
                return "Christmas"
            elif game_date.month == 1 and game_date.day == 1:
                return "New Year's"
            else:
                return "Holiday"

        if weekday == 3:
            return "Thursday Night"
        elif weekday == 6:
            return "Sunday Night"
        elif weekday == 0:
            return "Monday Night"
        elif weekday == 5:
            return "Saturday Night"

        return "Primetime"

    def can_make_picks(self):
        return not self.has_started
