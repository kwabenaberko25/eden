"""
Eden — Port Utilities

Helpers for finding an available network port, enabling automatic
port fallback when the default port is already in use.
"""

from __future__ import annotations

import socket


def is_port_available(host: str, port: int) -> bool:
    """
    Check whether a given port is available for binding.

    Uses a connect-based probe: if a connection to the port succeeds,
    something is already listening there. This is more reliable than
    a bind-based check on Windows where SO_REUSEADDR allows duplicate binds.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.1)
            result = sock.connect_ex((host, port))
            # connect_ex returns 0 if the connection succeeds (port in use)
            return result != 0
    except OSError:
        return True


def find_available_port(
    host: str = "127.0.0.1",
    start_port: int = 8000,
    max_attempts: int = 20,
) -> int:
    """
    Find the first available port starting from ``start_port``.

    Iterates upward from ``start_port`` until a free port is found.
    Raises ``RuntimeError`` if no port is available within ``max_attempts``.

    Args:
        host: The bind address to check against.
        start_port: The preferred port to start scanning from.
        max_attempts: Maximum number of ports to try before giving up.

    Returns:
        An available port number.
    """
    for offset in range(max_attempts):
        port = start_port + offset
        if is_port_available(host, port):
            return port

    raise RuntimeError(
        f"Could not find an available port in range "
        f"{start_port}–{start_port + max_attempts - 1}. "
        f"Please free up a port or specify a different one with --port."
    )
