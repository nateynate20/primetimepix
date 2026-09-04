# apps/leagues/forms.py
import re

from django import forms
from .models import LeagueCreationRequest, LeagueJoinRequest, League


class LeagueCreateForm(forms.ModelForm):
    class Meta:
        model = League
        fields = ['name', 'description', 'sport', 'is_private']
        _input_class = (
            'w-full px-4 py-2.5 bg-gray-50 dark:bg-gray-900 border border-gray-200 '
            'dark:border-gray-600 rounded-lg text-sm font-medium text-gray-900 '
            'dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none '
            'focus:border-accent-500 dark:focus:border-neon focus:ring-2 '
            'focus:ring-accent-500/20 dark:focus:ring-neon/20'
        )
        widgets = {
            'name': forms.TextInput(attrs={
                'class': _input_class,
                'placeholder': 'Enter league name',
            }),
            'description': forms.Textarea(attrs={
                'class': _input_class,
                'placeholder': 'Optional description for your league',
                'rows': 3,
            }),
            'sport': forms.Select(attrs={
                'class': _input_class,
            }),
            'is_private': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 rounded text-accent-600 dark:text-neon border-gray-300 dark:border-gray-600 focus:ring-accent-500 dark:focus:ring-neon',
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if League.objects.filter(name=name).exists():
            raise forms.ValidationError(f"A league named '{name}' already exists.")
        return name


class LeagueEditForm(forms.ModelForm):
    """Used by commissioners/co-commissioners to edit basic league details."""
    class Meta:
        model = League
        fields = ['name', 'description', 'join_code']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-3 text-gray-900 dark:text-white',
                'placeholder': 'Enter league name',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-3 text-gray-900 dark:text-white',
                'placeholder': 'Optional description for your league',
                'rows': 3,
            }),
            'join_code': forms.TextInput(attrs={
                'class': 'w-full bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-3 text-gray-900 dark:text-white font-mono uppercase',
                'placeholder': 'e.g. CHIEFS24',
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        qs = League.objects.filter(name=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f"A league named '{name}' already exists.")
        return name

    def clean_join_code(self):
        code = (self.cleaned_data.get('join_code') or '').strip().upper()
        # Blank means "keep the current code".
        if not code:
            return self.instance.join_code if self.instance and self.instance.pk else code
        if not re.fullmatch(r'[A-Z0-9-]{4,20}', code):
            raise forms.ValidationError(
                "Use 4–20 characters: letters, numbers, or hyphens only."
            )
        qs = League.objects.filter(join_code=code)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("That invite code is already taken. Try another.")
        return code


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