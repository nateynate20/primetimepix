# apps/leagues/management/commands/fix_league_memberships.py
from django.core.management.base import BaseCommand
from apps.leagues.models import League, LeagueMembership

class Command(BaseCommand):
    help = 'Fix league memberships for existing leagues created via admin'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
        
        # Find leagues where commissioner is not a member
        leagues_to_fix = []
        
        for league in League.objects.all():
            is_member = LeagueMembership.objects.filter(
                user=league.commissioner,
                league=league
            ).exists()
            
            if not is_member:
                leagues_to_fix.append(league)
                self.stdout.write(
                    f"Found league '{league.name}' where commissioner '{league.commissioner.username}' "
                    f"is not a member"
                )
        
        if not leagues_to_fix:
            self.stdout.write(self.style.SUCCESS("All leagues already have their commissioners as members!"))
            return
        
        # Fix the memberships
        fixed_count = 0
        for league in leagues_to_fix:
            if not dry_run:
                membership, created = LeagueMembership.objects.get_or_create(
                    user=league.commissioner,
                    league=league
                )
                if created:
                    fixed_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Added {league.commissioner.username} as member of '{league.name}'"
                        )
                    )
            else:
                self.stdout.write(
                    f"Would add {league.commissioner.username} as member of '{league.name}'"
                )
                fixed_count += 1
        
        # Set all leagues to approved if they aren't already
        unapproved_leagues = League.objects.filter(is_approved=False)
        if unapproved_leagues.exists() and not dry_run:
            updated_count = unapproved_leagues.update(is_approved=True)
            self.stdout.write(
                self.style.SUCCESS(f"✓ Approved {updated_count} leagues")
            )
        elif unapproved_leagues.exists() and dry_run:
            self.stdout.write(f"Would approve {unapproved_leagues.count()} leagues")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN COMPLETE - Would fix {fixed_count} league memberships. "
                    "Run without --dry-run to apply changes."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully fixed {fixed_count} league memberships!")
            )