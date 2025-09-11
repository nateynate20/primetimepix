#!/usr/bin/env bash
# Exit on error
set -o errexit

# -----------------------------------
# Production Build Script for Render
# -----------------------------------

# Ensure DJANGO_SETTINGS_MODULE points to production
export DJANGO_SETTINGS_MODULE=primetimepix.settings.production

# Upgrade pip and install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Apply database migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create cache table if using database cache
echo "Creating cache table (if needed)..."
python manage.py createcachetable || true

# Update NFL scores for recent games (last 7 days)
echo "Updating NFL scores..."
python manage.py update_scores || echo "Score update failed, continuing..."

# Optional: Update primetime game flags
echo "Checking primetime games..."
python manage.py update_primetime || echo "Primetime update failed, continuing..."

# Calculate pick results for standings
echo "Calculating pick results for standings..."
python manage.py calculate_results || echo "Pick calculation failed, continuing..."

echo "✅ Build completed successfully!"
