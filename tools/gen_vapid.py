"""Create a VAPID key pair for web push notifications.

    pip install py-vapid
    python tools/gen_vapid.py

Public key  -> fixtures.json -> "push" -> "publicKey"   (public, goes to the browsers)
Private key -> GitHub secret VAPID_PRIVATE_KEY          (never commit it)
Changing the keys makes every existing subscription invalid; people have to turn notifications on again.
"""
import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid


def b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


v = Vapid()
v.generate_keys()
public = v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
private = v.private_key.private_numbers().private_value.to_bytes(32, "big")
print("PUBLIC  (fixtures.json -> push.publicKey):", b64(public))
print("PRIVATE (GitHub secret VAPID_PRIVATE_KEY):", b64(private))
