"""
Eden — Email Message

Dataclass representing an email message.
"""

from dataclasses import dataclass


@dataclass
class EmailMessage:
    """
    Represents an outgoing email message.

    Usage:
        msg = EmailMessage(
            to="user@example.com",
            subject="Welcome!",
            body="Hello, welcome to our app.",
            html="<h1>Hello</h1><p>Welcome to our app.</p>",
        )
    """

    to: str | list[str]
    subject: str
    body: str = ""
    html: str | None = None
    from_email: str | None = None
    cc: list[str] | None = None
    bcc: list[str] | None = None
    reply_to: str | None = None
    attachments: list[tuple[str, bytes, str]] | None = None  # (filename, content, mime_type)

    @property
    def recipients(self) -> list[str]:
        """Get a flat list of all recipients (to + cc + bcc)."""
        result = []
        if isinstance(self.to, str):
            result.append(self.to)
        else:
            result.extend(self.to)
        if self.cc:
            result.extend(self.cc)
        if self.bcc:
            result.extend(self.bcc)
        return result

    @property
    def to_list(self) -> list[str]:
        """Get `to` as a list regardless of input type."""
        if isinstance(self.to, str):
            return [self.to]
        return self.to
