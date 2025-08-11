# apps/picks/forms.py
from django import forms
from .models import Pick
from apps.leagues.models import LeagueCreationRequest, LeagueJoinRequest, League


class PickForm(forms.ModelForm):
    class Meta:
        model = Pick
        fields = ['picked_team']  # user, league, game will be set in view


class LeagueCreationRequestForm(forms.ModelForm):
    class Meta:
        model = LeagueCreationRequest
        fields = ['league_name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class LeagueJoinRequestForm(forms.ModelForm):
    league = forms.ModelChoiceField(
        queryset=League.objects.none(),  # Start with empty queryset
        label="Select League",
        empty_label="Choose a league"
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            # Only show leagues that are public (not private) and where user is NOT a member
            self.fields['league'].queryset = League.objects.filter(is_private=False).exclude(members=self.user)

    def clean_league(self):
        league = self.cleaned_data.get('league')
        if self.user and league and self.user in league.members.all():
            raise forms.ValidationError("You are already a member of this league.")
        return league

    class Meta:
        model = LeagueJoinRequest
        fields = ['league']
