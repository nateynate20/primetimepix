#!/usr/bin/env bash
set -o errexit

export DJANGO_SETTINGS_MODULE=primetimepix.settings.production

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Create admin user if none exists
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin', 'evansna05@gmail.com', 'your-secure-admin-password')
    print('✓ Admin user created')
else:
    print('✓ Admin user already exists')
"

echo "=== CHECKING EXISTING DATA ==="
python manage.py shell -c "
from apps.leagues.models import League
from django.contrib.auth.models import User
from apps.games.models import Game

# Check if setup is already complete
leagues_exist = League.objects.count() >= 2
users_exist = User.objects.filter(is_superuser=False).count() >= 10
games_exist = Game.objects.count() >= 100

if leagues_exist and users_exist and games_exist:
    print('✓ All data already exists - skipping initial setup')
else:
    print('⚠ Initial setup needed')
"

# Only run expensive setup if data doesn't exist
python manage.py shell -c "
from apps.leagues.models import League, LeagueMembership
from django.contrib.auth.models import User
from apps.users.models import Profile
from apps.picks.models import Pick
from apps.games.models import Game

# Quick check - skip if data already exists
if League.objects.count() >= 2 and User.objects.filter(is_superuser=False).count() >= 10:
    print('✓ Leagues and users already exist - skipping creation')
else:
    print('Creating leagues and users...')
    
    admin_user = User.objects.filter(is_superuser=True).first()

    # Create leagues
    nfl_shaderoom, created1 = League.objects.get_or_create(
        name='NFL shaderoom',
        defaults={
            'commissioner': admin_user,
            'description': 'NFL Shaderoom Primetime Picks League',
            'is_private': True,
            'is_approved': True,
            'sport': 'NFL'
        }
    )

    heatabockas, created2 = League.objects.get_or_create(
        name='heatabockas',
        defaults={
            'commissioner': admin_user,
            'description': 'Heatabockas Primetime Picks League',
            'is_private': True,
            'is_approved': True,
            'sport': 'NFL'
        }
    )

    # User mapping
    all_users = {
        'von': {'email': '', 'team_name': 'Von Team'},
        'rashaun': {'email': '', 'team_name': 'Rashaun Team'},
        'kei': {'email': '', 'team_name': 'Kei Team'},
        'shank': {'email': '', 'team_name': 'Shank Team'},
        'ben': {'email': '', 'team_name': 'Ben Team'},
        'bryant': {'email': '', 'team_name': 'Bryant Team'},
        'shane': {'email': '', 'team_name': 'Shane Team'},
        'ivan': {'email': '', 'team_name': 'Ivan Team'},
        'teej': {'email': '', 'team_name': 'Teej Team'},
        'stef': {'email': '', 'team_name': 'Stef Team'},
        'yakk': {'email': '', 'team_name': 'Yakk Team'},
        'fishie': {'email': '', 'team_name': 'Fishie Team'},
    }

    league_stats = {
        'NFL shaderoom': {
            'von': {'wins': 3, 'losses': 1},
            'rashaun': {'wins': 1, 'losses': 3},
            'kei': {'wins': 0, 'losses': 0},
            'shank': {'wins': 2, 'losses': 2},
            'ben': {'wins': 2, 'losses': 2},
            'bryant': {'wins': 2, 'losses': 2},
        },
        'heatabockas': {
            'von': {'wins': 1, 'losses': 3},
            'shane': {'wins': 1, 'losses': 3},
            'ivan': {'wins': 1, 'losses': 3},
            'teej': {'wins': 2, 'losses': 2},
            'stef': {'wins': 2, 'losses': 2},
            'ben': {'wins': 2, 'losses': 2},
            'yakk': {'wins': 3, 'losses': 1},
            'fishie': {'wins': 1, 'losses': 1},
        }
    }

    sample_games = list(Game.objects.all()[:30])

    # Create users
    for username, user_data in all_users.items():
        user, user_created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': user_data['email'],
                'password': 'pbkdf2_sha256\$600000\$temp\$temp'
            }
        )
        
        if user_created:
            Profile.objects.create(user=user, team_name=user_data['team_name'])

    # Add users to leagues (simplified)
    def add_users_to_league_with_stats(league, users_stats):
        for username, stats in users_stats.items():
            user = User.objects.get(username=username)
            LeagueMembership.objects.get_or_create(user=user, league=league)
            
            existing_picks_count = Pick.objects.filter(user=user, league=league).count()
            if existing_picks_count == 0 and sample_games:
                picks_created = 0
                for i in range(stats['wins']):
                    if picks_created < len(sample_games):
                        game = sample_games[picks_created]
                        Pick.objects.create(
                            user=user, league=league, game=game,
                            picked_team=game.home_team, is_correct=True,
                            points=1, confidence=1
                        )
                        picks_created += 1
                
                for i in range(stats['losses']):
                    if picks_created < len(sample_games):
                        game = sample_games[picks_created]
                        Pick.objects.create(
                            user=user, league=league, game=game,
                            picked_team=game.away_team, is_correct=False,
                            points=0, confidence=1
                        )
                        picks_created += 1

    add_users_to_league_with_stats(nfl_shaderoom, league_stats['NFL shaderoom'])
    add_users_to_league_with_stats(heatabockas, league_stats['heatabockas'])

    # Add admin to leagues
    for league, wins, losses in [(nfl_shaderoom, 3, 1), (heatabockas, 3, 1)]:
        LeagueMembership.objects.get_or_create(user=admin_user, league=league)
        existing_picks = Pick.objects.filter(user=admin_user, league=league).count()
        if existing_picks == 0 and sample_games:
            picks_created = 0
            for i in range(wins + losses):
                if picks_created < len(sample_games):
                    game = sample_games[picks_created]
                    is_correct = i < wins
                    Pick.objects.create(
                        user=admin_user, league=league, game=game,
                        picked_team=game.home_team if is_correct else game.away_team,
                        is_correct=is_correct, points=1 if is_correct else 0,
                        confidence=1
                    )
                    picks_created += 1

    print(f'✓ Setup complete - {League.objects.count()} leagues, {User.objects.filter(is_superuser=False).count()} users')
"

# Generate password reset links only for users who haven't logged in
echo "=== GENERATING USER LOGIN LINKS ==="
python manage.py generate_password_links

# Only sync NFL schedule if games are missing
echo "=== CHECKING NFL SCHEDULE ==="
python manage.py shell -c "
from apps.games.models import Game
game_count = Game.objects.count()
if game_count < 100:
    print(f'Only {game_count} games found - syncing NFL schedule...')
    import subprocess
    subprocess.run(['python', 'manage.py', 'sync_nfl_schedule', '--all-weeks', '--season', '2024'])
else:
    print(f'✓ {game_count} games already synced - skipping NFL sync')
"

# Skip demo data if leagues already exist
python manage.py shell -c "
from apps.leagues.models import League
if League.objects.filter(name='Public NFL Picks League').exists():
    print('✓ Demo league already exists - skipping')
else:
    import subprocess
    subprocess.run(['python', 'manage.py', 'setup_demo_data'])
"

echo "=== FINAL UPDATES ==="
python manage.py update_scores || true
python manage.py update_primetime || true
python manage.py calculate_results || true

echo "Build completed successfully!"