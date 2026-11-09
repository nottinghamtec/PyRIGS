import base64

from cryptography.hazmat.primitives import serialization
from django.core.management.base import BaseCommand
from py_vapid import Vapid


def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


class Command(BaseCommand):
    help = "Prints a new VAPID key pair for web push, as environment variables."

    def handle(self, *args, **options):
        vapid = Vapid()
        vapid.generate_keys()
        private = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
        public = vapid.public_key.public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
        self.stdout.write(f"VAPID_PRIVATE_KEY={b64url(private)}")
        self.stdout.write(f"VAPID_PUBLIC_KEY={b64url(public)}")
