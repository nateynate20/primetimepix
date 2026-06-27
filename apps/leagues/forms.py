# apps/leagues/forms.py
from django import forms
from .models import LeagueCreationRequest, LeagueJoinRequest, League


class LeagueCreateForm(forms.ModelForm):
    class Meta:
        model = League
        fields = ['name', 'description', 'sport', 'is_private']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white',
                'placeholder': 'Enter league name',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white',
                'placeholder': 'Optional description for your league',
                'rows': 3,
            }),
            'sport': forms.Select(attrs={
                'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white',
            }),
            'is_private': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 rounded bg-gray-700 border-gray-600',
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if League.objects.filter(name=name).exists():
            raise forms.ValidationError(f"A league named '{name}' already exists.")
        return name


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
        queryset=League.objects.none(),
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
        self.user = user

        if user:
            self.fields['league'].queryset = League.objects.filter(
                is_approved=True,
            ).exclude(members=user).order_by('name')

    def clean_league(self):
        league = self.cleaned_data.get('league')
        if hasattr(self, 'user') and self.user and league:
            if self.user in league.members.all():
                raise forms.ValidationError("You are already a member of this league.")
        return league