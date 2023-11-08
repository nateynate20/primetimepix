from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from .forms import SignupUserForm

def login_user(request):
    if request.method == 'POST':
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.success(request=("There was a Error logging in, Try again SMH"))
            return redirect('login')
            pass
    else:
        return render(request, 'registration/login.html', {})

def logout_user(request):
    logout(request)
    messages.success(request=("you have logged out"))
    return redirect('home')

def signup(request):
    if request.method == 'POST':
        form = SignupUserForm(request.POST)
        if form.is_valid():
            form.save()
            # Automatically log in the user after registration
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request=("you have signed up.. good luck"))
                return redirect('home')
    else:
        form = SignupUserForm()

    return render(request, 'registration/signup.html', {'form': form,})



# Create your views here.
