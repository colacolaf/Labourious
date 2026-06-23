import pytest
from unittest.mock import patch, MagicMock
import time


def test_notification_service_dedup_prevents_spam():
    """Same notification key sent twice within cooldown window is dropped."""
    from backend.notifications.service import NotificationService

    svc = NotificationService()
    svc.smtp_configured = True
    svc._dedup_cache = {}
    svc._cooldown_seconds = 5

    with patch("smtplib.SMTP") as mock_smtp, \
         patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        mock_smtp_ssl.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_ssl.return_value.__exit__ = MagicMock(return_value=False)

        first = svc.send_email("user@test.com", "Test", "body", dedup_key="key-1")
        second = svc.send_email("user@test.com", "Test", "body", dedup_key="key-1")

    assert first is True
    assert second is False  # deduped


def test_notification_service_dedup_expires():
    """Same key after cooldown window is sent again."""
    from backend.notifications.service import NotificationService

    svc = NotificationService()
    svc.smtp_configured = True
    svc._dedup_cache = {}
    svc._cooldown_seconds = 1

    with patch("smtplib.SMTP") as mock_smtp, \
         patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        mock_smtp_ssl.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_ssl.return_value.__exit__ = MagicMock(return_value=False)

        first = svc.send_email("user@test.com", "Test", "body", dedup_key="key-2")
        time.sleep(2.0)
        second = svc.send_email("user@test.com", "Test", "body", dedup_key="key-2")

    assert first is True
    assert second is True  # cooldown expired
