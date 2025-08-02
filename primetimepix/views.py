# nflpix/views.py
from django.shortcuts import render

def landing_page(request):
    return render(request, 'nflpix/landing_page.html')
