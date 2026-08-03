# yourapp/utils.py
import hashlib
import hmac
from django.conf import settings
import os
import resend

resend.api_key = os.environ.get("RESEND_API_KEY")


def make_hash(value: str) -> str:
    normalized = value.strip().lower()
    return hmac.new(
        settings.HASH_SALT.encode(),
        normalized.encode(),
        hashlib.sha256
    ).hexdigest()





def send_email(to: str, subject: str, html: str, from_email: str = "onboarding@lenden.co.in"):
    """
    Send an email using Resend.

    Args:
        to: recipient email address (or list of addresses)
        subject: email subject line
        html: HTML content of the email
        from_email: verified sender address (defaults to Resend's test sender)

    Returns:
        dict response from Resend API (contains "id" on success)
    """
    params = {
        "from": from_email,
        "to": [to] if isinstance(to, str) else to,
        "subject": subject,
        "html": html,
    }

    return resend.Emails.send(params)