# Railway Cron Jobs Configuration
# These are separate Railway services that run on a schedule.
# Set up each as a new service on the Railway canvas pointing to the same repo.

## Required Cron Services

### 1. Update NFL Scores (CRITICAL - needed for picks to resolve)
# Schedule: Every 15 minutes on game days (Sun, Mon, Thu)
# Cron: */15 * * * 0,1,4,6
# Command: python manage.py update_scores
# When to run: Only during NFL season (September - February)
# Off-season: Change cron to "0 0 30 2 *" (never fires) or leave running (exits instantly)

### 2. Sync NFL Schedule (weekly)
# Schedule: Every Monday at 6am UTC
# Cron: 0 6 * * 1
# Command: python manage.py sync_nfl_schedule --season 2026

### 3. Send Pick Reminders
# Schedule: Every hour on game days
# Cron: 0 * * * 0,1,3,4,6
# Command: python manage.py send_pick_reminders

### 4. Generate CPU Picks (optional - for vs CPU feature)
# Schedule: Daily at 5am UTC
# Cron: 0 5 * * *
# Command: python manage.py generate_cpu_picks

## Environment Variables (same for all cron services)
# DATABASE_URL          - same as web service
# DJANGO_SETTINGS_MODULE - primetimepix.settings.production
# SECRET_KEY            - same as web service
# BREVO_API_KEY         - same as web service (for reminder emails)
# SITE_URL              - https://primetimepixsports.com

## Railway Setup Steps
# 1. On Railway canvas, click "+ New" > "Service"
# 2. Connect same GitHub repo
# 3. Go to Settings > set Start Command to the command above
# 4. Go to Settings > add Cron Schedule
# 5. Add all required environment variables
# 6. Deploy
