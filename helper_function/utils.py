# notifications/service.py
from firebase_admin import messaging
from accounts.models import FCMToken

def send_notification_to_user(user, title, body, data=None):
    """Send notification to all devices of a user."""
    tokens = FCMToken.objects.filter(user=user).values_list("token", flat=True)

    if not tokens:
        return {"error": "No tokens found for user"}

    message = messaging.MulticastMessage(
        tokens=list(tokens),
        notification=messaging.Notification(title=title, body=body),
        data=data or {},  # extra payload (must be dict of strings)
    )

    response = messaging.send_each_for_multicast(message)
    return {
        "success_count": response.success_count,
        "failure_count": response.failure_count,
    }


def send_notification_to_topic(topic, title, body, data=None):
    """Send notification to a Firebase topic."""
    message = messaging.Message(
        topic=topic,
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
    )
    response = messaging.send(message)
    return {"message_id": response}


def send_notification_to_token(token, title, body, data=None):
    """Send notification to a single device token."""
    message = messaging.Message(
        token=token,
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
    )
    response = messaging.send(message)
    return {"message_id": response}