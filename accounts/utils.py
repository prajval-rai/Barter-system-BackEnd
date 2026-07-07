# yourapp/utils.py
import hashlib
import hmac
from django.conf import settings


def make_hash(value: str) -> str:
    normalized = value.strip().lower()
    return hmac.new(
        settings.HASH_SALT.encode(),
        normalized.encode(),
        hashlib.sha256
    ).hexdigest()