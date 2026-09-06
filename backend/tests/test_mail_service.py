"""Unit tests for app/services/mail.py (Issue #53 — SMTP notifications).

CI never has a reachable SMTP server, so every test here either keeps
SMTP_ENABLED=False (the default) or monkeypatches smtplib.SMTP with a
mock/fake object. The overriding requirement is that send_mail_safe must
never raise, regardless of configuration or SMTP failures.
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.no_db


def test_send_mail_safe_noop_when_disabled(monkeypatch):
    """SMTP_ENABLED=False (default) → no SMTP connection is attempted."""
    from app.core.config import settings
    from app.services import mail

    monkeypatch.setattr(settings, "SMTP_ENABLED", False)

    with patch("smtplib.SMTP") as mock_smtp:
        mail.send_mail_safe(to_email="user@example.com", subject="Subject", body="Body")
        mock_smtp.assert_not_called()


def test_send_mail_safe_noop_when_no_recipient(monkeypatch):
    """Empty recipient → skipped even when SMTP is enabled."""
    from app.core.config import settings
    from app.services import mail

    monkeypatch.setattr(settings, "SMTP_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")

    with patch("smtplib.SMTP") as mock_smtp:
        mail.send_mail_safe(to_email="", subject="Subject", body="Body")
        mock_smtp.assert_not_called()


def test_send_mail_safe_noop_when_no_host(monkeypatch):
    """Empty SMTP_HOST → skipped even when SMTP_ENABLED is true."""
    from app.core.config import settings
    from app.services import mail

    monkeypatch.setattr(settings, "SMTP_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_HOST", "")

    with patch("smtplib.SMTP") as mock_smtp:
        mail.send_mail_safe(to_email="user@example.com", subject="Subject", body="Body")
        mock_smtp.assert_not_called()


def test_send_mail_safe_sends_via_smtp_when_enabled(monkeypatch):
    """When enabled with a recipient/host, an EmailMessage is sent with the
    expected To/Subject/body, TLS is started, and login is attempted."""
    from app.core.config import settings
    from app.services import mail

    monkeypatch.setattr(settings, "SMTP_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_PORT", 587)
    monkeypatch.setattr(settings, "SMTP_USER", "smtp-user")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "smtp-pass")
    monkeypatch.setattr(settings, "SMTP_FROM", "no-reply@example.com")
    monkeypatch.setattr(settings, "SMTP_USE_TLS", True)

    mock_conn = MagicMock()
    mock_smtp_cls = MagicMock()
    mock_smtp_cls.return_value.__enter__.return_value = mock_conn

    with patch("smtplib.SMTP", mock_smtp_cls):
        mail.send_mail_safe(
            to_email="recipient@example.com",
            subject="通知の件名",
            body="通知の本文",
        )

    mock_smtp_cls.assert_called_once_with("smtp.example.com", 587, timeout=10)
    mock_conn.starttls.assert_called_once()
    mock_conn.login.assert_called_once_with("smtp-user", "smtp-pass")
    assert mock_conn.send_message.call_count == 1
    sent_message = mock_conn.send_message.call_args[0][0]
    assert sent_message["To"] == "recipient@example.com"
    assert sent_message["Subject"] == "通知の件名"
    assert sent_message["From"] == "no-reply@example.com"
    assert sent_message.get_content().strip() == "通知の本文"


def test_send_mail_safe_skips_login_without_smtp_user(monkeypatch):
    """No SMTP_USER configured → login() is never called (anonymous relay)."""
    from app.core.config import settings
    from app.services import mail

    monkeypatch.setattr(settings, "SMTP_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(settings, "SMTP_USER", "")
    monkeypatch.setattr(settings, "SMTP_USE_TLS", False)

    mock_conn = MagicMock()
    mock_smtp_cls = MagicMock()
    mock_smtp_cls.return_value.__enter__.return_value = mock_conn

    with patch("smtplib.SMTP", mock_smtp_cls):
        mail.send_mail_safe(
            to_email="recipient@example.com", subject="Subject", body="Body"
        )

    mock_conn.starttls.assert_not_called()
    mock_conn.login.assert_not_called()
    mock_conn.send_message.assert_called_once()


def test_send_mail_safe_swallows_connection_errors(monkeypatch):
    """SMTP connection/send errors must never propagate to the caller."""
    from app.core.config import settings
    from app.services import mail

    monkeypatch.setattr(settings, "SMTP_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")

    with patch("smtplib.SMTP", side_effect=OSError("connection refused")):
        # Must not raise.
        mail.send_mail_safe(
            to_email="recipient@example.com", subject="Subject", body="Body"
        )


def test_send_mail_safe_swallows_send_errors(monkeypatch):
    """Errors raised inside the SMTP session (e.g. send_message) are swallowed."""
    from app.core.config import settings
    from app.services import mail

    monkeypatch.setattr(settings, "SMTP_ENABLED", True)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")

    mock_conn = MagicMock()
    mock_conn.send_message.side_effect = RuntimeError("boom")
    mock_smtp_cls = MagicMock()
    mock_smtp_cls.return_value.__enter__.return_value = mock_conn

    with patch("smtplib.SMTP", mock_smtp_cls):
        # Must not raise.
        mail.send_mail_safe(
            to_email="recipient@example.com", subject="Subject", body="Body"
        )
