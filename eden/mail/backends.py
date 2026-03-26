"""
Eden — Email Backends

Pluggable email sending backends: ConsoleBackend (dev) and SMTPBackend (production).
"""

import asyncio
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
            import sys
            sys.stdout.write(output + "\n")
            sys.stdout.flush()
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
        """Send a single email message."""
        try:
            import aiosmtplib
        except ImportError:
            raise ImportError(
                "aiosmtplib is required for SMTPBackend. "
                "Install it with: uv add aiosmtplib"
            )

        mime_msg = self._build_mime_message(message)

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

    async def send_bulk(self, messages: list[EmailMessage]) -> list[bool]:
        """
        Send multiple messages using a single persistent connection.
        Provides significant performance improvement for batch operations.
        """
        try:
            import aiosmtplib
        except ImportError:
            raise ImportError("aiosmtplib is required for SMTPBackend.")

        results = [False] * len(messages)
        
        # Use exponential backoff for connection retries
        max_retries = 3
        retry_delay = 1.0 # Base seconds

        smtp = aiosmtplib.SMTP(
            hostname=self.host,
            port=self.port,
            use_tls=False, # We use starttls manually if needed
            timeout=self.timeout
        )

        try:
            # 1. Connect and Authenticate (with retries)
            connected = False
            for attempt in range(max_retries):
                try:
                    await smtp.connect()
                    if self.use_tls:
                        await smtp.starttls()
                    
                    if self.username and self.password:
                        await smtp.login(self.username, self.password)
                    
                    connected = True
                    break
                except (aiosmtplib.SMTPException, OSError, asyncio.TimeoutError) as e:
                    logger.warning(f"SMTP connection attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (2 ** attempt))
                    else:
                        logger.error("SMTP connection failed after all retries.")
                        return results # All False

            # 2. Send messages sequentially over the open connection
            if connected:
                for i, message in enumerate(messages):
                    try:
                        mime_msg = self._build_mime_message(message)
                        await smtp.send_message(mime_msg)
                        results[i] = True
                        logger.debug(f"Bulk email sent to {message.to}")
                    except Exception as e:
                        logger.error(f"Failed to send bulk message {i} to {message.to}: {e}")
                        # Move to next message, don't kill the whole batch
        
        finally:
            try:
                if smtp.is_connected:
                    await smtp.quit()
            except Exception:
                # Connection might already be closed/dead — safe to ignore on cleanup
                pass

        success_count = sum(results)
        logger.info(f"Bulk email completed: {success_count}/{len(messages)} sent successfully.")
        return results

    def _build_mime_message(self, message: EmailMessage) -> MIMEMultipart:
        """Helper to build a MIME message from an EmailMessage object."""
        from_email = message.from_email or self.default_from

        # Build MIME message structure
        if message.attachments:
            # "mixed" container for attachments + body
            mime_msg = MIMEMultipart("mixed")
            # Internal "alternative" container for text vs html bodies
            body_part = MIMEMultipart("alternative")
            if message.body:
                body_part.attach(MIMEText(message.body, "plain", "utf-8"))
            if message.html:
                body_part.attach(MIMEText(message.html, "html", "utf-8"))
            mime_msg.attach(body_part)
        else:
            # Simple "alternative" container for text vs html bodies
            mime_msg = MIMEMultipart("alternative")
            if message.body:
                mime_msg.attach(MIMEText(message.body, "plain", "utf-8"))
            if message.html:
                mime_msg.attach(MIMEText(message.html, "html", "utf-8"))

        mime_msg["Subject"] = message.subject
        mime_msg["From"] = from_email
        mime_msg["To"] = ", ".join(message.to_list)

        if message.cc:
            mime_msg["Cc"] = ", ".join(message.cc)
        if message.reply_to:
            mime_msg["Reply-To"] = message.reply_to

        # Attach files
        if message.attachments:
            for filename, content, mime_type in message.attachments:
                try:
                    maintype, subtype = mime_type.split("/", 1)
                except ValueError:
                    maintype, subtype = "application", "octet-stream"
                    
                part = MIMEBase(maintype, subtype)
                part.set_payload(content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition", "attachment", filename=filename
                )
                mime_msg.attach(part)
        
        return mime_msg


class ResendBackend(EmailBackend):
    """
    Sends emails via the Resend API.
    
    Requires: `uv add httpx`
    """

    def __init__(self, api_key: str, from_email: str | None = None):
        self.api_key = api_key
        self.default_from = from_email

    async def send(self, message: EmailMessage) -> bool:
        """Send a single email via Resend."""
        results = await self.send_bulk([message])
        return all(results)

    async def send_bulk(self, messages: list[EmailMessage]) -> list[bool]:
        """
        Send multiple emails via Resend using batch API.
        
        Optimizes delivery by sending up to 100 emails per request.
        """
        try:
            import httpx
        except ImportError:
            raise ImportError(
                "httpx is required for ResendBackend. "
                "Install it with: uv add httpx"
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        results = []
        # Batch size for Resend is usually 100
        batch_size = 100
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(0, len(messages), batch_size):
                batch = messages[i : i + batch_size]
                
                payload = []
                for msg in batch:
                    item = {
                        "from": msg.from_email or self.default_from,
                        "to": msg.to if isinstance(msg.to, list) else [msg.to],
                        "subject": msg.subject,
                        "text": msg.body if msg.body else "",
                        "html": msg.html if msg.html else "",
                    }
                    if msg.cc: item["cc"] = msg.cc
                    if msg.bcc: item["bcc"] = msg.bcc
                    if msg.reply_to: item["reply_to"] = msg.reply_to
                    payload.append(item)

                # Retry logic for the entire batch request
                success = False
                for attempt in range(3):
                    try:
                        response = await client.post(
                            "https://api.resend.com/emails/batch",
                            json=payload,
                            headers=headers,
                        )
                        if response.status_code in (200, 201):
                            success = True
                            break
                        elif response.status_code >= 500:
                            wait = (2 ** attempt) + 0.1
                            await asyncio.sleep(wait)
                            continue
                        else:
                            logger.error(f"Resend batch error {response.status_code}: {response.text}")
                            break
                    except Exception as exc:
                        logger.warning(f"Resend batch attempt {attempt+1} failed: {exc}")
                        await asyncio.sleep(1)
                
                results.extend([success] * len(batch))
        
        return results


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
        """Send a single email via SES."""
        results = await self.send_bulk([message])
        return all(results)

    async def send_bulk(self, messages: list[EmailMessage]) -> list[bool]:
        """
        Send multiple emails via SES reusing the client.
        """
        try:
            import boto3
        except ImportError:
            raise ImportError(
                "boto3 is required for SESBackend. "
                "Install it with: uv add boto3"
            )

        client = boto3.client(
            "ses",
            region_name=self.region_name,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

        results = []
        for msg in messages:
            success = False
            for attempt in range(3):
                try:
                    await asyncio.to_thread(
                        client.send_email,
                        Source=msg.from_email or self.default_from,
                        Destination={
                            "ToAddresses": msg.to if isinstance(msg.to, list) else [msg.to],
                            "CcAddresses": msg.cc or [],
                            "BccAddresses": msg.bcc or [],
                        },
                        Message={
                            "Subject": {"Data": msg.subject, "Charset": "UTF-8"},
                            "Body": {
                                "Text": {"Data": msg.body or "", "Charset": "UTF-8"},
                                "Html": {"Data": msg.html or "", "Charset": "UTF-8"},
                            },
                        },
                        ReplyToAddresses=[msg.reply_to] if msg.reply_to else [],
                    )
                    success = True
                    break
                except Exception as exc:
                    # Check for transient errors
                    error_msg = str(exc).lower()
                    if "throttling" in error_msg or "requestlimitexceeded" in error_msg or "serviceunavailable" in error_msg:
                        wait = (2 ** attempt) + 0.1
                        await asyncio.sleep(wait)
                        continue
                    logger.error(f"SES error sending to {msg.to}: {exc}")
                    break
            results.append(success)
        
        return results

