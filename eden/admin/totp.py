"""
Two-Factor Authentication (2FA) with TOTP for Eden Admin Dashboard.

Implements Time-based One-Time Password (TOTP) using authenticator apps
like Google Authenticator, Authy, Microsoft Authenticator, etc.

Also supports backup codes for account recovery.

Usage:
    from eden.admin.totp import TOTPManager
    
    totp_manager = TOTPManager(issuer="Eden Admin")
    
    # Generate QR code for user
    secret, qr_code = totp_manager.generate_secret("admin")
    
    # Verify TOTP code
    if totp_manager.verify(secret, code):
        # Code is valid
        pass
    
    # Generate backup codes
    backup_codes = totp_manager.generate_backup_codes()
"""

import secrets
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
import base64
import hmac
import hashlib


@dataclass
class BackupCode:
    """A single backup code for account recovery."""
    code: str
    created_at: datetime
    used_at: Optional[datetime] = None
    
    def is_used(self) -> bool:
        """Check if code has been used."""
        return self.used_at is not None


class TOTPManager:
    """Manager for TOTP 2FA."""
    
    def __init__(
        self,
        issuer: str = "Eden Admin",
        name: str = "Eden Admin",
        time_step: int = 30,
        code_length: int = 6,
        window: int = 1
    ):
        """
        Initialize TOTP manager.
        
        Args:
            issuer: Issuer name (shown in authenticator apps)
            name: Service name
            time_step: Time step in seconds (default: 30)
            code_length: Number of digits in code (default: 6)
            window: Number of time steps to check (for clock skew tolerance)
        """
        self.issuer = issuer
        self.name = name
        self.time_step = time_step
        self.code_length = code_length
        self.window = window
    
    def generate_secret(self, username: str) -> tuple[str, str]:
        """
        Generate TOTP secret and QR code for a user.
        
        Args:
            username: Username
            
        Returns:
            (secret, provisioning_uri) - secret is base32 encoded, uri is for QR code
        """
        # Generate 32 bytes = 256 bits of random data
        random_bytes = secrets.token_bytes(32)
        secret = base64.b32encode(random_bytes).decode('utf-8')
        
        # Generate provisioning URI for QR code
        uri = self._generate_provisioning_uri(username, secret)
        
        return secret, uri
    
    def _generate_provisioning_uri(self, username: str, secret: str) -> str:
        """Generate provisioning URI for QR code."""
        # Format: otpauth://totp/Issuer:username?secret=SECRET&issuer=Issuer
        import urllib.parse
        
        label = f"{self.issuer}:{username}"
        params = {
            "secret": secret,
            "issuer": self.issuer,
            "algorithm": "SHA1",
            "digits": str(self.code_length),
            "period": str(self.time_step)
        }
        
        query_string = urllib.parse.urlencode(params)
        uri = f"otpauth://totp/{urllib.parse.quote(label, safe='')}?{query_string}"
        
        return uri
    
    def _get_totp_code(self, secret: str, timestamp: Optional[int] = None) -> str:
        """
        Get TOTP code for a given secret and timestamp.
        
        Args:
            secret: Base32-encoded secret
            timestamp: Unix timestamp (current time if not provided)
            
        Returns:
            TOTP code as string
        """
        if timestamp is None:
            timestamp = int(time.time())
        
        # Decode the secret
        try:
            key = base64.b32decode(secret)
        except Exception:
            raise ValueError("Invalid secret format")
        
        # Calculate time counter
        counter = int(timestamp / self.time_step)
        
        # Generate HMAC
        counter_bytes = counter.to_bytes(8, byteorder='big')
        hmac_hash = hmac.new(key, counter_bytes, hashlib.sha1).digest()
        
        # Extract dynamic binary code
        offset = hmac_hash[-1] & 0x0f
        code = hmac_hash[offset:offset + 4]
        code_int = int.from_bytes(code, byteorder='big') & 0x7fffffff
        
        # Format as zero-padded string
        return str(code_int % (10 ** self.code_length)).zfill(self.code_length)
    
    def verify(self, secret: str, code: str) -> bool:
        """
        Verify a TOTP code.
        
        Args:
            secret: Base32-encoded secret
            code: Code to verify (6 digits typically)
            
        Returns:
            True if code is valid
        """
        current_timestamp = int(time.time())
        
        # Check current and adjacent time windows (for clock skew tolerance)
        for i in range(-self.window, self.window + 1):
            timestamp = current_timestamp + (i * self.time_step)
            expected_code = self._get_totp_code(secret, timestamp)
            
            if code == expected_code:
                return True
        
        return False
    
    def get_current_code(self, secret: str) -> tuple[str, int]:
        """
        Get current TOTP code and seconds until next code.
        
        Args:
            secret: Base32-encoded secret
            
        Returns:
            (code, seconds_remaining)
        """
        timestamp = int(time.time())
        code = self._get_totp_code(secret, timestamp)
        
        # Calculate seconds until next code
        seconds_remaining = self.time_step - (timestamp % self.time_step)
        
        return code, seconds_remaining
    
    @staticmethod
    def generate_backup_codes(count: int = 10, length: int = 8) -> List[str]:
        """
        Generate backup codes for account recovery.
        
        Args:
            count: Number of codes to generate
            length: Length of each code
            
        Returns:
            List of backup codes
        """
        codes = []
        for _ in range(count):
            # Generate random hex string
            code = secrets.token_hex(length // 2)
            # Format as XXXX-XXXX for readability
            formatted = f"{code[:4].upper()}-{code[4:].upper()}"
            codes.append(formatted)
        
        return codes


class TOTPSecret:
    """Represents a TOTP secret for a user."""
    
    def __init__(
        self,
        username: str,
        secret: str,
        backup_codes: Optional[List[str]] = None
    ):
        """
        Initialize TOTP secret.
        
        Args:
            username: Username
            secret: Base32-encoded secret
            backup_codes: List of backup codes
        """
        self.username = username
        self.secret = secret
        self.backup_codes = {code: False for code in (backup_codes or [])}  # code -> used
        self.enabled_at: Optional[datetime] = None
        self.verified: bool = False


class TOTPSecretManager:
    """Manages TOTP secrets for users."""
    
    def __init__(self, issuer: str = "Eden Admin"):
        """Initialize TOTP secret manager."""
        self.totp_manager = TOTPManager(issuer=issuer)
        self.secrets: Dict[str, TOTPSecret] = {}  # username -> TOTPSecret
    
    def setup_2fa(self, username: str) -> tuple[str, List[str]]:
        """
        Setup 2FA for a user.
        
        Returns:
            (provisioning_uri, backup_codes)
        """
        # Generate TOTP secret
        secret, uri = self.totp_manager.generate_secret(username)
        
        # Generate backup codes
        backup_codes = TOTPManager.generate_backup_codes()
        
        # Store temporarily (before verification)
        totp_secret = TOTPSecret(username, secret, backup_codes)
        self.secrets[username] = totp_secret
        
        return uri, backup_codes
    
    def verify_setup(self, username: str, code: str) -> bool:
        """
        Verify TOTP setup by checking a code.
        
        Args:
            username: Username
            code: 6-digit TOTP code
            
        Returns:
            True if code is valid
        """
        if username not in self.secrets:
            return False
        
        totp_secret = self.secrets[username]
        if self.totp_manager.verify(totp_secret.secret, code):
            totp_secret.verified = True
            totp_secret.enabled_at = datetime.utcnow()
            return True
        
        return False
    
    def verify_code(self, username: str, code: str) -> bool:
        """
        Verify a TOTP code for login.
        
        Args:
            username: Username
            code: 6-digit TOTP code
            
        Returns:
            True if code is valid
        """
        if username not in self.secrets:
            return False
        
        totp_secret = self.secrets[username]
        if not totp_secret.verified:
            return False
        
        return self.totp_manager.verify(totp_secret.secret, code)
    
    def use_backup_code(self, username: str, code: str) -> bool:
        """
        Use a backup code for login (when TOTP device is unavailable).
        
        Args:
            username: Username
            code: Backup code
            
        Returns:
            True if backup code is valid and unused
        """
        if username not in self.secrets:
            return False
        
        totp_secret = self.secrets[username]
        
        # Check if code exists and hasn't been used
        if code in totp_secret.backup_codes:
            if not totp_secret.backup_codes[code]:
                totp_secret.backup_codes[code] = True
                return True
        
        return False
    
    def get_totp_secret(self, username: str) -> Optional[TOTPSecret]:
        """Get TOTP secret for user."""
        return self.secrets.get(username)
    
    def disable_2fa(self, username: str) -> bool:
        """
        Disable 2FA for a user.
        
        Args:
            username: Username
            
        Returns:
            True if disabled
        """
        if username in self.secrets:
            del self.secrets[username]
            return True
        return False
    
    def list_users_with_2fa(self) -> List[str]:
        """Get list of usernames with 2FA enabled."""
        return [u for u, s in self.secrets.items() if s.verified]


# Type hints
from typing import Dict
