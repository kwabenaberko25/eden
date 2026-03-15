from typing import Any, Type, Optional
import contextvars

# Global storage for the User model class
_user_model_var: contextvars.ContextVar[Optional[Type[Any]]] = contextvars.ContextVar("user_model", default=None)

def get_user_model() -> Type[Any]:
    """
    Returns the User model class used by the application.
    Defaults to eden.auth.models.User if not explicitly set.
    """
    model = _user_model_var.get()
    if model is None:
        from eden.auth.models import User
        return User
    return model

def set_user_model(model_cls: Type[Any]) -> None:
    """
    Sets the User model class to be used globally.
    """
    _user_model_var.set(model_cls)
