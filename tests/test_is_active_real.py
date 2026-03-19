
import pytest
from unittest.mock import Mock
from eden.context import is_active

def test_is_active_route_name():
    request = Mock()
    request.url.path = "/dashboard"
    request.url_for = Mock(return_value="/dashboard")
    
    # Matching dashboard route
    assert is_active(request, "dashboard") == True
    request.url_for.assert_called_with("dashboard")

def test_is_active_route_name_colon():
    request = Mock()
    request.url.path = "/admin/users"
    request.url_for = Mock(return_value="/admin/users")
    
    # Matching admin:users route (normalized to admin_users)
    assert is_active(request, "admin:users") == True
    request.url_for.assert_called_with("admin_users")

def test_is_active_wildcard_exact():
    request = Mock()
    request.url.path = "/admin"
    request.url_for = Mock(return_value="/admin")
    
    # admin:* matches /admin
    assert is_active(request, "admin:*") == True

def test_is_active_wildcard_subpath():
    request = Mock()
    request.url.path = "/admin/users/123"
    request.url_for = Mock(side_effect=lambda name: "/admin" if name == "admin" else "/unknown")
    
    # admin:* matches /admin/users/123
    assert is_active(request, "admin:*") == True

def test_is_active_wildcard_mismatch():
    request = Mock()
    request.url.path = "/dashboard"
    request.url_for = Mock(return_value="/admin")
    
    # admin:* does NOT match /dashboard
    assert is_active(request, "admin:*") == False

def test_is_active_literal_path():
    request = Mock()
    request.url.path = "/about"
    
    # Normal literal path should still work
    assert is_active(request, "/about") == True
    assert is_active(request, "/other") == False

def test_is_active_absolute_url():
    request = Mock()
    request.url.path = "/pricing"
    
    # Absolute URL should resolve to path
    assert is_active(request, "https://example.com/pricing") == True
    assert is_active(request, "https://example.com/other") == False
