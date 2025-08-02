# game_picks/forms.py
from django import forms
from .models import GameSelection, LeagueCreationRequest, LeagueJoinRequest, League

class GameSelectionForm(forms.ModelForm):
    class Meta:
        model = GameSelection
        fields = ['predicted_winner']

class LeagueCreationRequestForm(forms.ModelForm):
    class Meta:
        model = LeagueCreationRequest
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class LeagueJoinRequestForm(forms.ModelForm):
    league = forms.ModelChoiceField(
        queryset=League.objects.filter(is_approved=True),
        label="Select League",
        empty_label="Choose a league"
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            # Exclude leagues the user is already a member of
            self.fields['league'].queryset = League.objects.filter(is_approved=True).exclude(members=self.user)

    def clean_league(self):
        league = self.cleaned_data.get('league')
        if self.user and league and self.user in league.members.all():
            raise forms.ValidationError("You are already a member of this league.")
        return league

    class Meta:
        model = LeagueJoinRequest
        fields = ['league']
