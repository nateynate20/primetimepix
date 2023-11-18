# nflpix/views.py
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm


def landing_page(request):
    return render(request, 'nflpix/landing_page.html', {})
