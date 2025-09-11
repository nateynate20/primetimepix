#!/usr/bin/env bash
set -o errexit

export DJANGO_SETTINGS_MODULE=primetimepix.settings.production
export DATABASE_URL="postgresql://primetimepix:he9fE8B6HGO16dITUt0dTocFIzUf5Au6@dpg-d311vbndiees73aehp7g-a/primetimepix"

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
python manage.py createcachetable || true
python manage.py update_scores || true
python manage.py update_primetime || true
python manage.py calculate_results || true

echo "Build completed successfully!"
