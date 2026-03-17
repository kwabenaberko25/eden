"""
Eden — Email Helpers

High-level email sending functions and global backend configuration.
"""

from typing import Any

from eden.mail.backends import ConsoleBackend, EmailBackend
from eden.mail.message import EmailMessage

# Global backend instance
_mail_backend: EmailBackend | None = None


def configure_mail(backend: EmailBackend) -> None:
    """
    Set the global email backend.

    Usage:
        from eden.mail import configure_mail, SMTPBackend
        configure_mail(SMTPBackend(host="smtp.gmail.com", ...))
    """
    global _mail_backend
    _mail_backend = backend


def get_mail_backend() -> EmailBackend:
    """
    Get the global email backend.
    
    Priority:
    1. Explicitly configured backend (_mail_backend)
    2. SMTPBackend if EDEN_SMTP_URL is set
    3. ConsoleBackend (Default)
    """
    global _mail_backend
    if _mail_backend is not None:
        return _mail_backend

    import os
    from eden.mail.backends import SMTPBackend

    smtp_url = os.environ.get("EDEN_SMTP_URL")
    if smtp_url:
        _mail_backend = SMTPBackend.from_url(smtp_url)
    else:
        _mail_backend = ConsoleBackend()
    
    return _mail_backend


async def send_mail(
    to: str | list[str],
    subject: str,
    body: str = "",
    html: str | None = None,
    template: str | None = None,
    context: dict[str, Any] | None = None,
    from_email: str | None = None,
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    reply_to: str | None = None,
    attachments: list[tuple[str, bytes, str]] | None = None,
    backend: EmailBackend | None = None,
) -> bool:
    """
    High-level email sending helper.

    If `template` is provided, it renders the template using Eden's Jinja2 engine
    and uses the result as the HTML body.

    Args:
        to: Recipient email(s)
        subject: Email subject line
        body: Plain text body
        html: HTML body (alternative to template)
        template: Eden template name (e.g., "emails/welcome.html")
        context: Template context variables
        from_email: Sender email (overrides backend default)
        cc: CC recipients
        bcc: BCC recipients
        reply_to: Reply-to address
        attachments: List of (filename, content_bytes, mime_type) tuples
        backend: Override the global backend for this send

    Returns:
        True if sent successfully, False otherwise.

    Usage:
        # Simple text email
        await send_mail("user@example.com", "Hello", body="Welcome!")

        # Template email
        await send_mail(
            "user@example.com",
            "Welcome to Our App",
            template="emails/welcome.html",
            context={"user_name": "John"},
        )
    """
    # Render template if provided
    if template:
        try:
            from eden.app import Eden
            app = Eden.get_current()
            
            if app:
                rendered = app.templates.get_template(template).render(context or {})
            else:
                # Fallback if no app context (e.g. background task without Eden instance)
                from eden.templating import EdenTemplates
                # We should really cache this globally at the module level
                _global_templates = getattr(send_mail, "_templates", None)
                if not _global_templates:
                    _global_templates = EdenTemplates(directory="templates")
                    send_mail._templates = _global_templates
                rendered = _global_templates.get_template(template).render(context or {})
                
            html = rendered
        except Exception as e:
            import logging
            logging.getLogger("eden.mail").warning(
                f"Failed to render email template '{template}': {e}. "
                f"Falling back to plain text."
            )

    message = EmailMessage(
        to=to,
        subject=subject,
        body=body,
        html=html,
        from_email=from_email,
        cc=cc,
        bcc=bcc,
        reply_to=reply_to,
        attachments=attachments,
    )

    mail_backend = backend or get_mail_backend()
    return await mail_backend.send(message)


async def send_bulk_mail(
    messages: list[EmailMessage],
    backend: EmailBackend | None = None,
) -> list[bool]:
    """
    Send multiple email messages.

    Args:
        messages: List of EmailMessage objects
        backend: Override the global backend

    Returns:
        List of booleans indicating success for each message.
    """
    mail_backend = backend or get_mail_backend()
    return await mail_backend.send_bulk(messages)
