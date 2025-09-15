#!/usr/bin/env bash
set -euo pipefail  # safer than errexit alone

export DJANGO_SETTINGS_MODULE=primetimepix.settings.production

echo "=== BUILD STARTED ==="

# --------------------------------------
# Install dependencies
# --------------------------------------
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# --------------------------------------
# Collect static files and run migrations
# --------------------------------------
echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Applying migrations..."
python manage.py migrate

# --------------------------------------
# Ensure superuser exists
# --------------------------------------
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser(
        'admin',
        'evansna05@gmail.com',
        'your-secure-admin-password'
    )
    print('✓ Admin user created')
else:
    print('✓ Admin user already exists')
"

# --------------------------------------
# Check existing data
# --------------------------------------
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

# --------------------------------------
# Create leagues, users, and profiles if missing
# --------------------------------------
python manage.py shell -c "
from apps.leagues.models import League
from django.contrib.auth.models import User
from apps.users.models import Profile
from apps.games.models import Game

# Ensure leagues exist
admin_user = User.objects.filter(is_superuser=True).first()

leagues = [
    {'name': 'NFL shaderoom', 'description': 'NFL Shaderoom Primetime Picks League'},
    {'name': 'heatabockas', 'description': 'Heatabockas Primetime Picks League'}
]

for l in leagues:
    League.objects.get_or_create(
        name=l['name'],
        defaults={
            'commissioner': admin_user,
            'description': l['description'],
            'is_private': True,
            'is_approved': True,
            'sport': 'NFL'
        }
    )

# Create users and profiles
users_data = {
    'von': 'Von Team',
    'rashaun': 'Rashaun Team',
    'kei': 'Kei Team',
    'shank': 'Shank Team',
    'ben': 'Ben Team',
    'bryant': 'Bryant Team',
    'shane': 'Shane Team',
    'ivan': 'Ivan Team',
    'teej': 'Teej Team',
    'stef': 'Stef Team',
    'yakk': 'Yakk Team',
    'fishie': 'Fishie Team'
}

for username, team_name in users_data.items():
    user, created = User.objects.get_or_create(
        username=username,
        defaults={'password': 'pbkdf2_sha256$600000$temp$temp'}
    )
    # Ensure unique team_name and create profile safely
    if not hasattr(user, 'profile'):
        Profile.objects.get_or_create(
            user=user,
            defaults={'team_name': f'{team_name}'}
        )

print('✓ Users and profiles ensured')
"

# --------------------------------------
# Generate password reset links for first-time users
# --------------------------------------
echo "=== GENERATING PASSWORD RESET LINKS & SENDING EMAILS FOR FIRST-TIME USERS ==="
python manage.py generate_password_links

# --------------------------------------
# Sync NFL schedule if needed
# --------------------------------------
python manage.py shell -c "
from apps.games.models import Game
import subprocess

if Game.objects.count() < 100:
    print('Syncing NFL schedule...')
    subprocess.run(['python', 'manage.py', 'sync_nfl_schedule', '--all-weeks', '--season', '2024'])
else:
    print('✓ NFL schedule already synced')
"

# --------------------------------------
# Setup demo league if missing
# --------------------------------------
python manage.py shell -c "
from apps.leagues.models import League
import subprocess

if not League.objects.filter(name='Public NFL Picks League').exists():
    subprocess.run(['python', 'manage.py', 'setup_demo_data'])
else:
    print('✓ Demo league already exists - skipping')
"

# --------------------------------------
# Final updates
# --------------------------------------
python manage.py update_scores || true
python manage.py update_primetime || true
python manage.py calculate_results || true

echo "=== BUILD COMPLETED SUCCESSFULLY ==="
