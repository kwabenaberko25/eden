from __future__ import annotations
"""
Eden — OAuth Integration

Provides OAuth 2.0 login via Google and GitHub.
Uses httpx for async token exchange and profile fetching.

Usage:
    from eden.auth.oauth import OAuthManager

    oauth = OAuthManager()
    oauth.register_google(client_id="...", client_secret="...")
    oauth.register_github(client_id="...", client_secret="...")
    oauth.mount(app)
"""


import secrets
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urlencode
from sqlalchemy import select

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

from eden.responses import JsonResponse, RedirectResponse


# ── Provider Config ──────────────────────────────────────────────────────

@dataclass
class OAuthProvider:
    """Configuration for a single OAuth provider."""
    name: str
    client_id: str
    client_secret: str
    authorize_url: str = ""
    token_url: str = ""
    userinfo_url: str = ""
    scopes: list[str] = field(default_factory=list)
    # Callback after successful login: async def handler(request, user_info: dict) -> Response
    on_login: Callable[..., Any] | None = None

    async def get_user_info(self, client: httpx.AsyncClient, access_token: str) -> dict:
        """Fetch user profile from provider."""
        resp = await client.get(
            self.userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return resp.json()

class GoogleProvider(OAuthProvider):
    def __init__(self, client_id: str, client_secret: str, scopes: list[str] | None = None, on_login: Callable | None = None):
        super().__init__(
            name="google",
            client_id=client_id,
            client_secret=client_secret,
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://www.googleapis.com/oauth2/v2/userinfo",
            scopes=scopes or ["openid", "email", "profile"],
            on_login=on_login,
        )

class GitHubProvider(OAuthProvider):
    def __init__(self, client_id: str, client_secret: str, scopes: list[str] | None = None, on_login: Callable | None = None):
        super().__init__(
            name="github",
            client_id=client_id,
            client_secret=client_secret,
            authorize_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            userinfo_url="https://api.github.com/user",
            scopes=scopes or ["read:user", "user:email"],
            on_login=on_login,
        )

# ── OAuthManager ─────────────────────────────────────────────────────────

class OAuthManager:
    """
    Manages OAuth providers and mounts login/callback routes.
    """

    def __init__(self) -> None:
        self._providers: dict[str, OAuthProvider] = {}

    def register(self, provider: OAuthProvider) -> None:
        """Register an OAuth provider."""
        self._providers[provider.name] = provider

    def register_google(self, client_id: str, client_secret: str, **kwargs) -> None:
        self.register(GoogleProvider(client_id, client_secret, **kwargs))

    def register_github(self, client_id: str, client_secret: str, **kwargs) -> None:
        self.register(GitHubProvider(client_id, client_secret, **kwargs))

    def mount(self, app: Any, prefix: str = "/auth/oauth") -> None:
        """
        Mount login and callback routes for all registered providers.

        Generates:
            GET  {prefix}/{provider}/login    → Redirect to provider
            GET  {prefix}/{provider}/callback → Exchange code for token
        """
        if httpx is None:
            raise ImportError(
                "httpx is required for OAuth. Install it: pip install httpx"
            )

        # ── Profile Management ───────────────────────────────────────────────
        
        @app.get("/profile", name="profile", tags=["auth"])
        async def profile_view(request):
            """User profile and account management view."""
            if not hasattr(request, "user") or not request.user.is_authenticated:
                return RedirectResponse(url="/auth/login?next=/profile")
            
            from eden.auth.models import SocialAccount
            db = getattr(request.state, "db", None)
            
            # Fetch linked accounts
            stmt = select(SocialAccount).where(SocialAccount.user_id == request.user.id)
            social_accounts = (await db.execute(stmt)).scalars().all()
            
            # Set of provider names for membership check
            linked_providers = {sa.provider for sa in social_accounts}
            
            return app.render("profile.html", {
                "user": request.user,
                "social_accounts": social_accounts,
                "linked_providers": linked_providers,
                "available_providers": self._providers.keys(),
                "message": request.query_params.get("message")
            })

        @app.post(f"{prefix}/unlink/{{provider}}", name="oauth_unlink", tags=["auth"])
        async def unlink_provider(request, provider: str):
            """Unlink an OAuth provider from the current user account."""
            if not hasattr(request, "user") or not request.user.is_authenticated:
                 return RedirectResponse(url="/auth/login")
            
            from eden.auth.models import SocialAccount
            db = getattr(request.state, "db", None)
            
            # We must ensure the user has another way to log in (password or another social account)
            # Fetch all social links
            stmt = select(SocialAccount).where(SocialAccount.user_id == request.user.id)
            all_links = (await db.execute(stmt)).scalars().all()
            
            has_password = bool(getattr(request.user, "password_hash", None))
            
            if len(all_links) <= 1 and not has_password:
                return RedirectResponse(url="/profile?error=Cannot unlink last remaining login method. Please set a password first.")

            # Perform unlinking
            from sqlalchemy import delete
            stmt = delete(SocialAccount).where(
                SocialAccount.user_id == request.user.id,
                SocialAccount.provider == provider
            )
            await db.execute(stmt)
            await db.commit()
            
            return RedirectResponse(url="/profile?message=Account unlinked successfully")

        for provider_name, provider in self._providers.items():
            self._mount_provider(app, prefix, provider)

    def _mount_provider(self, app: Any, prefix: str, provider: OAuthProvider) -> None:
        """Mount login/callback routes for a single provider."""
        p = provider  # capture for closure

        @app.get(
            f"{prefix}/{p.name}/login",
            name=f"oauth_{p.name}_login",
            tags=["auth"],
        )
        async def login(request):
            """Redirect user to OAuth provider login page."""
            # Generate and store state in session for CSRF protection
            state = secrets.token_urlsafe(32)
            request.session["oauth_state"] = state

            callback_url = str(request.url_for(f"oauth_{p.name}_callback"))
            params = {
                "client_id": p.client_id,
                "redirect_uri": callback_url,
                "scope": " ".join(p.scopes),
                "response_type": "code",
                "state": state,
            }
            redirect_url = f"{p.authorize_url}?{urlencode(params)}"
            return RedirectResponse(url=redirect_url)

        @app.get(
            f"{prefix}/{p.name}/callback",
            name=f"oauth_{p.name}_callback",
            tags=["auth"],
        )
        async def callback(request):
            """Handle OAuth callback: exchange code for token and fetch user info."""
            code = request.query_params.get("code")
            state = request.query_params.get("state")

            # Validate state
            session_state = request.session.get("oauth_state")
            if not state or state != session_state:
                return JsonResponse(
                    {"error": "Invalid OAuth state. Possible CSRF attack."},
                    status_code=403,
                )

            # Clean up state
            request.session.pop("oauth_state", None)

            if not code:
                return JsonResponse(
                    {"error": "Missing authorization code."},
                    status_code=400,
                )

            callback_url = str(request.url_for(f"oauth_{p.name}_callback"))

            # Exchange code for access token
            async with httpx.AsyncClient() as client:
                token_data = {
                    "client_id": p.client_id,
                    "client_secret": p.client_secret,
                    "code": code,
                    "redirect_uri": callback_url,
                    "grant_type": "authorization_code",
                }

                headers = {"Accept": "application/json"}
                token_resp = await client.post(
                    p.token_url, data=token_data, headers=headers
                )
                token_json = token_resp.json()

                access_token = token_json.get("access_token")
                if not access_token:
                    return JsonResponse(
                        {"error": "Failed to obtain access token.", "details": token_json},
                        status_code=400,
                    )

                # Fetch user info
                user_resp = await client.get(
                    p.userinfo_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                user_info = user_resp.json()

            # Call the on_login handler if registered
            if p.on_login:
                import inspect
                result = p.on_login(request, user_info)
                if inspect.isawaitable(result):
                    result = await result
                return result

            # Default Eden Logic: Link or Login
            from sqlalchemy import select
            from eden.auth.models import User, SocialAccount

            db = getattr(request.state, "db", None)
            if not db:
                return JsonResponse({"error": "Database session not found."}, status_code=500)

            provider_user_id = str(user_info.get("id") or user_info.get("sub"))
            if not provider_user_id:
                return JsonResponse({"error": "Could not resolve provider user ID."}, status_code=400)

            # 1. Check if we're already logged in (Linking Flow)
            if hasattr(request, "user") and request.user.is_authenticated:
                # Check for existing link
                stmt = select(SocialAccount).where(
                    SocialAccount.provider == p.name,
                    SocialAccount.provider_user_id == provider_user_id
                )
                existing = (await db.execute(stmt)).scalar_one_or_none()
                
                if existing:
                    if existing.user_id != request.user.id:
                        return JsonResponse({"error": "This social account is already linked to another user."}, status_code=400)
                    return RedirectResponse(url="/profile?message=Account already linked")

                # Create new link
                new_link = SocialAccount(
                    user_id=request.user.id,
                    provider=p.name,
                    provider_user_id=provider_user_id,
                    provider_metadata=user_info
                )
                db.add(new_link)
                await db.commit()
                return RedirectResponse(url="/profile?message=Account linked successfully")

            # 2. Login Flow: Find SocialAccount
            stmt = select(SocialAccount).where(
                SocialAccount.provider == p.name,
                SocialAccount.provider_user_id == provider_user_id
            )
            social = (await db.execute(stmt)).scalar_one_or_none()

            if social:
                # Existing user, log them in
                stmt = select(User).where(User.id == social.user_id)
                user = (await db.execute(stmt)).scalar_one_or_none()
                if user:
                    request.session["user_id"] = user.id
                    return RedirectResponse(url="/")
                return JsonResponse({"error": "Linked user not found."}, status_code=404)

            # 3. New User Flow: Create User + SocialAccount
            email = user_info.get("email")
            if not email:
                return JsonResponse({"error": "Email is required from OAuth provider."}, status_code=400)

            # Check for existing user by email
            stmt = select(User).where(User.email == email)
            user = (await db.execute(stmt)).scalar_one_or_none()

            if not user:
                # Create user
                import secrets
                user = User(
                    email=email,
                    full_name=user_info.get("name") or user_info.get("login"),
                    is_active=True
                )
                # Set a random password for social-only users
                user.set_password(secrets.token_urlsafe(32))
                db.add(user)
                await db.flush() # Get ID

            # Link the account
            social = SocialAccount(
                user_id=user.id,
                provider=p.name,
                provider_user_id=provider_user_id,
                provider_metadata=user_info
            )
            db.add(social)
            await db.commit()

            request.session["user_id"] = user.id
            return RedirectResponse(url="/")
