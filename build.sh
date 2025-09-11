#!/usr/bin/env bash
set -o errexit

export DJANGO_SETTINGS_MODULE=primetimepix.settings.production
export DATABASE_URL="postgresql://primetimepix:he9fE8B6HGO16dITUt0dTocFIzUf5Au6@dpg-d311vbndiees73aehp7g-a/primetimepix"

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Sync the ENTIRE 2024-2025 NFL season
echo "=== SYNCING FULL NFL SEASON ==="
python manage.py sync_nfl_schedule --all-weeks --season 2024

# Check results
echo "=== SEASON SYNC RESULTS ==="
python manage.py shell -c "
from apps.games.models import Game
total = Game.objects.count()
primetime = sum(1 for g in Game.objects.all() if g.is_primetime)
print(f'Total games synced: {total}')
print(f'Primetime games: {primetime}')
print('Games by week:')
for week in range(1, 19):
    count = Game.objects.filter(week=week).count()
    if count > 0:
        print(f'  Week {week}: {count} games')
playoffs = Game.objects.filter(game_type__in=['playoff', 'wildcard', 'divisional', 'conference', 'superbowl']).count()
if playoffs > 0:
    print(f'Playoff games: {playoffs}')
"

python manage.py update_scores || true
python manage.py update_primetime || true
python manage.py calculate_results || true

echo "Build completed successfully!"