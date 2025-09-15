from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Test SendGrid email configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            default='evansna05@gmail.com',
            help='Email address to send test to',
        )

    def handle(self, *args, **options):
        to_email = options['to']
        
        self.stdout.write("=" * 60)
        self.stdout.write("SENDGRID CONFIGURATION TEST")
        self.stdout.write("=" * 60)
        
        # Check configuration
        self.stdout.write("\n📋 Configuration Check:")
        self.stdout.write(f"EMAIL_HOST: {settings.EMAIL_HOST}")
        self.stdout.write(f"EMAIL_PORT: {settings.EMAIL_PORT}")
        self.stdout.write(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
        
        api_key = os.getenv('SENDGRID_API_KEY', '')
        if api_key:
            self.stdout.write(f"SENDGRID_API_KEY: {api_key[:20]}... (hidden)")
        else:
            self.stdout.write(self.style.ERROR("❌ SENDGRID_API_KEY is NOT SET!"))
            self.stdout.write("\nTo fix this:")
            self.stdout.write("1. Get your API key from https://app.sendgrid.com/settings/api_keys")
            self.stdout.write("2. Set it in your .env file: SENDGRID_API_KEY=SG.your-key-here")
            return
        
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        
        # IMPORTANT: Check sender verification
        self.stdout.write("\n⚠️  IMPORTANT: Sender Verification")
        self.stdout.write(f"Make sure '{settings.DEFAULT_FROM_EMAIL}' is verified in SendGrid!")
        self.stdout.write("Go to: https://app.sendgrid.com/settings/sender_auth/senders")
        
        # Test email
        self.stdout.write(f"\n📧 Attempting to send test email to: {to_email}")
        
        try:
            result = send_mail(
                subject='PrimeTimePix - SendGrid Test Email',
                message='This is a plain text test from PrimeTimePix.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
            )
            
            if result:
                self.stdout.write(self.style.SUCCESS(f"✅ Email sent successfully to {to_email}!"))
                self.stdout.write("Check your inbox (and spam folder).")
            else:
                self.stdout.write(self.style.ERROR("❌ Email send returned False"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Email failed: {str(e)}"))
            self.stdout.write("\nTroubleshooting:")
            self.stdout.write("1. Verify your SendGrid API key is correct")
            self.stdout.write("2. Ensure your sender email is verified in SendGrid")
            
            # Additional debug info
            if "550" in str(e):
                self.stdout.write("\n⚠️  Error 550: Sender not verified!")
            elif "401" in str(e):
                self.stdout.write("\n⚠️  Error 401: Invalid API key!")
        
        self.stdout.write("\n" + "=" * 60)