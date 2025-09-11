#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run database migrations
python manage.py migrate

# Create cache table if using database cache
python manage.py createcachetable || true

# Update NFL scores for recent games (last 7 days)
echo "Updating NFL scores..."
python manage.py calculate_results || true

# Optional: Update primetime game flags
echo "Checking primetime games..."
python manage.py update_primetime || true

echo "Build completed successfully!"