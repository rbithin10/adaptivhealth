"""
Transactional email service.

Provides SMTP delivery for password reset emails with environment-driven
configuration and provider compatibility (including SendGrid SMTP).
"""

from email.message import EmailMessage
from typing import Optional
from urllib.parse import urlencode
import logging
import smtplib

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Handles SMTP email delivery for transactional backend flows."""

    @staticmethod
    def is_smtp_configured() -> bool:
        """Return True only when required SMTP fields are configured."""
        required_values = [
            settings.smtp_host,
            settings.smtp_username,
            settings.smtp_password,
            settings.smtp_from_email,
        ]
        return all(bool(value) for value in required_values)

    @staticmethod
    def build_password_reset_link(reset_token: str) -> str:
        """Build frontend reset-password URL with token query parameter."""
        base_url = settings.frontend_base_url.rstrip("/")
        reset_path = settings.password_reset_path
        if not reset_path.startswith("/"):
            reset_path = f"/{reset_path}"
        query_string = urlencode({"token": reset_token})
        return f"{base_url}{reset_path}?{query_string}"

    @staticmethod
    def send_password_reset_email(to_email: str, reset_link: str) -> None:
        """
        Send a password reset email via configured SMTP transport.

        Raises:
            RuntimeError: If SMTP is not configured.
            Exception: For SMTP transport failures.
        """
        if not EmailService.is_smtp_configured():
            raise RuntimeError("SMTP is not configured")

        smtp_host = settings.smtp_host or ""
        smtp_username = settings.smtp_username or ""
        smtp_password = settings.smtp_password or ""
        from_email = settings.smtp_from_email or ""

        subject = "Reset your Adaptiv Health password"
        html_body = f"""
        <html>
          <body>
            <p>Hello,</p>
            <p>We received a request to reset your Adaptiv Health password.</p>
            <p>
              <a href=\"{reset_link}\">Reset your password</a>
            </p>
            <p>If you did not request this, you can safely ignore this email.</p>
            <p>This link expires in 1 hour.</p>
            <p>Adaptiv Health Team</p>
          </body>
        </html>
        """.strip()
        text_body = (
            "We received a request to reset your Adaptiv Health password.\n\n"
            f"Reset your password: {reset_link}\n\n"
            "If you did not request this, you can safely ignore this email.\n"
            "This link expires in 1 hour."
        )

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{settings.smtp_from_name} <{from_email}>"
        message["To"] = to_email
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

        logger.info(
            "Attempting password reset email delivery",
            extra={
                "event": "password_reset_email_send_attempt",
                "smtp_host": settings.smtp_host,
                "smtp_port": settings.smtp_port,
                "use_tls": settings.smtp_use_tls,
                "use_ssl": settings.smtp_use_ssl,
                "recipient": to_email,
            },
        )

        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(smtp_host, settings.smtp_port, timeout=15) as smtp:
                smtp.login(smtp_username, smtp_password)
                smtp.send_message(message)
            return

        with smtplib.SMTP(smtp_host, settings.smtp_port, timeout=15) as smtp:
            smtp.ehlo()
            if settings.smtp_use_tls:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(message)


email_service = EmailService()
