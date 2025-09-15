# apps/users/management/commands/debug_sendgrid.py
# Run with: python manage.py debug_sendgrid

from django.core.management.base import BaseCommand
from django.conf import settings
import os
import requests


class Command(BaseCommand):
    help = 'Debug SendGrid configuration and test API directly'

    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write("SENDGRID DEEP DEBUGGING")
        self.stdout.write("=" * 60)
        
        # 1. Check API Key
        api_key = os.getenv('SENDGRID_API_KEY', '')
        if not api_key:
            self.stdout.write(self.style.ERROR("❌ No API key found!"))
            return
        
        self.stdout.write(f"✅ API Key found: {api_key[:7]}...{api_key[-4:]}")
        
        # 2. Test API Key validity
        self.stdout.write("\n📋 Testing API Key Validity...")
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # Test API key by getting account info
        response = requests.get(
            'https://api.sendgrid.com/v3/user/profile',
            headers=headers
        )
        
        if response.status_code == 200:
            self.stdout.write(self.style.SUCCESS("✅ API Key is valid!"))
            profile = response.json()
            self.stdout.write(f"Account Email: {profile.get('email', 'N/A')}")
        else:
            self.stdout.write(self.style.ERROR(f"❌ API Key validation failed: {response.status_code}"))
            self.stdout.write(f"Response: {response.text}")
            return
        
        # 3. Check verified senders
        self.stdout.write("\n📋 Checking Verified Senders...")
        response = requests.get(
            'https://api.sendgrid.com/v3/verified_senders',
            headers=headers
        )
        
        if response.status_code == 200:
            senders = response.json().get('results', [])
            if senders:
                self.stdout.write(self.style.SUCCESS(f"✅ Found {len(senders)} verified sender(s):"))
                for sender in senders:
                    status = "✅ Verified" if sender.get('verified') else "⚠️  Pending"
                    self.stdout.write(f"  {status} - {sender.get('from_email')} ({sender.get('from_name', 'No name')})")
                    if sender.get('from_email') == settings.DEFAULT_FROM_EMAIL:
                        self.stdout.write(self.style.SUCCESS(f"    ✅ This matches your DEFAULT_FROM_EMAIL!"))
            else:
                self.stdout.write(self.style.ERROR("❌ No verified senders found!"))
                self.stdout.write("You need to add and verify a sender at:")
                self.stdout.write("https://app.sendgrid.com/settings/sender_auth/senders")
        else:
            self.stdout.write(self.style.ERROR(f"❌ Failed to get senders: {response.status_code}"))
            self.stdout.write(f"Response: {response.text}")
        
        # 4. Check domain authentication
        self.stdout.write("\n📋 Checking Domain Authentication...")
        response = requests.get(
            'https://api.sendgrid.com/v3/whitelabel/domains',
            headers=headers
        )
        
        if response.status_code == 200:
            domains = response.json()
            if domains:
                self.stdout.write(f"Found {len(domains)} authenticated domain(s)")
                for domain in domains:
                    if domain.get('valid'):
                        self.stdout.write(f"  ✅ {domain.get('domain')} - Valid")
                    else:
                        self.stdout.write(f"  ⚠️  {domain.get('domain')} - Not Valid")
            else:
                self.stdout.write("ℹ️  No authenticated domains (this is okay for single sender)")
        
        # 5. Test sending with raw API
        self.stdout.write("\n📋 Testing Email Send via API...")
        self.stdout.write(f"From: {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"To: evansna05@gmail.com")
        
        email_data = {
            "personalizations": [{
                "to": [{"email": "evansna05@gmail.com"}]
            }],
            "from": {
                "email": settings.DEFAULT_FROM_EMAIL,
                "name": "PrimeTimePix"
            },
            "subject": "SendGrid API Test",
            "content": [{
                "type": "text/plain",
                "value": "This is a test email sent directly via SendGrid API."
            }]
        }
        
        response = requests.post(
            'https://api.sendgrid.com/v3/mail/send',
            headers=headers,
            json=email_data
        )
        
        if response.status_code == 202:
            self.stdout.write(self.style.SUCCESS("✅ Email sent successfully via API!"))
            self.stdout.write("Check your inbox!")
        else:
            self.stdout.write(self.style.ERROR(f"❌ Failed to send: {response.status_code}"))
            self.stdout.write(f"Response: {response.text}")
            
            # Parse error message
            if response.text:
                import json
                try:
                    error = json.loads(response.text)
                    for err in error.get('errors', []):
                        self.stdout.write(f"Error: {err.get('message')}")
                        if err.get('field'):
                            self.stdout.write(f"Field: {err.get('field')}")
                except:
                    pass
        
        # 6. Recommendations
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("RECOMMENDATIONS:")
        self.stdout.write("=" * 60)
        
        if settings.DEFAULT_FROM_EMAIL != "evansna05@gmail.com":
            self.stdout.write(f"⚠️  Your DEFAULT_FROM_EMAIL is '{settings.DEFAULT_FROM_EMAIL}'")
            self.stdout.write("   but you're trying to verify 'evansna05@gmail.com'")
            self.stdout.write("   Make sure they match!")
        
        self.stdout.write("\nIf you're still having issues:")
        self.stdout.write("1. Try deleting and re-adding the sender in SendGrid")
        self.stdout.write("2. Make sure you clicked the verification link in the email")
        self.stdout.write("3. Try using a different email address")
        self.stdout.write("4. Consider using Domain Authentication instead of Single Sender")
        self.stdout.write("\n" + "=" * 60)