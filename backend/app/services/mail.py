"""Outbound email delivery via SMTP.

``send_mail_safe`` is intended to run as a FastAPI ``BackgroundTask`` so a
disabled, misconfigured, or unreachable SMTP server never blocks the
triggering request — or, in CI/local dev (``SMTP_ENABLED=False`` by
default), the test suite. All failures are caught and logged as warnings;
nothing is ever re-raised to the caller.
"""

import smtplib
from email.message import EmailMessage

import structlog

from app.core.config import settings

logger = structlog.get_logger()


def send_mail_safe(to_email: str, subject: str, body: str) -> None:
    """Best-effort plaintext email send. Never raises."""
    if not settings.SMTP_ENABLED:
        logger.debug("mail_skipped", reason="smtp_disabled", to=to_email)
        return
    if not to_email:
        logger.debug("mail_skipped", reason="no_recipient")
        return
    if not settings.SMTP_HOST:
        logger.debug("mail_skipped", reason="no_smtp_host")
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM
    message["To"] = to_email
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            if settings.SMTP_USER:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        logger.info("mail_sent", to=to_email, subject=subject)
    except Exception as exc:
        # Deliberately broad: any SMTP/network failure must not propagate to
        # the request path (or fail tests) — email is a best-effort side
        # channel, not a transactional guarantee.
        logger.warning("mail_send_failed", to=to_email, error=str(exc))
