"""
Eden — Secure Password Hashing

Provides a high-level API for password hashing using Argon2id.
"""

from typing import Protocol

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


class Hasher(Protocol):
    """Protocol for password hashers."""
    def hash(self, password: str) -> str: ...
    def verify(self, password: str, hash: str) -> bool: ...
    def needs_rehash(self, hash: str) -> bool: ...

class Argon2Hasher:
    """
    Argon2id password hasher.

    Argon2 is the winner of the Password Hashing Competition (PHC)
    and is considered the state-of-the-art for password hashing.
    """

    def __init__(self, **kwargs):
        # Default settings are usually secure, but can be overridden
        self.ph = PasswordHasher(**kwargs)

    def hash(self, password: str) -> str:
        """Hash a password."""
        return self.ph.hash(password)

    def verify(self, password: str, hash: str) -> bool:
        """Verify a password against a hash."""
        try:
            return self.ph.verify(hash, password)
        except VerifyMismatchError:
            return False

    def needs_rehash(self, hash: str) -> bool:
        """Check if the hash needs to be re-hashed with updated parameters."""
        return self.ph.check_needs_rehash(hash)

# Default global hasher
hasher = Argon2Hasher()

def hash_password(password: str) -> str:
    """Convenience helper to hash a password using the default hasher."""
    return hasher.hash(password)

def check_password(password: str, hash: str) -> bool:
    """Convenience helper to verify a password using the default hasher."""
    return hasher.verify(password, hash)
