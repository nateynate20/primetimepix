from datetime import timedelta
from django.db import migrations

def shift_times_forward(apps, schema_editor):
    Game = apps.get_model('games', 'Game')
    shift = timedelta(hours=5)  # Eastern saved as UTC — shift +5h to correct UTC
    for game in Game.objects.all():
        if game.start_time:
            game.start_time = game.start_time + shift
            game.save(update_fields=['start_time'])

def shift_times_backward(apps, schema_editor):
    Game = apps.get_model('games', 'Game')
    shift = timedelta(hours=5)
    for game in Game.objects.all():
        if game.start_time:
            game.start_time = game.start_time - shift
            game.save(update_fields=['start_time'])

class Migration(migrations.Migration):

    dependencies = [
        ('games', '0002_alter_game_game_type_alter_game_status'),
    ]

    operations = [
        migrations.RunPython(shift_times_forward, shift_times_backward),
    ]
