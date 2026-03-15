"""
Eden — Secure Password Hashing

Provides a high-level API for password hashing using Argon2id.
"""

from typing import Any, Dict, Optional, Type, Union, List, Protocol

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


class Hasher(Protocol):
    """Protocol for password hashers."""
    algorithm: str
    def hash(self, password: str) -> str: ...
    def verify(self, password: str, hash: str) -> bool: ...
    def needs_rehash(self, hash: str) -> bool: ...

class Argon2Hasher:
    """
    Argon2id password hasher.
    """
    algorithm = "argon2"

    def __init__(self, **kwargs):
        self.ph = PasswordHasher(**kwargs)

    def hash(self, password: str) -> str:
        # Argon2 hashes are self-identifying, but we can prefix if needed.
        # Standard argon2-cffi output looks like $argon2id$v=19$m=...
        return self.ph.hash(password)

    def verify(self, password: str, hash: str) -> bool:
        try:
            return self.ph.verify(hash, password)
        except VerifyMismatchError:
            return False

    def needs_rehash(self, hash: str) -> bool:
        return self.ph.check_needs_rehash(hash)

class BcryptHasher:
    """
    Bcrypt password hasher (Placeholder if bcrypt is missing).
    """
    algorithm = "bcrypt"

    def hash(self, password: str) -> str:
        try:
            import bcrypt
            return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        except ImportError:
            raise ImportError("bcrypt is required. Install it: pip install bcrypt")

    def verify(self, password: str, hash: str) -> bool:
        try:
            import bcrypt
            return bcrypt.checkpw(password.encode(), hash.encode())
        except ImportError:
            return False

    def needs_rehash(self, hash: str) -> bool:
        return False

class HasherRegistry:
    """
    Manages multiple password hashers and handles algorithm-aware verification.
    """
    def __init__(self):
        self._hashers: dict[str, Hasher] = {}
        self._default_alg: str = "argon2"

    def register(self, hasher: Hasher):
        self._hashers[hasher.algorithm] = hasher

    def get_hasher(self, algorithm: Optional[str] = None) -> Hasher:
        alg = algorithm or self._default_alg
        if alg not in self._hashers:
            raise ValueError(f"No hasher registered for algorithm: {alg}")
        return self._hashers[alg]

    def identify_algorithm(self, hash_string: str) -> str:
        """Heuristically identify the algorithm used for a given hash."""
        if hash_string.startswith("$argon2"):
            return "argon2"
        if hash_string.startswith("$2") or hash_string.startswith("$2b$"):
            return "bcrypt"
        return self._default_alg

    def hash(self, password: str, algorithm: Optional[str] = None) -> str:
        return self.get_hasher(algorithm).hash(password)

    def verify(self, password: str, hash_string: str) -> bool:
        alg = self.identify_algorithm(hash_string)
        try:
            hasher = self.get_hasher(alg)
            return hasher.verify(password, hash_string)
        except (ValueError, ImportError):
            return False

    def needs_rehash(self, hash_string: str) -> bool:
        alg = self.identify_algorithm(hash_string)
        if alg != self._default_alg:
            return True
        return self.get_hasher(alg).needs_rehash(hash_string)

# Global registry
registry = HasherRegistry()
registry.register(Argon2Hasher())
registry.register(BcryptHasher())

# Backward compatible helpers
hasher = registry # For those accessing .hash directly

def hash_password(password: str, algorithm: Optional[str] = None) -> str:
    return registry.hash(password, algorithm)

def check_password(password: str, hash_string: str) -> bool:
    return registry.verify(password, hash_string)

def needs_rehash(hash_string: str) -> bool:
    return registry.needs_rehash(hash_string)
