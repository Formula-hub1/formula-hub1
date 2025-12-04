"""
Mail Manager - Wrapper for Flask-Mail
"""

from threading import Thread
from typing import Any, Dict, List, Optional

from flask import current_app, render_template
from flask_mail import Mail, Message


class MailManager:
    """
    Mail manager for sending emails using Flask-Mail
    Supports HTML and plain text templates
    """

    def __init__(self, app=None):
        self.mail = Mail()
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize with Flask app"""
        # Configure Flask-Mail
        app.config.setdefault("MAIL_SERVER", "smtp.gmail.com")
        app.config.setdefault("MAIL_PORT", 587)
        app.config.setdefault("MAIL_USE_TLS", True)
        app.config.setdefault("MAIL_USE_SSL", False)
        app.config.setdefault("MAIL_USERNAME", None)
        app.config.setdefault("MAIL_PASSWORD", None)
        app.config.setdefault("MAIL_DEFAULT_SENDER", None)

        self.mail.init_app(app)

    def send_async_email(self, app, msg):
        """Send email asynchronously"""
        with app.app_context():
            try:
                self.mail.send(msg)
                current_app.logger.info(f"Email sent successfully to {msg.recipients}")
            except Exception as e:
                current_app.logger.error(f"Failed to send email to {msg.recipients}: {str(e)}")

    def send_email(
        self,
        to: str | List[str],
        subject: str,
        template: str,
        context: Dict[str, Any],
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        sender: Optional[str] = None,
        async_send: bool = True,
    ) -> bool:
        """
        Send an email with HTML and text templates

        Args:
            to: Recipient email address or list of addresses
            subject: Email subject
            template: Template name (without extension, e.g., 'emails/welcome')
            context: Context dictionary for template rendering
            cc: CC recipients
            bcc: BCC recipients
            sender: Sender email (defaults to MAIL_DEFAULT_SENDER)
            async_send: Whether to send asynchronously (default: True)

        Returns:
            bool: True if email was queued/sent successfully
        """
        try:
            # Ensure 'to' is a list
            if isinstance(to, str):
                to = [to]

            # Render HTML and text templates
            try:
                html_body = render_template(f"{template}.html", **context)
            except Exception as e:
                current_app.logger.warning(f"HTML template not found for {template}: {str(e)}")
                html_body = None

            try:
                text_body = render_template(f"{template}.txt", **context)
            except Exception as e:
                current_app.logger.warning(f"Text template not found for {template}: {str(e)}")
                text_body = None

            # At least one template must exist
            if not html_body and not text_body:
                current_app.logger.error(f"No templates found for {template}")
                return False

            # Create message
            msg = Message(
                subject=subject,
                recipients=to,
                html=html_body,
                body=text_body,
                sender=sender or current_app.config.get("MAIL_DEFAULT_SENDER"),
                cc=cc,
                bcc=bcc,
            )

            # Send asynchronously or synchronously
            if async_send:
                Thread(target=self.send_async_email, args=(current_app._get_current_object(), msg)).start()
            else:
                self.mail.send(msg)
                current_app.logger.info(f"Email sent successfully to {to}")

            return True

        except Exception as e:
            current_app.logger.error(f"Error sending email: {str(e)}")
            return False

    def send_simple_email(
        self,
        to: str | List[str],
        subject: str,
        body: str,
        html: Optional[str] = None,
        sender: Optional[str] = None,
        async_send: bool = True,
    ) -> bool:
        """
        Send a simple email without templates

        Args:
            to: Recipient email address or list of addresses
            subject: Email subject
            body: Plain text body
            html: HTML body (optional)
            sender: Sender email (defaults to MAIL_DEFAULT_SENDER)
            async_send: Whether to send asynchronously

        Returns:
            bool: True if email was queued/sent successfully
        """
        try:
            # Ensure 'to' is a list
            if isinstance(to, str):
                to = [to]

            msg = Message(
                subject=subject,
                recipients=to,
                body=body,
                html=html,
                sender=sender or current_app.config.get("MAIL_DEFAULT_SENDER"),
            )

            # Send asynchronously or synchronously
            if async_send:
                Thread(target=self.send_async_email, args=(current_app._get_current_object(), msg)).start()
            else:
                self.mail.send(msg)
                current_app.logger.info(f"Simple email sent to {to}")

            return True

        except Exception as e:
            current_app.logger.error(f"Error sending simple email: {str(e)}")
            return False


# Singleton instance
mail_manager = MailManager()
