from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile


class SignupUserForm(UserCreationForm):
    email = forms.EmailField(max_length=254, required=True, widget=forms.EmailInput(attrs={'class':'form-control'}))
    team_name = forms.CharField(max_length=15, required=True, widget=forms.TextInput(attrs={'class':'form-control'}))

    class Meta:
        model = User
        fields = ('username', 'email', 'team_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ['username', 'password1', 'password2']:
            self.fields[field].widget.attrs['class'] = 'form-control'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already registered")
        return email

    def clean_team_name(self):
        team_name = self.cleaned_data.get('team_name')
        if Profile.objects.filter(team_name=team_name).exists():
            raise forms.ValidationError("Team name already taken")
        return team_name

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            Profile.objects.update_or_create(
                user=user, defaults={'team_name': self.cleaned_data['team_name']}
            )
        return user


class ProfileEditForm(forms.Form):
    team_name = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new team name',
        })
    )
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your email address',
        })
    )
    email_reminders_enabled = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_team_name(self):
        team_name = self.cleaned_data.get('team_name')
        existing = Profile.objects.filter(team_name=team_name).exclude(user=self.user)
        if existing.exists():
            raise forms.ValidationError("Team name already taken.")
        return team_name

    def clean_email(self):
        email = self.cleaned_data.get('email')
        existing = User.objects.filter(email=email).exclude(pk=self.user.pk)
        if existing.exists():
            raise forms.ValidationError("Email already in use by another account.")
        return email
