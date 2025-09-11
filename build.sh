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

# Create demo data
python manage.py setup_demo_data

# Sync full NFL season
echo "=== SYNCING FULL NFL SEASON ==="
python manage.py sync_nfl_schedule --all-weeks --season 2024

echo "=== FINAL SETUP COMPLETE ==="
python manage.py shell -c "
from apps.games.models import Game
from apps.leagues.models import League
from django.contrib.auth.models import User
print(f'✓ Games: {Game.objects.count()}')
print(f'✓ Primetime games: {sum(1 for g in Game.objects.all() if g.is_primetime)}')
print(f'✓ Leagues: {League.objects.count()}')
print(f'✓ Users: {User.objects.count()}')
"

python manage.py update_scores || true
python manage.py update_primetime || true
python manage.py calculate_results || true

echo "Build completed successfully!"