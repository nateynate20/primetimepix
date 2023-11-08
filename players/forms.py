# nflpix/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class SignupUserForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(max_length=254, required=True)
    phone_number = forms.CharField(max_length=15, required=True)
    team_name = forms.CharField(max_length=15, required=True)


    class Meta:
        model = User
        fields = ('username','email', 'password1', 'password2', 'first_name', 'last_name','phone_number', 'team_name')

