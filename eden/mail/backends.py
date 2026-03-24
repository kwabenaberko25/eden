"""
Eden — Email Backends

Pluggable email sending backends: ConsoleBackend (dev) and SMTPBackend (production).
"""

import logging
import urllib.parse
from abc import ABC, abstractmethod
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from eden.mail.message import EmailMessage

logger = logging.getLogger("eden.mail")


class EmailBackend(ABC):
    """Abstract base class for email backends."""

    @abstractmethod
    async def send(self, message: EmailMessage) -> bool:
        """
        Send an email message.

        Returns:
            True if the email was sent successfully, False otherwise.
        """
        pass

    async def send_bulk(self, messages: list[EmailMessage]) -> list[bool]:
        """Send multiple messages. Override for batch-optimized implementations."""
        results = []
        for msg in messages:
            results.append(await self.send(msg))
        return results


class ConsoleBackend(EmailBackend):
    """
    Prints emails to stdout/logger. Perfect for development.
    Zero external dependencies.

    Usage:
        from eden.mail import ConsoleBackend, configure_mail
        configure_mail(ConsoleBackend())
    """

    def __init__(self, stream: str = "logger"):
        """
        Args:
            stream: "logger" to use Python logging, "stdout" to use print().
        """
        self.stream = stream

    async def send(self, message: EmailMessage) -> bool:
        output = (
            f"\n{'=' * 60}\n"
            f"📧 EMAIL (ConsoleBackend)\n"
            f"{'=' * 60}\n"
            f"To:      {message.to}\n"
            f"From:    {message.from_email or '(default)'}\n"
            f"Subject: {message.subject}\n"
        )
        if message.cc:
            output += f"CC:      {', '.join(message.cc)}\n"
        if message.bcc:
            output += f"BCC:     {', '.join(message.bcc)}\n"
        if message.reply_to:
            output += f"Reply-To: {message.reply_to}\n"

        output += f"{'-' * 60}\n"
        if message.body:
            output += f"{message.body}\n"
        if message.html:
            output += f"{'-' * 60}\n[HTML]\n{message.html}\n"

        if message.attachments:
            output += f"{'-' * 60}\nAttachments: {len(message.attachments)}\n"
            for fname, _, mime in message.attachments:
                output += f"  - {fname} ({mime})\n"

        output += f"{'=' * 60}\n"

        if self.stream == "stdout":
            print(output)
        else:
            logger.info(output)

        return True


class SMTPBackend(EmailBackend):
    """
    Sends emails via SMTP using aiosmtplib (async).

    Requires: `uv add aiosmtplib` or `pip install aiosmtplib`

    Usage:
        from eden.mail import SMTPBackend, configure_mail
        configure_mail(SMTPBackend(
            host="smtp.gmail.com",
            port=587,
            username="you@gmail.com",
            password="your-app-password",
        ))
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 587,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        from_email: str | None = None,
        timeout: int = 30,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.default_from = from_email or username
        self.timeout = timeout

    @classmethod
    def from_url(cls, url: str) -> "SMTPBackend":
        """
        Create an SMTPBackend from a URL string.
        Format: smtp://user:pass@host:port/?use_tls=true&from_email=...
        """
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)

        return cls(
            host=parsed.hostname or "localhost",
            port=parsed.port or 587,
            username=parsed.username,
            password=parsed.password,
            use_tls=params.get("use_tls", ["true"])[0].lower() == "true",
            from_email=params.get("from_email", [None])[0],
        )

    async def send(self, message: EmailMessage) -> bool:
        try:
            import aiosmtplib
        except ImportError:
            raise ImportError(
                "aiosmtplib is required for SMTPBackend. "
                "Install it with: uv add aiosmtplib"
            )

        from_email = message.from_email or self.default_from

        # Build MIME message
        mime_msg = MIMEMultipart("alternative")
        mime_msg["Subject"] = message.subject
        mime_msg["From"] = from_email
        mime_msg["To"] = ", ".join(message.to_list)

        if message.cc:
            mime_msg["Cc"] = ", ".join(message.cc)
        if message.reply_to:
            mime_msg["Reply-To"] = message.reply_to

        # Attach text body
        if message.body:
            mime_msg.attach(MIMEText(message.body, "plain", "utf-8"))

        # Attach HTML body
        if message.html:
            mime_msg.attach(MIMEText(message.html, "html", "utf-8"))

        # Attach files
        if message.attachments:
            for filename, content, mime_type in message.attachments:
                maintype, subtype = mime_type.split("/", 1)
                part = MIMEBase(maintype, subtype)
                part.set_payload(content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition", "attachment", filename=filename
                )
                mime_msg.attach(part)

        try:
            await aiosmtplib.send(
                mime_msg,
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                start_tls=self.use_tls,
                timeout=self.timeout,
                recipients=message.recipients,
            )
            logger.info(f"Email sent to {message.to}: {message.subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {message.to}: {e}")
            return False


class ResendBackend(EmailBackend):
    """
    Sends emails via the Resend API.
    
    Requires: `uv add httpx`
    """

    def __init__(self, api_key: str, from_email: str | None = None):
        self.api_key = api_key
        self.default_from = from_email

    async def send(self, message: EmailMessage) -> bool:
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx is required for ResendBackend. "
                "Install it with: uv add httpx"
            )

        payload = {
            "from": message.from_email or self.default_from,
            "to": message.to if isinstance(message.to, list) else [message.to],
            "subject": message.subject,
            "text": message.body if message.body else "",
            "html": message.html if message.html else "",
        }

        if message.cc:
            payload["cc"] = message.cc
        if message.bcc:
            payload["bcc"] = message.bcc
        if message.reply_to:
            payload["reply_to"] = message.reply_to

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                json=payload,
                headers=headers,
                timeout=30.0,
            )
            
            if response.status_code in (200, 201):
                logger.info(f"Email sent via Resend to {message.to}")
                return True
            else:
                logger.error(f"Resend error: {response.status_code} - {response.text}")
                return False


class SESBackend(EmailBackend):
    """
    Sends emails via AWS SES.
    
    Requires: `uv add boto3`
    """

    def __init__(
        self,
        region_name: str = "us-east-1",
        access_key: str | None = None,
        secret_key: str | None = None,
        from_email: str | None = None,
    ):
        self.region_name = region_name
        self.access_key = access_key
        self.secret_key = secret_key
        self.default_from = from_email

    async def send(self, message: EmailMessage) -> bool:
        try:
            import boto3
        except ImportError:
            raise ImportError(
                "boto3 is required for SESBackend. "
                "Install it with: uv add boto3"
            )

        def _send():
            client = boto3.client(
                "ses",
                region_name=self.region_name,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
            )
            
            # For SES, we usually send raw email or use SendTemplatedEmail/SendEmail
            # We'll use SendEmail for simplicity
            response = client.send_email(
                Source=message.from_email or self.default_from,
                Destination={
                    "ToAddresses": message.to if isinstance(message.to, list) else [message.to],
                    "CcAddresses": message.cc or [],
                    "BccAddresses": message.bcc or [],
                },
                Message={
                    "Subject": {"Data": message.subject, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": message.body or "", "Charset": "UTF-8"},
                        "Html": {"Data": message.html or "", "Charset": "UTF-8"},
                    },
                },
                ReplyToAddresses=[message.reply_to] if message.reply_to else [],
            )
            return response

        try:
            await asyncio.to_thread(_send)
            logger.info(f"Email sent via SES to {message.to}")
            return True
        except Exception as e:
            logger.error(f"SES error sending to {message.to}: {e}")
            return False

