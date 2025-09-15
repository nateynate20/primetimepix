#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

export DJANGO_SETTINGS_MODULE=primetimepix.settings.production

# Log file
LOG_FILE="./build.log"

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    local type="$1"
    local message="$2"
    case "$type" in
        SUCCESS) echo -e "${GREEN}${message}${NC}" | tee -a "$LOG_FILE" ;;
        WARN)    echo -e "${YELLOW}${message}${NC}" | tee -a "$LOG_FILE" ;;
        ERROR)   echo -e "${RED}${message}${NC}" | tee -a "$LOG_FILE" ;;
        *)       echo "$message" | tee -a "$LOG_FILE" ;;
    esac
}

echo "=== BUILD STARTED at $(date) ===" | tee -a "$LOG_FILE"

log "INFO" "=== UPDATING PYTHON PACKAGES ==="
pip install --upgrade pip | tee -a "$LOG_FILE"
pip install -r requirements.txt | tee -a "$LOG_FILE"

log "INFO" "=== COLLECTING STATIC FILES ==="
python manage.py collectstatic --no-input | tee -a "$LOG_FILE"

log "INFO" "=== APPLYING MIGRATIONS ==="
python manage.py migrate | tee -a "$LOG_FILE"

log "INFO" "=== RUNNING INITIAL SETUP IN ONE SHOT ==="
python manage.py shell -c "
import time
import subprocess
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings
from apps.leagues.models import League
from apps.games.models import Game
from apps.users.models import Profile

LOG_FILE = '$LOG_FILE'

def log(type, message):
    colors = {'SUCCESS': '\033[0;32m', 'WARN': '\033[1;33m', 'ERROR': '\033[0;31m', 'INFO': ''}
    nc = '\033[0m'
    print(f'{colors.get(type, "")}{message}{nc}')
    with open(LOG_FILE, 'a') as f:
        f.write(f'[{type}] {message}\\n')

# Admin user
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin', 'evansna05@gmail.com', 'your-secure-admin-password')
    log('SUCCESS', 'Admin user created')
else:
    log('SUCCESS', 'Admin user already exists')

# Leagues
admin_user = User.objects.filter(is_superuser=True).first()
League.objects.get_or_create(
    name='NFL shaderoom',
    defaults={'commissioner': admin_user, 'description': 'NFL Shaderoom Primetime Picks League', 'is_private': True, 'is_approved': True, 'sport': 'NFL'}
)
League.objects.get_or_create(
    name='heatabockas',
    defaults={'commissioner': admin_user, 'description': 'Heatabockas Primetime Picks League', 'is_private': True, 'is_approved': True, 'sport': 'NFL'}
)

# Users and profiles
users_data = {
    'von': 'Von Team', 'rashaun': 'Rashaun Team', 'kei': 'Kei Team', 'shank': 'Shank Team',
    'ben': 'Ben Team', 'bryant': 'Bryant Team', 'shane': 'Shane Team', 'ivan': 'Ivan Team',
    'teej': 'Teej Team', 'stef': 'Stef Team', 'yakk': 'Yakk Team', 'fishie': 'Fishie Team'
}

for username, team_name in users_data.items():
    user, created = User.objects.get_or_create(username=username, defaults={'email': '', 'password': 'pbkdf2_sha256\$600000\$temp\$temp'})
    Profile.objects.get_or_create(user=user, defaults={'team_name': team_name})
log('SUCCESS', 'Users and profiles ensured')

# Password reset emails with retry
MAX_RETRIES = 3
RETRY_DELAY = 5
first_time_users = User.objects.filter(is_superuser=False, last_login__isnull=True).exclude(email='')

for user in first_time_users:
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    reset_link = f'https://primetimepix.onrender.com/users/reset/{uid}/{token}/'
    Profile.objects.get_or_create(user=user, defaults={'team_name': user.username + ' Team'})

    log('INFO', f'User: {user.username}')
    log('INFO', f'Email: {user.email}')
    log('INFO', f'Reset Link: {reset_link}')
    log('INFO', '-'*60)

    for attempt in range(1, MAX_RETRIES+1):
        try:
            send_mail(
                subject='Your PrimetimePix Password Reset Link',
                message=f'Hello {user.username},\\n\\nUse this link to set your password:\\n{reset_link}\\n\\nThanks!',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            log('SUCCESS', f'Email sent to {user.email} on attempt {attempt}')
            break
        except Exception as e:
            log('ERROR', f'Attempt {attempt} failed for {user.email}: {e}')
            if attempt < MAX_RETRIES:
                log('WARN', f'Retrying in {RETRY_DELAY} seconds...')
                time.sleep(RETRY_DELAY)
            else:
                log('ERROR', f'Could not send email to {user.email} after {MAX_RETRIES} attempts')

# Sync NFL schedule if needed
game_count = Game.objects.count()
if game_count < 100:
    log('WARN', f'Only {game_count} games found - syncing NFL schedule...')
    subprocess.run(['python', 'manage.py', 'sync_nfl_schedule', '--all-weeks', '--season', '2024'])
else:
    log('SUCCESS', f'{game_count} games already synced - skipping NFL sync')

# Setup demo league if missing
if not League.objects.filter(name='Public NFL Picks League').exists():
    log('WARN', 'Setting up demo league and data...')
    subprocess.run(['python', 'manage.py', 'setup_demo_data'])
else:
    log('SUCCESS', 'Demo league already exists - skipping')

# Final updates
subprocess.run(['python', 'manage.py', 'update_scores'], check=False)
subprocess.run(['python', 'manage.py', 'update_primetime'], check=False)
subprocess.run(['python', 'manage.py', 'calculate_results'], check=False)

log('SUCCESS', '=== BUILD COMPLETED SUCCESSFULLY ===')
"

echo -e "${GREEN}Build completed! See '$LOG_FILE' for full details.${NC}"
