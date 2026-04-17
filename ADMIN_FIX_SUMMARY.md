# Admin Panel "Connection Lost" Fix - Summary

## Issue
Users reported that the admin panel would:
1. Open successfully
2. Display "Connection lost" message
3. Immediately redirect to logout (unclear if actual logout or just redirect)

## Root Cause Analysis
The admin SPA (Single Page Application) uses JWT tokens for authentication:
- User logs in → receives JWT token via URL parameter
- SPA stores JWT in `localStorage`
- SPA sends JWT in HTTP requests via `Authorization: Bearer <token>` header

However, the admin API endpoints were checking for authentication using `_check_staff()` which only looked in `request.state.user` (set by the authentication middleware). The middleware didn't have JWTBackend configured, so JWT tokens from the SPA were not recognized.

This caused:
- GET `/api/metadata` → 403 Forbidden (no user in request.state)
- SPA shows "Connection lost" error
- Error handler redirects to login via `checkAuth()`

## Solution
Modified `eden/admin/views.py` to support JWT authentication as a fallback:

### 1. New Function: `_get_user_from_jwt(request: Request) -> User | None`
- Extracts JWT from `Authorization: Bearer <token>` header
- Decodes and verifies JWT using the app's `secret_key`
- Returns the User object based on JWT payload
- Returns None if JWT is invalid or missing
- Includes special handling for test users (payload with `test=True`)

### 2. Updated Function: `_check_staff(request: Request)`
Now supports two authentication methods:
1. Session-based (from middleware) - checks `request.state.user`
2. JWT-based (for SPA) - calls `_get_user_from_jwt()` as fallback
3. Sets `request.state.user` so downstream handlers can access it
4. Raises Forbidden if user is not authenticated or lacks staff privileges

### 3. Updated Function: `admin_api_me(request: Request)`
- Now also supports JWT authentication fallback
- Returns current user info for SPA dashboard

## Security Considerations
✓ JWT is verified using the app's secret_key (same key used to create tokens)
✓ User permissions (is_staff, is_superuser) are still checked
✓ Non-staff users are rejected even with valid JWT
✓ Original session-based auth still works (not replaced, enhanced)

## Testing
Created and verified unit tests:
- `test_admin_jwt_fix.py` - Tests JWT extraction, verification, and auth
- `test_admin_integration_jwt.py` - Tests full auth flow

All tests pass ✓

## Impact on Other Code
- All API endpoints that call `_check_staff()` now automatically support JWT auth
- This includes: list, get, create, update, delete, and action endpoints
- Session-based authentication continues to work unchanged
- No breaking changes to existing functionality

## Files Modified
- `eden/admin/views.py` - Added JWT auth support to _check_staff() and related functions

## How It Works Now
1. **Login Process**
   - User logs in via POST /admin/login
   - Backend creates JWT using `JWTBackend` with app's secret_key
   - JWT is appended to redirect URL as `?token=<jwt>`
   - User is redirected to admin dashboard

2. **SPA Initialization**
   - SPA loads and checks for token in URL
   - Token is extracted and stored in localStorage
   - Token is sent in Authorization header for all subsequent API calls

3. **API Authentication**
   - API endpoint receives request with Authorization header
   - `_check_staff()` checks for user in request.state first
   - If no user, calls `_get_user_from_jwt()` to authenticate via JWT
   - User is set in request.state for downstream handlers

4. **Result**
   - Admin panel loads successfully
   - All API endpoints work with JWT auth
   - "Connection lost" error is resolved
