import base64
import os
from unittest import mock

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from django.core.management import call_command

from notifications import push
from notifications.models import PushSubscription

pytestmark = pytest.mark.django_db


def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def test_generated_keys_sign_and_encrypt_a_real_push(settings, mic, capsys):
    call_command("generate_vapid_keys")
    keys = dict(line.split("=", 1) for line in capsys.readouterr().out.splitlines())
    settings.VAPID_PRIVATE_KEY = keys["VAPID_PRIVATE_KEY"]
    settings.VAPID_PUBLIC_KEY = keys["VAPID_PUBLIC_KEY"]
    assert len(base64.urlsafe_b64decode(keys["VAPID_PUBLIC_KEY"] + "==")) == 65

    device = ec.generate_private_key(ec.SECP256R1())
    p256dh = b64url(
        device.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    )
    PushSubscription.objects.create(
        user=mic, endpoint="https://push.example/send/1", p256dh=p256dh, auth=b64url(os.urandom(16))
    )

    with mock.patch("requests.post") as post:
        post.return_value = mock.Mock(status_code=201, ok=True)
        assert push.send_to_user(mic, {"title": "Hello"}) == 1
    headers = post.call_args.kwargs["headers"]
    assert headers["authorization"].startswith("vapid t=")
    assert headers["content-encoding"] == "aes128gcm"
