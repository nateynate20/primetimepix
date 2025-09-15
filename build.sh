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

    # Users
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

    sample_games = list(Game.objects.all()[:30])

    for username, data in all_users.items():
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': data['email'], 'password': 'pbkdf2_sha256\$600000\$temp\$temp'}
        )
        if created:
            Profile.objects.create(user=user, team_name=data['team_name'])

    print('✓ Users and profiles created')
"

# --------------------------------------
# Generate one-time password reset emails for new users
# --------------------------------------
echo "=== GENERATING PASSWORD RESET LINKS & SENDING EMAILS FOR FIRST-TIME USERS ==="
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
