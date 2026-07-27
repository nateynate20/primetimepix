import uuid

from django.conf import settings
from django.db import migrations, models


def populate_invite_codes(apps, schema_editor):
    League = apps.get_model("leagues", "League")
    for league in League.objects.all():
        league.invite_code = uuid.uuid4()
        league.save(update_fields=["invite_code"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("leagues", "0003_default_leagues_public"),
    ]

    operations = [
        migrations.AddField(
            model_name="league",
            name="co_commissioners",
            field=models.ManyToManyField(
                blank=True,
                help_text="Members who can help manage this league. Must already be members of the league.",
                related_name="leagues_co_commissioned",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="league",
            name="invite_code",
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(populate_invite_codes, noop_reverse),
        migrations.AlterField(
            model_name="league",
            name="invite_code",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
