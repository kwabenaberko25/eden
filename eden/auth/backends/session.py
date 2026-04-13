"""
Eden — Session Authentication Backend
"""


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
        if not hasattr(request, "session"):
            # SessionMiddleware might not be installed or configured
            return None

        user_id = request.session.get(self.SESSION_KEY)
        if not user_id:
            return None

        # Get database session from app state
        session = getattr(request.app.state, "db", None)
        return await User.get(session, user_id)

    async def login(self, request: Request, user: User) -> None:
        """
        Store the user ID in the session.
        """
        if hasattr(request, "session"):
            request.session[self.SESSION_KEY] = str(user.id)

    async def logout(self, request: Request) -> None:
        """
        Remove the user ID from the session.
        """
        if hasattr(request, "session"):
            request.session.pop(self.SESSION_KEY, None)
