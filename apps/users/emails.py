from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

class EmailService:
    """Centralized email service for the application"""
    
    @staticmethod
    def send_welcome_email(user):
        """Send welcome email to new users"""
        subject = f'Welcome to {settings.SITE_NAME}!'
        context = {
            'user': user,
            'site_name': settings.SITE_NAME,
            'site_url': settings.SITE_URL,
        }
        
        html_message = render_to_string('emails/welcome.html', context)
        plain_message = strip_tags(html_message)
        
        return send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
    
    @staticmethod
    def send_weekly_reminder(user, week, games):
        """Send weekly pick reminder"""
        subject = f'{settings.SITE_NAME} - Week {week} Primetime Picks Reminder'
        context = {
            'user': user,
            'week': week,
            'games': games,
            'site_name': settings.SITE_NAME,
            'picks_url': f"{settings.SITE_URL}/picks/?week={week}",
        }
        
        html_message = render_to_string('emails/weekly_reminder.html', context)
        plain_message = strip_tags(html_message)
        
        return send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
    
    @staticmethod
    def send_pick_confirmation(user, picks, league=None):
        """Send confirmation after picks are made"""
        subject = f'{settings.SITE_NAME} - Your Picks Have Been Saved'
        context = {
            'user': user,
            'picks': picks,
            'league': league,
            'site_name': settings.SITE_NAME,
            'standings_url': f"{settings.SITE_URL}/picks/standings/",
        }
        
        html_message = render_to_string('emails/pick_confirmation.html', context)
        plain_message = strip_tags(html_message)
        
        return send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
    
    @staticmethod
    def send_league_invite(user, league, inviter):
        """Send league invitation email"""
        subject = f'You\'ve been invited to join {league.name} on {settings.SITE_NAME}'
        context = {
            'user': user,
            'league': league,
            'inviter': inviter,
            'site_name': settings.SITE_NAME,
            'join_url': f"{settings.SITE_URL}/leagues/request-join/{league.id}/",
        }
        
        html_message = render_to_string('emails/league_invite.html', context)
        plain_message = strip_tags(html_message)
        
        return send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )