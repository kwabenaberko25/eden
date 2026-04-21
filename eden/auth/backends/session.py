"""
Eden — Session Authentication Backend
"""


from typing import Any
from eden.auth.base import AuthBackend
from eden.auth.models import User
from eden.requests import Request


class SessionBackend(AuthBackend[User]):
    """
    Stateful session-based authentication.
    Requires SessionMiddleware to be enabled.
    """

    SESSION_KEY = "_auth_user_id"

    async def authenticate(self, request: Request) -> User | None:
        """
        Check for a user ID in the session.
        """
        if "session" not in request.scope:
            # SessionMiddleware might not be installed or configured
            return None

        user_id = request.session.get(self.SESSION_KEY)
        if not user_id:
            return None

        # Get database session from app state
        session = getattr(request.app.state, "db", None)
        return await User.get(session=session, id=user_id)

    async def login(self, request: Request, user: Any) -> None:
        """Store user ID in the session and rotate session key to prevent fixation attacks."""
        if "session" in request.scope:
            # Rotate session to prevent fixation attacks
            old_data = dict(request.session)
            request.session.clear()
            request.session.update(old_data)
            # Set user ID in the fresh session
            request.session[self.SESSION_KEY] = str(user.id)

    async def logout(self, request: Request) -> None:
        """
        Remove the user ID from the session.
        """
        if "session" in request.scope:
            request.session.pop(self.SESSION_KEY, None)
