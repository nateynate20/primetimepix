#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input --settings=primetimepix.settings.production


# Run database migrations
python manage.py migrate

# Create cache table if using database cache
python manage.py createcachetable || true

# Update NFL scores for recent games (last 7 days)
echo "Updating NFL scores..."
python manage.py update_scores || true

# Optional: Update primetime game flags
echo "Checking primetime games..."
python manage.py update_primetime || true

echo "Calculate pick results for standings" 
python manage.py calculate_results || true

echo "Build completed successfully!"