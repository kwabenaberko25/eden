import pytest
import time
from eden.auth.passwords import generate_password_reset_token, verify_password_reset_token

def test_generate_and_verify_token():
    secret_key = "super-secret-key"
    email = "test@example.com"
    
    # Generate token
    token = generate_password_reset_token(email, secret_key)
    assert isinstance(token, str)
    
    # Verify token
    verified_email = verify_password_reset_token(token, secret_key)
    assert verified_email == email

def test_verify_expired_token():
    secret_key = "super-secret-key"
    email = "test@example.com"
    
    token = generate_password_reset_token(email, secret_key)
    
    # Set max_age to negative/0 to force immediate expiration
    verified_email = verify_password_reset_token(token, secret_key, max_age=-1)
    assert verified_email is None

def test_verify_invalid_token():
    secret_key = "super-secret-key"
    
    verified_email = verify_password_reset_token("invalid-token-string", secret_key)
    assert verified_email is None

def test_verify_wrong_secret():
    email = "test@example.com"
    token = generate_password_reset_token(email, "secret-1")
    
    verified_email = verify_password_reset_token(token, "secret-2")
    assert verified_email is None
