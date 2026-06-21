import pytest
from unittest.mock import patch, MagicMock
from backend.notifications.service import NotificationService


class TestNotificationServiceEmailNotConfigured:
    """Test email behavior when SMTP is not configured."""

    def test_send_email_returns_false_when_not_configured(self):
        """send_email should return False and log info when SMTP not configured."""
        with patch("backend.notifications.service.settings") as mock_settings:
            mock_settings.SMTP_HOST = None
            mock_settings.SMTP_USER = None
            mock_settings.SMTP_PASS = None

            service = NotificationService()
            result = service.send_email("test@example.com", "Subject", "Body")

            assert result is False

    def test_send_email_logs_skip_message_when_not_configured(self):
        """send_email should log info message when SMTP not configured."""
        with patch("backend.notifications.service.settings") as mock_settings:
            mock_settings.SMTP_HOST = None
            mock_settings.SMTP_USER = None
            mock_settings.SMTP_PASS = None

            with patch("backend.notifications.service.logger") as mock_logger:
                service = NotificationService()
                service.send_email("test@example.com", "Subject", "Body")

                mock_logger.info.assert_called_once()
                call_args = mock_logger.info.call_args[0][0]
                assert "SMTP not configured" in call_args
                assert "test@example.com" in call_args


class TestNotificationServiceEmailConfigured:
    """Test email behavior when SMTP is configured."""

    def test_send_email_returns_true_when_configured_and_successful(self):
        """send_email should return True when SMTP configured and send succeeds."""
        with patch("backend.notifications.service.settings") as mock_settings:
            mock_settings.SMTP_HOST = "smtp.example.com"
            mock_settings.SMTP_USER = "user@example.com"
            mock_settings.SMTP_PASS = "secret"
            mock_settings.SMTP_PORT = "465"

            with patch("backend.notifications.service.smtplib.SMTP_SSL") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server

                service = NotificationService()
                result = service.send_email("test@example.com", "Subject", "Body")

                assert result is True
                mock_server.login.assert_called_once_with("user@example.com", "secret")
                mock_server.send_message.assert_called_once()

    def test_send_email_returns_false_on_exception(self):
        """send_email should return False and log error on SMTP exception."""
        with patch("backend.notifications.service.settings") as mock_settings:
            mock_settings.SMTP_HOST = "smtp.example.com"
            mock_settings.SMTP_USER = "user@example.com"
            mock_settings.SMTP_PASS = "secret"
            mock_settings.SMTP_PORT = "465"

            with patch("backend.notifications.service.smtplib.SMTP_SSL") as mock_smtp:
                mock_smtp.side_effect = Exception("Connection failed")

                with patch("backend.notifications.service.logger") as mock_logger:
                    service = NotificationService()
                    result = service.send_email("test@example.com", "Subject", "Body")

                    assert result is False
                    mock_logger.error.assert_called_once()
                    call_args = mock_logger.error.call_args[0][0]
                    assert "Email send failed" in call_args
                    assert "test@example.com" in call_args

    def test_send_email_does_not_log_password(self):
        """send_email error logs should not contain the SMTP password."""
        with patch("backend.notifications.service.settings") as mock_settings:
            mock_settings.SMTP_HOST = "smtp.example.com"
            mock_settings.SMTP_USER = "user@example.com"
            mock_settings.SMTP_PASS = "secret-password"
            mock_settings.SMTP_PORT = "465"

            with patch("backend.notifications.service.smtplib.SMTP_SSL") as mock_smtp:
                mock_smtp.side_effect = Exception("Auth failed")

                with patch("backend.notifications.service.logger") as mock_logger:
                    service = NotificationService()
                    service.send_email("test@example.com", "Subject", "Body")

                    error_call_args = mock_logger.error.call_args[0][0]
                    assert "secret-password" not in error_call_args


class TestNotificationServiceSMSNotConfigured:
    """Test SMS behavior when Twilio is not configured."""

    def test_send_sms_returns_false_when_not_configured(self):
        """send_sms should return False and log info when Twilio not configured."""
        with patch("backend.notifications.service.settings") as mock_settings:
            mock_settings.SMTP_HOST = None
            mock_settings.SMTP_USER = None
            mock_settings.SMTP_PASS = None
            mock_settings.TWILIO_ACCOUNT_SID = None
            mock_settings.TWILIO_AUTH_TOKEN = None
            mock_settings.TWILIO_FROM_NUMBER = None

            service = NotificationService()
            result = service.send_sms("+1234567890", "Message")

            assert result is False

    def test_send_sms_logs_skip_message_when_not_configured(self):
        """send_sms should log info message when Twilio not configured."""
        with patch("backend.notifications.service.settings") as mock_settings:
            mock_settings.SMTP_HOST = None
            mock_settings.SMTP_USER = None
            mock_settings.SMTP_PASS = None
            mock_settings.TWILIO_ACCOUNT_SID = None
            mock_settings.TWILIO_AUTH_TOKEN = None
            mock_settings.TWILIO_FROM_NUMBER = None

            with patch("backend.notifications.service.logger") as mock_logger:
                service = NotificationService()
                service.send_sms("+1234567890", "Message")

                mock_logger.info.assert_called_once()
                call_args = mock_logger.info.call_args[0][0]
                assert "Twilio not configured" in call_args
                assert "+1234567890" in call_args


class TestNotificationServiceSMSConfigured:
    """Test SMS behavior when Twilio is configured."""

    def test_send_sms_returns_true_when_configured_and_successful(self):
        """send_sms should return True when Twilio configured and send succeeds."""
        with patch("backend.notifications.service.settings") as mock_settings:
            mock_settings.SMTP_HOST = None
            mock_settings.SMTP_USER = None
            mock_settings.SMTP_PASS = None
            mock_settings.TWILIO_ACCOUNT_SID = "test-sid"
            mock_settings.TWILIO_AUTH_TOKEN = "test-token"
            mock_settings.TWILIO_FROM_NUMBER = "+1111111111"

            with patch("twilio.rest.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                service = NotificationService()
                result = service.send_sms("+1234567890", "Message")

                assert result is True
                mock_client_class.assert_called_once_with("test-sid", "test-token")
                mock_client.messages.create.assert_called_once_with(
                    body="Message",
                    from_="+1111111111",
                    to="+1234567890"
                )

    def test_send_sms_returns_false_on_exception(self):
        """send_sms should return False and log error on Twilio exception."""
        with patch("backend.notifications.service.settings") as mock_settings:
            mock_settings.SMTP_HOST = None
            mock_settings.SMTP_USER = None
            mock_settings.SMTP_PASS = None
            mock_settings.TWILIO_ACCOUNT_SID = "test-sid"
            mock_settings.TWILIO_AUTH_TOKEN = "test-token"
            mock_settings.TWILIO_FROM_NUMBER = "+1111111111"

            with patch("twilio.rest.Client") as mock_client_class:
                mock_client_class.side_effect = Exception("API error")

                with patch("backend.notifications.service.logger") as mock_logger:
                    service = NotificationService()
                    result = service.send_sms("+1234567890", "Message")

                    assert result is False
                    mock_logger.error.assert_called_once()
                    call_args = mock_logger.error.call_args[0][0]
                    assert "SMS send failed" in call_args
                    assert "+1234567890" in call_args

    def test_send_sms_does_not_log_auth_token(self):
        """send_sms error logs should not contain the Twilio auth token."""
        with patch("backend.notifications.service.settings") as mock_settings:
            mock_settings.SMTP_HOST = None
            mock_settings.SMTP_USER = None
            mock_settings.SMTP_PASS = None
            mock_settings.TWILIO_ACCOUNT_SID = "test-sid"
            mock_settings.TWILIO_AUTH_TOKEN = "secret-token-xyz"
            mock_settings.TWILIO_FROM_NUMBER = "+1111111111"

            with patch("twilio.rest.Client") as mock_client_class:
                mock_client_class.side_effect = Exception("Auth failed")

                with patch("backend.notifications.service.logger") as mock_logger:
                    service = NotificationService()
                    service.send_sms("+1234567890", "Message")

                    error_call_args = mock_logger.error.call_args[0][0]
                    assert "secret-token-xyz" not in error_call_args
