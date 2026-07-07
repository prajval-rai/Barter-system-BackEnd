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



from django.core.mail import EmailMultiAlternatives
from django.conf import settings


def send_html_email(subject, plain_message, html_message, recipient_list):
    """
    Sends an email with both plain-text and HTML parts.
    recipient_list can be a string (single address) or a list.
    """
    if isinstance(recipient_list, str):
        recipient_list = [recipient_list]

    email = EmailMultiAlternatives(
        subject=subject,
        body=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipient_list,
    )
    email.attach_alternative(html_message, "text/html")
    email.send(fail_silently=False)

def build_admin_review_email(product, review_url):
    owner = product.owner
    image = product.images.first() if hasattr(product, "images") else None
    image_url = image.image.url if image else None

    plain_message = (
        f"New product listed for review\n\n"
        f"Title: {product.title}\n"
        f"Owner: {owner.username} ({getattr(owner, 'contact_number', 'N/A')})\n"
        f"Category: {getattr(product, 'category_name', '')}\n\n"
        f"Review it here: {review_url}"
    )

    html_message = f"""
    <html>
      <body style="margin:0; padding:0; background-color:#F8FAFF; font-family: 'DM Sans', Arial, sans-serif;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#F8FAFF; padding:32px 0;">
          <tr>
            <td align="center">
              <table role="presentation" width="480" cellpadding="0" cellspacing="0"
                     style="background:#ffffff; border-radius:12px; overflow:hidden; border:1px solid #E2E8F0; box-shadow:0 2px 12px rgba(15,23,42,0.08);">

                <!-- Header -->
                <tr>
                  <td style="background:linear-gradient(180deg,#D9ECFF 0%,#FFFFFF 100%); padding:20px 24px; border-bottom:1px solid #E2E8F0;">
                    <span style="display:inline-block; font-size:10px; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; color:#1A56DB; border:1px solid rgba(26,86,219,0.3); background:rgba(26,86,219,0.06); padding:3px 10px; border-radius:9999px;">
                      New Listing
                    </span>
                    <h1 style="margin:10px 0 0; font-size:20px; font-weight:700; color:#0C1B35; font-family: 'Plus Jakarta Sans', Arial, sans-serif;">
                      Product Awaiting Review
                    </h1>
                  </td>
                </tr>

                <!-- Product image -->
                {f'''
                <tr>
                  <td style="padding:0;">
                    <img src="{image_url}" alt="{product.title}" width="480" style="display:block; width:100%; height:auto; max-height:260px; object-fit:cover;">
                  </td>
                </tr>
                ''' if image_url else ''}

                <!-- Product details -->
                <tr>
                  <td style="padding:24px;">
                    <h2 style="margin:0 0 4px; font-size:16px; font-weight:700; color:#0C1B35; font-family: 'Plus Jakarta Sans', Arial, sans-serif;">
                      {product.title}
                    </h2>
                    <p style="margin:0 0 16px; font-size:13px; color:#94A3B8; line-height:1.5;">
                      {getattr(product, 'description', '') or 'No description provided.'}
                    </p>

                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #F0F6FB; padding-top:14px; margin-top:6px;">
                      <tr>
                        <td style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:#94A3B8; padding:6px 0;">Owner</td>
                        <td style="font-size:13px; color:#475569; text-align:right; padding:6px 0;">{owner.username}</td>
                      </tr>
                      <tr>
                        <td style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:#94A3B8; padding:6px 0;">Contact</td>
                        <td style="font-size:13px; color:#475569; text-align:right; padding:6px 0;">{getattr(owner, 'contact_number', 'N/A')}</td>
                      </tr>
                      <tr>
                        <td style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:#94A3B8; padding:6px 0;">Category</td>
                        <td style="font-size:13px; color:#475569; text-align:right; padding:6px 0;">{getattr(product, 'category_name', '—')}</td>
                      </tr>
                    </table>

                    <!-- CTA -->
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:22px;">
                      <tr>
                        <td align="center">
                          <a href="{review_url}"
                             style="display:inline-block; background:#1A56DB; color:#ffffff; text-decoration:none; font-size:14px; font-weight:700; padding:12px 28px; border-radius:8px; font-family: 'Plus Jakarta Sans', Arial, sans-serif;">
                            Review Product →
                          </a>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>

                <!-- Footer -->
                <tr>
                  <td style="padding:16px 24px; background:#F8FAFF; border-top:1px solid #F0F6FB;">
                    <p style="margin:0; font-size:11px; color:#94A3B8; text-align:center;">
                      BarterApp Admin Notifications
                    </p>
                  </td>
                </tr>

              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    return plain_message, html_message