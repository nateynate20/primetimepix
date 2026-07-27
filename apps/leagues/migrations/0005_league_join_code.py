import secrets

from django.db import migrations, models

ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def _gen(length=8):
    return ''.join(secrets.choice(ALPHABET) for _ in range(length))


def populate_join_codes(apps, schema_editor):
    League = apps.get_model("leagues", "League")
    used = set()
    for league in League.objects.all():
        code = _gen()
        while code in used or League.objects.filter(join_code=code).exists():
            code = _gen()
        used.add(code)
        league.join_code = code
        league.save(update_fields=["join_code"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("leagues", "0004_co_commissioners_invite_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="league",
            name="join_code",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.RunPython(populate_join_codes, noop_reverse),
        migrations.AlterField(
            model_name="league",
            name="join_code",
            field=models.CharField(
                blank=True,
                help_text="Short, shareable code used in the invite link (e.g. CHIEFS24).",
                max_length=20,
                unique=True,
            ),
        ),
    ]
