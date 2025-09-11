#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

# -----------------------------
# Environment
# -----------------------------
export DJANGO_SETTINGS_MODULE=primetimepix.settings.production
echo "Using settings: $DJANGO_SETTINGS_MODULE"

# -----------------------------
# Install dependencies
# -----------------------------
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# -----------------------------
# Collect static files
# -----------------------------
echo "Collecting static files..."
python manage.py collectstatic --no-input

# -----------------------------
# Run database migrations
# -----------------------------
echo "Running database migrations..."
python manage.py migrate

# -----------------------------
# Create cache table if using database cache
# -----------------------------
echo "Creating cache table (if needed)..."
python manage.py createcachetable || true

# -----------------------------
# Update NFL scores
# -----------------------------
echo "Updating NFL scores for recent games..."
python manage.py update_scores || true

# -----------------------------
# Update primetime games
# -----------------------------
echo "Checking primetime games..."
python manage.py update_primetime || true

# -----------------------------
# Calculate pick results
# -----------------------------
echo "Calculating pick results for standings..."
python manage.py calculate_results || true

echo "✅ Build completed successfully!"
