# apps/leagues/forms.py
from django import forms
from .models import LeagueCreationRequest, LeagueJoinRequest, League

class LeagueCreationRequestForm(forms.ModelForm):
    league_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter league name'
        }),
        label='League Name'
    )
    
    class Meta:
        model = LeagueCreationRequest
        fields = ['league_name']

class LeagueJoinRequestForm(forms.ModelForm):
    league = forms.ModelChoiceField(
        queryset=League.objects.filter(is_approved=True, is_private=False),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Choose a league to join",
        label="Select League"
    )

    class Meta:
        model = LeagueJoinRequest
        fields = ['league']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Exclude leagues where user is already a member
            self.fields['league'].queryset = League.objects.filter(
                is_approved=True,
                is_private=False
            ).exclude(members=user)

    def clean_league(self):
        league = self.cleaned_data.get('league')
        if hasattr(self, 'user') and self.user and league and self.user in league.members.all():
            raise forms.ValidationError("You are already a member of this league.")
        return league