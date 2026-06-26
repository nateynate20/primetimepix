from django.core.management.base import BaseCommand
from apps.picks.models import CPUPick


class Command(BaseCommand):
    help = 'Resolve CPU picks for completed games'

    def handle(self, *args, **options):
        unresolved = CPUPick.objects.filter(
            is_correct__isnull=True,
            game__status='final'
        ).select_related('game')

        resolved = 0
        for cpu_pick in unresolved:
            result = cpu_pick.resolve()
            if result is not None:
                status = "CORRECT" if result else "WRONG"
                self.stdout.write(f"  {cpu_pick.game}: CPU picked {cpu_pick.picked_team} -> {status}")
                resolved += 1

        self.stdout.write(self.style.SUCCESS(f"Resolved {resolved} CPU pick(s)."))
