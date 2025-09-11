#!/usr/bin/env bash
set -o errexit

export DJANGO_SETTINGS_MODULE=primetimepix.settings.production
export DATABASE_URL="postgresql://primetimepix:he9fE8B6HGO16dITUt0dTocFIzUf5Au6@dpg-d311vbndiees73aehp7g-a/primetimepix"

pip install --upgrade pip
pip install -r requirements.txt

# Debug settings and apps
echo "=== DJANGO SETTINGS DEBUG ==="
python -c "
import os
import django
from django.conf import settings
django.setup()
print('Settings module:', settings.SETTINGS_MODULE)
print('Database engine:', settings.DATABASES['default']['ENGINE'])
print('Games apps:', [app for app in settings.INSTALLED_APPS if 'games' in app])

# Test model import
try:
    from apps.games.models import Game
    print('✓ Game model imported successfully')
except Exception as e:
    print('✗ Game model import failed:', e)
"

python manage.py collectstatic --no-input
python manage.py migrate

# Test database connection
echo "=== DATABASE CONNECTION TEST ==="
python manage.py shell -c "
from apps.games.models import Game
print('Games in DB before sync:', Game.objects.count())
"

# Sync NFL data
echo "=== SYNCING NFL DATA ==="
python manage.py sync_nfl_schedule --week 1

# Check results
echo "=== FINAL RESULTS ==="
python manage.py shell -c "
from apps.games.models import Game
count = Game.objects.count()
print(f'Games in DB after sync: {count}')
if count > 0:
    for game in Game.objects.all()[:3]:
        print(f'  {game.away_team} @ {game.home_team} - Week {game.week} - Primetime: {game.is_primetime}')
"

python manage.py update_scores || true
python manage.py update_primetime || true
python manage.py calculate_results || true

echo "Build completed successfully!"