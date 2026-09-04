"""Generate a VAPID keypair for web push.

Run once, then set the printed values as env vars (VAPID_PUBLIC_KEY /
VAPID_PRIVATE_KEY) on the server. Keys are single-line base64url strings, safe
to paste into Railway env. Keep the private key secret; the public key is the
browser's applicationServerKey and is exposed to clients.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate a VAPID keypair (public/private) for web push notifications."

    def handle(self, *args, **options):
        from py_vapid import Vapid01
        from py_vapid.utils import b64urlencode
        from cryptography.hazmat.primitives import serialization

        v = Vapid01()
        v.generate_keys()

        public = b64urlencode(v.public_key.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        ))
        private = b64urlencode(
            v.private_key.private_numbers().private_value.to_bytes(32, 'big')
        )

        self.stdout.write(self.style.SUCCESS("VAPID keypair generated. Set these env vars:\n"))
        self.stdout.write(f"VAPID_PUBLIC_KEY={public}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={private}")
        self.stdout.write(self.style.WARNING(
            "\nKeep VAPID_PRIVATE_KEY secret. Restart the app after setting them."
        ))
