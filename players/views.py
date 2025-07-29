from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from players.forms import SignupUserForm  # import your custom form
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required



@login_required
def dashboard(request):
    user = request.user
    context = {
        'user': user,
        # Add any additional data you want to show on the dashboard
    }
    return render(request, 'user_dashboard.html', context)


def landing_page(request):
    return render(request, 'nflpix/landing.html')

def login_user(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('dashboard')

        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

def signup(request):
    if request.method == "POST":
        form = SignupUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully.")
            return redirect('dashboard')
')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SignupUserForm()
    return render(request, 'registration/signup.html', {'form': form})

@require_POST
def logout_user(request):
    logout(request)
    messages.success(request, "You have successfully logged out.")
    return redirect('landing_page')
