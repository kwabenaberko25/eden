"""
Tests for eden.port — port availability and auto-selection utilities.
"""

from __future__ import annotations

import socket

import pytest

from eden.port import find_available_port, is_port_available


# ── is_port_available ────────────────────────────────────────────────────


def test_is_port_available_open():
    """An unused port should be reported as available."""
    # Use a high ephemeral port unlikely to be in use
    assert is_port_available("127.0.0.1", 64123) is True


def test_is_port_available_occupied():
    """A port that is already bound should be reported as unavailable."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 64200))
    sock.listen(1)
    try:
        assert is_port_available("127.0.0.1", 64200) is False
    finally:
        sock.close()


# ── find_available_port ──────────────────────────────────────────────────


def test_find_available_port_first_free():
    """When the start port is free, it should be returned unchanged."""
    port = find_available_port("127.0.0.1", 64300)
    assert port == 64300


def test_find_available_port_skips_occupied():
    """When the start port is occupied, the next free port should be returned."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 64400))
    sock.listen(1)
    try:
        port = find_available_port("127.0.0.1", 64400)
        assert port == 64401
    finally:
        sock.close()


def test_find_available_port_max_attempts():
    """Should raise RuntimeError when all ports in range are occupied."""
    sockets = []
    base_port = 64500
    max_attempts = 3
    try:
        for i in range(max_attempts):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", base_port + i))
            s.listen(1)
            sockets.append(s)

        with pytest.raises(RuntimeError, match="Could not find an available port"):
            find_available_port("127.0.0.1", base_port, max_attempts=max_attempts)
    finally:
        for s in sockets:
            s.close()
