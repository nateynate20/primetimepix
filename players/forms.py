from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from players.models import Profile

class SignupUserForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class':'form-control'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class':'form-control'}))
    email = forms.EmailField(max_length=254, required=True, widget=forms.EmailInput(attrs={'class':'form-control'}))
    team_name = forms.CharField(max_length=15, required=True, widget=forms.TextInput(attrs={'class':'form-control'}))

    class Meta:
        model = User
        fields = ('username','first_name', 'last_name','email', 'team_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super(SignupUserForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['class'] = 'form-control'
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['class'] = 'form-control'

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
        user = super(SignupUserForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            Profile.objects.create(user=user, team_name=self.cleaned_data['team_name'])
        return user
