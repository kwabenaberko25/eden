"""
Eden — Email Tests

Tests for EmailMessage, ConsoleBackend, send_mail helper, and configuration.
"""

import pytest
from io import StringIO
from unittest.mock import patch, AsyncMock

from eden.mail.message import EmailMessage
from eden.mail.backends import ConsoleBackend, SMTPBackend, EmailBackend
from eden.mail.helpers import send_mail, configure_mail, get_mail_backend


# ── EmailMessage Tests ────────────────────────────────────────────────


class TestEmailMessage:
    """Tests for the EmailMessage dataclass."""

    def test_basic_message(self):
        msg = EmailMessage(to="user@example.com", subject="Hello", body="Hi there")
        assert msg.to == "user@example.com"
        assert msg.subject == "Hello"
        assert msg.body == "Hi there"
        assert msg.html is None

    def test_to_list_single(self):
        msg = EmailMessage(to="user@example.com", subject="Test")
        assert msg.to_list == ["user@example.com"]

    def test_to_list_multiple(self):
        msg = EmailMessage(to=["a@b.com", "c@d.com"], subject="Test")
        assert msg.to_list == ["a@b.com", "c@d.com"]

    def test_recipients_with_cc_bcc(self):
        msg = EmailMessage(
            to="a@b.com",
            subject="Test",
            cc=["cc@b.com"],
            bcc=["bcc@b.com"],
        )
        assert set(msg.recipients) == {"a@b.com", "cc@b.com", "bcc@b.com"}

    def test_attachments(self):
        msg = EmailMessage(
            to="user@example.com",
            subject="With File",
            attachments=[("report.pdf", b"%PDF-1.4", "application/pdf")],
        )
        assert len(msg.attachments) == 1
        assert msg.attachments[0][0] == "report.pdf"


# ── ConsoleBackend Tests ──────────────────────────────────────────────


class TestConsoleBackend:
    """Tests for the ConsoleBackend."""

    @pytest.mark.asyncio
    async def test_send_returns_true(self):
        backend = ConsoleBackend(stream="logger")
        msg = EmailMessage(to="user@example.com", subject="Hello", body="Hi")
        result = await backend.send(msg)
        assert result is True

    @pytest.mark.asyncio
    async def test_send_stdout(self, capsys):
        backend = ConsoleBackend(stream="stdout")
        msg = EmailMessage(
            to="user@example.com",
            subject="Test Subject",
            body="Test body content",
        )
        await backend.send(msg)
        captured = capsys.readouterr()
        assert "Test Subject" in captured.out
        assert "user@example.com" in captured.out
        assert "Test body content" in captured.out

    @pytest.mark.asyncio
    async def test_send_with_html(self, capsys):
        backend = ConsoleBackend(stream="stdout")
        msg = EmailMessage(
            to="user@example.com",
            subject="HTML Test",
            html="<h1>Hello</h1>",
        )
        await backend.send(msg)
        captured = capsys.readouterr()
        assert "<h1>Hello</h1>" in captured.out

    @pytest.mark.asyncio
    async def test_send_with_attachments(self, capsys):
        backend = ConsoleBackend(stream="stdout")
        msg = EmailMessage(
            to="user@example.com",
            subject="Attach Test",
            body="See attached",
            attachments=[("file.txt", b"content", "text/plain")],
        )
        await backend.send(msg)
        captured = capsys.readouterr()
        assert "file.txt" in captured.out

    @pytest.mark.asyncio
    async def test_send_bulk(self):
        backend = ConsoleBackend(stream="logger")
        msgs = [
            EmailMessage(to="a@b.com", subject="First"),
            EmailMessage(to="c@d.com", subject="Second"),
        ]
        results = await backend.send_bulk(msgs)
        assert results == [True, True]


# ── SMTPBackend Tests ─────────────────────────────────────────────────


class TestSMTPBackend:
    """Tests for the SMTPBackend (mocked aiosmtplib)."""

    def test_init(self):
        backend = SMTPBackend(
            host="smtp.example.com",
            port=587,
            username="user@example.com",
            password="secret",
        )
        assert backend.host == "smtp.example.com"
        assert backend.port == 587
        assert backend.default_from == "user@example.com"


# ── send_mail Helper Tests ────────────────────────────────────────────


class TestSendMail:
    """Tests for the send_mail helper function."""

    @pytest.mark.asyncio
    async def test_send_mail_basic(self):
        """send_mail should dispatch to the configured backend."""
        mock_backend = AsyncMock(spec=EmailBackend)
        mock_backend.send.return_value = True

        configure_mail(mock_backend)
        result = await send_mail("user@example.com", "Hello", body="Hi")

        assert result is True
        mock_backend.send.assert_called_once()
        sent_msg = mock_backend.send.call_args[0][0]
        assert sent_msg.to == "user@example.com"
        assert sent_msg.subject == "Hello"
        assert sent_msg.body == "Hi"

    @pytest.mark.asyncio
    async def test_send_mail_with_override_backend(self):
        """send_mail should use a specific backend when provided."""
        override_backend = AsyncMock(spec=EmailBackend)
        override_backend.send.return_value = True

        result = await send_mail(
            "user@example.com", "Test", body="Body", backend=override_backend
        )

        assert result is True
        override_backend.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_configure_and_get_backend(self):
        """configure_mail should set the global backend."""
        custom_backend = ConsoleBackend(stream="logger")
        configure_mail(custom_backend)

        retrieved = get_mail_backend()
        assert retrieved is custom_backend

    @pytest.mark.asyncio
    async def test_default_backend_is_console(self):
        """When no backend is configured, ConsoleBackend should be used."""
        from eden.mail import helpers
        helpers._mail_backend = None  # Reset

        backend = get_mail_backend()
        assert isinstance(backend, ConsoleBackend)
