from django.shortcuts import render
from django.http import HttpResponse
from django.core.mail import send_mail
from django.conf import settings
from apps.games.models import Game
from django.contrib.auth.models import User

def landing_page(request):
    context = {
        'total_games': Game.objects.count(),
        'primetime_games': sum(1 for g in Game.objects.all() if g.is_primetime),
        'active_users': User.objects.filter(is_active=True).count(),
    }
    return render(request, 'nflpix/landing_page.html', context)

def test_email(request):
    """Temporary function to test email in production"""
    try:
        # Show email configuration
        config_info = f"""
        Email Backend: {settings.EMAIL_BACKEND}
        Email Host: {settings.EMAIL_HOST}
        Email Port: {settings.EMAIL_PORT}
        Email Use TLS: {settings.EMAIL_USE_TLS}
        Email Host User: {settings.EMAIL_HOST_USER}
        Email Host Password Set: {bool(settings.EMAIL_HOST_PASSWORD)}
        Default From Email: {settings.DEFAULT_FROM_EMAIL}
        """
        
        # Try to send email
        result = send_mail(
            'PrimeTimePix Production Email Test',
            'This is a test email from your production server. If you receive this, email is working!',
            settings.DEFAULT_FROM_EMAIL,
            ['evansna05@gmail.com'],
            fail_silently=False,
        )
        
        return HttpResponse(f"""
        <h2>Email Test Results</h2>
        <h3>Configuration:</h3>
        <pre>{config_info}</pre>
        <h3>Send Result:</h3>
        <p>Email sent successfully! Result: {result}</p>
        <p>Check your email inbox for the test message.</p>
        """)
        
    except Exception as e:
        return HttpResponse(f"""
        <h2>Email Test Failed</h2>
        <h3>Configuration:</h3>
        <pre>{config_info if 'config_info' in locals() else 'Could not load config'}</pre>
        <h3>Error:</h3>
        <p style="color: red;">Email failed: {str(e)}</p>
        <p><strong>Error type:</strong> {type(e).__name__}</p>
        """)