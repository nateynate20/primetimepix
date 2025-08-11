# apps/leagues/forms.py
from django import forms
from .models import LeagueCreationRequest, LeagueJoinRequest

class LeagueCreationRequestForm(forms.ModelForm):
    class Meta:
        model = LeagueCreationRequest
        fields = ['approved']

class LeagueJoinRequestForm(forms.ModelForm):
    class Meta:
        model = LeagueJoinRequest
        fields = ['approved']
