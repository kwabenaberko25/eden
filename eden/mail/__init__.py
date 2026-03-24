"""
Eden — Email Package

Transactional email sending with pluggable backends.
"""

from eden.mail.backends import ConsoleBackend, EmailBackend, SMTPBackend, ResendBackend, SESBackend
from eden.mail.helpers import configure_mail, get_mail_backend, send_bulk_mail, send_mail
send_email = send_mail

from eden.mail.message import EmailMessage

__all__ = [
    "EmailMessage",
    "EmailBackend",
    "ConsoleBackend",
    "SMTPBackend",
    "ResendBackend",
    "SESBackend",
    "send_mail",
    "send_email",
    "send_bulk_mail",
    "configure_mail",
    "get_mail_backend",
]
