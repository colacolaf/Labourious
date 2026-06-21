import smtplib
from email.message import EmailMessage
from backend.config import settings
from backend.utils.logger import logger


class NotificationService:
    def __init__(self):
        self.smtp_configured = bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASS)
        self.sms_configured = bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER)

    def send_email(self, to: str, subject: str, body: str) -> bool:
        if not self.smtp_configured:
            logger.info(f"SMTP not configured, skipping email to {to}")
            return False
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_USER
            msg["To"] = to
            msg.set_content(body)
            with smtplib.SMTP_SSL(settings.SMTP_HOST, int(settings.SMTP_PORT or 465)) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Email send failed to {to}: {e}")
            return False

    def send_sms(self, to: str, body: str) -> bool:
        if not self.sms_configured:
            logger.info(f"Twilio not configured, skipping SMS to {to}")
            return False
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(body=body, from_=settings.TWILIO_FROM_NUMBER, to=to)
            return True
        except Exception as e:
            logger.error(f"SMS send failed to {to}: {e}")
            return False
