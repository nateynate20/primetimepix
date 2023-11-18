from django.contrib import admin
from .models import UserRecord, GameSelection, League

admin.site.register(UserRecord)
admin.site.register(GameSelection)
admin.site.register(League)