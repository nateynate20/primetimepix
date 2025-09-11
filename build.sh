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

# User mapping - same users across leagues with different stats
all_users = {
    'von': {'email': '', 'team_name': 'Von Team'},
    'rashaun': {'email': '', 'team_name': 'Rashaun Team'},
    'kei': {'email': '', 'team_name': 'Kei Team'},
    'shank': {'email': '', 'team_name': 'Shank Team'},
    'ben': {'email': '', 'team_name': 'Ben Team'},
    'bryant': {'email': '', 'team_name': 'Bryant Team'},
    'shane': {'email': '', 'team_name': 'Shane Team'},
    'ivan': {'email': '', 'team_name': 'Ivan Team'},
    'teej': {'email': '', 'team_name': 'Teej Team'},
    'stef': {'email': '', 'team_name': 'Stef Team'},
    'yakk': {'email': '', 'team_name': 'Yakk Team'},
    'fishie': {'email': '', 'team_name': 'Fishie Team'},
}

# League-specific stats
league_stats = {
    'NFL shaderoom': {
        'von': {'wins': 3, 'losses': 1},
        'rashaun': {'wins': 1, 'losses': 3},
        'kei': {'wins': 0, 'losses': 0},
        'shank': {'wins': 2, 'losses': 2},
        'ben': {'wins': 2, 'losses': 2},
        'bryant': {'wins': 2, 'losses': 2},
    },
    'heatabockas': {
        'von': {'wins': 1, 'losses': 3},
        'shane': {'wins': 1, 'losses': 3},
        'ivan': {'wins': 1, 'losses': 3},
        'teej': {'wins': 2, 'losses': 2},
        'stef': {'wins': 2, 'losses': 2},
        'ben': {'wins': 2, 'losses': 2},
        'yakk': {'wins': 3, 'losses': 1},
        'fishie': {'wins': 1, 'losses': 1},
    }
}

# Get multiple sample games to avoid duplicates
sample_games = list(Game.objects.all()[:30])

# Create all users first
for username, user_data in all_users.items():
    user, user_created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': user_data['email'],
            'password': 'pbkdf2_sha256\$600000\$temp\$temp'
        }
    )
    
    # Create profile only if user was just created
    if user_created:
        Profile.objects.create(user=user, team_name=user_data['team_name'])
        print(f'Created user: {username}')

# Function to add users to leagues with stats
def add_users_to_league_with_stats(league, users_stats):
    for username, stats in users_stats.items():
        user = User.objects.get(username=username)
        
        # Add to league
        LeagueMembership.objects.get_or_create(user=user, league=league)
        
        # Only create historical picks if user has no picks in this league
        existing_picks_count = Pick.objects.filter(user=user, league=league).count()
        if existing_picks_count == 0 and sample_games:
            picks_created = 0
            
            # Create win picks using different games
            for i in range(stats['wins']):
                if picks_created < len(sample_games):
                    game = sample_games[picks_created]
                    Pick.objects.create(
                        user=user,
                        league=league,
                        game=game,
                        picked_team=game.home_team,
                        is_correct=True,
                        points=1,
                        confidence=1
                    )
                    picks_created += 1
            
            # Create loss picks using different games
            for i in range(stats['losses']):
                if picks_created < len(sample_games):
                    game = sample_games[picks_created]
                    Pick.objects.create(
                        user=user,
                        league=league,
                        game=game,
                        picked_team=game.away_team,
                        is_correct=False,
                        points=0,
                        confidence=1
                    )
                    picks_created += 1
            
            print(f'Added {username} to {league.name}: {stats[\"wins\"]}W-{stats[\"losses\"]}L')
        else:
            print(f'{username} already has picks in {league.name}')

# Add users to leagues with their respective stats
add_users_to_league_with_stats(nfl_shaderoom, league_stats['NFL shaderoom'])
add_users_to_league_with_stats(heatabockas, league_stats['heatabockas'])

# Add admin user to both leagues with stats
def add_admin_to_league_with_stats(league, wins, losses):
    LeagueMembership.objects.get_or_create(user=admin_user, league=league)
    
    existing_picks_count = Pick.objects.filter(user=admin_user, league=league).count()
    if existing_picks_count == 0 and sample_games:
        picks_created = 0
        
        for i in range(wins):
            if picks_created < len(sample_games):
                game = sample_games[picks_created]
                Pick.objects.create(
                    user=admin_user,
                    league=league,
                    game=game,
                    picked_team=game.home_team,
                    is_correct=True,
                    points=1,
                    confidence=1
                )
                picks_created += 1
        
        for i in range(losses):
            if picks_created < len(sample_games):
                game = sample_games[picks_created]
                Pick.objects.create(
                    user=admin_user,
                    league=league,
                    game=game,
                    picked_team=game.away_team,
                    is_correct=False,
                    points=0,
                    confidence=1
                )
                picks_created += 1
        
        print(f'Added admin to {league.name}: {wins}W-{losses}L')
    else:
        print(f'Admin already has picks in {league.name}')

add_admin_to_league_with_stats(nfl_shaderoom, 3, 1)
add_admin_to_league_with_stats(heatabockas, 3, 1)

print(f'NFL Shaderoom members: {nfl_shaderoom.members.count()}')
print(f'Heatabockas members: {heatabockas.members.count()}')
"
# Generate password reset links for users
echo "=== GENERATING USER LOGIN LINKS ==="
python manage.py generate_password_links

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