"""
Eden — Auth Providers
"""
from eden.auth.backends.jwt import JWTBackend as JWTProvider

__all__ = ["JWTProvider"]
