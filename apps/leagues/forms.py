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
    
    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Optional description for your league',
            'rows': 3
        }),
        label='Description (Optional)'
    )
    
    class Meta:
        model = LeagueCreationRequest
        fields = ['league_name', 'description']

class LeagueJoinRequestForm(forms.ModelForm):
    league = forms.ModelChoiceField(
        queryset=League.objects.none(),  # Will be set in __init__
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
            # Show only approved, public leagues where user is NOT already a member
            self.fields['league'].queryset = League.objects.filter(
                is_approved=True,
                is_private=False
            ).exclude(members=user).order_by('name')

    def clean_league(self):
        league = self.cleaned_data.get('league')
        if hasattr(self, 'user') and self.user and league:
            if self.user in league.members.all():
                raise forms.ValidationError("You are already a member of this league.")
        return league