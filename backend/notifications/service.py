import smtplib
import time
from email.message import EmailMessage
from typing import Optional
from backend.config import settings
from backend.utils.logger import logger


class NotificationService:
    def __init__(self):
        self.smtp_configured = bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASS)
        self.sms_configured = bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER)
        self._dedup_cache: dict[str, float] = {}
        self._cooldown_seconds = settings.NOTIFICATION_COOLDOWN_MINUTES * 60

    def _is_duped(self, dedup_key: Optional[str]) -> bool:
        if not dedup_key:
            return False
        last = self._dedup_cache.get(dedup_key, 0)
        if time.time() - last < self._cooldown_seconds:
            return True
        self._dedup_cache[dedup_key] = time.time()
        # ponytail: unbounded dict — fine at single-user scale; add LRU if memory grows
        return False

    def send_email(self, to: str, subject: str, body: str, dedup_key: Optional[str] = None) -> bool:
        if not self.smtp_configured:
            logger.info(f"SMTP not configured, skipping email to {to}")
            return False
        if self._is_duped(dedup_key):
            logger.debug(f"Notification deduped (key={dedup_key})")
            return False
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_USER
            msg["To"] = to
            msg.set_content(body)
            port = int(settings.SMTP_PORT or 465)
            # SendGrid relay uses port 587 (TLS), others use 465 (SSL)
            if port == 587:
                with smtplib.SMTP(settings.SMTP_HOST, port) as server:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASS)
                    server.send_message(msg)
            else:
                with smtplib.SMTP_SSL(settings.SMTP_HOST, port) as server:
                    server.login(settings.SMTP_USER, settings.SMTP_PASS)
                    server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Email send failed to {to}: {e}")
            return False

    def send_sms(self, to: str, body: str, dedup_key: Optional[str] = None) -> bool:
        if not self.sms_configured:
            logger.info(f"Twilio not configured, skipping SMS to {to}")
            return False
        if self._is_duped(dedup_key):
            logger.debug(f"SMS notification deduped (key={dedup_key})")
            return False
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(body=body, from_=settings.TWILIO_FROM_NUMBER, to=to)
            return True
        except Exception as e:
            logger.error(f"SMS send failed to {to}: {e}")
            return False
