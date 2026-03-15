"""
Eden — Password Reset and Token Utilities
"""

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

def get_serializer(secret_key: str, salt: str = "password-reset") -> URLSafeTimedSerializer:
    """Get the token serializer."""
    return URLSafeTimedSerializer(secret_key, salt=salt)

def generate_password_reset_token(email: str, secret_key: str, salt: str = "password-reset") -> str:
    """
    Generate a time-limited, signed token for password reset.
    """
    serializer = get_serializer(secret_key, salt)
    return serializer.dumps({"email": email})

def verify_password_reset_token(
    token: str, 
    secret_key: str, 
    salt: str = "password-reset", 
    max_age: int = 3600
) -> str | None:
    """
    Verify a password reset token and return the associated email.
    Returns None if the token is invalid or expired.
    """
    serializer = get_serializer(secret_key, salt)
    try:
        data = serializer.loads(token, max_age=max_age)
        return data.get("email")
    except (BadSignature, SignatureExpired):
        return None
