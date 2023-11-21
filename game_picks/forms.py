# game_picks/forms.py
from django import forms
from .models import GameSelection

class GameSelectionForm(forms.ModelForm):
    class Meta:
        model = GameSelection
        fields = ['predicted_winner']