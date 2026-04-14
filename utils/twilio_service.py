from django.conf import settings
from twilio.rest import Client
from helper_function.config import Config

def send_whatsapp_message(to_number: str, message: str):
    """
    Send WhatsApp message using Twilio

    :param to_number: string (e.g. +919876543210)
    :param message: string
    :return: dict
    """
    # try:
    print("WWWWWWWWWWWWWWWWWWWWWWWWWWWWWWW",to_number,message)
    if not to_number or not message:
        return {
            "status": False,
            "error": "Phone number and message are required"
        }

    client = Client(
        Config.TWILIO_ACCOUNT_SID,
        Config.TWILIO_AUTH_TOKEN
    )

    print("........................",to_number)

    msg = client.messages.create(
        body=message,
        from_=Config.TWILIO_WHATSAPP_NUMBER,
        to=f"whatsapp:{to_number}"
    )

    print("***************************",msg)

    return {
        "status": True,
        "sid": msg.sid,
        "message": "Message sent successfully"
    }

    # except Exception as e:
    #     return {
    #         "status": False,
    #         "error": str(e)
    #     }