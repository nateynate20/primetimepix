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

echo "=== CREATING LEAGUES AND USERS ==="
python manage.py shell -c "
from apps.leagues.models import League, LeagueMembership
from django.contrib.auth.models import User
from apps.users.models import Profile
from apps.picks.models import Pick
from apps.games.models import Game

admin_user = User.objects.filter(is_superuser=True).first()

# Create leagues
nfl_shaderoom, created1 = League.objects.get_or_create(
    name='NFL shaderoom',
    defaults={
        'commissioner': admin_user,
        'description': 'NFL Shaderoom Primetime Picks League',
        'is_private': True,
        'is_approved': True,
        'sport': 'NFL'
    }
)

heatabockas, created2 = League.objects.get_or_create(
    name='heatabockas',
    defaults={
        'commissioner': admin_user,
        'description': 'Heatabockas Primetime Picks League',
        'is_private': True,
        'is_approved': True,
        'sport': 'NFL'
    }
)

print(f'Leagues: {nfl_shaderoom.name} and {heatabockas.name}')

# NFL Shaderoom users and stats (excluding nate1)
shaderoom_users = [
    {'username': 'von', 'email': '', 'team_name': 'Von Team', 'wins': 3, 'losses': 1},
    {'username': 'rashaun', 'email': '', 'team_name': 'Rashaun Team', 'wins': 1, 'losses': 3},
    {'username': 'kei', 'email': '', 'team_name': 'Kei Team', 'wins': 0, 'losses': 0},
    {'username': 'shank', 'email': '', 'team_name': 'Shank Team', 'wins': 2, 'losses': 2},
    {'username': 'ben1', 'email': '', 'team_name': 'Ben Team', 'wins': 2, 'losses': 2},
    {'username': 'bryant', 'email': '', 'team_name': 'Bryant Team', 'wins': 2, 'losses': 2},
]

# Heatabockas users and stats (excluding nate2)
heatabockas_users = [
    {'username': 'von2', 'email': '', 'team_name': 'Von Team', 'wins': 1, 'losses': 3},
    {'username': 'shane', 'email': '', 'team_name': 'Shane Team', 'wins': 1, 'losses': 3},
    {'username': 'ivan', 'email': '', 'team_name': 'Ivan Team', 'wins': 1, 'losses': 3},
    {'username': 'teej', 'email': '', 'team_name': 'Teej Team', 'wins': 2, 'losses': 2},
    {'username': 'stef', 'email': '', 'team_name': 'Stef Team', 'wins': 2, 'losses': 2},
    {'username': 'ben2', 'email': '', 'team_name': 'Ben Team', 'wins': 2, 'losses': 2},
    {'username': 'yakk', 'email': '', 'team_name': 'Yakk Team', 'wins': 3, 'losses': 1},
    {'username': 'fishie', 'email': '', 'team_name': 'Fishie Team', 'wins': 1, 'losses': 1},
]

# Get a sample game for historical picks
sample_game = Game.objects.first()

def create_users_for_league(users_data, league):
    for user_data in users_data:
        # Create user
        user, user_created = User.objects.get_or_create(
            username=user_data['username'],
            defaults={
                'email': user_data['email'],
                'password': 'pbkdf2_sha256\$600000\$temp\$temp'
            }
        )
        
        # Create profile
        if user_created:
            Profile.objects.create(user=user, team_name=user_data['team_name'])
        
        # Add to league
        LeagueMembership.objects.get_or_create(user=user, league=league)
        
        # Create historical picks if sample game exists
        if sample_game:
            # Create win picks
            for i in range(user_data['wins']):
                Pick.objects.get_or_create(
                    user=user,
                    league=league,
                    game=sample_game,
                    picked_team=sample_game.home_team,
                    defaults={
                        'is_correct': True,
                        'points': 1,
                        'confidence': 1
                    }
                )
            
            # Create loss picks  
            for i in range(user_data['losses']):
                Pick.objects.get_or_create(
                    user=user,
                    league=league,
                    game=sample_game,
                    picked_team=sample_game.away_team,
                    defaults={
                        'is_correct': False,
                        'points': 0,
                        'confidence': 1
                    }
                )
        
        print(f'Created user: {user.username} ({user_data[\"wins\"]}W-{user_data[\"losses\"]}L)')

def add_admin_to_league_with_stats(league, wins, losses):
    # Add admin user to league
    LeagueMembership.objects.get_or_create(user=admin_user, league=league)
    
    # Create historical picks for admin
    if sample_game:
        # Create win picks
        for i in range(wins):
            Pick.objects.get_or_create(
                user=admin_user,
                league=league,
                game=sample_game,
                picked_team=sample_game.home_team,
                defaults={
                    'is_correct': True,
                    'points': 1,
                    'confidence': 1
                }
            )
        
        # Create loss picks  
        for i in range(losses):
            Pick.objects.get_or_create(
                user=admin_user,
                league=league,
                game=sample_game,
                picked_team=sample_game.away_team,
                defaults={
                    'is_correct': False,
                    'points': 0,
                    'confidence': 1
                }
            )
    
    print(f'Added admin user to {league.name} with {wins}W-{losses}L')

# Create users for both leagues
create_users_for_league(shaderoom_users, nfl_shaderoom)
create_users_for_league(heatabockas_users, heatabockas)

# Add admin user to both leagues with respective stats
add_admin_to_league_with_stats(nfl_shaderoom, 3, 1)  # nate1 stats: 3W-1L
add_admin_to_league_with_stats(heatabockas, 3, 1)    # nate2 stats: 3W-1L

print(f'NFL Shaderoom members: {nfl_shaderoom.members.count()}')
print(f'Heatabockas members: {heatabockas.members.count()}')
print(f'Admin user {admin_user.username} added to both leagues')
"

# Generate password reset links (excluding admin)
echo "=== USER SETUP LINKS ==="
python manage.py generate_user_links


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