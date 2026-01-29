"""
Email Service for sending transactional emails.

Uses aiosmtplib for async SMTP operations.
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import logging

from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    """Async email service using SMTP."""

    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email asynchronously.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body of the email
            text_content: Optional plain text body

        Returns:
            True if sent successfully, False otherwise
        """
        if not settings.smtp_host:
            logger.warning(f"SMTP not configured, would send to {to_email}: {subject}")
            # Log the reset link for development
            if "reset" in subject.lower():
                logger.info(f"Reset email content: {html_content}")
            return False

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        message["To"] = to_email

        if text_content:
            message.attach(MIMEText(text_content, "plain"))
        message.attach(MIMEText(html_content, "html"))

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                start_tls=settings.smtp_use_tls
            )
            logger.info(f"Email sent to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    @staticmethod
    async def send_password_reset_email(to_email: str, reset_token: str) -> bool:
        """
        Send password reset email with token link.

        Args:
            to_email: Recipient email address
            reset_token: JWT reset token

        Returns:
            True if sent successfully, False otherwise
        """
        reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"

        subject = "Reset Your Password - Finance Buddy"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f8fafc;">
    <div style="background-color: white; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <h1 style="color: #1e293b; font-size: 24px; margin-bottom: 16px;">Reset Your Password</h1>
        <p style="color: #475569; font-size: 16px; line-height: 1.6;">
            You requested to reset your password for Finance Buddy.
        </p>
        <p style="color: #475569; font-size: 16px; line-height: 1.6;">
            Click the button below to set a new password. This link expires in 15 minutes.
        </p>
        <div style="text-align: center; margin: 32px 0;">
            <a href="{reset_url}" style="display: inline-block; background-color: #1e293b; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 500; font-size: 16px;">
                Reset Password
            </a>
        </div>
        <p style="color: #94a3b8; font-size: 14px; line-height: 1.6;">
            If you didn't request this, you can safely ignore this email. Your password will remain unchanged.
        </p>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;">
        <p style="color: #94a3b8; font-size: 12px;">
            If the button doesn't work, copy and paste this link into your browser:<br>
            <a href="{reset_url}" style="color: #64748b; word-break: break-all;">{reset_url}</a>
        </p>
    </div>
</body>
</html>
"""

        text_content = f"""Reset Your Password

You requested to reset your password for Finance Buddy.

Click this link to set a new password (expires in 15 minutes):
{reset_url}

If you didn't request this, you can safely ignore this email.
"""

        return await EmailService.send_email(to_email, subject, html_content, text_content)
